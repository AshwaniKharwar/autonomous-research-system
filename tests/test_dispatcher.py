from unittest.mock import AsyncMock, patch
from uuid import uuid4
import pytest
from sqlalchemy import select
from apps.db.database import async_session_factory
from apps.db.models import (
    DispatchLog,
    ResearchSession,
    ResearchStatus,
    ResearchTask,
    TaskStatus,
)
from apps.research_agent.cancellation import cancel_session, clear_token
from apps.research_agent.dispatcher import (
    compute_task_waves,
    dispatch_research_session,
    is_synthesis_task,
    is_transient_error,
)


def test_compute_task_waves():
    tasks = [
        {"task_key": "t1", "depends_on": []},
        {"task_key": "t2", "depends_on": []},
        {"task_key": "t3", "depends_on": ["t1"]},
        {"task_key": "t4", "depends_on": ["t1", "t2"]},
        {"task_key": "t5", "depends_on": ["t3", "t4"]},
    ]
    waves = compute_task_waves(tasks)
    assert len(waves) == 3
    # Wave 1 has t1, t2
    w1_keys = {t["task_key"] for t in waves[0]}
    assert w1_keys == {"t1", "t2"}
    # Wave 2 has t3, t4
    w2_keys = {t["task_key"] for t in waves[1]}
    assert w2_keys == {"t3", "t4"}
    # Wave 3 has t5
    w3_keys = {t["task_key"] for t in waves[2]}
    assert w3_keys == {"t5"}


@pytest.mark.asyncio
async def test_concurrent_wave_execution_multiple_parallel_tasks():
    """Verify that multiple parallel tasks in the same wave do not crash due to concurrent session usage."""
    async with async_session_factory() as db:
        session = ResearchSession(
            query="Concurrent wave test session",
            status=ResearchStatus.RUNNING,
        )
        db.add(session)
        await db.commit()
        await db.refresh(session)
        session_id = session.id

        # 3 tasks in the exact same wave (no dependencies)
        for i in range(1, 4):
            task = ResearchTask(
                session_id=session_id,
                task_key=f"task-0{i}",
                title=f"Parallel Task {i}",
                angle="Concurrency Test",
                questions=[f"Question {i}"],
                search_budget=5,
                min_sources=2,
                depends_on=[],
                status=TaskStatus.PENDING,
            )
            db.add(task)
        await db.commit()

    async def mock_run_agent(task_data, dep_findings):
        # Simulate slight async delay to ensure coroutines overlap
        import asyncio
        await asyncio.sleep(0.05)
        return f"Findings for {task_data['task_key']}"

    with patch("apps.research_agent.dispatcher.run_task_agent", side_effect=mock_run_agent):
        findings, logs = await dispatch_research_session(session_id)

    assert len(findings) == 3
    assert len(logs) == 3
    assert "task-01" in findings
    assert "task-02" in findings
    assert "task-03" in findings

    # Verify database updates
    async with async_session_factory() as db:
        stmt = select(ResearchTask).where(ResearchTask.session_id == session_id)
        res = await db.execute(stmt)
        tasks = list(res.scalars().all())
        assert len(tasks) == 3
        for t in tasks:
            assert t.status == TaskStatus.COMPLETED
            assert t.wave == 1
            assert t.findings == f"Findings for {t.task_key}"

        log_stmt = select(DispatchLog).where(DispatchLog.session_id == session_id)
        log_res = await db.execute(log_stmt)
        dispatch_logs = list(log_res.scalars().all())
        assert len(dispatch_logs) == 3
        assert all(l.status == "COMPLETED" for l in dispatch_logs)


