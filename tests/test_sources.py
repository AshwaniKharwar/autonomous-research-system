from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch
from uuid import uuid4
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from apps.api.main import app
from apps.api.schemas import ResearchTaskResponse
from apps.db.database import async_session_factory
from apps.db.models import ResearchSession, ResearchStatus, ResearchTask, TaskStatus
from apps.research_agent.dispatcher import dispatch_research_session
from apps.research_agent.task_agent import (
    TaskAgentResult,
    extract_sources_from_findings,
)


def test_extract_sources_standard_format():
    findings = """# task-01: Perovskite Solar Cells
## Answer summary
Perovskite cells have achieved remarkable laboratory efficiency gains.

## Findings
Efficiencies have exceeded 33% in tandem architectures [S1].
Stability remains the primary hurdle for long-term commercialization [S2].

## Sources
[S1] NREL. Best Research-Cell Efficiency Chart. https://www.nrel.gov/pv/cell-efficiency.html. 2024-01-15. Data repository.
[S2] Nature Energy. Degradation mechanisms in metal halide perovskites. https://www.nature.com/articles/s41560-023-01234-5. 2023-11-20. Journal article.
"""
    sources = extract_sources_from_findings(findings)
    assert len(sources) == 2
    assert sources[0]["id"] == "S1"
    assert sources[0]["url"] == "https://www.nrel.gov/pv/cell-efficiency.html"
    assert "NREL" in sources[0]["title"]
    assert sources[0]["date"] == "2024-01-15"
    assert "Data repository" in sources[0]["snippet"]

    assert sources[1]["id"] == "S2"
    assert sources[1]["url"] == "https://www.nature.com/articles/s41560-023-01234-5"
    assert "Nature Energy" in sources[1]["title"]
    assert sources[1]["date"] == "2023-11-20"


def test_extract_sources_markdown_links_and_bullets():
    findings = """# task-02: Battery Technology
## Findings
Overview of battery technology.

### References
- [S1] [Solid State Battery Overview](https://example.com/battery) - Published on 2024-03-10 by EnergyLab.
* [S2] [Lithium-Sulfur Frontiers](https://example.com/lis) (June 2023)
"""
    sources = extract_sources_from_findings(findings)
    assert len(sources) == 2
    assert sources[0]["id"] == "S1"
    assert sources[0]["url"] == "https://example.com/battery"
    assert sources[0]["title"] == "Solid State Battery Overview"
    assert sources[0]["date"] == "2024-03-10"

    assert sources[1]["id"] == "S2"
    assert sources[1]["url"] == "https://example.com/lis"
    assert sources[1]["title"] == "Lithium-Sulfur Frontiers"
    assert "2023" in sources[1]["date"]


def test_extract_sources_numbered_and_fallback():
    findings = """## Summary
Key breakthroughs in quantum computing.

## Citations
1. [1] Quantum supremacy benchmark. https://quantum-lab.org/paper. 2024.
2. [2] Fault-tolerant qubits. https://qubit-research.org/results. 2023-12-01.
"""
    sources = extract_sources_from_findings(findings)
    assert len(sources) == 2
    assert sources[0]["id"] == "S1"
    assert sources[0]["url"] == "https://quantum-lab.org/paper"
    assert sources[0]["date"] == "2024"

    assert sources[1]["id"] == "S2"
    assert sources[1]["url"] == "https://qubit-research.org/results"
    assert sources[1]["date"] == "2023-12-01"


def test_extract_sources_empty_and_no_sources():
    assert extract_sources_from_findings("") == []
    assert extract_sources_from_findings("Plain text with no urls or sources") == []


def test_task_agent_result_behavior():
    result = TaskAgentResult(
        findings="# Findings\nContent",
        sources=[{"id": "S1", "url": "https://test.com", "title": "Test", "date": "2024", "snippet": "Snippet"}],
    )
    # 1. Attribute access
    assert result.findings == "# Findings\nContent"
    assert len(result.sources) == 1

    # 2. Tuple unpacking
    f, s = result
    assert f == "# Findings\nContent"
    assert s == result.sources

    # 3. Indexing
    assert result[0] == "# Findings\nContent"
    assert result[1] == result.sources

    # 4. Dict .get()
    assert result.get("findings") == "# Findings\nContent"
    assert result.get("sources") == result.sources
    assert result.get("nonexistent", "default") == "default"

    # 5. Length and tuple check
    assert len(result) == 2
    assert isinstance(result, tuple)


