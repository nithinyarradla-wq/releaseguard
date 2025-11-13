"""Rule definitions for release evaluation."""

from dataclasses import dataclass
from enum import Enum
from typing import Optional

from releaseguard.db.models import Signal, SignalType


class Severity(str, Enum):
    """Severity level of a rule violation."""

    BLOCK = "BLOCK"
    WARN = "WARN"
    INFO = "INFO"


@dataclass
class RuleResult:
    """Result of evaluating a single rule."""

    rule: str
    severity: Severity
    observed: float
    limit: float
    message: str
    passed: bool

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "rule": self.rule,
            "severity": self.severity.value,
            "observed": self.observed,
            "limit": self.limit,
            "message": self.message,
            "passed": self.passed,
        }


# Default thresholds for hard gates
DEFAULT_THRESHOLDS = {
    # Test thresholds
    "e2e_pass_rate_min": 0.98,
    "integration_pass_rate_min": 0.95,
    "unit_pass_rate_min": 0.95,
    "total_tests_min": 1,  # At least 1 test must run
    # Coverage thresholds
    "line_coverage_min": 0.70,
    "coverage_drop_max": 0.02,
    # Performance thresholds (for future use)
    "p95_regression_max": 0.15,
    "error_rate_max": 0.01,
    # Canary thresholds (for future use)
    "canary_5xx_rate_max": 0.01,
}


def get_signal_value(signals: list[Signal], signal_type: SignalType, name: str) -> Optional[float]:
    """Get the numeric value of a signal by type and name."""
    for signal in signals:
        if signal.type == signal_type and signal.name == name:
            return signal.value_num
    return None


def evaluate_hard_gates(
    signals: list[Signal], thresholds: Optional[dict] = None
) -> list[RuleResult]:
    """Evaluate hard gate rules that can immediately block a release."""
    results = []
    t = thresholds or DEFAULT_THRESHOLDS

    # Test hard gates
    e2e_pass_rate = get_signal_value(signals, SignalType.TEST, "e2e_pass_rate")
    if e2e_pass_rate is not None:
        passed = e2e_pass_rate >= t["e2e_pass_rate_min"]
        results.append(
            RuleResult(
                rule="E2E_PASS_RATE",
                severity=Severity.BLOCK if not passed else Severity.INFO,
                observed=e2e_pass_rate,
                limit=t["e2e_pass_rate_min"],
                message=f"E2E pass rate {e2e_pass_rate:.1%} {'<' if not passed else '>='} {t['e2e_pass_rate_min']:.0%} threshold",
                passed=passed,
            )
        )

    integration_pass_rate = get_signal_value(signals, SignalType.TEST, "integration_pass_rate")
    if integration_pass_rate is not None:
        passed = integration_pass_rate >= t["integration_pass_rate_min"]
        results.append(
            RuleResult(
                rule="INTEGRATION_PASS_RATE",
                severity=Severity.BLOCK if not passed else Severity.INFO,
                observed=integration_pass_rate,
                limit=t["integration_pass_rate_min"],
                message=f"Integration pass rate {integration_pass_rate:.1%} {'<' if not passed else '>='} {t['integration_pass_rate_min']:.0%} threshold",
                passed=passed,
            )
        )

    unit_pass_rate = get_signal_value(signals, SignalType.TEST, "unit_pass_rate")
    if unit_pass_rate is not None:
        passed = unit_pass_rate >= t["unit_pass_rate_min"]
        results.append(
            RuleResult(
                rule="UNIT_PASS_RATE",
                severity=Severity.BLOCK if not passed else Severity.INFO,
                observed=unit_pass_rate,
                limit=t["unit_pass_rate_min"],
                message=f"Unit pass rate {unit_pass_rate:.1%} {'<' if not passed else '>='} {t['unit_pass_rate_min']:.0%} threshold",
                passed=passed,
            )
        )

    total_tests = get_signal_value(signals, SignalType.TEST, "total_tests")
    if total_tests is not None:
        passed = total_tests >= t["total_tests_min"]
        results.append(
            RuleResult(
                rule="TOTAL_TESTS",
                severity=Severity.BLOCK if not passed else Severity.INFO,
                observed=total_tests,
                limit=t["total_tests_min"],
                message=f"Total tests executed: {int(total_tests)} {'<' if not passed else '>='} {t['total_tests_min']} minimum",
                passed=passed,
            )
        )

    # Coverage hard gates
    line_coverage = get_signal_value(signals, SignalType.COVERAGE, "line_coverage")
    if line_coverage is not None:
        passed = line_coverage >= t["line_coverage_min"]
        results.append(
            RuleResult(
                rule="LINE_COVERAGE",
                severity=Severity.WARN if not passed else Severity.INFO,
                observed=line_coverage,
                limit=t["line_coverage_min"],
                message=f"Line coverage {line_coverage:.1%} {'<' if not passed else '>='} {t['line_coverage_min']:.0%} threshold",
                passed=passed,
            )
        )

    coverage_drop = get_signal_value(signals, SignalType.COVERAGE, "coverage_drop")
    if coverage_drop is not None:
        passed = coverage_drop <= t["coverage_drop_max"]
        results.append(
            RuleResult(
                rule="COVERAGE_DROP",
                severity=Severity.WARN if not passed else Severity.INFO,
                observed=coverage_drop,
                limit=t["coverage_drop_max"],
                message=f"Coverage drop {coverage_drop:.1%} {'>' if not passed else '<='} {t['coverage_drop_max']:.0%} max allowed",
                passed=passed,
            )
        )

    return results


