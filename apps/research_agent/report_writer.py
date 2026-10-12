import logging
from langchain.agents import create_agent
from apps.research_agent.prompts import ReportWriterAgentPrompt
from apps.research_agent.tools import read_file, write_file, list_files
from apps.research_agent.utils import extract_last_text, get_model

logger = logging.getLogger("research_agent.report_writer")


async def report_writer() -> str:
    logger.info("Compiling final report...")
    model = get_model("report_writer")
    agent = create_agent(
        model=model,
        tools=[list_files, read_file, write_file],
        system_prompt=ReportWriterAgentPrompt,
    )

    result = await agent.ainvoke(
        {
            "messages": [
                (
                    "user",
                    "Compile the final report. Read /research/plan.md, "
                    "/research/tasks.json, and every file in /research/findings/, "
                    "then write /research/report.md.",
                )
            ]
        }
    )
    return extract_last_text(result)
