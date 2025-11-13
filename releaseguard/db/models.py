"""SQLAlchemy database models."""

import uuid
from datetime import datetime
from enum import Enum
from typing import Optional

from sqlalchemy import String, Float, Text, ForeignKey, JSON, Enum as SQLEnum
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Base class for all models."""

    pass


class SignalType(str, Enum):
    """Types of signals that can be ingested."""

    TEST = "TEST"
    COVERAGE = "COVERAGE"
    PERF = "PERF"
    CANARY = "CANARY"
    DEP = "DEP"


class Decision(str, Enum):
    """Possible evaluation decisions."""

    APPROVE = "APPROVE"
    WARN = "WARN"
    BLOCK = "BLOCK"


class Release(Base):
    """A release record representing a pipeline run."""

    __tablename__ = "releases"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    service: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    env: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    git_sha: Mapped[str] = mapped_column(String(40), nullable=False)
    build_id: Mapped[str] = mapped_column(String(255), nullable=False)
    pipeline_id: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    signals: Mapped[list["Signal"]] = relationship("Signal", back_populates="release")
    evaluations: Mapped[list["Evaluation"]] = relationship("Evaluation", back_populates="release")


class Signal(Base):
    """A signal collected from the pipeline (test results, coverage, etc.)."""

    __tablename__ = "signals"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    release_id: Mapped[str] = mapped_column(String(36), ForeignKey("releases.id"), nullable=False)
    type: Mapped[SignalType] = mapped_column(SQLEnum(SignalType), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    value_num: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    value_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    collected_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    release: Mapped["Release"] = relationship("Release", back_populates="signals")


class Policy(Base):
    """Scoring policy configuration for a service/environment."""

    __tablename__ = "policies"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    service: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    env: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    rules_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    version: Mapped[int] = mapped_column(default=1)
    updated_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, onupdate=datetime.utcnow)

    evaluations: Mapped[list["Evaluation"]] = relationship("Evaluation", back_populates="policy")


class Evaluation(Base):
    """Result of evaluating a release against a policy."""

    __tablename__ = "evaluations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    release_id: Mapped[str] = mapped_column(String(36), ForeignKey("releases.id"), nullable=False)
    policy_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("policies.id"), nullable=True
    )
    risk_score: Mapped[float] = mapped_column(Float, nullable=False)
    decision: Mapped[Decision] = mapped_column(SQLEnum(Decision), nullable=False)
    rationale_json: Mapped[list] = mapped_column(JSON, nullable=False)
    evaluated_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    release: Mapped["Release"] = relationship("Release", back_populates="evaluations")
    policy: Mapped[Optional["Policy"]] = relationship("Policy", back_populates="evaluations")
