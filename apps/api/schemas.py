from datetime import datetime
from typing import Any
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field
from apps.db.models import ResearchStatus, TaskStatus


class ResearchCreateRequest(BaseModel):
    query: str = Field(..., min_length=5, description="The research question or topic.")


class ResearchReviseRequest(BaseModel):
    feedback: str = Field(..., min_length=3, description="Feedback or instructions to revise the research plan.")


class ResearchPlanResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str | None = None
    summary: str | None = None
    content: str
    created_at: datetime | None = None
    updated_at: datetime | None = None


class ResearchTaskResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    task_key: str
    title: str
    angle: str | None = None
    task_type: str = "research"
    context: str | None = None
    questions: list[str] = Field(default_factory=list)
    scope: str | None = None
    preferred_sources: list[str] = Field(default_factory=list)
    search_budget: int = 15
    min_sources: int = 6
    depends_on: list[str] = Field(default_factory=list)
    status: TaskStatus = TaskStatus.PENDING
    findings: str | None = None
    wave: int | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class ResearchReportResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    content: str
    word_count: int | None = None
    created_at: datetime | None = None


class DispatchLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    task_key: str
    wave: int
    status: str
    note: str | None = None
    created_at: datetime | None = None


class ResearchSessionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    query: str
    status: ResearchStatus
    created_at: datetime | None = None
    updated_at: datetime | None = None
    plan: ResearchPlanResponse | None = None
    tasks: list[ResearchTaskResponse] = Field(default_factory=list)
    report: ResearchReportResponse | None = None
    dispatch_logs: list[DispatchLogResponse] = Field(default_factory=list)


class StartResearchResponse(BaseModel):
    id: UUID
    status: ResearchStatus
    message: str
