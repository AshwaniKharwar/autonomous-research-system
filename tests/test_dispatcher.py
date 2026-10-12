from unittest.mock import AsyncMock, patch
from uuid import uuid4
import pytest
from sqlalchemy import select
from apps.db.database import async_session_factory
from apps.db.models import (
    DispatchLog,
    ResearchSession,
    ResearchStatus,
    ResearchTask,
    TaskStatus,
)
from apps.research_agent.dispatcher import compute_task_waves, dispatch_research_session


def test_compute_task_waves():
    tasks = [
        {"task_key": "t1", "depends_on": []},
        {"task_key": "t2", "depends_on": []},
        {"task_key": "t3", "depends_on": ["t1"]},
        {"task_key": "t4", "depends_on": ["t1", "t2"]},
        {"task_key": "t5", "depends_on": ["t3", "t4"]},
    ]
    waves = compute_task_waves(tasks)
    assert len(waves) == 3
    # Wave 1 has t1, t2
    w1_keys = {t["task_key"] for t in waves[0]}
    assert w1_keys == {"t1", "t2"}
    # Wave 2 has t3, t4
    w2_keys = {t["task_key"] for t in waves[1]}
    assert w2_keys == {"t3", "t4"}
    # Wave 3 has t5
    w3_keys = {t["task_key"] for t in waves[2]}
    assert w3_keys == {"t5"}


@pytest.mark.asyncio
async def test_concurrent_wave_execution_multiple_parallel_tasks():
    """Verify that multiple parallel tasks in the same wave do not crash due to concurrent session usage."""
    async with async_session_factory() as db:
        session = ResearchSession(
            query="Concurrent wave test session",
            status=ResearchStatus.RUNNING,
        )
        db.add(session)
        await db.commit()
        await db.refresh(session)
        session_id = session.id

        # 3 tasks in the exact same wave (no dependencies)
        for i in range(1, 4):
            task = ResearchTask(
                session_id=session_id,
                task_key=f"task-0{i}",
                title=f"Parallel Task {i}",
                angle="Concurrency Test",
                questions=[f"Question {i}"],
                search_budget=5,
                min_sources=2,
                depends_on=[],
                status=TaskStatus.PENDING,
            )
            db.add(task)
        await db.commit()

    async def mock_run_agent(task_data, dep_findings):
        # Simulate slight async delay to ensure coroutines overlap
        import asyncio
        await asyncio.sleep(0.05)
        return f"Findings for {task_data['task_key']}"

    with patch("apps.research_agent.dispatcher.run_task_agent", side_effect=mock_run_agent):
        findings, logs = await dispatch_research_session(session_id)

    assert len(findings) == 3
    assert len(logs) == 3
    assert "task-01" in findings
    assert "task-02" in findings
    assert "task-03" in findings

    # Verify database updates
    async with async_session_factory() as db:
        stmt = select(ResearchTask).where(ResearchTask.session_id == session_id)
        res = await db.execute(stmt)
        tasks = list(res.scalars().all())
        assert len(tasks) == 3
        for t in tasks:
            assert t.status == TaskStatus.COMPLETED
            assert t.wave == 1
            assert t.findings == f"Findings for {t.task_key}"

        log_stmt = select(DispatchLog).where(DispatchLog.session_id == session_id)
        log_res = await db.execute(log_stmt)
        dispatch_logs = list(log_res.scalars().all())
        assert len(dispatch_logs) == 3
        assert all(l.status == "COMPLETED" for l in dispatch_logs)


@pytest.mark.asyncio
async def test_dependent_task_fails_when_upstream_dependency_fails():
    """Verify that a task whose dependency failed is marked FAILED without executing run_task_agent."""
    async with async_session_factory() as db:
        session = ResearchSession(
            query="Dependency failure test session",
            status=ResearchStatus.RUNNING,
        )
        db.add(session)
        await db.commit()
        await db.refresh(session)
        session_id = session.id

        task1 = ResearchTask(
            session_id=session_id,
            task_key="task-01",
            title="Prerequisite Task",
            angle="Dependency Test",
            questions=["Question 1"],
            search_budget=5,
            min_sources=2,
            depends_on=[],
            status=TaskStatus.PENDING,
        )
        task2 = ResearchTask(
            session_id=session_id,
            task_key="task-02",
            title="Dependent Task",
            angle="Dependency Test",
            questions=["Question 2"],
            search_budget=5,
            min_sources=2,
            depends_on=["task-01"],
            status=TaskStatus.PENDING,
        )
        db.add_all([task1, task2])
        await db.commit()

    mock_agent = AsyncMock()
    mock_agent.side_effect = RuntimeError("Simulated API failure in task-01")

    with patch("apps.research_agent.dispatcher.run_task_agent", mock_agent):
        findings, logs = await dispatch_research_session(session_id)

    # task-01 ran and failed; task-02 was skipped because task-01 was incomplete
    assert "task-01" not in findings
    assert "task-02" not in findings
    # mock_agent should only have been called ONCE (for task-01), NOT for task-02!
    assert mock_agent.call_count == 1

    async with async_session_factory() as db:
        stmt = select(ResearchTask).where(ResearchTask.session_id == session_id).order_by(ResearchTask.task_key)
        res = await db.execute(stmt)
        tasks = list(res.scalars().all())
        assert len(tasks) == 2
        assert tasks[0].task_key == "task-01"
        assert tasks[0].status == TaskStatus.FAILED
        assert tasks[1].task_key == "task-02"
        assert tasks[1].status == TaskStatus.FAILED

        log_stmt = select(DispatchLog).where(DispatchLog.session_id == session_id).order_by(DispatchLog.task_key)
        log_res = await db.execute(log_stmt)
        dispatch_logs = list(log_res.scalars().all())
        assert len(dispatch_logs) == 2
        assert dispatch_logs[0].status == "FAILED"
        assert "Simulated API failure" in dispatch_logs[0].note
        assert dispatch_logs[1].status == "FAILED"
        assert "Dependency 'task-01' failed or not completed" in dispatch_logs[1].note
