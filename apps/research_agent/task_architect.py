import json
import logging
import re
from typing import Any
from langchain.agents import create_agent
from pydantic import BaseModel, Field, model_validator
from apps.research_agent.prompts import TaskArchitectAgentPrompt
from apps.research_agent.utils import extract_last_text, get_model

logger = logging.getLogger("research_agent.task_architect")


class ResearchTaskSpec(BaseModel):
    id: str = Field(default="", description="Task identifier, e.g. 'task-01'")
    title: str = Field(default="", description="Descriptive title of the research task")
    angle: str = Field(default="", description="Research angle or dimension this task investigates")
    type: str = Field(default="research", description="Task type, e.g. 'research' or 'synthesis'")
    context: str = Field(default="", description="Context and background needed for the researcher")
    questions: list[str] = Field(default_factory=list, description="3-5 specific questions to answer")
    scope: str = Field(default="", description="Scope boundaries of the research task")
    preferred_sources: list[str] = Field(default_factory=list, description="Preferred source types or domains")
    search_budget: int = Field(default=15, description="Search budget limit (max web searches)")
    min_sources: int = Field(default=6, description="Minimum number of sources to collect")
    depends_on: list[str] = Field(default_factory=list, description="Task IDs this task depends on")
    feeds_report_section: str = Field(default="", description="Section of the final report this task informs")

    @model_validator(mode="before")
    @classmethod
    def normalize_fields(cls, data: Any) -> Any:
        if isinstance(data, dict):
            for k in ["preferred_sources", "depends_on", "questions"]:
                if k in data and data[k] is None:
                    data[k] = []
            for k in ["feeds_report_section", "type", "context", "scope", "angle", "id", "title"]:
                if k in data and data[k] is None:
                    data[k] = "research" if k == "type" else ""
            if "search_budget" in data and data["search_budget"] is None:
                data["search_budget"] = 15
            if "min_sources" in data and data["min_sources"] is None:
                data["min_sources"] = 6
        return data


class TaskListSpec(BaseModel):
    tasks: list[ResearchTaskSpec] = Field(
        default_factory=list,
        description="Structured list of concrete research tasks architected from the research plan."
    )

    @model_validator(mode="before")
    @classmethod
    def handle_none(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "tasks" in data and data["tasks"] is None:
                data["tasks"] = []
        return data


def _extract_json_array(text: str) -> list[dict[str, Any]]:
    """Robustly parse a JSON array of task objects from model text."""
    text = text.strip()

    # Try 1: Markdown code block containing JSON array or object with tasks
    match = re.search(r"```(?:json)?\s*(\{.*?\}|\[.*?\])\s*```", text, re.DOTALL)
    if match:
        try:
            parsed = json.loads(match.group(1))
            if isinstance(parsed, list):
                return parsed
            if isinstance(parsed, dict) and isinstance(parsed.get("tasks"), list):
                return parsed["tasks"]
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
        if isinstance(parsed, dict) and isinstance(parsed.get("tasks"), list):
            return parsed["tasks"]
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

    tasks_raw: list[Any] = []

    # Attempt 1: Try structured output with TaskListSpec
    if hasattr(model, "with_structured_output"):
        try:
            structured_model = model.with_structured_output(TaskListSpec)
            structured_result = await structured_model.ainvoke([
                ("system", prompt),
                ("user", "Analyze the research plan and return the structured research tasks."),
            ])
            if isinstance(structured_result, TaskListSpec):
                tasks_raw = structured_result.tasks
            elif isinstance(structured_result, dict):
                tasks_raw = structured_result.get("tasks", [])
            elif isinstance(structured_result, list):
                tasks_raw = structured_result
            else:
                logger.warning(
                    f"Unexpected structured output result type: {type(structured_result)}"
                )
        except Exception as exc:
            logger.warning(
                f"Structured output failed with error: {exc}. Falling back to standard agent extraction."
            )

    # Attempt 2: Fallback to agent + _extract_json_array if structured output yielded nothing
    if not tasks_raw:
        logger.info("Structured output yielded no tasks; falling back to agent / JSON array extraction...")
        try:
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
            tasks_raw = _extract_json_array(raw_output)
        except Exception as exc:
            logger.error(f"Fallback extraction also failed: {exc}")
            raise

    # Normalize fields to match service.py expectations
    cleaned_tasks: list[dict[str, Any]] = []
    for i, t in enumerate(tasks_raw, 1):
        if isinstance(t, ResearchTaskSpec):
            task_id = t.id or f"task-{i:02d}"
            title = t.title or f"Research Task {i}"
            angle = t.angle or ""
            task_type = t.type or "research"
            context = t.context or ""
            questions = list(t.questions) if t.questions else []
            scope = t.scope or ""
            preferred_sources = list(t.preferred_sources) if t.preferred_sources else []
            search_budget = int(t.search_budget or 15)
            min_sources = int(t.min_sources or 6)
            depends_on = list(t.depends_on) if t.depends_on else []
            feeds_report_section = t.feeds_report_section or ""
        elif isinstance(t, dict):
            try:
                spec = ResearchTaskSpec.model_validate(t)
                task_id = spec.id or f"task-{i:02d}"
                title = spec.title or f"Research Task {i}"
                angle = spec.angle or ""
                task_type = spec.type or "research"
                context = spec.context or ""
                questions = list(spec.questions) if spec.questions else []
                scope = spec.scope or ""
                preferred_sources = list(spec.preferred_sources) if spec.preferred_sources else []
                search_budget = int(spec.search_budget or 15)
                min_sources = int(spec.min_sources or 6)
                depends_on = list(spec.depends_on) if spec.depends_on else []
                feeds_report_section = spec.feeds_report_section or ""
            except Exception:
                task_id = str(t.get("id") or f"task-{i:02d}")
                title = str(t.get("title") or f"Research Task {i}")
                angle = str(t.get("angle") or "")
                task_type = str(t.get("type") or "research")
                context = str(t.get("context") or "")
                questions = t.get("questions") if isinstance(t.get("questions"), list) else []
                scope = str(t.get("scope") or "")
                preferred_sources = (
                    t.get("preferred_sources")
                    if isinstance(t.get("preferred_sources"), list)
                    else []
                )
                search_budget = int(t.get("search_budget") or 15)
                min_sources = int(t.get("min_sources") or 6)
                depends_on = (
                    t.get("depends_on")
                    if isinstance(t.get("depends_on"), list)
                    else []
                )
                feeds_report_section = str(t.get("feeds_report_section") or "")
        else:
            continue

        cleaned_tasks.append({
            "task_key": task_id,
            "title": title,
            "angle": angle,
            "task_type": task_type,
            "context": context,
            "questions": questions,
            "scope": scope,
            "preferred_sources": preferred_sources,
            "search_budget": search_budget,
            "min_sources": min_sources,
            "depends_on": depends_on,
            "feeds_report_section": feeds_report_section,
        })

    logger.info(f"Architected {len(cleaned_tasks)} tasks successfully.")
    return cleaned_tasks


__all__ = [
    "ResearchTaskSpec",
    "TaskListSpec",
    "_extract_json_array",
    "task_architect",
]