@pytest.mark.asyncio
async def test_dependent_task_fails_when_upstream_dependency_fails():
    """Verify that a task whose dependency failed is marked FAILED without executing run_task_agent."""
    async with async_session_factory() as db:
        session = ResearchSession(
            query="Dependency failure test session",
            status=ResearchStatus.RUNNING,
        )
        db.add(session)
        await db.commit()
        await db.refresh(session)
        session_id = session.id

        task1 = ResearchTask(
            session_id=session_id,
            task_key="task-01",
            title="Prerequisite Task",
            angle="Dependency Test",
            questions=["Question 1"],
            search_budget=5,
            min_sources=2,
            depends_on=[],
            status=TaskStatus.PENDING,
        )
        task2 = ResearchTask(
            session_id=session_id,
            task_key="task-02",
            title="Dependent Task",
            angle="Dependency Test",
            questions=["Question 2"],
            search_budget=5,
            min_sources=2,
            depends_on=["task-01"],
            status=TaskStatus.PENDING,
        )
        db.add_all([task1, task2])
        await db.commit()

    mock_agent = AsyncMock()
    mock_agent.side_effect = RuntimeError("Simulated API failure in task-01")

    with patch("apps.research_agent.dispatcher.run_task_agent", mock_agent):
        findings, logs = await dispatch_research_session(session_id)

    # task-01 ran and failed; task-02 was skipped because task-01 was incomplete
    assert "task-01" not in findings
    assert "task-02" not in findings
    # mock_agent should only have been called ONCE (for task-01), NOT for task-02!
    assert mock_agent.call_count == 1

    async with async_session_factory() as db:
        stmt = select(ResearchTask).where(ResearchTask.session_id == session_id).order_by(ResearchTask.task_key)
        res = await db.execute(stmt)
        tasks = list(res.scalars().all())
        assert len(tasks) == 2
        assert tasks[0].task_key == "task-01"
        assert tasks[0].status == TaskStatus.FAILED
        assert tasks[1].task_key == "task-02"
        assert tasks[1].status == TaskStatus.FAILED

        log_stmt = select(DispatchLog).where(DispatchLog.session_id == session_id).order_by(DispatchLog.task_key)
        log_res = await db.execute(log_stmt)
        dispatch_logs = list(log_res.scalars().all())
        assert len(dispatch_logs) == 2
        assert dispatch_logs[0].status == "FAILED"
        assert "Simulated API failure" in dispatch_logs[0].note
        assert dispatch_logs[1].status == "FAILED"
        assert "Dependency 'task-01' failed or not completed" in dispatch_logs[1].note


@pytest.mark.asyncio
async def test_dispatch_cancellation_skips_subsequent_waves():
    """Verify that cancelling a session stops execution before subsequent waves and logs CANCELLED."""
    async with async_session_factory() as db:
        session = ResearchSession(
            query="Cancellation wave test session",
            status=ResearchStatus.RUNNING,
        )
        db.add(session)
        await db.commit()
        await db.refresh(session)
        session_id = session.id

        # Wave 1 task
        task1 = ResearchTask(
            session_id=session_id,
            task_key="task-01",
            title="Wave 1 Task",
            angle="Wave 1",
            questions=["Q1"],
            search_budget=5,
            min_sources=2,
            depends_on=[],
            status=TaskStatus.PENDING,
        )
        # Wave 2 task
        task2 = ResearchTask(
            session_id=session_id,
            task_key="task-02",
            title="Wave 2 Task",
            angle="Wave 2",
            questions=["Q2"],
            search_budget=5,
            min_sources=2,
            depends_on=["task-01"],
            status=TaskStatus.PENDING,
        )
        db.add_all([task1, task2])
        await db.commit()

    try:
        # Simulate cancellation during wave 1 execution
        async def mock_run_agent(task_data, dep_findings):
            cancel_session(session_id)
            return f"Findings for {task_data['task_key']}"

        with patch("apps.research_agent.dispatcher.run_task_agent", side_effect=mock_run_agent):
            findings, logs = await dispatch_research_session(session_id)

        # Wave 1 finished, but Wave 2 was skipped because session was cancelled
        assert "task-01" in findings
        assert "task-02" not in findings

        # Check dispatch logs to confirm cancellation was recorded
        async with async_session_factory() as db:
            log_stmt = select(DispatchLog).where(
                DispatchLog.session_id == session_id,
                DispatchLog.status == "CANCELLED",
            )
            log_res = await db.execute(log_stmt)
            cancelled_logs = list(log_res.scalars().all())
            assert len(cancelled_logs) >= 1
            assert "Workflow cancelled" in cancelled_logs[0].note

            # task-02 should still be PENDING in DB
            t2_stmt = select(ResearchTask).where(
                ResearchTask.session_id == session_id,
                ResearchTask.task_key == "task-02",
            )
            t2_res = await db.execute(t2_stmt)
            task2_db = t2_res.scalar_one_or_none()
            assert task2_db is not None
            assert task2_db.status == TaskStatus.PENDING
    finally:
        clear_token(session_id)


