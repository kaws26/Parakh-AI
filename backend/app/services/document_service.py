"""Utility service for saving uploaded documents and extracting text content."""

from __future__ import annotations

import hashlib
import uuid
from pathlib import Path

from fastapi import UploadFile


class DocumentService:
    """Service helpers for handling uploaded document files."""

    @staticmethod
    def _safe_filename(filename: str) -> str:
        cleaned = Path(filename).name
        return cleaned or "document.txt"

    @staticmethod
    def extract_text(file_name: str, file_bytes: bytes) -> str:
        """Read plain text from a supported upload format."""
        suffix = Path(file_name).suffix.lower()

        if suffix in {".txt", ".md", ".csv", ".json"}:
            return file_bytes.decode("utf-8", errors="replace")

        if suffix == ".pdf":
            try:
                from pypdf import PdfReader
            except ImportError:
                try:
                    import fitz  # type: ignore
                except ImportError as exc:  # pragma: no cover - depends on optional lib
                    raise ValueError("PDF extraction requires pypdf or PyMuPDF to be installed.") from exc
                with fitz.open(stream=file_bytes, filetype="pdf") as pdf:
                    return "\n".join(page.get_text() for page in pdf)

            reader = PdfReader(file_bytes)
            return "\n".join(page.extract_text() or "" for page in reader.pages)

        raise ValueError(f"Unsupported file type: {suffix or 'unknown'}")

    @staticmethod
    async def save_upload(file: UploadFile, topic_id: uuid.UUID, upload_dir: str | Path | None = None) -> dict:
        """Persist the uploaded file to disk and return metadata for database storage."""
        destination = Path(upload_dir) if upload_dir is not None else Path("uploads")
        destination.mkdir(parents=True, exist_ok=True)

        filename = DocumentService._safe_filename(file.filename or "document.txt")
        persisted_path = destination / f"{uuid.uuid4()}_{filename}"
        content = await file.read()
        persisted_path.write_bytes(content)

        content_hash = hashlib.sha256(content).hexdigest()
        return {
            "topic_id": topic_id,
            "filename": filename,
            "file_path": str(persisted_path),
            "content_hash": content_hash,
            "raw_content": content,
        }
