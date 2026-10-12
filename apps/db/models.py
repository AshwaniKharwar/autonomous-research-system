import enum
from uuid import uuid4
from sqlalchemy import (
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship
from apps.db.database import Base


class ResearchStatus(str, enum.Enum):
    PENDING_APPROVAL = "PENDING_APPROVAL"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class TaskStatus(str, enum.Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class ResearchSession(Base):
    __tablename__ = "research_sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    query = Column(Text, nullable=False)
    status = Column(
        Enum(ResearchStatus, name="research_status_enum"),
        default=ResearchStatus.PENDING_APPROVAL,
        nullable=False,
        index=True,
    )
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    plan = relationship(
        "ResearchPlan",
        back_populates="session",
        uselist=False,
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    tasks = relationship(
        "ResearchTask",
        back_populates="session",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="ResearchTask.task_key",
    )
    report = relationship(
        "ResearchReport",
        back_populates="session",
        uselist=False,
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    dispatch_logs = relationship(
        "DispatchLog",
        back_populates="session",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="DispatchLog.created_at",
    )


class ResearchPlan(Base):
    __tablename__ = "research_plans"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    session_id = Column(
        UUID(as_uuid=True),
        ForeignKey("research_sessions.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    title = Column(String(500), nullable=True)
    summary = Column(Text, nullable=True)
    content = Column(Text, nullable=False)
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    session = relationship("ResearchSession", back_populates="plan")


class ResearchTask(Base):
    __tablename__ = "research_tasks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    session_id = Column(
        UUID(as_uuid=True),
        ForeignKey("research_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    task_key = Column(String(50), nullable=False)
    title = Column(String(500), nullable=False)
    angle = Column(String(500), nullable=True)
    task_type = Column(String(50), default="research", nullable=False)
    context = Column(Text, nullable=True)
    questions = Column(JSONB, nullable=False, default=list)
    scope = Column(Text, nullable=True)
    preferred_sources = Column(JSONB, default=list)
    search_budget = Column(Integer, default=15, nullable=False)
    min_sources = Column(Integer, default=6, nullable=False)
    depends_on = Column(JSONB, default=list, nullable=False)
    status = Column(
        Enum(TaskStatus, name="task_status_enum"),
        default=TaskStatus.PENDING,
        nullable=False,
        index=True,
    )
    findings = Column(Text, nullable=True)
    sources = Column(JSONB, default=list)
    wave = Column(Integer, nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    session = relationship("ResearchSession", back_populates="tasks")


class ResearchReport(Base):
    __tablename__ = "research_reports"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    session_id = Column(
        UUID(as_uuid=True),
        ForeignKey("research_sessions.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    content = Column(Text, nullable=False)
    word_count = Column(Integer, nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    session = relationship("ResearchSession", back_populates="report")


class DispatchLog(Base):
    __tablename__ = "dispatch_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    session_id = Column(
        UUID(as_uuid=True),
        ForeignKey("research_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    task_key = Column(String(50), nullable=False)
    wave = Column(Integer, nullable=False)
    status = Column(String(50), nullable=False)
    note = Column(Text, nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    session = relationship("ResearchSession", back_populates="dispatch_logs")
