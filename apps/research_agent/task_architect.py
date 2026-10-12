import json
import logging
import re
from typing import Any
from langchain.agents import create_agent
from apps.research_agent.prompts import TaskArchitectAgentPrompt
from apps.research_agent.utils import extract_last_text, get_model

logger = logging.getLogger("research_agent.task_architect")


def _extract_json_array(text: str) -> list[dict[str, Any]]:
    """Robustly parse a JSON array of task objects from model text."""
    text = text.strip()

    # Try 1: Markdown code block
    match = re.search(r"```(?:json)?\s*(\[\s*\{.*\}\s*\])\s*```", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass

    # Try 2: First '[' to last ']'
    start = text.find("[")
    end = text.rfind("]")
    if start != -1 and end != -1 and end > start:
        try:
            parsed = json.loads(text[start : end + 1])
            if isinstance(parsed, list):
                return parsed
        except json.JSONDecodeError:
            pass

    # Try 3: Direct JSON loads
    try:
        parsed = json.loads(text)
        if isinstance(parsed, list):
            return parsed
    except json.JSONDecodeError:
        pass

    raise ValueError(f"Failed to extract valid JSON task array from model output: {text[:200]}...")


async def task_architect(query: str, plan_content: str) -> list[dict[str, Any]]:
    """Convert research query and plan content into a structured list of tasks."""
    logger.info("Architecting research tasks from plan...")
    model = get_model("architect")
    
    prompt = TaskArchitectAgentPrompt.format(
        query=query,
        plan_content=plan_content,
    )

    agent = create_agent(
        model=model,
        tools=[],
        system_prompt=prompt,
    )

    result = await agent.ainvoke({
        "messages": [
            ("user", "Analyze the research plan and return the JSON array of research tasks.")
        ]
    })
    
    raw_output = extract_last_text(result)
    tasks = _extract_json_array(raw_output)
    
    # Normalize fields
    cleaned_tasks = []
    for i, t in enumerate(tasks, 1):
        if not isinstance(t, dict):
            continue
        task_id = t.get("id") or f"task-{i:02d}"
        cleaned_tasks.append({
            "task_key": task_id,
            "title": t.get("title", f"Research Task {i}"),
            "angle": t.get("angle", ""),
            "task_type": t.get("type", "research"),
            "context": t.get("context", ""),
            "questions": t.get("questions") or [],
            "scope": t.get("scope", ""),
            "preferred_sources": t.get("preferred_sources") or [],
            "search_budget": int(t.get("search_budget") or 15),
            "min_sources": int(t.get("min_sources") or 6),
            "depends_on": t.get("depends_on") or [],
            "feeds_report_section": t.get("feeds_report_section", ""),
        })

    logger.info(f"Architected {len(cleaned_tasks)} tasks successfully.")
    return cleaned_tasks