def test_is_synthesis_task_variations():
    """Verify that synthesis and summary tasks are correctly identified."""
    assert is_synthesis_task({"type": "synthesis"}) is True
    assert is_synthesis_task({"task_type": "synthesis"}) is True
    assert is_synthesis_task({"angle": "Strategic Synthesis & Recommendations"}) is True
    assert is_synthesis_task({"title": "Synthesis of Key Findings"}) is True
    assert is_synthesis_task({"title": "Executive Summary"}) is True
    assert is_synthesis_task({"type": "research", "title": "Market Trends", "angle": "Finance"}) is False
    assert is_synthesis_task({}) is False
    assert is_synthesis_task({"type": None, "title": None, "angle": None}) is False


def test_is_transient_error_variations():
    """Verify transient error classification."""
    assert is_transient_error(TimeoutError("Connection timeout")) is True
    assert is_transient_error(ConnectionError("Refused")) is True
    assert is_transient_error(Exception("429 rate limit exceeded")) is True
    assert is_transient_error(Exception("503 Service Unavailable")) is True
    assert is_transient_error(Exception("RESOURCE_EXHAUSTED: quota reached")) is True

    class Custom429(Exception):
        status_code = 429

    assert is_transient_error(Custom429()) is True
    assert is_transient_error(ValueError("Invalid syntax")) is False
    assert is_transient_error(RuntimeError("Simulated API failure in task-01")) is False


@pytest.mark.asyncio
async def test_synthesis_task_continues_when_one_of_two_dependencies_missing():
    """Verify that a synthesis task with 1 of 2 dependencies succeeding completes with degraded/partial findings."""
    async with async_session_factory() as db:
        session = ResearchSession(
            query="Soft dependency synthesis test session",
            status=ResearchStatus.RUNNING,
        )
        db.add(session)
        await db.commit()
        await db.refresh(session)
        session_id = session.id

        task1 = ResearchTask(
            session_id=session_id,
            task_key="task-01",
            title="Prerequisite Task 1",
            angle="Wave 1",
            task_type="research",
            context="Context for task 1",
            questions=["Q1"],
            search_budget=5,
            min_sources=2,
            depends_on=[],
            status=TaskStatus.PENDING,
        )
        task2 = ResearchTask(
            session_id=session_id,
            task_key="task-02",
            title="Prerequisite Task 2",
            angle="Wave 1",
            task_type="research",
            context="Context for task 2",
            questions=["Q2"],
            search_budget=5,
            min_sources=2,
            depends_on=[],
            status=TaskStatus.PENDING,
        )
        task3 = ResearchTask(
            session_id=session_id,
            task_key="task-03",
            title="Synthesis of All Findings",
            angle="Synthesis",
            task_type="synthesis",
            context="Base context for synthesis task",
            questions=["Q3"],
            search_budget=5,
            min_sources=2,
            depends_on=["task-01", "task-02"],
            status=TaskStatus.PENDING,
        )
        db.add_all([task1, task2, task3])
        await db.commit()

    captured_task_data = None
    captured_dep_findings = None

    async def mock_run_agent(task_data, dep_findings):
        nonlocal captured_task_data, captured_dep_findings
        if task_data["task_key"] == "task-01":
            return "Findings from task-01"
        elif task_data["task_key"] == "task-02":
            raise RuntimeError("Task 02 permanent error")
        elif task_data["task_key"] == "task-03":
            captured_task_data = task_data
            captured_dep_findings = dep_findings
            return "Synthesis findings based on available research"
        raise ValueError(f"Unexpected task: {task_data['task_key']}")

    with patch("apps.research_agent.dispatcher.run_task_agent", side_effect=mock_run_agent):
        findings, logs = await dispatch_research_session(session_id)

    # task-01 succeeded, task-02 failed, task-03 succeeded with partial dependencies
    assert "task-01" in findings
    assert "task-02" not in findings
    assert "task-03" in findings
    assert findings["task-03"] == "Synthesis findings based on available research"

    # Verify context and dep_findings passed to task-03
    assert captured_task_data is not None
    assert "Upstream dependency findings missing for: task-02" in captured_task_data["context"]
    assert "Base context for synthesis task" in captured_task_data["context"]
    assert captured_dep_findings == {"task-01": "Findings from task-01"}

    # Verify database state
    async with async_session_factory() as db:
        stmt = (
            select(ResearchTask)
            .where(ResearchTask.session_id == session_id)
            .order_by(ResearchTask.task_key)
        )
        res = await db.execute(stmt)
        tasks = list(res.scalars().all())
        assert len(tasks) == 3
        assert tasks[0].task_key == "task-01" and tasks[0].status == TaskStatus.COMPLETED
        assert tasks[1].task_key == "task-02" and tasks[1].status == TaskStatus.FAILED
        assert tasks[2].task_key == "task-03" and tasks[2].status == TaskStatus.COMPLETED
        assert tasks[2].findings == "Synthesis findings based on available research"

        log_stmt = (
            select(DispatchLog)
            .where(DispatchLog.session_id == session_id)
            .order_by(DispatchLog.task_key)
        )
        log_res = await db.execute(log_stmt)
        logs_db = list(log_res.scalars().all())
        assert len(logs_db) == 3
        assert logs_db[0].status == "COMPLETED"
        assert logs_db[1].status == "FAILED"
        assert logs_db[2].status == "COMPLETED"
        assert "Completed with partial dependencies: missing [task-02]" in logs_db[2].note


