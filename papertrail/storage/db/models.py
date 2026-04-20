"""SQLAlchemy ORM models matching the database schema."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from papertrail.storage.db.base import Base


# ---------------------------------------------------------------------------
# Playbooks
# ---------------------------------------------------------------------------

class PlaybookModel(Base):
    __tablename__ = "playbooks"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    slug: Mapped[str] = mapped_column(String(128), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    version: Mapped[str] = mapped_column(String(32), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    extends_playbook_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("playbooks.id")
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_base: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    configs: Mapped[list[PlaybookConfigModel]] = relationship(
        back_populates="playbook", cascade="all, delete-orphan"
    )

    __table_args__ = (
        UniqueConstraint("slug", "version", name="uq_playbooks_slug_version"),
        Index("idx_playbooks_slug_active", "slug", postgresql_where=("is_active = TRUE")),
    )


class PlaybookConfigModel(Base):
    __tablename__ = "playbook_configs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    playbook_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("playbooks.id", ondelete="CASCADE"), nullable=False
    )
    config_type: Mapped[str] = mapped_column(
        String(32),
        CheckConstraint(
            "config_type IN ('meta','classify','schema','validate','rules','postprocess')"
        ),
        nullable=False,
    )
    content: Mapped[dict] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    playbook: Mapped[PlaybookModel] = relationship(back_populates="configs")

    __table_args__ = (
        UniqueConstraint("playbook_id", "config_type", name="uq_configs_playbook_type"),
        Index("idx_configs_playbook", "playbook_id"),
    )


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------

class ToolModel(Base):
    __tablename__ = "tools"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    handler: Mapped[str] = mapped_column(String(255), nullable=False)
    input_schema: Mapped[dict] = mapped_column(JSONB, nullable=False)
    output_schema: Mapped[dict] = mapped_column(JSONB, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


# ---------------------------------------------------------------------------
# Runs
# ---------------------------------------------------------------------------

class RunModel(Base):
    __tablename__ = "runs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    run_uid: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    playbook_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("playbooks.id")
    )
    playbook_slug: Mapped[str] = mapped_column(String(128), nullable=False)
    playbook_version: Mapped[str] = mapped_column(String(32), nullable=False)

    input_file_uri: Mapped[str] = mapped_column(Text, nullable=False)
    input_file_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    input_file_name: Mapped[str | None] = mapped_column(String(512))
    input_file_size_bytes: Mapped[int | None] = mapped_column(Integer)
    input_file_mime: Mapped[str | None] = mapped_column(String(64))

    status: Mapped[str] = mapped_column(
        String(32),
        CheckConstraint(
            "status IN ('created','running','awaiting_hitl','completed','failed','cancelled')"
        ),
        nullable=False,
    )
    decision: Mapped[str | None] = mapped_column(
        String(32),
        CheckConstraint("decision IN ('approve','flag','reject','escalate')"),
    )

    aggregate_confidence: Mapped[float | None] = mapped_column(Float)
    confidence_breakdown: Mapped[dict | None] = mapped_column(JSONB)
    warnings: Mapped[dict | None] = mapped_column(JSONB)

    superseded_by_run_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("runs.id")
    )
    requested_by: Mapped[str | None] = mapped_column(String(128))

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    duration_ms: Mapped[int | None] = mapped_column(Integer)

    passes: Mapped[list[RunPassModel]] = relationship(
        back_populates="run", cascade="all, delete-orphan"
    )
    elements: Mapped[list[RunElementModel]] = relationship(
        back_populates="run", cascade="all, delete-orphan"
    )
    corrections: Mapped[list[RunCorrectionModel]] = relationship(
        back_populates="run", cascade="all, delete-orphan"
    )
    rule_evaluations: Mapped[list[RunRuleEvaluationModel]] = relationship(
        back_populates="run", cascade="all, delete-orphan"
    )
    hitl_events: Mapped[list[RunHITLEventModel]] = relationship(
        back_populates="run", cascade="all, delete-orphan"
    )
    trace_events: Mapped[list[TraceEventModel]] = relationship(
        back_populates="run", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("idx_runs_hash", "input_file_hash"),
        Index("idx_runs_playbook_status", "playbook_id", "status"),
        Index("idx_runs_created", "created_at"),
        Index(
            "idx_runs_status_pending",
            "status",
            postgresql_where="status IN ('created','running','awaiting_hitl')",
        ),
    )


class RunPassModel(Base):
    __tablename__ = "run_passes"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("runs.id", ondelete="CASCADE"), nullable=False
    )
    pass_name: Mapped[str] = mapped_column(String(32), nullable=False)
    pass_order: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(
        String(32),
        CheckConstraint("status IN ('pending','running','success','failed','skipped')"),
        nullable=False,
    )
    confidence: Mapped[float | None] = mapped_column(Float)
    output: Mapped[dict | None] = mapped_column(JSONB)
    output_blob_uri: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    duration_ms: Mapped[int | None] = mapped_column(Integer)
    error: Mapped[str | None] = mapped_column(Text)

    run: Mapped[RunModel] = relationship(back_populates="passes")

    __table_args__ = (
        Index("idx_passes_run", "run_id", "pass_order"),
    )


class RunElementModel(Base):
    __tablename__ = "run_elements"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("runs.id", ondelete="CASCADE"), nullable=False
    )
    element_name: Mapped[str] = mapped_column(String(128), nullable=False)
    element_type: Mapped[str | None] = mapped_column(String(32))
    value: Mapped[dict | None] = mapped_column(JSONB)
    llm_confidence: Mapped[float | None] = mapped_column(Float)
    ocr_confidence: Mapped[float | None] = mapped_column(Float)
    source_region: Mapped[str | None] = mapped_column(String(128))
    notes: Mapped[str | None] = mapped_column(Text)
    validation_status: Mapped[str | None] = mapped_column(
        String(32),
        CheckConstraint(
            "validation_status IN ('pending','pass','fail','unable_to_evaluate')"
        ),
    )
    validation_details: Mapped[dict | None] = mapped_column(JSONB)
    is_final: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    attempt_number: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    run: Mapped[RunModel] = relationship(back_populates="elements")

    __table_args__ = (
        Index("idx_elements_run", "run_id", "element_name"),
        Index("idx_elements_final", "run_id", postgresql_where="is_final = TRUE"),
    )


class RunCorrectionModel(Base):
    __tablename__ = "run_corrections"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("runs.id", ondelete="CASCADE"), nullable=False
    )
    attempt_number: Mapped[int] = mapped_column(Integer, nullable=False)
    element_name: Mapped[str] = mapped_column(String(128), nullable=False)
    hint_text: Mapped[str] = mapped_column(Text, nullable=False)
    previous_value: Mapped[dict | None] = mapped_column(JSONB)
    new_value: Mapped[dict | None] = mapped_column(JSONB)
    succeeded: Mapped[bool | None] = mapped_column(Boolean)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    run: Mapped[RunModel] = relationship(back_populates="corrections")

    __table_args__ = (
        Index("idx_corrections_run", "run_id", "attempt_number"),
    )


class RunRuleEvaluationModel(Base):
    __tablename__ = "run_rule_evaluations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("runs.id", ondelete="CASCADE"), nullable=False
    )
    rule_name: Mapped[str] = mapped_column(String(128), nullable=False)
    rule_type: Mapped[str] = mapped_column(
        String(32),
        CheckConstraint("rule_type IN ('condition','transformation')"),
        nullable=False,
    )
    fired: Mapped[bool] = mapped_column(Boolean, nullable=False)
    action: Mapped[str | None] = mapped_column(String(32))
    reason: Mapped[str | None] = mapped_column(Text)
    evaluation_details: Mapped[dict | None] = mapped_column(JSONB)
    order_executed: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    run: Mapped[RunModel] = relationship(back_populates="rule_evaluations")

    __table_args__ = (
        Index("idx_rules_run", "run_id", "order_executed"),
    )


class RunHITLEventModel(Base):
    __tablename__ = "run_hitl_events"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("runs.id", ondelete="CASCADE"), nullable=False
    )
    checkpoint_type: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(
        String(32),
        CheckConstraint("status IN ('awaiting','resolved','abandoned')"),
        nullable=False,
    )
    context: Mapped[dict | None] = mapped_column(JSONB)
    resolution: Mapped[dict | None] = mapped_column(JSONB)
    resolved_by: Mapped[str | None] = mapped_column(String(128))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    run: Mapped[RunModel] = relationship(back_populates="hitl_events")

    __table_args__ = (
        Index(
            "idx_hitl_awaiting",
            "status",
            postgresql_where="status = 'awaiting'",
        ),
    )


class TraceEventModel(Base):
    __tablename__ = "trace_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("runs.id", ondelete="CASCADE"), nullable=False
    )
    ts: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    stage: Mapped[str] = mapped_column(String(64), nullable=False)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    level: Mapped[str] = mapped_column(
        String(16),
        CheckConstraint("level IN ('debug','info','warning','error')"),
        default="info",
        nullable=False,
    )
    payload: Mapped[dict | None] = mapped_column(JSONB)

    run: Mapped[RunModel] = relationship(back_populates="trace_events")

    __table_args__ = (
        Index("idx_trace_run_ts", "run_id", "ts"),
        Index(
            "idx_trace_errors",
            "level",
            "ts",
            postgresql_where="level IN ('warning','error')",
        ),
    )
