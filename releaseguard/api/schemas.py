"""Pydantic schemas for API requests and responses."""

from datetime import datetime
from typing import Optional, Any

from pydantic import BaseModel, Field

from releaseguard.db.models import SignalType, Decision


class ReleaseCreate(BaseModel):
    """Request schema for creating a release."""

    service: str = Field(..., description="Name of the service")
    env: str = Field(..., description="Environment (staging, prod)")
    git_sha: str = Field(..., description="Git commit SHA", min_length=7, max_length=40)
    build_id: str = Field(..., description="CI build identifier")
    pipeline_id: str = Field(..., description="CI pipeline identifier")


class ReleaseResponse(BaseModel):
    """Response schema for a release."""

    id: str
    service: str
    env: str
    git_sha: str
    build_id: str
    pipeline_id: str
    created_at: datetime

    model_config = {"from_attributes": True}


class SignalCreate(BaseModel):
    """Request schema for creating a signal."""

    type: SignalType = Field(..., description="Type of signal (TEST, COVERAGE, PERF, CANARY, DEP)")
    name: str = Field(..., description="Signal name (e.g., 'e2e_pass_rate', 'line_coverage')")
    value_num: Optional[float] = Field(None, description="Numeric value of the signal")
    value_text: Optional[str] = Field(None, description="Text value of the signal")
    metadata_json: Optional[dict[str, Any]] = Field(
        None, description="Additional metadata (e.g., failed test names)"
    )


class SignalResponse(BaseModel):
    """Response schema for a signal."""

    id: str
    release_id: str
    type: SignalType
    name: str
    value_num: Optional[float]
    value_text: Optional[str]
    metadata_json: Optional[dict[str, Any]]
    collected_at: datetime

    model_config = {"from_attributes": True}


class RuleResultResponse(BaseModel):
    """Response schema for a single rule evaluation result."""

    rule: str
    severity: str
    observed: float
    limit: float
    message: str
    passed: bool


class EvaluationResponse(BaseModel):
    """Response schema for an evaluation."""

    decision: Decision
    risk_score: float
    rationale: list[RuleResultResponse]
    report_url: str


class ReportResponse(BaseModel):
    """Response schema for a release report."""

    release: ReleaseResponse
    signals: list[SignalResponse]
    evaluation: Optional[EvaluationResponse]
    summary: dict[str, Any]
