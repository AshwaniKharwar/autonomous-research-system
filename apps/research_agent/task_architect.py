import logging
from langchain.agents import create_agent
from apps.research_agent.prompts import TaskArchitectAgentPrompt
from apps.research_agent.tools import read_file, write_file, create_directory, list_files, search_web
from apps.research_agent.utils import extract_last_text, get_model

logger = logging.getLogger("research_agent.task_architect")


async def task_architect(query: str) -> str:
    logger.info("Creating research tasks...")
    model = get_model("architect")
    agent = create_agent(
        model=model,
        tools=[list_files, write_file, read_file, create_directory, search_web],
        system_prompt=TaskArchitectAgentPrompt,
    )

    result = await agent.ainvoke({
        "messages": [
            ("user", query)
        ]
    })
    return extract_last_text(result)
