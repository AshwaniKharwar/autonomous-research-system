from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from apps.api.main import app
from apps.db.database import get_db
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
        response = await client.post("/api/v1/researches", json={"query": "hi"})
        assert response.status_code == 422


@pytest.mark.asyncio
async def test_get_non_existent_research_session():
    random_id = str(uuid4())
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(f"/api/v1/researches/{random_id}")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_start_non_existent_research_session():
    random_id = str(uuid4())
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(f"/api/v1/researches/{random_id}/start")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_api_workflow_create_and_start_with_mocked_agents():
    """Test full API orchestration with /api/v1/researches."""
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

    # Test POST /api/v1/researches
    with patch("apps.api.router.create_research_session", new_callable=AsyncMock) as mock_create:
        mock_create.return_value = mock_session

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post("/api/v1/researches", json={"query": "Explain solid state batteries"})
            assert resp.status_code == 201
            data = resp.json()
            assert data["id"] == str(mock_session_id)
            assert data["status"] == "PENDING_APPROVAL"
            assert data["plan"]["title"] == "Solid State Plan"
            assert len(data["tasks"]) == 1
            assert data["tasks"][0]["task_key"] == "task-01"

    # Test POST /api/v1/researches/{id}/start
    mock_db = AsyncMock(spec=AsyncSession)
    mock_res = MagicMock()
    mock_res.rowcount = 1
    mock_db.execute.return_value = mock_res
    app.dependency_overrides[get_db] = lambda: mock_db

    try:
        with patch("apps.api.router.execute_research_workflow", new_callable=AsyncMock) as mock_exec:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                resp = await client.post(f"/api/v1/researches/{mock_session_id}/start")
                assert resp.status_code == 202
                data = resp.json()
                assert data["id"] == str(mock_session_id)
                assert data["status"] == "RUNNING"
                assert "initiated in background" in data["message"].lower()
    finally:
        app.dependency_overrides.pop(get_db, None)


