from __future__ import annotations

import os
import signal
import subprocess
import sys
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parent
CODE_ROOT = ROOT.parent
YOLO_APP_ROOT = CODE_ROOT / "cv" / "code"
YOLO_MODEL_ROOT = CODE_ROOT / "cv" / "model"
PORT = os.environ.get("BACKEND_PORT", "8001")
YOLO_PORT = os.environ.get("YOLO_SERVICE_PORT", "8002")
START_YOLO_SERVICE = os.environ.get("START_YOLO_SERVICE", "true").lower() in {
    "1",
    "true",
    "yes",
    "on",
}


def _spawn(
    cmd: list[str],
    *,
    cwd: Path = ROOT,
    extra_env: dict[str, str] | None = None,
) -> subprocess.Popen:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(cwd)
    if extra_env:
        env.update(extra_env)
    return subprocess.Popen(cmd, cwd=cwd, env=env)


def _run_once(cmd: list[str]) -> None:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT)
    subprocess.run(cmd, cwd=ROOT, env=env, check=True)


def main() -> int:
    yolo_cmd = [
        sys.executable,
        "-m",
        "uvicorn",
        "yolo:app",
        "--host",
        "127.0.0.1",
        "--port",
        YOLO_PORT,
    ]
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

    children: list[tuple[str, subprocess.Popen, bool]] = []

    def shutdown(*_args):
        for _, proc, _ in children:
            if proc.poll() is None:
                proc.terminate()
        for _, proc, _ in children:
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
        children.append(("celery", _spawn(celery_cmd), True))
        time.sleep(2)
        if START_YOLO_SERVICE:
            yolo_file = YOLO_APP_ROOT / "yolo.py"
            detector_path = YOLO_MODEL_ROOT / "yolo11m.pt"
            if not detector_path.exists():
                detector_path = YOLO_MODEL_ROOT / "yolov8n.pt"
            if yolo_file.exists():
                yolo_env = {
                    "YOLO_MODEL_PATH": os.environ.get(
                        "YOLO_MODEL_PATH",
                        str(YOLO_MODEL_ROOT / "yolov8n-pose.pt"),
                    ),
                    "DETECTOR_MODEL_PATH": os.environ.get(
                        "DETECTOR_MODEL_PATH",
                        str(detector_path),
                    ),
                    "USE_DUAL_STAGE": os.environ.get("USE_DUAL_STAGE", "true"),
                }
                children.append(
                    (
                        "yolo",
                        _spawn(yolo_cmd, cwd=YOLO_APP_ROOT, extra_env=yolo_env),
                        False,
                    )
                )
                time.sleep(2)
            else:
                print(f"[run_backend_stack] YOLO service skipped: {yolo_file} not found")
        children.append(("uvicorn", _spawn(uvicorn_cmd), True))
        while True:
            for name, proc, critical in list(children):
                code = proc.poll()
                if code is not None:
                    if critical:
                        print(f"[run_backend_stack] critical child {name} exited: {code}")
                        shutdown()
                        return code
                    print(f"[run_backend_stack] optional child {name} exited: {code}")
                    children = [child for child in children if child[1] is not proc]
            time.sleep(1)
    finally:
        shutdown()


if __name__ == "__main__":
    raise SystemExit(main())
