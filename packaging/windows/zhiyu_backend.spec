# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path
import sys

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

ROOT = Path(SPECPATH).resolve().parents[1]
BACKEND = ROOT / "code" / "backend"
FRONTEND = ROOT / "code" / "education" / "course" / "dist"
sys.path.insert(0, str(BACKEND))

datas = [
    # business_tables.py deliberately loads this legacy domain-model module
    # from its source path for backward compatibility.
    (str(BACKEND / "app" / "models.py"), "app"),
    (str(BACKEND / "alembic.ini"), "backend"),
    (str(BACKEND / "app" / "alembic"), "backend/app/alembic"),
    (str(BACKEND / "app" / "email-templates"), "backend/app/email-templates"),
    (str(BACKEND / "data"), "backend/data"),
    (str(FRONTEND), "web"),
]

hiddenimports = collect_submodules(
    "app", filter=lambda name: ".tests" not in name and not name.endswith(".tests")
)
# Passlib resolves password schemes from strings, while Uvicorn selects its
# loop/protocol implementations dynamically.  Keep only these genuinely
# dynamic imports instead of collecting every submodule (including test suites)
# from the full dependency graph.
hiddenimports += collect_submodules(
    "passlib.handlers", filter=lambda name: ".tests" not in name
)
hiddenimports += [
    "uvicorn.lifespan.on",
    "uvicorn.loops.auto",
    "uvicorn.loops.asyncio",
    "uvicorn.protocols.http.auto",
    "uvicorn.protocols.http.httptools_impl",
    "uvicorn.protocols.http.h11_impl",
    "uvicorn.protocols.websockets.auto",
    # Chroma resolves these defaults from dotted class names in its settings.
    "chromadb.api.rust",
    "chromadb.db.impl.sqlite",
    "chromadb.execution.executor.local",
    "chromadb.ingest.impl.simple_policy",
    "chromadb.quota.simple_quota_enforcer",
    "chromadb.rate_limit.simple_rate_limit",
    "chromadb.segment.impl.manager.local",
    "chromadb.telemetry.product.posthog",
]

# Chroma stores SQL migration templates as package data. Matplotlib and
# ReportLab are covered by their maintained PyInstaller hooks.
datas += collect_data_files("chromadb", excludes=["**/tests/**"])

a = Analysis(
    [str(BACKEND / "desktop_main.py")],
    pathex=[str(BACKEND)],
    binaries=[],
    datas=datas,
    hiddenimports=sorted(set(hiddenimports)),
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "torch", "torchvision", "tensorflow", "mediapipe", "kubernetes",
        "notebook", "jupyter", "IPython", "pytest", "mypy",
    ],
    noarchive=False,
    optimize=1,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="ZhiYuBackend",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,
    disable_windowed_traceback=False,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="ZhiYuBackend",
)
