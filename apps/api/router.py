from typing import Optional
from uuid import UUID
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Response, status
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession
from apps.api.schemas import (
    ResearchCreateRequest,
    ResearchReviseRequest,
    ResearchSessionResponse,
    ResearchTaskResponse,
    StartResearchResponse,
)
from apps.db.database import get_db
from apps.db.models import ResearchSession, ResearchStatus
from apps.research_agent.service import (
    create_research_session,
    delete_research_session,
    execute_research_workflow,
    get_research_session,
    get_research_task,
    get_research_tasks,
    list_research_sessions,
    revise_research_session,
)

router = APIRouter(prefix="/api/v1/researches", tags=["Researches"])


@router.get(
    "",
    response_model=list[ResearchSessionResponse],
    summary="List Research Sessions",
)
async def list_researches(
    status_filter: Optional[ResearchStatus] = Query(None, alias="status", description="Filter by research status"),
    limit: int = Query(20, ge=1, le=100, description="Max items to return"),
    offset: int = Query(0, ge=0, description="Items to skip"),
    db: AsyncSession = Depends(get_db),
):
    """List research sessions with optional status filter and pagination."""
    return await list_research_sessions(db, status=status_filter, limit=limit, offset=offset)


@router.post(
    "",
    response_model=ResearchSessionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Research Plan & Tasks (Pending Approval)",
)
async def create_plan_and_tasks(
    req: ResearchCreateRequest,
    db: AsyncSession = Depends(get_db),
):
    """Generate a structured research plan and architect subtasks.

    The session and all generated subtasks are saved in PostgreSQL with status
    'PENDING_APPROVAL'. Task execution will NOT start until approval is granted.
    """
    try:
        session = await create_research_session(req.query, db)
        return session
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create research plan and tasks: {str(e)}",
        )


@router.get(
    "/{id}",
    response_model=ResearchSessionResponse,
    summary="Get Research Session Details",
)
async def get_research(
    id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Retrieve full details of a research session including plan, tasks, logs, and report."""
    session = await get_research_session(id, db)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Research session with ID {id} not found.",
        )
    return session


@router.put(
    "/{id}",
    response_model=ResearchSessionResponse,
    summary="Revise Research Plan & Re-architect Tasks",
)
async def revise_research(
    id: UUID,
    req: ResearchReviseRequest,
    db: AsyncSession = Depends(get_db),
):
    """Revise an existing research plan and re-architect subtasks based on user feedback.

    Can only be performed while the research session is in 'PENDING_APPROVAL' status.
    """
    try:
        updated_session = await revise_research_session(id, req.feedback, db)
        return updated_session
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to revise research plan: {str(e)}",
        )


@router.delete(
    "/{id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete Research Session",
)
async def delete_research(
    id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Delete a research session and all associated tasks, plan, and reports."""
    deleted = await delete_research_session(id, db)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Research session with ID {id} not found.",
        )
    return None


@router.post(
    "/{id}/start",
    response_model=StartResearchResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Approve and Start Research Tasks Execution",
)
async def start_research_tasks(
    id: UUID,
    background_tasks: BackgroundTasks,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    """Approve the generated research plan and subtasks, then start wave execution.

    Changes the session status to RUNNING atomically and dispatches research agents
    in the background. Clients can poll GET /api/v1/researches/{id} for progress.
    """
    stmt = (
        update(ResearchSession)
        .where(
            ResearchSession.id == id,
            ResearchSession.status == ResearchStatus.PENDING_APPROVAL,
        )
        .values(status=ResearchStatus.RUNNING)
    )
    res = await db.execute(stmt)
    if res.rowcount == 0:
        session = await get_research_session(id, db)
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Research session with ID {id} not found.",
            )
        if session.status == ResearchStatus.RUNNING:
            response.status_code = status.HTTP_200_OK
            return StartResearchResponse(
                id=id,
                status=session.status,
                message=f"Session {id} is already running.",
            )
        if session.status == ResearchStatus.COMPLETED:
            response.status_code = status.HTTP_200_OK
            return StartResearchResponse(
                id=id,
                status=session.status,
                message=f"Session {id} task is completed.",
            )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Session {id} cannot be started (current status: '{session.status}').",
        )

    await db.commit()
    background_tasks.add_task(execute_research_workflow, id)

    return StartResearchResponse(
        id=id,
        status=ResearchStatus.RUNNING,
        message="Research approved. Task execution initiated in background.",
    )


@router.get(
    "/{id}/tasks",
    response_model=list[ResearchTaskResponse],
    summary="List All Tasks for a Research Session",
)
async def list_research_tasks_endpoint(
    id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Retrieve all subtasks associated with the given research session."""
    session = await get_research_session(id, db)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Research session with ID {id} not found.",
        )
    return await get_research_tasks(id, db)


@router.get(
    "/{id}/tasks/{task_id}",
    response_model=ResearchTaskResponse,
    summary="Get Single Task Details for a Research Session",
)
async def get_research_task_endpoint(
    id: UUID,
    task_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Retrieve details for a specific task using its UUID or task_key (e.g. 'task-01')."""
    session = await get_research_session(id, db)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Research session with ID {id} not found.",
        )

    task = await get_research_task(id, task_id, db)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task '{task_id}' not found in research session {id}.",
        )
    return task
