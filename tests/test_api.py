"""Tests for API endpoints."""

import pytest


def test_health_check(client):
    """Test health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy", "service": "releaseguard"}


def test_root(client):
    """Test root endpoint."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["service"] == "ReleaseGuard"
    assert data["version"] == "0.1.0"


def test_create_release(client):
    """Test creating a release."""
    response = client.post(
        "/releases",
        json={
            "service": "payments",
            "env": "staging",
            "git_sha": "abc1234567890",
            "build_id": "build-123",
            "pipeline_id": "gha-991",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["service"] == "payments"
    assert data["env"] == "staging"
    assert data["git_sha"] == "abc1234567890"
    assert "id" in data


def test_get_release(client):
    """Test getting a release."""
    # Create a release first
    create_response = client.post(
        "/releases",
        json={
            "service": "payments",
            "env": "staging",
            "git_sha": "abc1234567890",
            "build_id": "build-123",
            "pipeline_id": "gha-991",
        },
    )
    release_id = create_response.json()["id"]

    # Get the release
    response = client.get(f"/releases/{release_id}")
    assert response.status_code == 200
    assert response.json()["id"] == release_id


def test_get_release_not_found(client):
    """Test getting a non-existent release."""
    response = client.get("/releases/nonexistent-id")
    assert response.status_code == 404


def test_create_signal(client):
    """Test creating a signal for a release."""
    # Create a release first
    create_response = client.post(
        "/releases",
        json={
            "service": "payments",
            "env": "staging",
            "git_sha": "abc1234567890",
            "build_id": "build-123",
            "pipeline_id": "gha-991",
        },
    )
    release_id = create_response.json()["id"]

    # Create a signal
    response = client.post(
        f"/releases/{release_id}/signals",
        json={
            "type": "TEST",
            "name": "e2e_pass_rate",
            "value_num": 0.98,
            "metadata_json": {"total": 100, "passed": 98},
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["type"] == "TEST"
    assert data["name"] == "e2e_pass_rate"
    assert data["value_num"] == 0.98


def test_get_signals(client):
    """Test getting signals for a release."""
    # Create a release first
    create_response = client.post(
        "/releases",
        json={
            "service": "payments",
            "env": "staging",
            "git_sha": "abc1234567890",
            "build_id": "build-123",
            "pipeline_id": "gha-991",
        },
    )
    release_id = create_response.json()["id"]

    # Create signals
    client.post(
        f"/releases/{release_id}/signals",
        json={"type": "TEST", "name": "e2e_pass_rate", "value_num": 0.98},
    )
    client.post(
        f"/releases/{release_id}/signals",
        json={"type": "COVERAGE", "name": "line_coverage", "value_num": 0.85},
    )

    # Get signals
    response = client.get(f"/releases/{release_id}/signals")
    assert response.status_code == 200
    signals = response.json()
    assert len(signals) == 2


def test_evaluate_release_approve(client):
    """Test evaluating a release that should be approved."""
    # Create a release
    create_response = client.post(
        "/releases",
        json={
            "service": "payments",
            "env": "staging",
            "git_sha": "abc1234567890",
            "build_id": "build-123",
            "pipeline_id": "gha-991",
        },
    )
    release_id = create_response.json()["id"]

    # Add good signals
    client.post(
        f"/releases/{release_id}/signals",
        json={"type": "TEST", "name": "e2e_pass_rate", "value_num": 1.0},
    )
    client.post(
        f"/releases/{release_id}/signals",
        json={"type": "TEST", "name": "unit_pass_rate", "value_num": 1.0},
    )
    client.post(
        f"/releases/{release_id}/signals",
        json={"type": "TEST", "name": "total_tests", "value_num": 100},
    )
    client.post(
        f"/releases/{release_id}/signals",
        json={"type": "COVERAGE", "name": "line_coverage", "value_num": 0.90},
    )

    # Evaluate
    response = client.post(f"/releases/{release_id}/evaluate")
    assert response.status_code == 200
    data = response.json()
    assert data["decision"] == "APPROVE"
    assert data["risk_score"] < 30


def test_evaluate_release_block(client):
    """Test evaluating a release that should be blocked."""
    # Create a release
    create_response = client.post(
        "/releases",
        json={
            "service": "payments",
            "env": "staging",
            "git_sha": "abc1234567890",
            "build_id": "build-123",
            "pipeline_id": "gha-991",
        },
    )
    release_id = create_response.json()["id"]

    # Add bad signals
    client.post(
        f"/releases/{release_id}/signals",
        json={"type": "TEST", "name": "e2e_pass_rate", "value_num": 0.50},  # Very low
    )
    client.post(
        f"/releases/{release_id}/signals",
        json={"type": "TEST", "name": "total_tests", "value_num": 100},
    )

    # Evaluate
    response = client.post(f"/releases/{release_id}/evaluate")
    assert response.status_code == 200
    data = response.json()
    assert data["decision"] == "BLOCK"
    assert len(data["rationale"]) > 0


def test_evaluate_release_no_signals(client):
    """Test evaluating a release without signals."""
    # Create a release
    create_response = client.post(
        "/releases",
        json={
            "service": "payments",
            "env": "staging",
            "git_sha": "abc1234567890",
            "build_id": "build-123",
            "pipeline_id": "gha-991",
        },
    )
    release_id = create_response.json()["id"]

    # Evaluate without signals
    response = client.post(f"/releases/{release_id}/evaluate")
    assert response.status_code == 400


def test_get_report(client):
    """Test getting a report for a release."""
    # Create a release
    create_response = client.post(
        "/releases",
        json={
            "service": "payments",
            "env": "staging",
            "git_sha": "abc1234567890",
            "build_id": "build-123",
            "pipeline_id": "gha-991",
        },
    )
    release_id = create_response.json()["id"]

    # Add signals
    client.post(
        f"/releases/{release_id}/signals",
        json={"type": "TEST", "name": "e2e_pass_rate", "value_num": 0.99},
    )
    client.post(
        f"/releases/{release_id}/signals",
        json={"type": "TEST", "name": "total_tests", "value_num": 100},
    )

    # Evaluate first
    client.post(f"/releases/{release_id}/evaluate")

    # Get report
    response = client.get(f"/releases/{release_id}/report")
    assert response.status_code == 200
    data = response.json()
    assert "release" in data
    assert "signals" in data
    assert "evaluation" in data
    assert "summary" in data
