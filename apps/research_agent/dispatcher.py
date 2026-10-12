import json
import logging
import os
from langchain.agents import create_agent
from langchain_core.tools import tool
from apps.research_agent.prompts import DispatcherAgentPrompt
from apps.research_agent.tools import list_files, read_file, write_file, BASE_DIR
from apps.research_agent.task_agent import run_task_agent
from apps.research_agent.utils import extract_last_text, get_model

logger = logging.getLogger("research_agent.dispatcher")


def _load_task(task_ref: str) -> dict:
    """Accept either a task JSON object or a task id like 'task-01'."""
    task_ref = task_ref.strip()
    if task_ref.startswith("{"):
        return json.loads(task_ref)

    tasks_path = os.path.join(BASE_DIR, "tasks.json")
    if not os.path.exists(tasks_path):
        raise FileNotFoundError(f"tasks.json does not exist at {tasks_path}. Ensure task architect has executed.")

    with open(tasks_path, "r", encoding="utf-8") as f:
        tasks = json.load(f)
    for task in tasks:
        if isinstance(task, dict) and task.get("id") == task_ref:
            return task
    raise ValueError(f"Unknown task: {task_ref}")


@tool
async def dispatch_task(task_ref: str) -> str:
    """Launch a Task Research Agent for ONE task.

    Pass task_ref as the task's exact JSON object (preferred) or just its id,
    for example 'task-01'. Returns the researcher's summary and output path.
    """
    try:
        task = _load_task(task_ref)
    except Exception as e:
        logger.error(f"Could not resolve task {task_ref}: {e}")
        return f"Error: could not resolve task ({e})"

    logger.info(f"Dispatching task {task.get('id')}: {task.get('title')}")
    try:
        summary = await run_task_agent(task)
    except Exception as e:
        logger.error(f"Task {task.get('id')} failed: {e}")
        return f"Error: task {task.get('id')} failed ({e})"
    return f"{task.get('id')} -> {task.get('output_file')}\n{summary}"


async def dispatch_research() -> str:
    logger.info("Dispatching research tasks...")
    model = get_model("dispatcher")
    agent = create_agent(
        model=model,
        tools=[list_files, read_file, write_file, dispatch_task],
        system_prompt=DispatcherAgentPrompt,
    )

    result = await agent.ainvoke(
        {
            "messages": [
                (
                    "user",
                    "Read /research/tasks.json and dispatch every task, wave by wave.",
                )
            ]
        }
    )
    return extract_last_text(result)
