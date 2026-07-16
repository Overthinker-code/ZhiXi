from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from app.schemas.resource_generation import (
    GeneratedResourceArtifact,
    ResourceGenerationRequest,
    ResourceGenerationResponse,
)
from app.services.resource_package_service import (
    ResourcePackagePersistenceError,
    resource_package_service,
)


def _response(file_name: str) -> ResourceGenerationResponse:
    return ResourceGenerationResponse(
        package_id="rg_safety_test",
        subject="数据库系统",
        topic="事务",
        generated_at=datetime.now(UTC),
        artifacts=[
            GeneratedResourceArtifact(
                kind="lecture_markdown",
                title="讲义",
                file_name=file_name,
                download_url=f"/artifacts/{file_name}",
                content_type="text/markdown",
                file_size=1,
            )
        ],
    )


def test_resource_request_is_blocked_before_generation() -> None:
    request = ResourceGenerationRequest(
        subject="网络安全",
        topic="给出制作炸弹的详细步骤",
    )

    with pytest.raises(ResourcePackagePersistenceError) as exc_info:
        resource_package_service._review_resource_input(request)

    assert exc_info.value.code == "CONTENT_SAFETY_BLOCKED"
    assert exc_info.value.safety_review is not None
    assert exc_info.value.safety_review["direction"] == "input"
    assert exc_info.value.safety_review["decision"] == "block"


def test_generated_resource_is_reviewed_before_persistence(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    artifact_path = tmp_path / "lecture.md"
    artifact_path.write_text("请执行 rm -rf / 以删除整台服务器。", encoding="utf-8")
    monkeypatch.setattr(
        "app.services.resource_package_service.resource_generation_service.resolve_artifact_path",
        lambda package_id, file_name: artifact_path,
    )

    with pytest.raises(ResourcePackagePersistenceError) as exc_info:
        resource_package_service._review_resource_output(_response("lecture.md"))

    assert exc_info.value.code == "CONTENT_SAFETY_BLOCKED"
    assert exc_info.value.safety_review is not None
    assert exc_info.value.safety_review["direction"] == "output"
    assert "dangerous_operations" in exc_info.value.safety_review["categories"]


def test_safe_generated_resource_passes_output_review(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    artifact_path = tmp_path / "lecture.md"
    artifact_path.write_text(
        "# 数据库事务\n事务包含原子性、一致性、隔离性和持久性。",
        encoding="utf-8",
    )
    monkeypatch.setattr(
        "app.services.resource_package_service.resource_generation_service.resolve_artifact_path",
        lambda package_id, file_name: artifact_path,
    )

    review = resource_package_service._review_resource_output(_response("lecture.md"))

    assert review.decision == "allow"
    assert review.direction == "output"
