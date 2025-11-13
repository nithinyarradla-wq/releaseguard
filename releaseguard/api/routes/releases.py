"""Release management endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from releaseguard.db import get_db, Release, Signal, Evaluation
from releaseguard.api.schemas import (
    ReleaseCreate,
    ReleaseResponse,
    SignalCreate,
    SignalResponse,
    EvaluationResponse,
    ReportResponse,
    RuleResultResponse,
)
from releaseguard.engine import evaluate_release

router = APIRouter(prefix="/releases", tags=["releases"])


@router.post("", response_model=ReleaseResponse, status_code=status.HTTP_201_CREATED)
def create_release(release_data: ReleaseCreate, db: Session = Depends(get_db)) -> Release:
    """Create a new release record."""
    release = Release(
        service=release_data.service,
        env=release_data.env,
        git_sha=release_data.git_sha,
        build_id=release_data.build_id,
        pipeline_id=release_data.pipeline_id,
    )
    db.add(release)
    db.commit()
    db.refresh(release)
    return release


@router.get("/{release_id}", response_model=ReleaseResponse)
def get_release(release_id: str, db: Session = Depends(get_db)) -> Release:
    """Get a release by ID."""
    release = db.query(Release).filter(Release.id == release_id).first()
    if not release:
        raise HTTPException(status_code=404, detail="Release not found")
    return release


@router.post("/{release_id}/signals", response_model=SignalResponse, status_code=status.HTTP_201_CREATED)
def create_signal(
    release_id: str, signal_data: SignalCreate, db: Session = Depends(get_db)
) -> Signal:
    """Ingest a signal for a release."""
    release = db.query(Release).filter(Release.id == release_id).first()
    if not release:
        raise HTTPException(status_code=404, detail="Release not found")

    signal = Signal(
        release_id=release_id,
        type=signal_data.type,
        name=signal_data.name,
        value_num=signal_data.value_num,
        value_text=signal_data.value_text,
        metadata_json=signal_data.metadata_json,
    )
    db.add(signal)
    db.commit()
    db.refresh(signal)
    return signal


@router.get("/{release_id}/signals", response_model=list[SignalResponse])
def get_signals(release_id: str, db: Session = Depends(get_db)) -> list[Signal]:
    """Get all signals for a release."""
    release = db.query(Release).filter(Release.id == release_id).first()
    if not release:
        raise HTTPException(status_code=404, detail="Release not found")
    return list(release.signals)


@router.post("/{release_id}/evaluate", response_model=EvaluationResponse)
def evaluate(release_id: str, db: Session = Depends(get_db)) -> dict:
    """Evaluate a release and return a decision."""
    release = db.query(Release).filter(Release.id == release_id).first()
    if not release:
        raise HTTPException(status_code=404, detail="Release not found")

    signals = list(release.signals)
    if not signals:
        raise HTTPException(
            status_code=400, detail="No signals found for release. Ingest signals before evaluating."
        )

    result = evaluate_release(signals)

    # Persist evaluation
    evaluation = Evaluation(
        release_id=release_id,
        risk_score=result.risk_score,
        decision=result.decision,
        rationale_json=[r.to_dict() for r in result.rationale],
    )
    db.add(evaluation)
    db.commit()

    return {
        "decision": result.decision,
        "risk_score": round(result.risk_score, 2),
        "rationale": [
            RuleResultResponse(**r.to_dict()) for r in result.rationale if not r.passed
        ],
        "report_url": f"/releases/{release_id}/report",
    }


@router.get("/{release_id}/report", response_model=ReportResponse)
def get_report(release_id: str, db: Session = Depends(get_db)) -> dict:
    """Get a detailed report for a release."""
    release = db.query(Release).filter(Release.id == release_id).first()
    if not release:
        raise HTTPException(status_code=404, detail="Release not found")

    signals = list(release.signals)
    evaluations = list(release.evaluations)

    # Build summary
    summary = {
        "total_signals": len(signals),
        "signal_types": list(set(s.type.value for s in signals)),
    }

    # Get latest evaluation
    latest_eval = None
    if evaluations:
        latest = max(evaluations, key=lambda e: e.evaluated_at)
        latest_eval = {
            "decision": latest.decision,
            "risk_score": latest.risk_score,
            "rationale": [
                RuleResultResponse(**r) for r in latest.rationale_json if not r.get("passed", True)
            ],
            "report_url": f"/releases/{release_id}/report",
        }
        summary["decision"] = latest.decision.value
        summary["risk_score"] = latest.risk_score

    return {
        "release": release,
        "signals": signals,
        "evaluation": latest_eval,
        "summary": summary,
    }
