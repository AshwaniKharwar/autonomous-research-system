import asyncio
import logging
import os
from typing import Any, Callable
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from apps.db.database import async_session_factory as default_session_factory
from apps.db.models import DispatchLog, ResearchTask, TaskStatus
from apps.research_agent.cancellation import is_cancelled
from apps.research_agent.task_agent import run_task_agent

logger = logging.getLogger("research_agent.dispatcher")

TRANSIENT_EXCEPTIONS = (
    TimeoutError,
    asyncio.TimeoutError,
    ConnectionError,
    ConnectionResetError,
    ConnectionRefusedError,
)

TRANSIENT_KEYWORDS = (
    "rate limit",
    "rate_limit",
    "ratelimit",
    "429",
    "503",
    "502",
    "504",
    "timeout",
    "timed out",
    "connection reset",
    "connection refused",
    "connection error",
    "network error",
    "resource_exhausted",
    "resource exhausted",
    "temporarily unavailable",
    "service unavailable",
    "overloaded",
    "transient",
)


def is_synthesis_task(task_data: dict[str, Any]) -> bool:
    """Check if a task is a synthesis or summary task."""
    task_type = str(task_data.get("type") or task_data.get("task_type") or "").lower()
    task_angle = str(task_data.get("angle") or "").lower()
    task_title = str(task_data.get("title") or "").lower()
    return (
        task_type == "synthesis"
        or "synthesis" in task_angle
        or "synthesis" in task_title
        or "summary" in task_title
    )


def is_transient_error(exc: Exception) -> bool:
    """Determine whether an exception is a transient error eligible for retry."""
    if isinstance(exc, TRANSIENT_EXCEPTIONS):
        return True
    status_code = getattr(exc, "status_code", None) or getattr(exc, "status", None)
    if status_code in (429, 502, 503, 504):
        return True
    exc_str = str(exc).lower()
    exc_name = type(exc).__name__.lower()
    return any(kw in exc_str or kw in exc_name for kw in TRANSIENT_KEYWORDS)


def compute_task_waves(tasks: list[dict[str, Any]]) -> list[list[dict[str, Any]]]:
    """Sort tasks topologically into execution waves based on depends_on."""
    task_map = {t["task_key"]: t for t in tasks}
    completed_ids: set[str] = set()
    remaining = list(tasks)
    waves: list[list[dict[str, Any]]] = []

    while remaining:
        current_wave = []
        for t in remaining:
            deps = t.get("depends_on") or []
            # Ready if all dependencies are in completed_ids
            if all(dep in completed_ids for dep in deps):
                current_wave.append(t)

        if not current_wave:
            # Circular dependency or missing dependency detected, force execution of remainder
            logger.warning("Circular or unresolvable dependencies detected; breaking cycle.")
            current_wave = remaining[:]

        waves.append(current_wave)
        for t in current_wave:
            completed_ids.add(t["task_key"])
            remaining.remove(t)

    return waves


