"""Tests for the scoring engine."""

import pytest

from releaseguard.db.models import Signal, SignalType, Decision
from releaseguard.engine.rules import (
    evaluate_hard_gates,
    RuleResult,
    Severity,
    get_signal_value,
)
from releaseguard.engine.scoring import (
    evaluate_release,
    compute_test_risk,
    compute_coverage_risk,
)


def make_signal(signal_type: SignalType, name: str, value: float) -> Signal:
    """Create a mock signal for testing."""
    signal = Signal(
        id="test-signal",
        release_id="test-release",
        type=signal_type,
        name=name,
        value_num=value,
    )
    return signal


class TestHardGates:
    """Tests for hard gate rules."""

    def test_e2e_pass_rate_pass(self):
        """Test E2E pass rate rule when passing."""
        signals = [make_signal(SignalType.TEST, "e2e_pass_rate", 0.99)]
        results = evaluate_hard_gates(signals)
        assert len(results) == 1
        assert results[0].rule == "E2E_PASS_RATE"
        assert results[0].passed is True

    def test_e2e_pass_rate_fail(self):
        """Test E2E pass rate rule when failing."""
        signals = [make_signal(SignalType.TEST, "e2e_pass_rate", 0.90)]
        results = evaluate_hard_gates(signals)
        assert len(results) == 1
        assert results[0].rule == "E2E_PASS_RATE"
        assert results[0].passed is False
        assert results[0].severity == Severity.BLOCK

    def test_zero_tests_blocks(self):
        """Test that zero tests executed blocks."""
        signals = [make_signal(SignalType.TEST, "total_tests", 0)]
        results = evaluate_hard_gates(signals)
        result = next(r for r in results if r.rule == "TOTAL_TESTS")
        assert result.passed is False
        assert result.severity == Severity.BLOCK

    def test_coverage_drop_warns(self):
        """Test that coverage drop warns."""
        signals = [make_signal(SignalType.COVERAGE, "coverage_drop", 0.03)]
        results = evaluate_hard_gates(signals)
        result = next(r for r in results if r.rule == "COVERAGE_DROP")
        assert result.passed is False
        assert result.severity == Severity.WARN


class TestRiskScoring:
    """Tests for risk scoring."""

    def test_perfect_tests_zero_risk(self):
        """Test that 100% pass rate gives zero test risk."""
        signals = [
            make_signal(SignalType.TEST, "unit_pass_rate", 1.0),
            make_signal(SignalType.TEST, "e2e_pass_rate", 1.0),
        ]
        risk = compute_test_risk(signals)
        assert risk == 0.0

    def test_failed_tests_increase_risk(self):
        """Test that failed tests increase risk."""
        signals = [
            make_signal(SignalType.TEST, "unit_pass_rate", 0.80),
        ]
        risk = compute_test_risk(signals)
        assert risk > 0

    def test_coverage_risk(self):
        """Test coverage risk calculation."""
        # High coverage = low risk
        signals = [make_signal(SignalType.COVERAGE, "line_coverage", 0.90)]
        risk = compute_coverage_risk(signals)
        assert risk == 0.10  # 1 - 0.90

    def test_coverage_drop_risk(self):
        """Test coverage drop increases risk."""
        signals = [make_signal(SignalType.COVERAGE, "coverage_drop", 0.05)]
        risk = compute_coverage_risk(signals)
        assert risk == 0.5  # 0.05 * 10


class TestEvaluateRelease:
    """Tests for the main evaluate_release function."""

    def test_good_release_approved(self):
        """Test that a good release is approved."""
        signals = [
            make_signal(SignalType.TEST, "e2e_pass_rate", 1.0),
            make_signal(SignalType.TEST, "unit_pass_rate", 1.0),
            make_signal(SignalType.TEST, "total_tests", 100),
            make_signal(SignalType.COVERAGE, "line_coverage", 0.90),
        ]
        result = evaluate_release(signals)
        assert result.decision == Decision.APPROVE
        assert result.risk_score < 30

    def test_bad_tests_blocked(self):
        """Test that a release with bad tests is blocked."""
        signals = [
            make_signal(SignalType.TEST, "e2e_pass_rate", 0.50),
            make_signal(SignalType.TEST, "total_tests", 100),
        ]
        result = evaluate_release(signals)
        assert result.decision == Decision.BLOCK

    def test_no_signals_low_risk(self):
        """Test that no signals results in low risk (but may need signals to evaluate)."""
        signals = []
        result = evaluate_release(signals)
        assert result.risk_score == 0

    def test_rationale_included(self):
        """Test that rationale is included for failed rules."""
        signals = [
            make_signal(SignalType.TEST, "e2e_pass_rate", 0.50),
        ]
        result = evaluate_release(signals)
        failed_rules = [r for r in result.rationale if not r.passed]
        assert len(failed_rules) > 0
