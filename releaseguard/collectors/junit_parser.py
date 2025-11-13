"""JUnit XML parser for test results.

Usage:
    from releaseguard.collectors.junit_parser import parse_junit_xml
    results = parse_junit_xml("path/to/junit.xml")
"""

import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class TestSummary:
    """Summary of test results from JUnit XML."""

    total: int
    passed: int
    failed: int
    skipped: int
    errors: int
    duration_seconds: float
    pass_rate: float
    failed_tests: list[str]


def parse_junit_xml(file_path: str | Path) -> TestSummary:
    """Parse a JUnit XML file and return test summary."""
    tree = ET.parse(file_path)
    root = tree.getroot()

    total = 0
    failed = 0
    skipped = 0
    errors = 0
    duration = 0.0
    failed_tests = []

    # Handle both <testsuites> and single <testsuite> root
    testsuites = root.findall(".//testsuite")
    if root.tag == "testsuite":
        testsuites = [root]

    for testsuite in testsuites:
        total += int(testsuite.get("tests", 0))
        failed += int(testsuite.get("failures", 0))
        skipped += int(testsuite.get("skipped", 0))
        errors += int(testsuite.get("errors", 0))
        duration += float(testsuite.get("time", 0))

        # Collect failed test names
        for testcase in testsuite.findall(".//testcase"):
            if testcase.find("failure") is not None or testcase.find("error") is not None:
                classname = testcase.get("classname", "")
                name = testcase.get("name", "")
                failed_tests.append(f"{classname}.{name}" if classname else name)

    passed = total - failed - skipped - errors
    pass_rate = passed / total if total > 0 else 0.0

    return TestSummary(
        total=total,
        passed=passed,
        failed=failed,
        skipped=skipped,
        errors=errors,
        duration_seconds=duration,
        pass_rate=pass_rate,
        failed_tests=failed_tests,
    )


def to_signals(summary: TestSummary, test_type: str = "unit") -> list[dict]:
    """Convert TestSummary to signal payloads for API ingestion."""
    return [
        {
            "type": "TEST",
            "name": f"{test_type}_pass_rate",
            "value_num": summary.pass_rate,
            "metadata_json": {
                "total": summary.total,
                "passed": summary.passed,
                "failed": summary.failed,
                "skipped": summary.skipped,
            },
        },
        {
            "type": "TEST",
            "name": "total_tests",
            "value_num": summary.total,
        },
        {
            "type": "TEST",
            "name": f"{test_type}_duration_seconds",
            "value_num": summary.duration_seconds,
        },
    ]
