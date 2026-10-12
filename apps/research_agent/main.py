import asyncio
import logging
from apps.db.database import async_session_factory
from apps.research_agent.service import (
    create_research_session,
    execute_research_workflow,
    get_research_session,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("research_agent.main")


async def run_pipeline(query: str):
    logger.info("Starting Research Agent Workflow...")

    # Phase 1: Plan and subtasks creation
    async with async_session_factory() as db:
        session = await create_research_session(query, db)
        session_id = session.id
        logger.info(f"Session {session_id} created with status: {session.status}")
        logger.info(f"Number of subtasks created: {len(session.tasks)}")
        for t in session.tasks:
            logger.info(f"  - [{t.task_key}] {t.title} (depends_on: {t.depends_on})")

    print("\n" + "=" * 60)
    print(f"Research Session ID: {session_id}")
    print(f"Status: PENDING_APPROVAL")
    print(f"Awaiting approval to start task execution.")
    print("=" * 60 + "\n")

    # In API flow, this is triggered via POST /api/v1/research/{session_id}/start
    # Here we simulate starting after approval:
    logger.info(f"Starting execution for session {session_id}...")
    await execute_research_workflow(session_id)

    async with async_session_factory() as db:
        completed = await get_research_session(session_id, db)
        if completed and completed.report:
            print("\n" + "=" * 60)
            print(f"Research Session {session_id} COMPLETED.")
            print(f"Report word count: {completed.report.word_count}")
            print("=" * 60 + "\n")
            print(completed.report.content[:1000] + "\n...")


if __name__ == "__main__":
    query = "How do solid-state batteries differ from lithium-ion, and which companies are closest to mass production?"
    asyncio.run(run_pipeline(query))