@pytest.mark.asyncio
async def test_start_research_endpoint_already_running():
    now = datetime.now(timezone.utc)
    session_id = uuid4()
    mock_session = ResearchSession(
        id=session_id,
        query="Running query",
        status=ResearchStatus.RUNNING,
        created_at=now,
        updated_at=now,
    )

    mock_db = AsyncMock(spec=AsyncSession)
    mock_res = MagicMock()
    mock_res.rowcount = 0
    mock_db.execute.return_value = mock_res
    app.dependency_overrides[get_db] = lambda: mock_db

    try:
        with patch("apps.api.router.get_research_session", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_session
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                resp = await client.post(f"/api/v1/researches/{session_id}/start")
                assert resp.status_code == 200
                data = resp.json()
                assert data["id"] == str(session_id)
                assert data["status"] == "RUNNING"
                assert "already running" in data["message"].lower()
    finally:
        app.dependency_overrides.pop(get_db, None)


@pytest.mark.asyncio
async def test_start_research_endpoint_already_completed():
    now = datetime.now(timezone.utc)
    session_id = uuid4()
    mock_session = ResearchSession(
        id=session_id,
        query="Completed query",
        status=ResearchStatus.COMPLETED,
        created_at=now,
        updated_at=now,
    )

    mock_db = AsyncMock(spec=AsyncSession)
    mock_res = MagicMock()
    mock_res.rowcount = 0
    mock_db.execute.return_value = mock_res
    app.dependency_overrides[get_db] = lambda: mock_db

    try:
        with patch("apps.api.router.get_research_session", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_session
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                resp = await client.post(f"/api/v1/researches/{session_id}/start")
                assert resp.status_code == 200
                data = resp.json()
                assert data["id"] == str(session_id)
                assert data["status"] == "COMPLETED"
                assert "task is completed" in data["message"].lower()
    finally:
        app.dependency_overrides.pop(get_db, None)


@pytest.mark.asyncio
async def test_start_research_endpoint_failed_status_conflict():
    now = datetime.now(timezone.utc)
    session_id = uuid4()
    mock_session = ResearchSession(
        id=session_id,
        query="Failed query",
        status=ResearchStatus.FAILED,
        created_at=now,
        updated_at=now,
    )

    mock_db = AsyncMock(spec=AsyncSession)
    mock_res = MagicMock()
    mock_res.rowcount = 0
    mock_db.execute.return_value = mock_res
    app.dependency_overrides[get_db] = lambda: mock_db

    try:
        with patch("apps.api.router.get_research_session", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_session
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                resp = await client.post(f"/api/v1/researches/{session_id}/start")
                assert resp.status_code == 409
                assert "cannot be started" in resp.json()["detail"].lower()
    finally:
        app.dependency_overrides.pop(get_db, None)


@pytest.mark.asyncio
async def test_list_researches_endpoint():
    now = datetime.now(timezone.utc)
    mock_sessions = [
        ResearchSession(
            id=uuid4(),
            query="Query 1",
            status=ResearchStatus.PENDING_APPROVAL,
            created_at=now,
            updated_at=now,
        ),
        ResearchSession(
            id=uuid4(),
            query="Query 2",
            status=ResearchStatus.COMPLETED,
            created_at=now,
            updated_at=now,
        ),
    ]

    with patch("apps.api.router.list_research_sessions", new_callable=AsyncMock) as mock_list:
        mock_list.return_value = mock_sessions

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/v1/researches?limit=10&offset=0")
            assert resp.status_code == 200
            data = resp.json()
            assert len(data) == 2
            assert data[0]["query"] == "Query 1"
            assert data[1]["status"] == "COMPLETED"


@pytest.mark.asyncio
async def test_delete_research_endpoint():
    session_id = uuid4()
    with patch("apps.api.router.delete_research_session", new_callable=AsyncMock) as mock_del:
        mock_del.return_value = True

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.delete(f"/api/v1/researches/{session_id}")
            assert resp.status_code == 204


@pytest.mark.asyncio
async def test_revise_research_endpoint():
    now = datetime.now(timezone.utc)
    session_id = uuid4()
    mock_revised_session = ResearchSession(
        id=session_id,
        query="Original query",
        status=ResearchStatus.PENDING_APPROVAL,
        created_at=now,
        updated_at=now,
    )
    mock_revised_plan = ResearchPlan(
        id=uuid4(),
        session_id=session_id,
        title="Revised Plan",
        content="# Revised Plan Content",
        created_at=now,
        updated_at=now,
    )
    mock_revised_session.plan = mock_revised_plan

    with patch("apps.api.router.revise_research_session", new_callable=AsyncMock) as mock_rev:
        mock_rev.return_value = mock_revised_session

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.put(
                f"/api/v1/researches/{session_id}",
                json={"feedback": "Focus more on solid electrolyte interface."},
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["id"] == str(session_id)
            assert data["plan"]["title"] == "Revised Plan"
            assert "Revised Plan Content" in data["plan"]["content"]


@pytest.mark.asyncio
async def test_get_tasks_endpoints():
    now = datetime.now(timezone.utc)
    session_id = uuid4()
    mock_task_id = uuid4()
    mock_task = ResearchTask(
        id=mock_task_id,
        session_id=session_id,
        task_key="task-01",
        title="Task 1",
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

    mock_session = ResearchSession(
        id=session_id,
        query="Test query",
        status=ResearchStatus.PENDING_APPROVAL,
        created_at=now,
        updated_at=now,
    )

    with patch("apps.api.router.get_research_session", new_callable=AsyncMock) as mock_get_sess, \
         patch("apps.api.router.get_research_tasks", new_callable=AsyncMock) as mock_get_tasks, \
         patch("apps.api.router.get_research_task", new_callable=AsyncMock) as mock_get_task:
        mock_get_sess.return_value = mock_session
        mock_get_tasks.return_value = [mock_task]
        mock_get_task.return_value = mock_task

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            # 1. GET /api/v1/researches/{id}/tasks
            resp1 = await client.get(f"/api/v1/researches/{session_id}/tasks")
            assert resp1.status_code == 200
            tasks_data = resp1.json()
            assert len(tasks_data) == 1
            assert tasks_data[0]["task_key"] == "task-01"

            # 2. GET /api/v1/researches/{id}/tasks/task-01
            resp2 = await client.get(f"/api/v1/researches/{session_id}/tasks/task-01")
            assert resp2.status_code == 200
            task_data = resp2.json()
            assert task_data["task_key"] == "task-01"
            assert task_data["title"] == "Task 1"


@pytest.mark.asyncio
async def test_cancel_non_existent_research_session():
    random_id = str(uuid4())
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(f"/api/v1/researches/{random_id}/cancel")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_cancel_pending_approval_research_session():
    now = datetime.now(timezone.utc)
    session_id = uuid4()
    mock_session = ResearchSession(
        id=session_id,
        query="Test query",
        status=ResearchStatus.CANCELLED,
        created_at=now,
        updated_at=now,
    )

    with patch("apps.api.router.cancel_research_session", new_callable=AsyncMock) as mock_cancel:
        mock_cancel.return_value = (mock_session, "cancelled")

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(f"/api/v1/researches/{session_id}/cancel")
            assert resp.status_code == 200
            data = resp.json()
            assert data["id"] == str(session_id)
            assert data["status"] == "CANCELLED"
            assert "cancelled successfully" in data["message"]


@pytest.mark.asyncio
async def test_cancel_already_cancelled_session_idempotent():
    now = datetime.now(timezone.utc)
    session_id = uuid4()
    mock_session = ResearchSession(
        id=session_id,
        query="Test query",
        status=ResearchStatus.CANCELLED,
        created_at=now,
        updated_at=now,
    )

    with patch("apps.api.router.cancel_research_session", new_callable=AsyncMock) as mock_cancel:
        mock_cancel.return_value = (mock_session, "already_cancelled")

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(f"/api/v1/researches/{session_id}/cancel")
            assert resp.status_code == 200
            data = resp.json()
            assert data["id"] == str(session_id)
            assert data["status"] == "CANCELLED"
            assert "already cancelled" in data["message"]


@pytest.mark.asyncio
async def test_cancel_completed_session_conflict():
    now = datetime.now(timezone.utc)
    session_id = uuid4()
    mock_session = ResearchSession(
        id=session_id,
        query="Test query",
        status=ResearchStatus.COMPLETED,
        created_at=now,
        updated_at=now,
    )

    with patch("apps.api.router.cancel_research_session", new_callable=AsyncMock) as mock_cancel:
        mock_cancel.return_value = (mock_session, "conflict")

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(f"/api/v1/researches/{session_id}/cancel")
            assert resp.status_code == 409
            assert "cannot be cancelled" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_cancel_failed_session_conflict():
    now = datetime.now(timezone.utc)
    session_id = uuid4()
    mock_session = ResearchSession(
        id=session_id,
        query="Test query",
        status=ResearchStatus.FAILED,
        created_at=now,
        updated_at=now,
    )

    with patch("apps.api.router.cancel_research_session", new_callable=AsyncMock) as mock_cancel:
        mock_cancel.return_value = (mock_session, "conflict")

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(f"/api/v1/researches/{session_id}/cancel")
            assert resp.status_code == 409
            assert "cannot be cancelled" in resp.json()["detail"]

