from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch
from uuid import uuid4
import pytest
from httpx import ASGITransport, AsyncClient
from apps.api.main import app
from apps.db.models import (
    ResearchPlan,
    ResearchSession,
    ResearchStatus,
    ResearchTask,
    TaskStatus,
)


@pytest.mark.asyncio
async def test_health_endpoint():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "healthy", "service": "research_agent_system"}


@pytest.mark.asyncio
async def test_create_research_validation_error():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Query too short (< 5 characters)
        response = await client.post("/api/v1/research", json={"query": "hi"})
        assert response.status_code == 422


@pytest.mark.asyncio
async def test_get_non_existent_research_session():
    random_id = str(uuid4())
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(f"/api/v1/research/{random_id}")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_start_non_existent_research_session():
    random_id = str(uuid4())
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(f"/api/v1/research/{random_id}/start")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_api_workflow_create_and_start_with_mocked_agents():
    """Test full API orchestration (create plan/tasks -> PENDING_APPROVAL -> start -> RUNNING)."""
    now = datetime.now(timezone.utc)
    mock_session_id = uuid4()

    mock_session = ResearchSession(
        id=mock_session_id,
        query="Explain solid state batteries",
        status=ResearchStatus.PENDING_APPROVAL,
        created_at=now,
        updated_at=now,
    )
    mock_plan = ResearchPlan(
        id=uuid4(),
        session_id=mock_session_id,
        title="Solid State Plan",
        content="# Plan",
        created_at=now,
        updated_at=now,
    )
    mock_task = ResearchTask(
        id=uuid4(),
        session_id=mock_session_id,
        task_key="task-01",
        title="Electrolyte chemistry",
        task_type="research",
        questions=["Q1"],
        preferred_sources=[],
        search_budget=15,
        min_sources=6,
        depends_on=[],
        status=TaskStatus.PENDING,
        created_at=now,
        updated_at=now,
    )
    mock_session.plan = mock_plan
    mock_session.tasks = [mock_task]

    # Test POST /api/v1/research
    with patch("apps.api.router.create_research_session", new_callable=AsyncMock) as mock_create:
        mock_create.return_value = mock_session

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post("/api/v1/research", json={"query": "Explain solid state batteries"})
            assert resp.status_code == 201
            data = resp.json()
            assert data["id"] == str(mock_session_id)
            assert data["status"] == "PENDING_APPROVAL"
            assert data["plan"]["title"] == "Solid State Plan"
            assert len(data["tasks"]) == 1
            assert data["tasks"][0]["task_key"] == "task-01"

    # Test POST /api/v1/research/{id}/start
    with patch("apps.api.router.get_research_session", new_callable=AsyncMock) as mock_get, \
         patch("apps.api.router.execute_research_workflow", new_callable=AsyncMock) as mock_exec:
        mock_get.return_value = mock_session

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(f"/api/v1/research/{mock_session_id}/start")
            assert resp.status_code == 202
            data = resp.json()
            assert data["id"] == str(mock_session_id)
            assert data["status"] == "RUNNING"
            assert "initiated in background" in data["message"].lower()
