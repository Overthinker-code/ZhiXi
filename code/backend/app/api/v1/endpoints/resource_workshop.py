from __future__ import annotations

import json
import os
import re
from datetime import datetime
from typing import Any, Literal
from uuid import uuid4

import httpx
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field, model_validator
from sqlmodel import Session

from app.api import deps
from app.api.deps import CurrentUser
from app.core.config import settings
from app.services.user_memory_profile_service import (
    MemoryProfilePayload,
    user_memory_profile_service,
)

router = APIRouter()

MAX_IMAGE_BASE64_CHARS = 10_000_000


def _clamp_score(value: Any, default: float = 0.52) -> float:
    try:
        score = float(value)
    except (TypeError, ValueError):
        score = default
    return round(max(0.0, min(1.0, score)), 4)


def _normalize_topic(topic: Any) -> str:
    return re.sub(r"\s+", "", str(topic or "").strip())[:24]


def _extract_json_blob(raw: str) -> dict[str, Any]:
    text = (raw or "").strip()
    if not text:
        return {}
    try:
        data = json.loads(text)
        if isinstance(data, dict):
            return data
    except Exception:
        pass
    match = re.search(r"\{[\s\S]*\}", text)
    if not match:
        return {}
    try:
        data = json.loads(match.group(0))
        if isinstance(data, dict):
            return data
    except Exception:
        return {}
    return {}


def _profile_for_user(db: Session, user_id: str) -> dict[str, Any]:
    profile = user_memory_profile_service.get_profile_dict(db, user_id)
    return profile if isinstance(profile, dict) else {}


def _upsert_profile_from_dict(db: Session, user_id: str, profile: dict[str, Any]) -> None:
    payload = MemoryProfilePayload(
        weak_points=[
            str(item).strip()
            for item in (profile.get("weak_points") or [])
            if str(item).strip()
        ],
        learning_style=str(profile.get("learning_style") or "").strip(),
        current_goal=str(profile.get("current_goal") or "").strip(),
        mastery_map={
            _normalize_topic(topic): _clamp_score(score)
            for topic, score in (profile.get("mastery_map") or {}).items()
            if _normalize_topic(topic)
        },
        mastery_update=profile.get("mastery_update") or {},
    )
    user_memory_profile_service.upsert_profile(db, user_id=user_id, payload=payload)


class ResourcePackageRequest(BaseModel):
    subject: str = Field(..., min_length=1, max_length=40)
    topic: str | None = Field(default=None, max_length=80)
    goal: str | None = Field(default=None, max_length=160)
    difficulty: Literal["auto", "foundation", "standard", "challenge"] = "auto"
    minutes: int = Field(default=30, ge=10, le=120)
    resource_count: int = Field(default=5, ge=3, le=8)


class ResourceItem(BaseModel):
    title: str
    type: Literal[
        "lecture_doc",
        "mind_map",
        "practice_set",
        "reading",
        "case_project",
        "video_script",
        "reflection",
    ]
    estimated_minutes: int
    difficulty: Literal["foundation", "standard", "challenge"]
    description: str
    mastery_target: str
    content_preview: str = ""


class ResourcePackageResponse(BaseModel):
    package_id: str
    subject: str
    topic: str
    goal: str
    personalization_basis: list[str] = Field(default_factory=list)
    resources: list[ResourceItem]
    next_check: dict[str, Any]


class ExerciseGradeRequest(BaseModel):
    subject: str = Field(..., min_length=1, max_length=40)
    topic: str = Field(..., min_length=1, max_length=80)
    question: str = Field(..., min_length=1, max_length=4000)
    student_answer: str = Field(..., min_length=1, max_length=4000)
    reference_answer: str | None = Field(default=None, max_length=4000)
    max_score: float = Field(default=100, gt=0, le=100)


class ExerciseGradeResponse(BaseModel):
    topic: str
    score: float
    is_correct: bool
    mastery_before: float
    mastery_after: float
    mastery_delta: float
    feedback: str
    strengths: list[str] = Field(default_factory=list)
    gaps: list[str] = Field(default_factory=list)
    follow_up: list[str] = Field(default_factory=list)
    mastery_update: dict[str, Any] = Field(default_factory=dict)


