"""Windows desktop/installer entry point for the complete ZhiYu web app.

The production Vue build is served by the same FastAPI process.  This keeps
the installed application to one local port and avoids requiring Node.js on
the target computer.
"""
from __future__ import annotations

import os
import sys
import threading
import time
import webbrowser
from pathlib import Path

import httpx
import uvicorn
from fastapi import HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles


FROZEN = bool(getattr(sys, "frozen", False))
if FROZEN:
    # PyInstaller one-folder builds expose bundled data through _MEIPASS.
    ROOT = Path(sys._MEIPASS)  # type: ignore[attr-defined]
    BACKEND_ROOT = ROOT / "backend"
    WEB_ROOT = ROOT / "web"
    RUNTIME_ROOT = Path(sys.executable).resolve().parent
else:
    BACKEND_ROOT = Path(__file__).resolve().parent
    ROOT = BACKEND_ROOT.parent
    WEB_ROOT = ROOT / "education" / "course" / "dist"
    RUNTIME_ROOT = BACKEND_ROOT

# Settings reads ../.env relative to the process working directory.  In the
# installed layout the executable lives in ``<install>/runtime`` and the
# editable private configuration lives at ``<install>/.env``.
os.chdir(RUNTIME_ROOT)

from app.main import app  # noqa: E402  (working directory must be set first)


if not WEB_ROOT.is_dir() or not (WEB_ROOT / "index.html").is_file():
    raise RuntimeError(f"前端构建产物不存在：{WEB_ROOT}")

assets = WEB_ROOT / "assets"
if assets.is_dir():
    app.mount("/assets", StaticFiles(directory=assets), name="desktop-assets")


@app.get("/{full_path:path}", include_in_schema=False, tags=["desktop"])
async def desktop_spa(full_path: str):
    """Serve safe public files and fall back to Vue Router's index page."""
    requested = (WEB_ROOT / full_path).resolve()
    if requested != WEB_ROOT and WEB_ROOT not in requested.parents:
        raise HTTPException(status_code=404)
    if requested.is_file():
        return FileResponse(requested)
    return FileResponse(WEB_ROOT / "index.html")


def open_when_ready(url: str) -> None:
    for _ in range(90):
        try:
            if httpx.get(f"{url}/api/v1/readyz", timeout=1.0).status_code < 500:
                webbrowser.open(url)
                return
        except httpx.HTTPError:
            pass
        time.sleep(1)


def main() -> None:
    host = os.environ.get("ZHIXI_DESKTOP_HOST", "127.0.0.1")
    port = int(os.environ.get("ZHIXI_DESKTOP_PORT", "8001"))
    url = f"http://{host}:{port}"
    if os.environ.get("ZHIXI_DESKTOP_OPEN_BROWSER", "true").lower() not in {
        "0",
        "false",
        "no",
    }:
        threading.Thread(target=open_when_ready, args=(url,), daemon=True).start()
    uvicorn.run(app, host=host, port=port, log_level="info")


if __name__ == "__main__":
    main()