@pytest.mark.asyncio
async def test_hard_dependency_task_fails_when_prerequisite_missing():
    """Verify that a non-synthesis task strictly fails when any dependency is missing."""
    async with async_session_factory() as db:
        session = ResearchSession(
            query="Hard dependency strict failure test session",
            status=ResearchStatus.RUNNING,
        )
        db.add(session)
        await db.commit()
        await db.refresh(session)
        session_id = session.id

        task1 = ResearchTask(
            session_id=session_id,
            task_key="task-01",
            title="Prerequisite Task",
            angle="Phase 1",
            task_type="research",
            questions=["Q1"],
            search_budget=5,
            min_sources=2,
            depends_on=[],
            status=TaskStatus.PENDING,
        )
        task2 = ResearchTask(
            session_id=session_id,
            task_key="task-02",
            title="Detailed Technology Deep Dive",
            angle="Phase 2 Deep Dive",
            task_type="research",
            questions=["Q2"],
            search_budget=5,
            min_sources=2,
            depends_on=["task-01"],
            status=TaskStatus.PENDING,
        )
        db.add_all([task1, task2])
        await db.commit()

    mock_agent = AsyncMock()
    mock_agent.side_effect = RuntimeError("Task 1 hard failure")

    with patch("apps.research_agent.dispatcher.run_task_agent", mock_agent):
        findings, logs = await dispatch_research_session(session_id)

    assert "task-01" not in findings
    assert "task-02" not in findings
    # mock_agent should only have been called for task-01, never for task-02
    assert mock_agent.call_count == 1

    async with async_session_factory() as db:
        stmt = (
            select(ResearchTask)
            .where(ResearchTask.session_id == session_id)
            .order_by(ResearchTask.task_key)
        )
        res = await db.execute(stmt)
        tasks = list(res.scalars().all())
        assert len(tasks) == 2
        assert tasks[0].status == TaskStatus.FAILED
        assert tasks[1].status == TaskStatus.FAILED

        log_stmt = (
            select(DispatchLog)
            .where(DispatchLog.session_id == session_id)
            .order_by(DispatchLog.task_key)
        )
        log_res = await db.execute(log_stmt)
        logs_db = list(log_res.scalars().all())
        assert len(logs_db) == 2
        assert logs_db[1].status == "FAILED"
        assert "Dependency 'task-01' failed or not completed" in logs_db[1].note


