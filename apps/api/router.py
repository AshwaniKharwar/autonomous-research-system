from uuid import UUID
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from apps.api.schemas import (
    ResearchCreateRequest,
    ResearchSessionResponse,
    StartResearchResponse,
)
from apps.db.database import get_db
from apps.db.models import ResearchStatus
from apps.research_agent.service import (
    create_research_session,
    execute_research_workflow,
    get_research_session,
)

router = APIRouter(prefix="/api/v1/research", tags=["Research"])


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


@router.post(
    "/{session_id}/start",
    response_model=StartResearchResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Approve and Start Research Tasks Execution",
)
async def start_research_tasks(
    session_id: UUID,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Approve the generated research plan and subtasks, then start wave execution.

    Changes the session status to RUNNING and dispatches research agents
    in the background. Clients can poll GET /api/v1/research/{session_id} for progress.
    """
    session = await get_research_session(session_id, db)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Research session with ID {session_id} not found.",
        )

    if session.status != ResearchStatus.PENDING_APPROVAL:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Session {session_id} is in '{session.status}' status. Only 'PENDING_APPROVAL' sessions can be started.",
        )

    # Queue background execution
    background_tasks.add_task(execute_research_workflow, session_id)

    return StartResearchResponse(
        id=session_id,
        status=ResearchStatus.RUNNING,
        message="Research approved. Task execution initiated in background.",
    )


@router.get(
    "/{session_id}",
    response_model=ResearchSessionResponse,
    summary="Get Research Session Status and Results",
)
async def get_research_status(
    session_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Retrieve full details of a research session including plan, tasks, logs, and report."""
    session = await get_research_session(session_id, db)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Research session with ID {session_id} not found.",
        )
    return session
