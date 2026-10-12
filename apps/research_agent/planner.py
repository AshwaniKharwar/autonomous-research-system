import logging
from langchain.agents import create_agent
from apps.research_agent.prompts import PlannerAgentPrompt
from apps.research_agent.tools import search_web
from apps.research_agent.utils import extract_last_text, get_model

logger = logging.getLogger("research_agent.planner")


async def research_planner(query: str) -> str:
    """Generate a structured research plan for the query in markdown."""
    logger.info("Starting research plan generation...")
    model = get_model("planner")
    agent = create_agent(
        model=model,
        tools=[search_web],
        system_prompt=PlannerAgentPrompt.format(USER_QUERY=query),
    )

    result = await agent.ainvoke({
        "messages": [
            ("user", f"Create a comprehensive research plan for the query: {query}")
        ]
    })
    return extract_last_text(result)