@pytest.mark.asyncio
async def test_synthesis_task_fails_when_less_than_half_dependencies_succeed():
    """Verify that a synthesis task fails if fewer than 50% of its dependencies succeeded (e.g. 1 of 3)."""
    async with async_session_factory() as db:
        session = ResearchSession(
            query="Synthesis failure under 50% test session",
            status=ResearchStatus.RUNNING,
        )
        db.add(session)
        await db.commit()
        await db.refresh(session)
        session_id = session.id

        task1 = ResearchTask(
            session_id=session_id,
            task_key="task-01",
            title="Angle 1",
            task_type="research",
            questions=["Q1"],
            search_budget=5,
            min_sources=2,
            depends_on=[],
            status=TaskStatus.PENDING,
        )
        task2 = ResearchTask(
            session_id=session_id,
            task_key="task-02",
            title="Angle 2",
            task_type="research",
            questions=["Q2"],
            search_budget=5,
            min_sources=2,
            depends_on=[],
            status=TaskStatus.PENDING,
        )
        task3 = ResearchTask(
            session_id=session_id,
            task_key="task-03",
            title="Angle 3",
            task_type="research",
            questions=["Q3"],
            search_budget=5,
            min_sources=2,
            depends_on=[],
            status=TaskStatus.PENDING,
        )
        task4 = ResearchTask(
            session_id=session_id,
            task_key="task-04",
            title="Cross-Angle Synthesis Report",
            task_type="synthesis",
            questions=["Q4"],
            search_budget=5,
            min_sources=2,
            depends_on=["task-01", "task-02", "task-03"],
            status=TaskStatus.PENDING,
        )
        db.add_all([task1, task2, task3, task4])
        await db.commit()

    async def mock_run_agent(task_data, dep_findings):
        if task_data["task_key"] == "task-01":
            return "Findings from task-01"
        elif task_data["task_key"] == "task-02":
            raise RuntimeError("Error 2")
        elif task_data["task_key"] == "task-03":
            raise RuntimeError("Error 3")
        elif task_data["task_key"] == "task-04":
            return "Should not run"
        raise ValueError("Unknown task")

    with patch("apps.research_agent.dispatcher.run_task_agent", side_effect=mock_run_agent):
        findings, logs = await dispatch_research_session(session_id)

    assert "task-01" in findings
    assert "task-02" not in findings
    assert "task-03" not in findings
    assert "task-04" not in findings

    async with async_session_factory() as db:
        stmt = (
            select(ResearchTask)
            .where(ResearchTask.session_id == session_id, ResearchTask.task_key == "task-04")
        )
        res = await db.execute(stmt)
        task4_db = res.scalar_one_or_none()
        assert task4_db is not None
        assert task4_db.status == TaskStatus.FAILED

        log_stmt = (
            select(DispatchLog)
            .where(DispatchLog.session_id == session_id, DispatchLog.task_key == "task-04")
        )
        log_res = await db.execute(log_stmt)
        task4_log = log_res.scalar_one_or_none()
        assert task4_log is not None
        assert task4_log.status == "FAILED"
        assert "Dependency 'task-02' failed or not completed" in task4_log.note


@pytest.mark.asyncio
async def test_transient_failure_retry_mechanism():
    """Verify that a transient error is retried and succeeds if a subsequent attempt succeeds."""
    async with async_session_factory() as db:
        session = ResearchSession(
            query="Transient retry test session",
            status=ResearchStatus.RUNNING,
        )
        db.add(session)
        await db.commit()
        await db.refresh(session)
        session_id = session.id

        task = ResearchTask(
            session_id=session_id,
            task_key="task-01",
            title="Transient Network Task",
            angle="Retry Test",
            questions=["Q1"],
            search_budget=5,
            min_sources=2,
            depends_on=[],
            status=TaskStatus.PENDING,
        )
        db.add(task)
        await db.commit()

    call_count = 0

    async def mock_run_agent(task_data, dep_findings):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise TimeoutError("Temporary network timeout")
        return "Success after retry"

    with patch.dict("os.environ", {"TASK_AGENT_RETRY_SLEEP": "0.01"}):
        with patch("apps.research_agent.dispatcher.run_task_agent", side_effect=mock_run_agent):
            findings, logs = await dispatch_research_session(session_id)

    assert call_count == 2
    assert "task-01" in findings
    assert findings["task-01"] == "Success after retry"

    async with async_session_factory() as db:
        stmt = select(ResearchTask).where(ResearchTask.session_id == session_id)
        res = await db.execute(stmt)
        task_db = res.scalar_one_or_none()
        assert task_db is not None
        assert task_db.status == TaskStatus.COMPLETED
        assert task_db.findings == "Success after retry"

