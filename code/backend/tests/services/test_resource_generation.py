import os
from datetime import datetime, timedelta
from uuid import uuid4

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


def test_resource_generation_response_hides_paths_and_keeps_context(tmp_path):
    service = ResourceGenerationService()
    service.output_root = tmp_path
    course_id = uuid4()

    response = service.generate(
        ResourceGenerationRequest(
            course_id=course_id,
            resource_id="res-ai-search-01",
            node_id="resource-2",
            node_label="智能搜索",
            map_type="problem",
            source="resource-card",
            subject="人工智能导论",
            topic="智能搜索",
            learning_goal="生成能回流课程图谱的资料包",
            difficulty="standard",
            target_minutes=45,
            resource_types=["lecture_markdown", "mind_map", "quality_checklist"],
        )
    )

    assert response.course_id == course_id
    assert response.resource_id == "res-ai-search-01"
    assert response.node_id == "resource-2"
    assert response.node_label == "智能搜索"
    assert response.map_type == "problem"
    assert response.source == "resource-card"
    assert response.artifacts
    assert all(not hasattr(artifact, "file_path") for artifact in response.artifacts)

    manifest = tmp_path / response.package_id / "manifest.json"
    manifest_text = manifest.read_text(encoding="utf-8")
    assert str(course_id) in manifest_text
    assert "res-ai-search-01" in manifest_text
    assert "resource-2" in manifest_text


def test_recent_packages_filters_before_limit(tmp_path):
    service = ResourceGenerationService()
    service.output_root = tmp_path
    target_course_id = str(uuid4())
    other_course_id = str(uuid4())

    for index in range(13):
        folder = tmp_path / f"other_{index}"
        folder.mkdir()
        (folder / "manifest.json").write_text(
            (
                '{"package_id":"other_%s","course_id":"%s","subject":"其他课程",'
                '"topic":"其他主题","generated_at":"2026-06-20T00:00:00",'
                '"artifacts":[]}'
            )
            % (index, other_course_id),
            encoding="utf-8",
        )
        (folder / "lecture.md").write_text("# other", encoding="utf-8")
        timestamp = (datetime.utcnow() + timedelta(minutes=index)).timestamp()
        os.utime(folder, (timestamp, timestamp))

    target_folder = tmp_path / "target_old"
    target_folder.mkdir()
    (target_folder / "manifest.json").write_text(
        (
            '{"package_id":"target_old","course_id":"%s","resource_id":"res-1",'
            '"node_id":"node-1","node_label":"目标节点","map_type":"problem",'
            '"source":"resource-card","subject":"人工智能导论","topic":"智能搜索",'
            '"generated_at":"2026-06-19T00:00:00","artifacts":[]}'
        )
        % target_course_id,
        encoding="utf-8",
    )
    (target_folder / "lecture.md").write_text("# target", encoding="utf-8")
    old_timestamp = (datetime.utcnow() - timedelta(days=1)).timestamp()
    os.utime(target_folder, (old_timestamp, old_timestamp))

    packages = service.list_recent_packages(limit=12, course_id=target_course_id)

    assert [package["package_id"] for package in packages] == ["target_old"]
    assert packages[0]["resource_id"] == "res-1"
    assert packages[0]["node_id"] == "node-1"
