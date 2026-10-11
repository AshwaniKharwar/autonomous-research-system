import json
from langchain.agents import create_agent
from langchain_core.tools import tool
from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv
import os
from apps.research_agent.prompts import DispatcherAgentprompt
from apps.research_agent.tools import list_files, read_file, write_file, BASE_DIR
from apps.research_agent.task_agent import run_task_agent
load_dotenv()


model = ChatGoogleGenerativeAI(
    api_key=os.getenv("GEMINI_API_KEY"),
    model=os.getenv("GEMINI_PLANNER_MODEL"),
)


def _load_task(task_ref: str) -> dict:
    """Accept either a task JSON object or a task id like 'task-01'."""
    task_ref = task_ref.strip()
    if task_ref.startswith("{"):
        return json.loads(task_ref)

    with open(os.path.join(BASE_DIR, "tasks.json")) as f:
        tasks = json.load(f)
    for task in tasks:
        if task["id"] == task_ref:
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
        return f"Error: could not resolve task ({e})"

    print(f"Dispatching {task['id']}: {task['title']}")
    try:
        summary = await run_task_agent(task)
    except Exception as e:
        return f"Error: task {task['id']} failed ({e})"
    return f"{task['id']} -> {task['output_file']}\n{summary}"


async def dispatch_research() -> str:
    print("Dispatching research tasks....")
    agent = create_agent(
        model=model,
        tools=[list_files, read_file, write_file, dispatch_task],
        system_prompt=DispatcherAgentprompt,
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
    return result["messages"][-1].content