def evaluate_performance_gates(
    signals: list[Signal], thresholds: Optional[dict] = None
) -> list[RuleResult]:
    """Evaluate performance-related rules."""
    results = []
    t = thresholds or DEFAULT_THRESHOLDS

    p95_regression = get_signal_value(signals, SignalType.PERF, "p95_regression")
    if p95_regression is not None:
        passed = p95_regression <= t["p95_regression_max"]
        results.append(
            RuleResult(
                rule="P95_REGRESSION",
                severity=Severity.BLOCK if not passed else Severity.INFO,
                observed=p95_regression,
                limit=t["p95_regression_max"],
                message=f"P95 latency regression {p95_regression:.1%} {'>' if not passed else '<='} {t['p95_regression_max']:.0%} max",
                passed=passed,
            )
        )

    error_rate = get_signal_value(signals, SignalType.PERF, "error_rate")
    if error_rate is not None:
        passed = error_rate <= t["error_rate_max"]
        results.append(
            RuleResult(
                rule="ERROR_RATE",
                severity=Severity.BLOCK if not passed else Severity.INFO,
                observed=error_rate,
                limit=t["error_rate_max"],
                message=f"Error rate {error_rate:.2%} {'>' if not passed else '<='} {t['error_rate_max']:.1%} max",
                passed=passed,
            )
        )

    return results


def evaluate_canary_gates(
    signals: list[Signal], thresholds: Optional[dict] = None
) -> list[RuleResult]:
    """Evaluate canary health rules."""
    results = []
    t = thresholds or DEFAULT_THRESHOLDS

    canary_5xx_rate = get_signal_value(signals, SignalType.CANARY, "5xx_rate")
    if canary_5xx_rate is not None:
        passed = canary_5xx_rate <= t["canary_5xx_rate_max"]
        results.append(
            RuleResult(
                rule="CANARY_5XX_RATE",
                severity=Severity.BLOCK if not passed else Severity.INFO,
                observed=canary_5xx_rate,
                limit=t["canary_5xx_rate_max"],
                message=f"Canary 5xx rate {canary_5xx_rate:.2%} {'>' if not passed else '<='} {t['canary_5xx_rate_max']:.1%} max",
                passed=passed,
            )
        )

    return results
