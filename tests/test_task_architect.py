import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from apps.research_agent.task_architect import (
    ResearchTaskSpec,
    TaskListSpec,
    _extract_json_array,
    task_architect,
)


def test_research_task_spec_defaults():
    spec = ResearchTaskSpec(
        id="task-01",
        title="Sample Task",
        angle="Technical Angle",
        context="Sample Context",
        questions=["Q1", "Q2"],
        scope="2024-2025",
    )
    assert spec.id == "task-01"
    assert spec.title == "Sample Task"
    assert spec.angle == "Technical Angle"
    assert spec.type == "research"
    assert spec.context == "Sample Context"
    assert spec.questions == ["Q1", "Q2"]
    assert spec.scope == "2024-2025"
    assert spec.preferred_sources == []
    assert spec.search_budget == 15
    assert spec.min_sources == 6
    assert spec.depends_on == []
    assert spec.feeds_report_section == ""


def test_research_task_spec_coercion_of_nones():
    data = {
        "id": "task-02",
        "title": "Task with Nones",
        "angle": None,
        "type": None,
        "context": None,
        "questions": None,
        "scope": None,
        "preferred_sources": None,
        "search_budget": None,
        "min_sources": None,
        "depends_on": None,
        "feeds_report_section": None,
    }
    spec = ResearchTaskSpec.model_validate(data)
    assert spec.id == "task-02"
    assert spec.title == "Task with Nones"
    assert spec.angle == ""
    assert spec.type == "research"
    assert spec.context == ""
    assert spec.questions == []
    assert spec.scope == ""
    assert spec.preferred_sources == []
    assert spec.search_budget == 15
    assert spec.min_sources == 6
    assert spec.depends_on == []
    assert spec.feeds_report_section == ""


def test_task_list_spec():
    task1 = ResearchTaskSpec(id="task-01", title="Task 1")
    task2 = ResearchTaskSpec(id="task-02", title="Task 2")
    spec_list = TaskListSpec(tasks=[task1, task2])

    assert len(spec_list.tasks) == 2
    assert spec_list.tasks[0].id == "task-01"
    assert spec_list.tasks[1].title == "Task 2"

    # None handling
    empty_list = TaskListSpec.model_validate({"tasks": None})
    assert empty_list.tasks == []


def test_extract_json_array_markdown_block():
    text = """Here are the tasks:
```json
[
  {
    "id": "task-01",
    "title": "First Task",
    "angle": "Architecture",
    "type": "research",
    "context": "Context",
    "questions": ["Q1"],
    "scope": "Global",
    "preferred_sources": ["Source A"],
    "search_budget": 12,
    "min_sources": 5,
    "depends_on": [],
    "feeds_report_section": "Sec 1"
  }
]
```
Hope this helps!"""
    result = _extract_json_array(text)
    assert len(result) == 1
    assert result[0]["id"] == "task-01"
    assert result[0]["title"] == "First Task"


def test_extract_json_array_object_with_tasks():
    text = """```json
{
  "tasks": [
    {
      "id": "task-01",
      "title": "Wrapped in object"
    }
  ]
}
```"""
    result = _extract_json_array(text)
    assert len(result) == 1
    assert result[0]["id"] == "task-01"


def test_extract_json_array_raw_brackets():
    text = 'Some preamble [{"id": "task-03", "title": "Bracket Task"}] some postscript'
    result = _extract_json_array(text)
    assert len(result) == 1
    assert result[0]["id"] == "task-03"


def test_extract_json_array_invalid():
    with pytest.raises(ValueError, match="Failed to extract valid JSON task array"):
        _extract_json_array("Invalid text with no JSON arrays or objects")


