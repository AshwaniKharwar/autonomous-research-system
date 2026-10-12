import json
import logging
from typing import Any
from langchain.agents import create_agent
from apps.research_agent.prompts import TaskResearcherAgentPrompt
from apps.research_agent.tools import build_search_tool, fetch_page
from apps.research_agent.utils import extract_last_text, get_model

logger = logging.getLogger("research_agent.task_agent")

DEFAULT_SEARCH_BUDGET = 15


async def run_task_agent(
    task: dict[str, Any],
    dependency_findings: dict[str, str] | None = None,
) -> str:
    """Run one research task using web research tools and return findings markdown."""
    task_id = task.get("task_key") or task.get("id") or "unknown-task"
    task_title = task.get("title", "Untitled Task")
    budget = int(task.get("search_budget") or DEFAULT_SEARCH_BUDGET)

    logger.info(f"Running task agent for {task_id}: '{task_title}' (budget={budget})")
    search_tool = build_search_tool(budget)
    model = get_model("task")

    dep_section = ""
    if dependency_findings:
        dep_texts = []
        for dep_id, finding in dependency_findings.items():
            dep_texts.append(f"### Previous Findings from {dep_id}:\n{finding}")
        dep_section = "Earlier task findings you must build upon:\n" + "\n\n".join(dep_texts)

    prompt = TaskResearcherAgentPrompt.format(
        task=json.dumps(task, indent=2),
        task_id=task_id,
        task_title=task_title,
        search_budget=budget,
        dependency_findings_section=dep_section,
    )

    agent = create_agent(
        model=model,
        tools=[search_tool, fetch_page],
        system_prompt=prompt,
    )

    message = (
        f"Research task {task_id} ('{task_title}') according to its scope, "
        "questions, and budget. Output your complete findings."
    )

    result = await agent.ainvoke(
        {"messages": [("user", message)]},
        config={"recursion_limit": budget * 4 + 25},
    )
    return extract_last_text(result)
