import json
from langchain.agents import create_agent
from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv
import os
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
load_dotenv()


DEFAULT_SEARCH_BUDGET = 15


model = ChatGoogleGenerativeAI(
    api_key=os.getenv("GEMINI_API_KEY"),
    model=os.getenv("GEMINI_PLANNER_MODEL"),
)


def _last_text(result: dict) -> str:
    content = result["messages"][-1].content
    if isinstance(content, list):
        return "\n".join(
            block.get("text", "") if isinstance(block, dict) else str(block)
            for block in content
        )
    return content


def _dependency_paths(task: dict) -> list[str]:
    depends_on = task.get("depends_on") or []
    if not depends_on:
        return []
    with open(os.path.join(BASE_DIR, "tasks.json")) as f:
        tasks = json.load(f)
    by_id = {t["id"]: t for t in tasks}
    return [by_id[dep]["output_file"] for dep in depends_on if dep in by_id]


async def run_task_agent(task: dict) -> str:
    """Run one self-contained research task and write its findings file."""
    budget = int(task.get("search_budget") or DEFAULT_SEARCH_BUDGET)
    search_tool = build_search_tool(budget)

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
            task_id=task["id"],
            task_title=task["title"],
            search_budget=budget,
        ),
    )

    message = (
        f"Research task {task['id']} and write your findings to {task['output_file']}."
    )
    deps = _dependency_paths(task)
    if deps:
        message += f"\nEarlier findings you may read: {', '.join(deps)}."

    result = await agent.ainvoke(
        {"messages": [("user", message)]},
        config={"recursion_limit": budget * 4 + 25},
    )
    return _last_text(result)
