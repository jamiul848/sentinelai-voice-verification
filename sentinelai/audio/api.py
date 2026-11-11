"""FastAPI router integration for SentinelAI Audio Preprocessing.

Provides an endpoint for uploading WAV recordings, validating audio integrity,
and returning structured acoustic metrics and verification readiness.
"""

from typing import Any, Dict
from fastapi import APIRouter, File, HTTPException, UploadFile, status
from pydantic import BaseModel

from sentinelai.audio.config import AudioPreprocessingConfig
from sentinelai.audio.exceptions import (
    AudioDurationError,
    AudioFileCorruptedError,
    EmptyAudioFileError,
    InvalidAudioValueError,
    SilentAudioError,
)
from sentinelai.audio.metrics import AudioMetrics
from sentinelai.audio.preprocessor import AudioPreprocessor

router = APIRouter(prefix="/audio", tags=["Audio Preprocessing"])


class AudioPreprocessingResponse(BaseModel):
    """Response schema returned by the /audio/preprocess endpoint."""

    is_valid: bool
    filename: str
    sample_rate: int
    original_sample_rate: int
    duration_sec: float
    original_duration_sec: float
    num_channels: int
    num_samples: int
    rms_energy: float
    peak_amplitude: float
    metrics: AudioMetrics
    tensor_shape: list[int]
    metadata: Dict[str, Any]


@router.post(
    "/preprocess",
    response_model=AudioPreprocessingResponse,
    status_code=status.HTTP_200_OK,
    summary="Validate and preprocess a WAV audio file",
    description="Decodes WAV audio, converts stereo to mono, resamples to 16kHz, "
                "checks recording duration, detects corruption/silence, and computes metrics.",
)
async def preprocess_audio_file(
    file: UploadFile = File(..., description="WAV audio recording file to validate and preprocess"),
) -> AudioPreprocessingResponse:
    """Preprocess an uploaded WAV recording."""
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file must have a valid filename.",
        )

    content = await file.read()
    if len(content) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded audio file is empty (0 bytes).",
        )

    preprocessor = AudioPreprocessor(config=AudioPreprocessingConfig())

    try:
        result = preprocessor.process(content, source_id=file.filename)
    except EmptyAudioFileError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except AudioFileCorruptedError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except AudioDurationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except (InvalidAudioValueError, SilentAudioError) as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected preprocessing failure: {exc}",
        )

    return AudioPreprocessingResponse(
        is_valid=result.is_valid,
        filename=file.filename,
        sample_rate=result.sample_rate,
        original_sample_rate=result.original_sample_rate,
        duration_sec=round(result.duration_sec, 4),
        original_duration_sec=round(result.original_duration_sec, 4),
        num_channels=result.num_channels,
        num_samples=result.num_samples,
        rms_energy=float(result.rms_energy),
        peak_amplitude=float(result.peak_amplitude),
        metrics=result.metrics,
        tensor_shape=list(result.audio_tensor.shape),
        metadata=result.metadata,
    )