class ImageAnalyzeRequest(BaseModel):
    subject: str | None = Field(default=None, max_length=40)
    question_text: str | None = Field(default=None, max_length=2000)
    image_url: str | None = None
    image_base64: str | None = None

    @model_validator(mode="after")
    def _require_image(self) -> "ImageAnalyzeRequest":
        if not self.image_url and not self.image_base64:
            raise ValueError("image_url or image_base64 is required")
        if self.image_base64 and len(self.image_base64) > MAX_IMAGE_BASE64_CHARS:
            raise ValueError("image_base64 is too large")
        return self


class ImageAnalyzeResponse(BaseModel):
    source: Literal["qwen3-vl", "fallback"]
    status: Literal["success", "fallback"]
    subject: str
    problem_type: str
    extracted_text: str
    answer_markdown: str = ""
    solution_outline: list[str] = Field(default_factory=list)
    answer_hint: str
    diagram: dict[str, Any] = Field(default_factory=dict)
    confidence: float
    limitations: list[str] = Field(default_factory=list)


def _select_topic(request: ResourcePackageRequest, profile: dict[str, Any]) -> str:
    if request.topic and request.topic.strip():
        return request.topic.strip()
    weak_points = [
        str(item).strip() for item in profile.get("weak_points") or [] if str(item).strip()
    ]
    if weak_points:
        return weak_points[0]
    mastery_map = profile.get("mastery_map") or {}
    if isinstance(mastery_map, dict) and mastery_map:
        return str(min(mastery_map.items(), key=lambda item: _clamp_score(item[1]))[0])
    return f"{request.subject}核心知识点"


def _target_difficulty(
    request: ResourcePackageRequest,
    profile: dict[str, Any],
    topic: str,
) -> Literal["foundation", "standard", "challenge"]:
    if request.difficulty != "auto":
        return request.difficulty
    mastery = _clamp_score((profile.get("mastery_map") or {}).get(_normalize_topic(topic)))
    if mastery < 0.5:
        return "foundation"
    if mastery > 0.78:
        return "challenge"
    return "standard"


