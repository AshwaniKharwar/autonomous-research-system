from unittest.mock import AsyncMock, patch
import pytest
from sqlalchemy import select
from apps.db.database import async_session_factory
from apps.db.models import ResearchSession, ResearchStatus, TaskStatus
from apps.research_agent.service import (
    create_research_session,
    delete_research_session,
    execute_research_workflow,
    get_research_session,
    get_research_task,
    get_research_tasks,
    list_research_sessions,
    revise_research_session,
)


@pytest.mark.asyncio
async def test_full_service_postgres_workflow():
    sample_query = "What are the latest breakthroughs in perovskite solar cells?"
    sample_plan = "# Research Plan: Perovskite Solar Cells\n\n## Brief\nGoal: assess commercial viability."
    sample_tasks = [
        {
            "task_key": "task-01",
            "title": "Perovskite Stability and Degradation",
            "angle": "Material Science",
            "task_type": "research",
            "context": "Investigate moisture and thermal degradation.",
            "questions": ["How long do cells last under continuous illumination?"],
            "scope": "2023-2025",
            "preferred_sources": ["Nature Energy"],
            "search_budget": 10,
            "min_sources": 4,
            "depends_on": [],
        },
        {
            "task_key": "task-02",
            "title": "Tandem Silicon-Perovskite Efficiency Benchmarks",
            "angle": "Efficiency",
            "task_type": "research",
            "context": "Assess tandem solar cell efficiency records.",
            "questions": ["What is the record laboratory efficiency?"],
            "scope": "Global",
            "preferred_sources": ["NREL"],
            "search_budget": 10,
            "min_sources": 4,
            "depends_on": ["task-01"],
        },
    ]

    # Phase 1: Planning and subtask creation with agents
    with patch("apps.research_agent.service.research_planner", new_callable=AsyncMock) as mock_plan, \
         patch("apps.research_agent.service.task_architect", new_callable=AsyncMock) as mock_arch:
        mock_plan.return_value = sample_plan
        mock_arch.return_value = sample_tasks

        async with async_session_factory() as db:
            session = await create_research_session(sample_query, db)
            session_id = session.id
            assert session.status == ResearchStatus.PENDING_APPROVAL

    # Verify persisted in PostgreSQL
    async with async_session_factory() as db:
        saved_session = await get_research_session(session_id, db)
        assert saved_session is not None
        assert saved_session.status == ResearchStatus.PENDING_APPROVAL
        assert saved_session.plan.content == sample_plan
        assert len(saved_session.tasks) == 2
        assert saved_session.tasks[0].task_key == "task-01"
        assert saved_session.tasks[0].status == TaskStatus.PENDING
        assert saved_session.tasks[1].depends_on == ["task-01"]

    # Phase 2: Start task execution (approval granted)
    sample_finding_1 = "# task-01 findings\nDegradation is mitigated via self-assembled monolayers."
    sample_finding_2 = "# task-02 findings\nRecord lab efficiency reached 33.9% in tandem configurations."
    sample_report = "# Perovskite Solar Cells Final Report\n\n## Executive Summary\nBreakthroughs have reached 33.9% efficiency..."

    async def mock_run_task(task_data, deps=None):
        if task_data["task_key"] == "task-01":
            return sample_finding_1
        return sample_finding_2

    with patch("apps.research_agent.dispatcher.run_task_agent", side_effect=mock_run_task), \
         patch("apps.research_agent.service.report_writer", new_callable=AsyncMock) as mock_writer:
        mock_writer.return_value = sample_report

        await execute_research_workflow(session_id)

    # Verify execution results in PostgreSQL
    async with async_session_factory() as db:
        completed = await get_research_session(session_id, db)
        assert completed is not None
        assert completed.status == ResearchStatus.COMPLETED
        assert len(completed.tasks) == 2
        assert all(t.status == TaskStatus.COMPLETED for t in completed.tasks)
        assert completed.tasks[0].findings == sample_finding_1
        assert completed.tasks[1].findings == sample_finding_2
        assert completed.report is not None
        assert completed.report.content == sample_report
        assert len(completed.dispatch_logs) == 2

        # Clean up test session
        await db.delete(completed)
        await db.commit()