def test_research_task_response_schema():
    task_data = {
        "id": uuid4(),
        "task_key": "task-01",
        "title": "Test Task",
        "questions": ["Q1"],
        "status": TaskStatus.COMPLETED,
        "findings": "# Findings",
        "sources": [
            {
                "id": "S1",
                "url": "https://example.com/source1",
                "title": "Source 1",
                "date": "2024-01-01",
                "snippet": "Test snippet",
            }
        ],
    }
    resp = ResearchTaskResponse.model_validate(task_data)
    assert len(resp.sources) == 1
    assert resp.sources[0]["id"] == "S1"
    assert resp.sources[0]["url"] == "https://example.com/source1"

    # None sources coerced to empty list
    task_data_none = {
        "id": uuid4(),
        "task_key": "task-02",
        "title": "Pending Task",
        "sources": None,
    }
    resp_none = ResearchTaskResponse.model_validate(task_data_none)
    assert resp_none.sources == []


@pytest.mark.asyncio
async def test_dispatcher_persists_sources_in_postgres():
    """Verify that dispatch_research_session persists structured sources into ResearchTask.sources JSONB column."""
    async with async_session_factory() as db:
        session = ResearchSession(
            query="Perovskite solar research test",
            status=ResearchStatus.RUNNING,
        )
        db.add(session)
        await db.commit()
        await db.refresh(session)
        session_id = session.id

        task = ResearchTask(
            session_id=session_id,
            task_key="task-01",
            title="Perovskite Stability Analysis",
            questions=["What improves stability?"],
            search_budget=5,
            min_sources=2,
            depends_on=[],
            status=TaskStatus.PENDING,
        )
        db.add(task)
        await db.commit()

    sample_findings = """# task-01: Perovskite Stability Analysis
## Answer summary
2D/3D heterostructures dramatically improve stability.

## Sources
[S1] Science. 2D/3D perovskite interface stabilization. https://science.org/doi/10.1126/science.1234. 2024-02-01. Journal paper.
[S2] Nature Materials. Moisture resistance via hydrophobic cations. https://nature.com/articles/nmat5678. 2023-09-15. Article.
"""
    expected_sources = [
        {
            "id": "S1",
            "url": "https://science.org/doi/10.1126/science.1234",
            "title": "Science. 2D/3D perovskite interface stabilization",
            "date": "2024-02-01",
            "snippet": "2024-02-01. Journal paper",
        },
        {
            "id": "S2",
            "url": "https://nature.com/articles/nmat5678",
            "title": "Nature Materials. Moisture resistance via hydrophobic cations",
            "date": "2023-09-15",
            "snippet": "2023-09-15. Article",
        },
    ]

    async def mock_run_agent(task_data, dep_findings):
        return TaskAgentResult(findings=sample_findings, sources=expected_sources)

    with patch("apps.research_agent.dispatcher.run_task_agent", side_effect=mock_run_agent):
        all_findings, logs = await dispatch_research_session(session_id)

    # 1. Verify all_findings is the markdown text
    assert "task-01" in all_findings
    assert all_findings["task-01"] == sample_findings

    # 2. Verify database record has sources persisted in JSONB column
    async with async_session_factory() as db:
        stmt = select(ResearchTask).where(
            ResearchTask.session_id == session_id,
            ResearchTask.task_key == "task-01",
        )
        res = await db.execute(stmt)
        saved_task = res.scalar_one_or_none()
        assert saved_task is not None
        assert saved_task.status == TaskStatus.COMPLETED
        assert saved_task.findings == sample_findings
        assert isinstance(saved_task.sources, list)
        assert len(saved_task.sources) == 2
        assert saved_task.sources[0]["id"] == "S1"
        assert saved_task.sources[0]["url"] == "https://science.org/doi/10.1126/science.1234"
        assert saved_task.sources[1]["id"] == "S2"
        assert saved_task.sources[1]["url"] == "https://nature.com/articles/nmat5678"

    # 3. Verify API endpoint returns sources in JSON response
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get(f"/api/v1/researches/{session_id}/tasks/task-01")
        assert resp.status_code == 200
        task_json = resp.json()
        assert "sources" in task_json
        assert len(task_json["sources"]) == 2
        assert task_json["sources"][0]["id"] == "S1"
        assert task_json["sources"][0]["url"] == "https://science.org/doi/10.1126/science.1234"

        # Also verify session details endpoint includes sources in task list
        resp_session = await client.get(f"/api/v1/researches/{session_id}")
        assert resp_session.status_code == 200
        session_json = resp_session.json()
        assert len(session_json["tasks"]) == 1
        assert len(session_json["tasks"][0]["sources"]) == 2

    # Cleanup test session
    async with async_session_factory() as db:
        del_sess = await db.get(ResearchSession, session_id)
        if del_sess:
            await db.delete(del_sess)
            await db.commit()
