#!/usr/bin/env python3
"""Audit and add SHA-256 digests to persisted legacy resource packages."""

from __future__ import annotations

import json
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from sqlmodel import Session, select

from app.core.db import engine
from app.models.generated_resource_package import GeneratedResourcePackage
from app.services.resource_generation_service import resource_generation_service


def main() -> None:
    summary = {"packages": 0, "artifacts_verified": 0, "digests_added": 0}
    with Session(engine) as session:
        packages = session.exec(select(GeneratedResourcePackage)).all()
        for package in packages:
            result = resource_generation_service.backfill_package_artifact_digests(
                package.id
            )
            summary["packages"] += 1
            summary["artifacts_verified"] += result["verified"]
            summary["digests_added"] += result["updated"]
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    main()
