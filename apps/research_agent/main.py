import asyncio
import logging
from apps.research_agent.planner import research_planner
from apps.research_agent.task_architect import task_architect
from apps.research_agent.dispatcher import dispatch_research
from apps.research_agent.report_writer import report_writer

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("research_agent.main")


async def main(query: str):
    logger.info("Starting end-to-end research workflow...")

    # Step 1: Create research plan
    logger.info("Step 1: Generating research plan...")
    plan_summary = await research_planner(query)
    logger.info(f"Plan summary: {plan_summary}")

    # Step 2: Convert plan into concrete research tasks
    logger.info("Step 2: Architecting research tasks...")
    tasks_summary = await task_architect(query)
    logger.info(f"Tasks summary: {tasks_summary}")

    # Step 3: Dispatch research tasks wave by wave
    logger.info("Step 3: Dispatching research tasks...")
    dispatch_summary = await dispatch_research()
    logger.info(f"Dispatch summary: {dispatch_summary}")

    # Step 4: Compile findings into final report
    logger.info("Step 4: Compiling final report...")
    report = await report_writer()
    print(report)


if __name__ == "__main__":
    query = "How do solid-state batteries differ from lithium-ion, and which companies are closest to mass production?"
    asyncio.run(main(query))