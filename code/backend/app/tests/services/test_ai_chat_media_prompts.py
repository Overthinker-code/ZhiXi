from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

from app.api.v1.endpoints.ai_chat import (
    _image_generation_prompt,
    _persist_chat_media,
    _seedance_video_prompt,
)
from app.services.media_generation_service import media_generation_service


def test_stack_image_prompt_uses_controlled_visual_language() -> None:
    topic, prompt = _image_generation_prompt("生成一张栈的入栈出栈教学图片")
    assert topic == "栈的后进先出与入栈出栈"
    lowered = prompt.lower()
    assert "16:9" in prompt
    assert "orange at the bottom" in lowered
    assert "blue in the middle" in lowered
    assert "green at the top" in lowered
    assert "downward arrow" in lowered and "upward arrow" in lowered
    assert "subtitle-safe" in lowered
    assert "no text" in lowered and "no watermark" in lowered


def test_stack_video_prompt_uses_controlled_visual_language() -> None:
    topic, prompt = _seedance_video_prompt("请为数据结构课程生成一个5秒的栈操作教学动画：A、B、C依次入栈，然后C先出栈。")
    assert topic == "栈的后进先出与入栈出栈"
    lowered = prompt.lower()
    assert "16:9" in prompt
    assert "orange at the bottom" in lowered
    assert "blue in the middle" in lowered
    assert "green at the top" in lowered
    assert "entering from above" in lowered and "leaving upward" in lowered
    assert "fixed-camera" in lowered
    assert "subtitle-safe" in lowered
    assert "no text" in lowered and "no watermark" in lowered


def test_persisted_chat_media_uses_selected_course_name_as_subject(monkeypatch) -> None:
    course_id = uuid4()
    owner_id = uuid4()
    captured: dict[str, object] = {}

    class FakeSession:
        def get(self, _model, value):
            assert value == course_id
            return SimpleNamespace(name="数据结构")

    def fake_persist(_db, **kwargs):
        captured.update(kwargs)
        resource = SimpleNamespace(
            id=uuid4(), file_name="stack.mp4", file_size=123
        )
        return SimpleNamespace(
            resource=resource,
            preview_url="/preview",
            download_url="/download",
        )

    monkeypatch.setattr(media_generation_service, "persist_resource", fake_persist)
    _persist_chat_media(
        FakeSession(),
        owner_id=owner_id,
        source_path=Path("stack.mp4"),
        content_type="video/mp4",
        provider="deterministic_stack_fallback",
        title="栈操作教学视频",
        kind="video",
        topic="栈的后进先出",
        course_id=course_id,
    )
    assert captured["subject"] == "数据结构"
    assert captured["course_id"] == course_id
