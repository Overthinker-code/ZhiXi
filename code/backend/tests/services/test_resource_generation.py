from app.schemas.resource_generation import ResourceGenerationRequest
from app.services.resource_generation_service import ResourceGenerationService


def test_resource_package_contains_closed_loop_artifacts(tmp_path):
    service = ResourceGenerationService()
    service.output_root = tmp_path

    response = service.generate(
        ResourceGenerationRequest(
            subject="人工智能导论",
            topic="智能搜索",
            learning_goal="理解智能搜索的状态空间、评价函数和图谱关系",
            difficulty="standard",
            target_minutes=45,
            use_web_search=False,
        )
    )

    names = {artifact.file_name for artifact in response.artifacts}
    assert {
        "lecture.md",
        "practice.md",
        "mind-map.mmd",
        "quality-checklist.md",
    }.issubset(names)

    package_dir = tmp_path / response.package_id
    lecture = (package_dir / "lecture.md").read_text(encoding="utf-8")
    practice = (package_dir / "practice.md").read_text(encoding="utf-8")
    mind_map = (package_dir / "mind-map.mmd").read_text(encoding="utf-8")
    checklist = (package_dir / "quality-checklist.md").read_text(encoding="utf-8")

    assert "课堂笔记对齐" in lecture
    assert "课程图谱绑定" in lecture
    assert "标准答案框架" in practice
    assert "AI 追练" in practice
    assert "quality-checklist.md" in mind_map
    assert "质量门槛" in checklist
    assert "继续生成规则" in checklist
    assert all("待填写" not in text for text in [lecture, practice, checklist])
