from __future__ import annotations

import os
import signal
import subprocess
import sys
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parent
PORT = os.environ.get("BACKEND_PORT", "8001")


def _spawn(cmd: list[str]) -> subprocess.Popen:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT)
    return subprocess.Popen(cmd, cwd=ROOT, env=env)


def _run_once(cmd: list[str]) -> None:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT)
    subprocess.run(cmd, cwd=ROOT, env=env, check=True)


def main() -> int:
    celery_cmd = [
        sys.executable,
        "-m",
        "celery",
        "-A",
        "app.worker.celery_app:celery",
        "worker",
        "--loglevel=info",
        "--pool=solo",
    ]
    uvicorn_cmd = [
        sys.executable,
        "-m",
        "uvicorn",
        "app.main:app",
        "--host",
        "0.0.0.0",
        "--port",
        PORT,
    ]

    children: list[subprocess.Popen] = []

    def shutdown(*_args):
        for proc in children:
            if proc.poll() is None:
                proc.terminate()
        for proc in children:
            if proc.poll() is None:
                try:
                    proc.wait(timeout=8)
                except subprocess.TimeoutExpired:
                    proc.kill()

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    try:
        _run_once([sys.executable, "backend_pre_start.py"])
        _run_once([sys.executable, "initial_data.py"])
        children.append(_spawn(celery_cmd))
        time.sleep(2)
        children.append(_spawn(uvicorn_cmd))
        while True:
            for proc in children:
                code = proc.poll()
                if code is not None:
                    shutdown()
                    return code
            time.sleep(1)
    finally:
        shutdown()


if __name__ == "__main__":
    raise SystemExit(main())
