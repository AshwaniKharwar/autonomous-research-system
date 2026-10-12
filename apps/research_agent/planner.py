import logging
from langchain.agents import create_agent
from apps.research_agent.prompts import PlanRevisionAgentPrompt, PlannerAgentPrompt
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


async def revise_research_plan(query: str, current_plan: str, feedback: str) -> str:
    """Revise an existing research plan based on user feedback."""
    logger.info(f"Revising research plan with feedback: {feedback[:100]}...")
    model = get_model("planner")
    prompt = PlanRevisionAgentPrompt.format(
        USER_QUERY=query,
        CURRENT_PLAN=current_plan,
        FEEDBACK=feedback,
    )
    agent = create_agent(
        model=model,
        tools=[search_web],
        system_prompt=prompt,
    )

    result = await agent.ainvoke({
        "messages": [
            ("user", f"Revise the research plan incorporating the following feedback:\n{feedback}")
        ]
    })
    return extract_last_text(result)
