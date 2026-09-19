"""Convenience script to run both backend and frontend development servers concurrently."""

import os
import signal
import subprocess
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = ROOT_DIR / "backend"
FRONTEND_DIR = ROOT_DIR / "frontend"


def get_backend_python() -> str:
    """Find python executable in backend venv or fall back to system python."""
    if sys.platform == "win32":
        venv_py = BACKEND_DIR / ".venv" / "Scripts" / "python.exe"
    else:
        venv_py = BACKEND_DIR / ".venv" / "bin" / "python"

    if venv_py.exists():
        return str(venv_py)
    return sys.executable


def main() -> None:
    """Start backend and frontend processes concurrently."""
    print("=" * 60)
    print(" Starting AI-Based Viva Voce System (Development Mode)")
    print("=" * 60)

    py_bin = get_backend_python()
    print(f"[*] Using Python: {py_bin}")
    print("[*] Starting FastAPI backend on http://127.0.0.1:8000...")

    backend_cmd = [
        py_bin,
        "-m",
        "uvicorn",
        "app.main:app",
        "--reload",
        "--host",
        "127.0.0.1",
        "--port",
        "8000",
    ]

    backend_proc = subprocess.Popen(
        backend_cmd,
        cwd=str(BACKEND_DIR),
    )

    print("[*] Starting Vite React frontend on http://localhost:5173...")
    npm_cmd = "npm.cmd" if sys.platform == "win32" else "npm"
    frontend_proc = subprocess.Popen(
        [npm_cmd, "run", "dev"],
        cwd=str(FRONTEND_DIR),
    )

    def signal_handler(sig, frame):
        print("\nShutting down dev servers...")
        backend_proc.terminate()
        frontend_proc.terminate()
        backend_proc.wait()
        frontend_proc.wait()
        print("Done.")
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, signal_handler)

    try:
        backend_proc.wait()
        frontend_proc.wait()
    except KeyboardInterrupt:
        signal_handler(None, None)


if __name__ == "__main__":
    main()