@pytest.mark.asyncio
async def test_service_plan_revision_and_task_queries():
    sample_query = "What is quantum dot display technology?"
    initial_plan = "# Plan 1\nQuantum dots..."
    initial_tasks = [
        {
            "task_key": "task-01",
            "title": "Quantum Dot Synthesis",
            "angle": "Synthesis",
            "questions": ["How are quantum dots synthesized?"],
            "depends_on": [],
        }
    ]

    with patch("apps.research_agent.service.research_planner", new_callable=AsyncMock) as mock_plan, \
         patch("apps.research_agent.service.task_architect", new_callable=AsyncMock) as mock_arch:
        mock_plan.return_value = initial_plan
        mock_arch.return_value = initial_tasks

        async with async_session_factory() as db:
            session = await create_research_session(sample_query, db)
            session_id = session.id

    revised_plan = "# Revised Plan\nQD-OLED vs Micro-LED..."
    revised_tasks = [
        {
            "task_key": "task-01",
            "title": "QD-OLED Manufacturing",
            "angle": "Manufacturing",
            "questions": ["How are QD-OLED panels manufactured?"],
            "depends_on": [],
        },
        {
            "task_key": "task-02",
            "title": "Micro-LED Comparison",
            "angle": "Comparison",
            "questions": ["How does Micro-LED compare?"],
            "depends_on": ["task-01"],
        },
    ]

    # Test Plan Revision
    with patch("apps.research_agent.service.revise_research_plan", new_callable=AsyncMock) as mock_rev_plan, \
         patch("apps.research_agent.service.task_architect", new_callable=AsyncMock) as mock_rev_arch:
        mock_rev_plan.return_value = revised_plan
        mock_rev_arch.return_value = revised_tasks

        async with async_session_factory() as db:
            revised_session = await revise_research_session(
                session_id=session_id,
                feedback="Compare with Micro-LED as well.",
                db=db,
            )
            assert revised_session.plan.content == revised_plan
            assert len(revised_session.tasks) == 2
            assert revised_session.tasks[1].task_key == "task-02"

    # Test Task Listing & Single Task Lookup
    async with async_session_factory() as db:
        tasks = await get_research_tasks(session_id, db)
        assert len(tasks) == 2
        assert tasks[0].task_key == "task-01"

        single_task = await get_research_task(session_id, "task-02", db)
        assert single_task is not None
        assert single_task.title == "Micro-LED Comparison"

        single_task_by_uuid = await get_research_task(session_id, str(single_task.id), db)
        assert single_task_by_uuid is not None
        assert single_task_by_uuid.task_key == "task-02"

        # Test Listing sessions
        sessions = await list_research_sessions(db, status=ResearchStatus.PENDING_APPROVAL)
        assert any(s.id == session_id for s in sessions)

        # Test Deletion
        deleted = await delete_research_session(session_id, db)
        assert deleted is True

        queried_after = await get_research_session(session_id, db)
        assert queried_after is None


@pytest.mark.asyncio
async def test_execute_research_workflow_when_already_running():
    query = "Test already running workflow"
    async with async_session_factory() as db:
        session = ResearchSession(
            query=query,
            status=ResearchStatus.RUNNING,
        )
        db.add(session)
        await db.commit()
        await db.refresh(session)
        session_id = session.id

    with patch("apps.research_agent.service.dispatch_research_session", new_callable=AsyncMock) as mock_dispatch, \
         patch("apps.research_agent.service.report_writer", new_callable=AsyncMock) as mock_writer:
        mock_dispatch.return_value = ([], [])
        mock_writer.return_value = "# Report"

        await execute_research_workflow(session_id)
        assert mock_dispatch.called

    async with async_session_factory() as db:
        final_session = await get_research_session(session_id, db)
        assert final_session.status == ResearchStatus.COMPLETED
        await db.delete(final_session)
        await db.commit()


@pytest.mark.asyncio
async def test_execute_research_workflow_rejects_completed_status():
    query = "Test completed status workflow"
    async with async_session_factory() as db:
        session = ResearchSession(
            query=query,
            status=ResearchStatus.COMPLETED,
        )
        db.add(session)
        await db.commit()
        await db.refresh(session)
        session_id = session.id

    with patch("apps.research_agent.service.dispatch_research_session", new_callable=AsyncMock) as mock_dispatch:
        await execute_research_workflow(session_id)
        assert not mock_dispatch.called

    async with async_session_factory() as db:
        final_session = await get_research_session(session_id, db)
        assert final_session.status == ResearchStatus.COMPLETED
        await db.delete(final_session)
        await db.commit()