async def dispatch_research_session(
    session_id: UUID,
    db: AsyncSession | None = None,
    session_factory: async_sessionmaker[AsyncSession] | Callable[[], Any] | None = None,
    max_concurrency: int | None = None,
) -> tuple[dict[str, str], list[str]]:
    """Execute all tasks for a research session wave by wave, saving findings to Postgres."""
    logger.info(f"Starting wave-by-wave dispatch for session {session_id}...")

    factory = session_factory or default_session_factory

    concurrency_limit = (
        max_concurrency
        if max_concurrency is not None
        else int(os.getenv("MAX_CONCURRENT_TASKS", "5"))
    )
    semaphore = asyncio.Semaphore(concurrency_limit)

    # Fetch tasks from database
    if db is not None:
        stmt = select(ResearchTask).where(ResearchTask.session_id == session_id)
        result = await db.execute(stmt)
        db_tasks = list(result.scalars().all())
    else:
        async with factory() as fetch_db:
            stmt = select(ResearchTask).where(ResearchTask.session_id == session_id)
            result = await fetch_db.execute(stmt)
            db_tasks = list(result.scalars().all())

    if not db_tasks:
        logger.warning(f"No tasks found for session {session_id}")
        return {}, ["No tasks found"]

    task_dicts = [
        {
            "id": str(t.id),
            "task_key": t.task_key,
            "title": t.title,
            "angle": t.angle,
            "type": t.task_type,
            "task_type": t.task_type,
            "context": t.context,
            "questions": t.questions,
            "scope": t.scope,
            "preferred_sources": t.preferred_sources,
            "search_budget": t.search_budget,
            "min_sources": t.min_sources,
            "depends_on": t.depends_on,
        }
        for t in db_tasks
    ]

    waves = compute_task_waves(task_dicts)
    logger.info(f"Computed {len(waves)} waves for session {session_id}")

    all_findings: dict[str, str] = {}
    summary_logs: list[str] = []

    for wave_idx, wave_tasks in enumerate(waves, 1):
        if is_cancelled(session_id):
            logger.info(f"Session {session_id} is cancelled. Halting wave execution.")
            async with factory() as task_db:
                log_entry = DispatchLog(
                    session_id=session_id,
                    task_key=f"wave-{wave_idx}",
                    wave=wave_idx,
                    status="CANCELLED",
                    note="Workflow cancelled; remaining waves skipped.",
                )
                task_db.add(log_entry)
                await task_db.commit()
            summary_logs.append(f"Wave {wave_idx}: CANCELLED (Workflow cancelled)")
            break

        logger.info(f"Executing Wave {wave_idx} with {len(wave_tasks)} tasks...")

        async def _execute_single_task(task_data: dict[str, Any]):
            task_key = task_data["task_key"]
            deps = task_data.get("depends_on") or []

            async with semaphore:
                if is_cancelled(session_id):
                    logger.info(f"Task {task_key} skipped because session {session_id} was cancelled.")
                    return f"Wave {wave_idx} - {task_key}: SKIPPED (Session cancelled)"

                # Check if any dependencies failed or are missing
                missing_deps = [d for d in deps if d not in all_findings]
                has_partial_deps = False
                if missing_deps:
                    total_deps = len(deps)
                    succeeded_deps_count = total_deps - len(missing_deps)
                    is_synthesis = is_synthesis_task(task_data)

                    # Soft dependency logic: synthesis tasks can proceed if at least 50% of deps succeeded
                    if is_synthesis and total_deps > 0 and (succeeded_deps_count * 2 >= total_deps):
                        has_partial_deps = True
                        logger.warning(
                            f"Synthesis task {task_key} proceeding with partial dependencies "
                            f"({succeeded_deps_count}/{total_deps} succeeded). Missing: {missing_deps}"
                        )
                        # Prepend note to context detailing missing upstream dependency findings
                        missing_str = ", ".join(missing_deps)
                        missing_note = (
                            f"[NOTE: Upstream dependency findings missing for: {missing_str}. "
                            f"Proceeding with available partial findings.]"
                        )
                        existing_context = task_data.get("context") or ""
                        task_data = {
                            **task_data,
                            "context": f"{missing_note}\n\n{existing_context}".strip(),
                        }
                    else:
                        logger.warning(
                            f"Task {task_key} skipped because dependency '{missing_deps[0]}' is not completed."
                        )
                        status_str = "FAILED"
                        note_str = f"Dependency '{missing_deps[0]}' failed or not completed"

                        async with factory() as task_db:
                            task_stmt = select(ResearchTask).where(
                                ResearchTask.session_id == session_id,
                                ResearchTask.task_key == task_key,
                            )
                            t_res = await task_db.execute(task_stmt)
                            task_row = t_res.scalar_one_or_none()
                            if task_row:
                                task_row.status = TaskStatus.FAILED
                                task_row.wave = wave_idx
                                await task_db.commit()

                            log_entry = DispatchLog(
                                session_id=session_id,
                                task_key=task_key,
                                wave=wave_idx,
                                status=status_str,
                                note=note_str,
                            )
                            task_db.add(log_entry)
                            await task_db.commit()

                        return f"Wave {wave_idx} - {task_key}: {status_str} ({note_str})"

                dep_findings = {d: all_findings[d] for d in deps if d in all_findings}

                # 1. Update task status to RUNNING (short-lived session)
                async with factory() as task_db:
                    task_stmt = select(ResearchTask).where(
                        ResearchTask.session_id == session_id,
                        ResearchTask.task_key == task_key,
                    )
                    t_res = await task_db.execute(task_stmt)
                    task_row = t_res.scalar_one_or_none()
                    if task_row:
                        task_row.status = TaskStatus.RUNNING
                        task_row.wave = wave_idx
                        await task_db.commit()

                # 2. Run task agent with retry for transient failures
                max_retries = int(os.getenv("TASK_AGENT_MAX_RETRIES", "2"))
                retry_sleep_base = float(os.getenv("TASK_AGENT_RETRY_SLEEP", "0.5"))
                findings_text = None
                status_str = "FAILED"
                note_str = ""

                for attempt in range(max_retries + 1):
                    try:
                        findings_text = await run_task_agent(task_data, dep_findings)
                        status_str = "COMPLETED"
                        if has_partial_deps:
                            missing_str = ", ".join(missing_deps)
                            note_str = f"Completed with partial dependencies: missing [{missing_str}]"
                        else:
                            note_str = "Completed successfully"
                        all_findings[task_key] = findings_text
                        break
                    except Exception as e:
                        if attempt < max_retries and is_transient_error(e):
                            logger.warning(
                                f"Task {task_key} attempt {attempt + 1} failed with transient error: {e}. Retrying..."
                            )
                            await asyncio.sleep(retry_sleep_base * (attempt + 1))
                            continue
                        logger.error(f"Task {task_key} failed: {e}", exc_info=True)
                        status_str = "FAILED"
                        note_str = str(e)
                        findings_text = None
                        break

                # 3. Update task status and persist log in DB (short-lived session)
                async with factory() as task_db:
                    task_stmt = select(ResearchTask).where(
                        ResearchTask.session_id == session_id,
                        ResearchTask.task_key == task_key,
                    )
                    t_res = await task_db.execute(task_stmt)
                    task_row = t_res.scalar_one_or_none()
                    if task_row:
                        if status_str == "COMPLETED":
                            task_row.status = TaskStatus.COMPLETED
                            task_row.findings = findings_text
                        else:
                            task_row.status = TaskStatus.FAILED
                        await task_db.commit()

                    log_entry = DispatchLog(
                        session_id=session_id,
                        task_key=task_key,
                        wave=wave_idx,
                        status=status_str,
                        note=note_str,
                    )
                    task_db.add(log_entry)
                    await task_db.commit()

                return f"Wave {wave_idx} - {task_key}: {status_str}"

        # Execute all tasks in this wave concurrently
        wave_results = await asyncio.gather(*[_execute_single_task(t) for t in wave_tasks])
        summary_logs.extend(wave_results)

    logger.info(f"Session {session_id} wave dispatch complete.")
    return all_findings, summary_logs


# Backward-compatibility alias
dispatch_research = dispatch_research_session
