import json
import logging
import os
from langchain.agents import create_agent
from apps.research_agent.prompts import TaskResearcherAgentPrompt
from apps.research_agent.tools import (
    read_file,
    write_file,
    list_files,
    create_directory,
    fetch_page,
    build_search_tool,
    BASE_DIR,
)
from apps.research_agent.utils import extract_last_text, get_model

logger = logging.getLogger("research_agent.task_agent")

DEFAULT_SEARCH_BUDGET = 15


def _dependency_paths(task: dict) -> list[str]:
    depends_on = task.get("depends_on") or []
    if not depends_on:
        return []
    tasks_path = os.path.join(BASE_DIR, "tasks.json")
    if not os.path.exists(tasks_path):
        logger.warning(f"tasks.json not found at {tasks_path} while resolving dependencies for {task.get('id')}")
        return []
    try:
        with open(tasks_path, "r", encoding="utf-8") as f:
            tasks = json.load(f)
        by_id = {t["id"]: t for t in tasks if isinstance(t, dict) and "id" in t}
        return [by_id[dep]["output_file"] for dep in depends_on if dep in by_id and "output_file" in by_id[dep]]
    except Exception as e:
        logger.error(f"Error reading {tasks_path}: {e}")
        return []


async def run_task_agent(task: dict) -> str:
    """Run one self-contained research task and write its findings file."""
    task_id = task.get("id", "unknown-task")
    task_title = task.get("title", "Untitled Task")
    output_file = task.get("output_file", f"/research/findings/{task_id}.md")
    budget = int(task.get("search_budget") or DEFAULT_SEARCH_BUDGET)

    logger.info(f"Running task agent for {task_id}: {task_title} (budget={budget})")
    search_tool = build_search_tool(budget)
    model = get_model("task")

    agent = create_agent(
        model=model,
        tools=[
            list_files,
            read_file,
            write_file,
            create_directory,
            search_tool,
            fetch_page,
        ],
        system_prompt=TaskResearcherAgentPrompt.format(
            task=json.dumps(task, indent=2),
            task_id=task_id,
            task_title=task_title,
            search_budget=budget,
        ),
    )

    message = f"Research task {task_id} and write your findings to {output_file}."
    deps = _dependency_paths(task)
    if deps:
        message += f"\nEarlier findings you may read: {', '.join(deps)}."

    result = await agent.ainvoke(
        {"messages": [("user", message)]},
        config={"recursion_limit": budget * 4 + 25},
    )
    return extract_last_text(result)
