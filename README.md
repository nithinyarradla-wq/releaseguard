# ReleaseGuard

An Automated Release Quality Gate Platform that evaluates pipeline signals and makes release decisions.

## Overview

ReleaseGuard ingests signals from CI/CD pipelines (tests, coverage, performance, canary metrics), computes a Risk Score, and returns a decision:

- **APPROVE** - Safe to ship
- **WARN** - Ship allowed but requires sign-off
- **BLOCK** - Do not ship

## Features

- REST API for release management and signal ingestion
- Hard gates for tests and coverage thresholds
- Weighted risk scoring engine
- Detailed rationale for decisions
- Release reports with signal summaries

## Quick Start

### Installation

```bash
pip install -e ".[dev]"
```

### Run the Server

```bash
python run.py
```

The API will be available at `http://localhost:8000`. View docs at `http://localhost:8000/docs`.

### Run Tests

```bash
pytest tests/ -v
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/releases` | Create a release record |
| GET | `/releases/{id}` | Get release details |
| POST | `/releases/{id}/signals` | Ingest a signal |
| GET | `/releases/{id}/signals` | List signals for a release |
| POST | `/releases/{id}/evaluate` | Evaluate release and get decision |
| GET | `/releases/{id}/report` | Get detailed release report |
| GET | `/health` | Health check |

## Example Usage

### 1. Create a Release

```bash
curl -X POST http://localhost:8000/releases \
  -H "Content-Type: application/json" \
  -d '{
    "service": "payments",
    "env": "staging",
    "git_sha": "abc1234567890",
    "build_id": "build-123",
    "pipeline_id": "gha-991"
  }'
```

### 2. Ingest Signals

```bash
# Test results
curl -X POST http://localhost:8000/releases/{id}/signals \
  -H "Content-Type: application/json" \
  -d '{
    "type": "TEST",
    "name": "e2e_pass_rate",
    "value_num": 0.98
  }'

# Coverage
curl -X POST http://localhost:8000/releases/{id}/signals \
  -H "Content-Type: application/json" \
  -d '{
    "type": "COVERAGE",
    "name": "line_coverage",
    "value_num": 0.85
  }'
```

### 3. Evaluate

```bash
curl -X POST http://localhost:8000/releases/{id}/evaluate
```

Response:
```json
{
  "decision": "APPROVE",
  "risk_score": 12.5,
  "rationale": [],
  "report_url": "/releases/{id}/report"
}
```

## Signal Types

| Type | Signals |
|------|---------|
| TEST | `unit_pass_rate`, `integration_pass_rate`, `e2e_pass_rate`, `total_tests`, `flaky_rate` |
| COVERAGE | `line_coverage`, `coverage_drop` |
| PERF | `p95_regression`, `error_rate` |
| CANARY | `5xx_rate`, `p95_regression` |

## Hard Gate Thresholds

| Rule | Threshold | Severity |
|------|-----------|----------|
| E2E Pass Rate | >= 98% | BLOCK |
| Integration Pass Rate | >= 95% | BLOCK |
| Unit Pass Rate | >= 95% | BLOCK |
| Total Tests | >= 1 | BLOCK |
| Line Coverage | >= 70% | WARN |
| Coverage Drop | <= 2% | WARN |
| P95 Regression | <= 15% | BLOCK |
| Error Rate | <= 1% | BLOCK |

## Project Structure

```
releaseguard/
├── api/           # FastAPI routes and schemas
├── engine/        # Scoring and rules engine
├── db/            # Database models and migrations
├── collectors/    # Signal parsers (JUnit, coverage, etc.)
└── config.py      # Configuration
```

## Configuration

Environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `RELEASEGUARD_DATABASE_URL` | `sqlite:///./releaseguard.db` | Database connection |
| `RELEASEGUARD_DEBUG` | `false` | Debug mode |
| `RELEASEGUARD_APPROVE_THRESHOLD` | `30.0` | Risk score below this = APPROVE |
| `RELEASEGUARD_WARN_THRESHOLD` | `60.0` | Risk score above this = BLOCK |

## License

MIT