@pytest.mark.asyncio
async def test_task_architect_with_structured_output():
    task1 = ResearchTaskSpec(
        id="task-01",
        title="Structured Task 1",
        angle="Angle 1",
        type="research",
        context="Context 1",
        questions=["Q1"],
        scope="Scope 1",
        preferred_sources=["Source 1"],
        search_budget=10,
        min_sources=4,
        depends_on=[],
        feeds_report_section="Section 1",
    )
    task_list = TaskListSpec(tasks=[task1])

    mock_structured_model = MagicMock()
    mock_structured_model.ainvoke = AsyncMock(return_value=task_list)

    mock_base_model = MagicMock()
    mock_base_model.with_structured_output.return_value = mock_structured_model

    with patch("apps.research_agent.task_architect.get_model", return_value=mock_base_model):
        results = await task_architect("query", "plan")

    assert len(results) == 1
    t = results[0]
    assert t["task_key"] == "task-01"
    assert t["title"] == "Structured Task 1"
    assert t["angle"] == "Angle 1"
    assert t["task_type"] == "research"
    assert t["context"] == "Context 1"
    assert t["questions"] == ["Q1"]
    assert t["scope"] == "Scope 1"
    assert t["preferred_sources"] == ["Source 1"]
    assert t["search_budget"] == 10
    assert t["min_sources"] == 4
    assert t["depends_on"] == []
    assert t["feeds_report_section"] == "Section 1"
    mock_base_model.with_structured_output.assert_called_once_with(TaskListSpec)


@pytest.mark.asyncio
async def test_task_architect_structured_output_returns_dict():
    raw_dict = {
        "tasks": [
            {
                "id": "task-01",
                "title": "Dict Task",
                "angle": "Angle Dict",
                "type": "synthesis",
                "context": "Context Dict",
                "questions": ["Q Dict"],
                "scope": "Scope Dict",
                "preferred_sources": [],
                "search_budget": 8,
                "min_sources": 3,
                "depends_on": [],
                "feeds_report_section": "Summary",
            }
        ]
    }
    mock_structured_model = MagicMock()
    mock_structured_model.ainvoke = AsyncMock(return_value=raw_dict)

    mock_base_model = MagicMock()
    mock_base_model.with_structured_output.return_value = mock_structured_model

    with patch("apps.research_agent.task_architect.get_model", return_value=mock_base_model):
        results = await task_architect("query", "plan")

    assert len(results) == 1
    assert results[0]["task_key"] == "task-01"
    assert results[0]["task_type"] == "synthesis"
    assert results[0]["title"] == "Dict Task"
    assert results[0]["search_budget"] == 8


@pytest.mark.asyncio
async def test_task_architect_fallback_when_structured_output_raises():
    mock_base_model = MagicMock()
    mock_base_model.with_structured_output.side_effect = RuntimeError("Structured output unsupported")

    fallback_agent_result = {
        "messages": [
            MagicMock(
                content='[{"id": "task-fallback-01", "title": "Fallback Task", "angle": "Fallback Angle"}]'
            )
        ]
    }
    mock_agent = MagicMock()
    mock_agent.ainvoke = AsyncMock(return_value=fallback_agent_result)

    with patch("apps.research_agent.task_architect.get_model", return_value=mock_base_model), \
         patch("apps.research_agent.task_architect.create_agent", return_value=mock_agent):
        results = await task_architect("query", "plan")

    assert len(results) == 1
    assert results[0]["task_key"] == "task-fallback-01"
    assert results[0]["title"] == "Fallback Task"
    assert results[0]["angle"] == "Fallback Angle"
    assert results[0]["task_type"] == "research"
    assert results[0]["search_budget"] == 15
    assert results[0]["min_sources"] == 6


@pytest.mark.asyncio
async def test_task_architect_fallback_when_structured_output_empty():
    empty_list = TaskListSpec(tasks=[])
    mock_structured_model = MagicMock()
    mock_structured_model.ainvoke = AsyncMock(return_value=empty_list)

    mock_base_model = MagicMock()
    mock_base_model.with_structured_output.return_value = mock_structured_model

    fallback_agent_result = {
        "messages": [
            MagicMock(
                content='```json\n[{"id": "task-01", "title": "Recovered Task"}]\n```'
            )
        ]
    }
    mock_agent = MagicMock()
    mock_agent.ainvoke = AsyncMock(return_value=fallback_agent_result)

    with patch("apps.research_agent.task_architect.get_model", return_value=mock_base_model), \
         patch("apps.research_agent.task_architect.create_agent", return_value=mock_agent):
        results = await task_architect("query", "plan")

    assert len(results) == 1
    assert results[0]["task_key"] == "task-01"
    assert results[0]["title"] == "Recovered Task"
