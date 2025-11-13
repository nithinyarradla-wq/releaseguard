"""Risk scoring engine."""

from dataclasses import dataclass
from typing import Optional

from releaseguard.config import settings
from releaseguard.db.models import Signal, SignalType, Decision
from releaseguard.engine.rules import (
    RuleResult,
    Severity,
    evaluate_hard_gates,
    evaluate_performance_gates,
    evaluate_canary_gates,
    get_signal_value,
)


# Category weights for weighted risk score
DEFAULT_WEIGHTS = {
    "tests": 0.35,
    "coverage": 0.10,
    "perf": 0.25,
    "canary": 0.25,
    "deps": 0.05,
}


@dataclass
class EvaluationResult:
    """Result of evaluating a release."""

    decision: Decision
    risk_score: float
    rationale: list[RuleResult]

    def to_dict(self) -> dict:
        """Convert to dictionary for API response."""
        return {
            "decision": self.decision.value,
            "risk_score": round(self.risk_score, 2),
            "rationale": [r.to_dict() for r in self.rationale if not r.passed],
        }


def compute_test_risk(signals: list[Signal]) -> float:
    """Compute risk score for test signals (0-1)."""
    risks = []

    unit_pass_rate = get_signal_value(signals, SignalType.TEST, "unit_pass_rate")
    if unit_pass_rate is not None:
        risks.append(1 - unit_pass_rate)

    integration_pass_rate = get_signal_value(signals, SignalType.TEST, "integration_pass_rate")
    if integration_pass_rate is not None:
        risks.append(1 - integration_pass_rate)

    e2e_pass_rate = get_signal_value(signals, SignalType.TEST, "e2e_pass_rate")
    if e2e_pass_rate is not None:
        # E2E failures are weighted more heavily
        risks.append((1 - e2e_pass_rate) * 1.5)

    flaky_rate = get_signal_value(signals, SignalType.TEST, "flaky_rate")
    if flaky_rate is not None:
        risks.append(flaky_rate * 0.5)

    if not risks:
        return 0.0

    return min(1.0, sum(risks) / len(risks))


def compute_coverage_risk(signals: list[Signal]) -> float:
    """Compute risk score for coverage signals (0-1)."""
    risks = []

    line_coverage = get_signal_value(signals, SignalType.COVERAGE, "line_coverage")
    if line_coverage is not None:
        # Lower coverage = higher risk
        # 100% coverage = 0 risk, 0% coverage = 1 risk
        risks.append(1 - line_coverage)

    coverage_drop = get_signal_value(signals, SignalType.COVERAGE, "coverage_drop")
    if coverage_drop is not None:
        # Coverage drops are weighted based on severity
        # 2% drop = 0.2 risk, 10% drop = 1.0 risk
        risks.append(min(1.0, coverage_drop * 10))

    if not risks:
        return 0.0

    return min(1.0, max(risks))


def compute_perf_risk(signals: list[Signal]) -> float:
    """Compute risk score for performance signals (0-1)."""
    risks = []

    p95_regression = get_signal_value(signals, SignalType.PERF, "p95_regression")
    if p95_regression is not None:
        # 15% regression = 1.0 risk
        risks.append(min(1.0, p95_regression / 0.15))

    error_rate = get_signal_value(signals, SignalType.PERF, "error_rate")
    if error_rate is not None:
        # 1% error rate = 1.0 risk
        risks.append(min(1.0, error_rate / 0.01))

    if not risks:
        return 0.0

    return min(1.0, max(risks))


def compute_canary_risk(signals: list[Signal]) -> float:
    """Compute risk score for canary signals (0-1)."""
    risks = []

    canary_5xx_rate = get_signal_value(signals, SignalType.CANARY, "5xx_rate")
    if canary_5xx_rate is not None:
        # 1% 5xx rate = 1.0 risk
        risks.append(min(1.0, canary_5xx_rate / 0.01))

    canary_latency_regression = get_signal_value(signals, SignalType.CANARY, "p95_regression")
    if canary_latency_regression is not None:
        risks.append(min(1.0, canary_latency_regression / 0.15))

    if not risks:
        return 0.0

    return min(1.0, max(risks))


def compute_weighted_risk_score(
    signals: list[Signal], weights: Optional[dict] = None
) -> float:
    """Compute overall weighted risk score (0-100)."""
    w = weights or DEFAULT_WEIGHTS

    test_risk = compute_test_risk(signals)
    coverage_risk = compute_coverage_risk(signals)
    perf_risk = compute_perf_risk(signals)
    canary_risk = compute_canary_risk(signals)
    # deps_risk not implemented in MVP

    weighted_score = (
        w["tests"] * test_risk
        + w["coverage"] * coverage_risk
        + w["perf"] * perf_risk
        + w["canary"] * canary_risk
    )

    return weighted_score * 100


def evaluate_release(
    signals: list[Signal],
    thresholds: Optional[dict] = None,
    weights: Optional[dict] = None,
) -> EvaluationResult:
    """
    Evaluate a release based on its signals.

    Returns a decision (APPROVE/WARN/BLOCK), risk score, and rationale.
    """
    # Collect all rule results
    all_results: list[RuleResult] = []

    # Run hard gates
    all_results.extend(evaluate_hard_gates(signals, thresholds))
    all_results.extend(evaluate_performance_gates(signals, thresholds))
    all_results.extend(evaluate_canary_gates(signals, thresholds))

    # Check for any BLOCK-level failures
    has_block = any(r.severity == Severity.BLOCK and not r.passed for r in all_results)
    has_warn = any(r.severity == Severity.WARN and not r.passed for r in all_results)

    # Compute weighted risk score
    risk_score = compute_weighted_risk_score(signals, weights)

    # Determine decision based on hard gates first, then risk score
    if has_block:
        decision = Decision.BLOCK
    elif has_warn or risk_score >= settings.warn_threshold:
        decision = Decision.WARN
    elif risk_score >= settings.approve_threshold:
        decision = Decision.WARN
    else:
        decision = Decision.APPROVE

    # If risk score is very high, escalate to BLOCK
    if risk_score >= settings.warn_threshold:
        decision = Decision.BLOCK

    return EvaluationResult(
        decision=decision,
        risk_score=risk_score,
        rationale=all_results,
    )
