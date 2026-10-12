import pytest
from uuid import uuid4
from sqlalchemy import select
from apps.db.database import async_session_factory
from apps.db.models import (
    DispatchLog,
    ResearchPlan,
    ResearchReport,
    ResearchSession,
    ResearchStatus,
    ResearchTask,
    TaskStatus,
)


@pytest.mark.asyncio
async def test_research_session_lifecycle_and_relationships():
    async with async_session_factory() as db:
        # 1. Create a session
        session = ResearchSession(
            query="Test query for battery storage",
            status=ResearchStatus.PENDING_APPROVAL,
        )
        db.add(session)
        await db.commit()
        await db.refresh(session)
        session_id = session.id

        assert session.id is not None
        assert session.status == ResearchStatus.PENDING_APPROVAL

        # 2. Add ResearchPlan
        plan = ResearchPlan(
            session_id=session_id,
            title="Battery Plan",
            summary="A test plan for battery research",
            content="# Plan Content\n\n- Angle 1\n- Angle 2",
        )
        db.add(plan)
        await db.commit()

        # 3. Add ResearchTasks
        task1 = ResearchTask(
            session_id=session_id,
            task_key="task-01",
            title="Anode chemistry benchmark",
            angle="Chemistry",
            questions=["What is the energy density?"],
            search_budget=10,
            min_sources=4,
            depends_on=[],
            status=TaskStatus.PENDING,
        )
        task2 = ResearchTask(
            session_id=session_id,
            task_key="task-02",
            title="Manufacturing cost analysis",
            angle="Manufacturing",
            questions=["What is the cost per kWh?"],
            search_budget=12,
            min_sources=5,
            depends_on=["task-01"],
            status=TaskStatus.PENDING,
        )
        db.add_all([task1, task2])
        await db.commit()

        # 4. Add DispatchLog
        log_entry = DispatchLog(
            session_id=session_id,
            task_key="task-01",
            wave=1,
            status="COMPLETED",
            note="Success",
        )
        db.add(log_entry)

        # 5. Add ResearchReport
        report = ResearchReport(
            session_id=session_id,
            content="# Final Battery Report\nExecutive summary...",
            word_count=50,
        )
        db.add(report)

        # 6. Update session status to COMPLETED
        session_stmt = select(ResearchSession).where(ResearchSession.id == session_id)
        res = await db.execute(session_stmt)
        fetched_session = res.scalar_one()
        fetched_session.status = ResearchStatus.COMPLETED
        await db.commit()

    # Query back in a new session and verify eager-loaded relationships
    async with async_session_factory() as db:
        stmt = select(ResearchSession).where(ResearchSession.id == session_id)
        res = await db.execute(stmt)
        queried = res.scalar_one()

        assert queried.status == ResearchStatus.COMPLETED
        assert queried.plan is not None
        assert queried.plan.title == "Battery Plan"
        assert len(queried.tasks) == 2
        assert queried.tasks[0].task_key == "task-01"
        assert queried.tasks[1].depends_on == ["task-01"]
        assert queried.report is not None
        assert queried.report.word_count == 50
        assert len(queried.dispatch_logs) == 1

        # Clean up test data
        await db.delete(queried)
        await db.commit()
