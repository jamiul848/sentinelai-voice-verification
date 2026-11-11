"""Unit and integration tests for the SentinelAI FastAPI application and audio API.

NOTE ON TEST SIGNALS:
All test audio signals used here are mathematically generated synthetic fixtures.
No real speaker data or fabricated human voice recordings are used.
"""

import io
from pathlib import Path
import pytest
from fastapi import FastAPI, HTTPException, UploadFile
from fastapi.testclient import TestClient

from sentinelai.audio.api import preprocess_audio_file
from sentinelai.main import app, create_app


@pytest.fixture
def client() -> TestClient:
    """Fixture providing a TestClient configured with the main FastAPI application."""
    return TestClient(app)


# -----------------------------------------------------------------------------
# Application Startup and Route Registration Tests
# -----------------------------------------------------------------------------


def test_fastapi_app_initialization() -> None:
    """Verify that create_app returns a valid FastAPI instance with correct metadata."""
    new_app = create_app()
    assert isinstance(new_app, FastAPI)
    assert new_app.title == "SentinelAI Voice Verification Platform"
    assert new_app.version == "0.1.0"


def test_app_health_and_root_endpoints(client: TestClient) -> None:
    """Verify that root (/) and health (/health) endpoints respond correctly."""
    root_res = client.get("/")
    assert root_res.status_code == 200
    root_json = root_res.json()
    assert root_json["status"] == "online"
    assert "SentinelAI" in root_json["service"]

    health_res = client.get("/health")
    assert health_res.status_code == 200
    assert health_res.json() == {"status": "healthy"}


def test_audio_preprocess_route_is_registered(client: TestClient) -> None:
    """Verify that /audio/preprocess route is registered on the FastAPI application."""
    # A GET request to a POST endpoint should yield 405 Method Not Allowed (proving route exists)
    res = client.get("/audio/preprocess")
    assert res.status_code == 405

    # A POST request without body should yield 422 Unprocessable Content (FastAPI validation)
    res_post = client.post("/audio/preprocess")
    assert res_post.status_code == 422


# -----------------------------------------------------------------------------
# Application Integration Tests for /audio/preprocess via TestClient
# -----------------------------------------------------------------------------


def test_app_preprocess_valid_file(client: TestClient, synthetic_mono_wav_16k: Path) -> None:
    """Verify full HTTP POST /audio/preprocess upload workflow with a valid synthetic WAV file."""
    with open(synthetic_mono_wav_16k, "rb") as f:
        response = client.post(
            "/audio/preprocess",
            files={"file": ("test_synthetic_mono.wav", f, "audio/wav")},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["is_valid"] is True
    assert data["filename"] == "test_synthetic_mono.wav"
    assert data["sample_rate"] == 16000
    assert data["num_channels"] == 1
    assert data["tensor_shape"] == [1, data["num_samples"]]
    assert "metrics" in data
    assert data["metrics"]["is_silent"] is False


def test_app_preprocess_empty_file(client: TestClient) -> None:
    """Verify that uploading an empty 0-byte file returns HTTP 400 Bad Request."""
    response = client.post(
        "/audio/preprocess",
        files={"file": ("empty.wav", io.BytesIO(b""), "audio/wav")},
    )
    assert response.status_code == 400
    assert "empty" in response.json()["detail"].lower()


def test_app_preprocess_corrupted_file(client: TestClient, corrupted_wav_file: Path) -> None:
    """Verify that uploading a corrupted audio file returns HTTP 422."""
    with open(corrupted_wav_file, "rb") as f:
        response = client.post(
            "/audio/preprocess",
            files={"file": ("corrupted.wav", f, "audio/wav")},
        )
    assert response.status_code == 422
    assert "corrupt" in response.json()["detail"].lower() or "invalid" in response.json()["detail"].lower()


def test_app_preprocess_too_short_file(client: TestClient, synthetic_too_short_wav: Path) -> None:
    """Verify that uploading audio shorter than min_duration returns HTTP 400."""
    with open(synthetic_too_short_wav, "rb") as f:
        response = client.post(
            "/audio/preprocess",
            files={"file": ("too_short.wav", f, "audio/wav")},
        )
    assert response.status_code == 400
    assert "shorter than minimum" in response.json()["detail"].lower()


# -----------------------------------------------------------------------------
# Direct Async Function Unit Tests
# -----------------------------------------------------------------------------


@pytest.mark.anyio
async def test_api_preprocess_valid_file_direct(synthetic_mono_wav_16k: Path) -> None:
    """Test API endpoint handler directly with a valid synthetic WAV file."""
    raw_bytes = synthetic_mono_wav_16k.read_bytes()
    upload = UploadFile(
        file=io.BytesIO(raw_bytes),
        filename="test_synthetic_mono.wav",
    )

    response = await preprocess_audio_file(file=upload)
    assert response.is_valid is True
    assert response.filename == "test_synthetic_mono.wav"
    assert response.sample_rate == 16000
    assert response.num_channels == 1
    assert response.tensor_shape == [1, response.num_samples]


@pytest.mark.anyio
async def test_api_preprocess_empty_file_direct() -> None:
    """Test API endpoint handler directly with an empty file (0 bytes)."""
    upload = UploadFile(
        file=io.BytesIO(b""),
        filename="empty.wav",
    )
    with pytest.raises(HTTPException) as exc_info:
        await preprocess_audio_file(file=upload)
    assert exc_info.value.status_code == 400
    assert "empty" in exc_info.value.detail


@pytest.mark.anyio
async def test_api_preprocess_corrupted_file_direct(corrupted_wav_file: Path) -> None:
    """Test API endpoint handler directly with a corrupted audio file."""
    upload = UploadFile(
        file=io.BytesIO(corrupted_wav_file.read_bytes()),
        filename="corrupted.wav",
    )
    with pytest.raises(HTTPException) as exc_info:
        await preprocess_audio_file(file=upload)
    assert exc_info.value.status_code == 422
    assert "corrupt" in exc_info.value.detail.lower() or "invalid" in exc_info.value.detail.lower()


@pytest.mark.anyio
async def test_api_preprocess_too_short_file_direct(synthetic_too_short_wav: Path) -> None:
    """Test API endpoint handler directly with a file that is too short."""
    upload = UploadFile(
        file=io.BytesIO(synthetic_too_short_wav.read_bytes()),
        filename="too_short.wav",
    )
    with pytest.raises(HTTPException) as exc_info:
        await preprocess_audio_file(file=upload)
    assert exc_info.value.status_code == 400
    assert "shorter than minimum" in exc_info.value.detail
