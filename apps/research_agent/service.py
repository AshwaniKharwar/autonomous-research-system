import logging
from typing import Any
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from apps.db.database import async_session_factory
from apps.db.models import (
    ResearchPlan,
    ResearchReport,
    ResearchSession,
    ResearchStatus,
    ResearchTask,
    TaskStatus,
)
from apps.research_agent.dispatcher import dispatch_research_session
from apps.research_agent.planner import research_planner
from apps.research_agent.report_writer import report_writer
from apps.research_agent.task_architect import task_architect

logger = logging.getLogger("research_agent.service")


async def create_research_session(
    query: str,
    db: AsyncSession,
) -> ResearchSession:
    """Phase 1: Create plan & subtasks, persist in Postgres with PENDING_APPROVAL status."""
    logger.info(f"Creating research session for query: '{query}'")

    # 1. Initialize session record
    session = ResearchSession(
        query=query,
        status=ResearchStatus.PENDING_APPROVAL,
    )
    db.add(session)
    await db.flush()  # obtain session.id

    # 2. Generate research plan
    logger.info(f"Generating research plan for session {session.id}...")
    plan_content = await research_planner(query)
    plan = ResearchPlan(
        session_id=session.id,
        title=f"Plan: {query[:100]}",
        summary=f"Research plan for: {query[:200]}",
        content=plan_content,
    )
    db.add(plan)
    await db.flush()

    # 3. Architect subtasks from plan
    logger.info(f"Architecting subtasks for session {session.id}...")
    tasks_data = await task_architect(query, plan_content)

    for t_data in tasks_data:
        task_row = ResearchTask(
            session_id=session.id,
            task_key=t_data["task_key"],
            title=t_data["title"],
            angle=t_data.get("angle"),
            task_type=t_data.get("task_type", "research"),
            context=t_data.get("context"),
            questions=t_data.get("questions", []),
            scope=t_data.get("scope"),
            preferred_sources=t_data.get("preferred_sources", []),
            search_budget=t_data.get("search_budget", 15),
            min_sources=t_data.get("min_sources", 6),
            depends_on=t_data.get("depends_on", []),
            status=TaskStatus.PENDING,
        )
        db.add(task_row)

    await db.commit()
    await db.refresh(session)
    logger.info(f"Session {session.id} created with {len(tasks_data)} tasks. Awaiting user approval.")
    return session


async def execute_research_workflow(session_id: UUID) -> None:
    """Phase 2: Transition status to RUNNING, dispatch tasks wave-by-wave, and compile report."""
    logger.info(f"Starting background execution for session {session_id}...")

    async with async_session_factory() as db:
        try:
            # 1. Fetch and validate session
            stmt = select(ResearchSession).where(ResearchSession.id == session_id)
            result = await db.execute(stmt)
            session = result.scalar_one_or_none()
            if not session:
                logger.error(f"Session {session_id} not found for background execution.")
                return

            if session.status != ResearchStatus.PENDING_APPROVAL:
                logger.warning(
                    f"Session {session_id} is in status '{session.status}', cannot start tasks."
                )
                return

            # 2. Update status to RUNNING
            session.status = ResearchStatus.RUNNING
            await db.commit()
            logger.info(f"Session {session_id} status changed to RUNNING.")

            # 3. Dispatch tasks wave by wave
            all_findings, _ = await dispatch_research_session(session_id, db)

            # 4. Fetch plan and tasks for report compilation
            plan_stmt = select(ResearchPlan).where(ResearchPlan.session_id == session_id)
            plan_res = await db.execute(plan_stmt)
            plan = plan_res.scalar_one_or_none()
            plan_content = plan.content if plan else ""

            tasks_stmt = select(ResearchTask).where(ResearchTask.session_id == session_id)
            tasks_res = await db.execute(tasks_stmt)
            tasks = list(tasks_res.scalars().all())

            task_dicts = [
                {
                    "task_key": t.task_key,
                    "title": t.title,
                    "feeds_report_section": t.angle or "",
                }
                for t in tasks
            ]

            # 5. Compile final report
            logger.info(f"Compiling final report for session {session_id}...")
            report_text = await report_writer(
                query=session.query,
                plan_content=plan_content,
                tasks=task_dicts,
                findings=all_findings,
            )

            # 6. Save report in DB
            report = ResearchReport(
                session_id=session.id,
                content=report_text,
                word_count=len(report_text.split()),
            )
            db.add(report)

            # 7. Mark session COMPLETED
            session.status = ResearchStatus.COMPLETED
            await db.commit()
            logger.info(f"Session {session_id} successfully completed and saved to Postgres.")

        except Exception as e:
            logger.error(f"Execution failed for session {session_id}: {e}", exc_info=True)
            try:
                stmt = select(ResearchSession).where(ResearchSession.id == session_id)
                res = await db.execute(stmt)
                failed_session = res.scalar_one_or_none()
                if failed_session:
                    failed_session.status = ResearchStatus.FAILED
                    await db.commit()
            except Exception as rollback_err:
                logger.error(f"Error updating status to FAILED for session {session_id}: {rollback_err}")


async def get_research_session(
    session_id: UUID,
    db: AsyncSession,
) -> ResearchSession | None:
    """Retrieve full research session details with plan, tasks, logs, and report."""
    stmt = select(ResearchSession).where(ResearchSession.id == session_id)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()