def _build_resource_package(
    request: ResourcePackageRequest,
    profile: dict[str, Any],
) -> ResourcePackageResponse:
    topic = _select_topic(request, profile)
    difficulty = _target_difficulty(request, profile, topic)
    goal = (
        (request.goal or "").strip()
        or str(profile.get("current_goal") or "").strip()
        or f"巩固 {topic} 并完成一次可解释的练习闭环"
    )
    weak_points = [
        str(item).strip() for item in profile.get("weak_points") or [] if str(item).strip()
    ][:3]
    learning_style = str(profile.get("learning_style") or "").strip()
    per_item = max(5, request.minutes // request.resource_count)
    templates: list[
        tuple[
            str,
            Literal[
                "lecture_doc",
                "mind_map",
                "practice_set",
                "reading",
                "case_project",
                "video_script",
                "reflection",
            ],
            str,
            str,
        ]
    ] = [
        (
            f"{topic} 个性化讲解文档",
            "lecture_doc",
            "围绕学生当前基础分层讲解核心概念、使用场景和易错边界。",
            f"先用一句话解释 {topic}，再列出 3 个必须掌握的判断条件。",
        ),
        (
            f"{topic} 思维导图",
            "mind_map",
            "用中心主题、关键分支和关联概念构成可复习的知识结构。",
            f"中心节点：{topic}；分支：定义、步骤、例题、易错点、迁移应用。",
        ),
        (
            f"{topic} 分层练习题",
            "practice_set",
            "生成基础、标准、挑战三层练习，并附带提示和考查点。",
            "基础题检查定义；标准题检查步骤；挑战题检查与相邻知识点的迁移。",
        ),
        (
            f"{topic} 拓展阅读材料",
            "reading",
            "给出适合当前掌握度的阅读方向，避免过早进入高难资料。",
            f"推荐先读课堂笔记中的 {topic} 章节，再补充一个真实应用案例。",
        ),
        (
            f"{topic} 实操案例",
            "case_project",
            "把知识点落到小任务或代码/数据案例中，训练可迁移能力。",
            "设计一个 20 分钟小任务：输入条件、操作步骤、验收结果三段式完成。",
        ),
        (
            f"{topic} 数字人讲解脚本",
            "video_script",
            "生成适合口播的视频脚本，可直接进入数字人创作舱二次生成。",
            f"大家好，本节课我们用 3 分钟讲清楚 {topic} 的核心思路和常见误区。",
        ),
        (
            f"{topic} 讲给同学听",
            "reflection",
            "用 90 秒口头解释核心思路，暴露表达断点和隐藏漏洞。",
            f"请用自己的话讲清 {topic} 的定义、一个例子和一个常见误区。",
        ),
        (
            f"{topic} 小测验",
            "practice_set",
            "用 3 个短问快速检查概念、步骤和应用场景。",
            "小测包含 1 道概念判断、1 道步骤排序和 1 道应用分析。",
        ),
    ]
    resources = [
        ResourceItem(
            title=title,
            type=item_type,
            estimated_minutes=per_item,
            difficulty=difficulty,
            description=description,
            mastery_target=topic,
            content_preview=preview,
        )
        for title, item_type, description, preview in templates[: request.resource_count]
    ]
    basis = []
    if weak_points:
        basis.append("薄弱点：" + "、".join(weak_points))
    if learning_style:
        basis.append(f"学习偏好：{learning_style}")
    basis.append(f"目标难度：{difficulty}")
    return ResourcePackageResponse(
        package_id=f"rw_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{uuid4().hex[:8]}",
        subject=request.subject.strip(),
        topic=topic,
        goal=goal,
        personalization_basis=basis,
        resources=resources,
        next_check={
            "method": "完成 2 道变式题后提交批改",
            "endpoint": "/api/v1/resource-workshop/exercises/grade",
            "target_mastery_delta": 0.04 if difficulty == "foundation" else 0.03,
        },
    )


def _grade_exercise(request: ExerciseGradeRequest) -> tuple[float, list[str], list[str], str]:
    answer = request.student_answer.strip()
    reference = (request.reference_answer or "").strip()
    question_terms = {
        token
        for token in re.split(r"[\s，。！？；,.!?;:：、()\[\]{}]+", request.question)
        if len(token) >= 2
    }
    answer_terms = {
        token
        for token in re.split(r"[\s，。！？；,.!?;:：、()\[\]{}]+", answer)
        if len(token) >= 2
    }
    if reference:
        ref_terms = {
            token
            for token in re.split(r"[\s，。！？；,.!?;:：、()\[\]{}]+", reference)
            if len(token) >= 2
        }
        overlap = len(answer_terms & ref_terms) / max(1, len(ref_terms))
        length_ratio = min(len(answer) / max(1, len(reference)), 1.15)
        score = request.max_score * min(1.0, overlap * 0.72 + min(length_ratio, 1.0) * 0.28)
    else:
        coverage = len(answer_terms & question_terms) / max(1, len(question_terms))
        structure_bonus = 0.15 if re.search(r"(因为|所以|首先|其次|因此|步骤|结论)", answer) else 0
        length_bonus = min(len(answer) / 280, 1.0) * 0.2
        score = request.max_score * min(1.0, 0.45 + coverage * 0.4 + structure_bonus + length_bonus)
    score = round(max(0.0, min(request.max_score, score)), 1)
    strengths = ["答案已覆盖题目核心信息"] if score >= request.max_score * 0.6 else []
    if re.search(r"(因为|所以|首先|其次|因此|步骤|结论)", answer):
        strengths.append("表达中包含推理或步骤线索")
    gaps = []
    if score < request.max_score * 0.85:
        gaps.append("关键条件、公式依据或结论校验仍需补全")
    if reference and score < request.max_score * 0.7:
        gaps.append("与参考答案的关键要点重合不足")
    feedback = (
        "整体正确，可以进入变式训练。"
        if score >= request.max_score * 0.85
        else "已形成部分思路，但还需要补齐依据、步骤和最后校验。"
    )
    return score, strengths, gaps, feedback


def _apply_mastery_update(
    db: Session,
    user_id: str,
    request: ExerciseGradeRequest,
    score: float,
) -> tuple[float, float, dict[str, Any]]:
    topic = _normalize_topic(request.topic)
    profile = _profile_for_user(db, user_id)
    mastery_map = {
        _normalize_topic(key): _clamp_score(value)
        for key, value in (profile.get("mastery_map") or {}).items()
        if _normalize_topic(key)
    }
    before = mastery_map.get(topic, user_memory_profile_service.MASTERY_DEFAULT)
    observed = _clamp_score(score / request.max_score)
    reliability = 0.34 if request.reference_answer else 0.26
    after = _clamp_score((1 - reliability) * before + reliability * observed)
    mastery_map[topic] = after
    weak_points = [
        str(item).strip() for item in (profile.get("weak_points") or []) if str(item).strip()
    ]
    if after < 0.6 and request.topic not in weak_points:
        weak_points = [request.topic, *weak_points][:6]
    elif after >= 0.72:
        weak_points = [item for item in weak_points if _normalize_topic(item) != topic]
    update = {
        "formula": "M_new = clamp((1-r) * M_old + r * score_ratio, 0, 1)",
        "source": "resource_workshop.exercise_grade",
        "topic": topic,
        "score_ratio": observed,
        "reliability": reliability,
        "delta": round(after - before, 4),
        "updated_at": datetime.utcnow().isoformat(),
    }
    profile.update(
        {
            "weak_points": weak_points,
            "mastery_map": mastery_map,
            "mastery_update": update,
        }
    )
    _upsert_profile_from_dict(db, user_id, profile)
    return before, after, update


async def _call_qwen3_vl(request: ImageAnalyzeRequest) -> dict[str, Any]:
    api_key = (
        settings.MULTIMODAL_API_KEY
        or os.getenv("QWEN_API_KEY")
        or os.getenv("DASHSCOPE_API_KEY")
        or settings.OPENAI_API_KEY
    )
    base_url = (
        settings.MULTIMODAL_API_BASE
        or os.getenv("QWEN_OPENAI_BASE_URL")
        or os.getenv("QWEN_API_BASE")
        or settings.OPENAI_API_BASE
        or "https://dashscope.aliyuncs.com/compatible-mode/v1"
    ).rstrip("/")
    primary_model = os.getenv("QWEN_VL_MODEL") or settings.MULTIMODAL_MODEL
    fallback_model = os.getenv("QWEN_VL_FALLBACK_MODEL") or settings.MULTIMODAL_FALLBACK_MODEL
    models = []
    for candidate in (primary_model, fallback_model):
        if candidate and candidate not in models:
            models.append(candidate)
    if not api_key:
        raise RuntimeError("Qwen3-VL API key is not configured")
    image_ref = request.image_url or request.image_base64 or ""
    if request.image_base64 and not request.image_base64.startswith("data:"):
        image_ref = f"data:image/png;base64,{request.image_base64}"
    prompt = (
        "你是拍照搜题分析助手。请识别图片中的题目，输出严格 JSON："
        "{\"subject\":\"学科\",\"problem_type\":\"题型\",\"extracted_text\":\"题干文本\","
        "\"answer_markdown\":\"完整讲解，公式使用 $...$ 或 $$...$$\","
        "\"solution_outline\":[\"步骤1\",\"步骤2\"],\"answer_hint\":\"只给提示不直接泄题\","
        "\"diagram\":{\"type\":\"mermaid\",\"content\":\"flowchart TD...\"},"
        "\"confidence\":0.0,\"limitations\":[\"不确定处\"]}。"
        f"\n补充题干：{request.question_text or '无'}\n学科：{request.subject or '未知'}"
    )
    last_error: Exception | None = None
    async with httpx.AsyncClient(timeout=settings.MULTIMODAL_TIMEOUT_SECONDS) as client:
        for model in models:
            payload = {
                "model": model,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {"type": "image_url", "image_url": {"url": image_ref}},
                        ],
                    }
                ],
                "temperature": 0.1,
                "max_tokens": 900,
            }
            try:
                response = await client.post(
                    f"{base_url}/chat/completions",
                    headers={"Authorization": f"Bearer {api_key}"},
                    json=payload,
                )
                response.raise_for_status()
                data = response.json()
                content = (
                    data.get("choices", [{}])[0]
                    .get("message", {})
                    .get("content", "")
                )
                if isinstance(content, list):
                    content = "\n".join(
                        str(block.get("text", "")) if isinstance(block, dict) else str(block)
                        for block in content
                    )
                parsed = _extract_json_blob(str(content))
                if not parsed:
                    raise RuntimeError(f"{model} returned non-JSON content")
                return parsed
            except Exception as exc:
                last_error = exc
    raise RuntimeError(f"Qwen3-VL request failed: {last_error}")


