from pathlib import Path

from app.api.v1.endpoints.ai_chat import (
    _is_seedance_video_intent,
    _is_structured_diagram_intent,
    _prefers_rendered_diagram_image,
)
from app.services.teaching_artifact_service import teaching_artifact_service


SALARY_PROMPT = (
    "美国某大学共有200名教师，工资少于26000的教师按赡养人数和工龄增加工资。"
    "画出此系统的数据流图，给我生成图片，不要插图，不要Mermaid，黑字白底。"
)


def test_explicit_png_dfd_bypasses_mermaid_route():
    assert _is_structured_diagram_intent(SALARY_PROMPT)
    assert _prefers_rendered_diagram_image(SALARY_PROMPT)


def test_plain_mermaid_compatible_request_keeps_existing_route():
    prompt = "请生成TCP拥塞控制流程图"
    assert _is_structured_diagram_intent(prompt)
    assert not _prefers_rendered_diagram_image(prompt)


def test_tcp_video_request_is_not_intercepted_by_mermaid():
    prompt = "帮我生成一个讲解TCP拥塞控制基础知识的视频"
    assert _is_seedance_video_intent(prompt)
    assert not _is_structured_diagram_intent(prompt)
    assert not _prefers_rendered_diagram_image(prompt)


def test_salary_dfd_renderer_creates_real_png():
    artifact = teaching_artifact_service.generate_data_flow_diagram(
        "教师工资调整系统", SALARY_PROMPT
    )
    path = teaching_artifact_service.image_output_dir / artifact["file_name"]
    try:
        assert artifact["kind"] == "image"
        assert artifact["resource_type"] == "data_flow_diagram"
        assert artifact["diagram_source"] == "verified_salary_dfd_template"
        assert path.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
        assert path.stat().st_size > 20_000
    finally:
        Path(path).unlink(missing_ok=True)
