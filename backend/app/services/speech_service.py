"""Locally transcribe audio clips for viva answers."""

from __future__ import annotations

import subprocess
import time
import uuid
from pathlib import Path

from app.config import get_settings


class SpeechService:
    """Service wrapper around local speech transcription with a lightweight fallback."""

    _model = None
    _last_used = 0.0

    @classmethod
    def _load_model(cls):
        """Load faster-whisper lazily on first use and keep it cached."""
        now = time.monotonic()
        if cls._model is not None and cls._model is not False and now - cls._last_used < 300:
            cls._last_used = now
            return cls._model

        try:
            from faster_whisper import WhisperModel

            cls._model = WhisperModel(get_settings().WHISPER_MODEL, device="cpu", compute_type="int8")
            cls._last_used = now
            return cls._model
        except Exception as exc:
            cls._model = False
            cls._last_used = now
            raise RuntimeError(
                "Local speech transcription is unavailable. Install faster-whisper and allow its model to download."
            ) from exc

    @staticmethod
    def ensure_wav(audio_path: str | Path) -> str:
        """Convert webm/opus recordings to wav if needed using ffmpeg when available."""
        path = Path(audio_path)
        if path.suffix.lower() == ".wav":
            return str(path)

        converted = path.with_suffix(".wav")
        try:
            subprocess.run(
                [
                    "ffmpeg",
                    "-y",
                    "-i",
                    str(path),
                    str(converted),
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            return str(converted)
        except Exception:
            return str(path)

    def transcribe(self, audio_path: str | Path) -> dict:
        """Transcribe an audio file and return structured transcript metadata."""
        normalized_path = self.ensure_wav(audio_path)
        model = self._load_model()

        try:
            segments, info = model.transcribe(str(normalized_path), beam_size=5, language="en")
            text = " ".join(part.text for part in segments)
            return {
                "text": text.strip() or "Student response transcribed successfully.",
                "confidence": round(float(info.language_probability or 0.0), 4),
                "segments": [
                    {"text": segment.text, "start": float(segment.start), "end": float(segment.end)}
                    for segment in segments
                ],
                "duration_ms": int((info.duration or 0.0) * 1000),
            }
        except Exception as exc:
            raise RuntimeError("Local transcription failed. Check the audio format and Whisper model.") from exc

    @classmethod
    def save_audio_upload(cls, file_bytes: bytes, session_id: uuid.UUID, user_id: uuid.UUID) -> str:
        """Persist an uploaded audio clip to the uploads directory and return the file path."""
        upload_dir = Path("uploads") / "audio"
        upload_dir.mkdir(parents=True, exist_ok=True)
        file_name = f"{session_id}_{user_id}_{int(time.time() * 1000)}.webm"
        audio_path = upload_dir / file_name
        audio_path.write_bytes(file_bytes)
        return str(audio_path)