def _fallback_image_analysis(request: ImageAnalyzeRequest, reason: str) -> ImageAnalyzeResponse:
    subject = (request.subject or "未知学科").strip() or "未知学科"
    question_text = (request.question_text or "").strip()
    extracted = question_text or "已收到图片，但当前未能稳定读取图片文字。"
    return ImageAnalyzeResponse(
        source="fallback",
        status="fallback",
        subject=subject,
        problem_type="图片题目分析骨架",
        extracted_text=extracted,
        answer_markdown=(
            "### 解题提示\n"
            "当前图片识别服务未就绪。请先补充题干文字，系统会继续给出分步讲解。"
        ),
        solution_outline=[
            "先人工确认题干、图表标注和已知条件是否完整。",
            "圈出要求求解或证明的目标，并把相关公式、概念或约束列成清单。",
            "按条件到结论的顺序尝试建立解题路径；若是选择题，逐项排除明显矛盾选项。",
        ],
        answer_hint="请补充更清晰的题干文字，或重新上传包含完整题目边界的图片。",
        diagram={
            "type": "mermaid",
            "content": "flowchart TD\nA[确认题干] --> B[提取条件]\nB --> C[匹配公式或概念]\nC --> D[分步求解]",
        },
        confidence=0.42 if question_text else 0.28,
        limitations=[f"视觉模型暂不可用：{reason}", "fallback 不会声称已读取图片细节"],
    )


@router.post("/packages", response_model=ResourcePackageResponse)
def generate_resource_package(
    *,
    db: Session = Depends(deps.get_db),
    current_user: CurrentUser,
    request: ResourcePackageRequest,
) -> Any:
    profile = _profile_for_user(db, str(current_user.id))
    return _build_resource_package(request, profile)


@router.post("/exercises/grade", response_model=ExerciseGradeResponse)
def grade_exercise_and_update_mastery(
    *,
    db: Session = Depends(deps.get_db),
    current_user: CurrentUser,
    request: ExerciseGradeRequest,
) -> Any:
    score, strengths, gaps, feedback = _grade_exercise(request)
    before, after, update = _apply_mastery_update(
        db,
        str(current_user.id),
        request,
        score,
    )
    topic = _normalize_topic(request.topic)
    follow_up = [
        f"用自己的话复述 {request.topic} 的适用条件。",
        "再做 1 道同知识点变式题，并写出每一步依据。",
    ]
    if after < 0.6:
        follow_up.insert(0, f"先回看 {request.topic} 的概念卡和标准例题。")
    return ExerciseGradeResponse(
        topic=topic,
        score=score,
        is_correct=score >= request.max_score * 0.85,
        mastery_before=before,
        mastery_after=after,
        mastery_delta=round(after - before, 4),
        feedback=feedback,
        strengths=strengths,
        gaps=gaps,
        follow_up=follow_up,
        mastery_update=update,
    )


@router.post("/images/analyze", response_model=ImageAnalyzeResponse)
async def analyze_image_problem(
    *,
    current_user: CurrentUser,
    request: ImageAnalyzeRequest,
) -> Any:
    _ = current_user
    try:
        parsed = await _call_qwen3_vl(request)
        return ImageAnalyzeResponse(
            source="qwen3-vl",
            status="success",
            subject=str(parsed.get("subject") or request.subject or "未知学科"),
            problem_type=str(parsed.get("problem_type") or "图片题目"),
            extracted_text=str(parsed.get("extracted_text") or request.question_text or ""),
            answer_markdown=str(parsed.get("answer_markdown") or ""),
            solution_outline=[
                str(item)
                for item in (parsed.get("solution_outline") or [])
                if str(item).strip()
            ][:6],
            answer_hint=str(parsed.get("answer_hint") or "先识别已知条件，再匹配对应公式或概念。"),
            diagram=parsed.get("diagram") if isinstance(parsed.get("diagram"), dict) else {},
            confidence=_clamp_score(parsed.get("confidence"), default=0.65),
            limitations=[
                str(item)
                for item in (parsed.get("limitations") or [])
                if str(item).strip()
            ][:4],
        )
    except Exception as exc:
        return _fallback_image_analysis(request, str(exc))
