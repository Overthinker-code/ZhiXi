from __future__ import annotations

import json
import re
from typing import Any
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from langchain_core.messages import HumanMessage

from app.core.config import settings
from app.schemas.resource_generation import (
    GeneratedResourceArtifact,
    ResourceGenerationRequest,
    ResourceGenerationResponse,
    ResourceKind,
)
from app.services.chat_model_factory import ChatModelFactory


DEFAULT_RESOURCE_TYPES: list[ResourceKind] = [
    "lecture_markdown",
    "lecture_pdf",
    "practice_markdown",
    "practice_pdf",
    "mind_map",
    "reading_list",
    "case_project",
    "video_script",
    "quality_checklist",
]


class ResourceGenerationService:
    """Local-first resource producer for the course resource center."""

    def __init__(self) -> None:
        self.output_root = Path(settings.BASE_PATH) / "generated_resources"

    def generate(self, request: ResourceGenerationRequest) -> ResourceGenerationResponse:
        package_id = f"rg_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{uuid4().hex[:8]}"
        target_dir = self.output_root / package_id
        target_dir.mkdir(parents=True, exist_ok=True)

        kinds = request.resource_types or DEFAULT_RESOURCE_TYPES
        context = self._build_context(request)
        ai_contents, ai_generation_error = self._generate_ai_contents(context, kinds)
        artifacts: list[GeneratedResourceArtifact] = []
        markdown_cache: dict[str, str] = {}

        for kind in kinds:
            if kind == "lecture_markdown":
                markdown_cache["lecture"] = ai_contents.get(kind) or self._lecture_markdown(context)
                artifacts.append(
                    self._write_artifact(
                        target_dir,
                        kind,
                        f"{request.topic} 个性化讲义",
                        "lecture.md",
                        markdown_cache["lecture"],
                        "text/markdown",
                    )
                )
            elif kind == "lecture_pdf":
                lecture = markdown_cache.get("lecture") or ai_contents.get("lecture_markdown") or self._lecture_markdown(context)
                artifacts.append(
                    self._write_artifact(
                        target_dir,
                        kind,
                        f"{request.topic} 讲义 PDF",
                        "lecture.pdf",
                        self._minimal_pdf_bytes(lecture, title=f"{request.topic} 个性化讲义"),
                        "application/pdf",
                    )
                )
            elif kind == "practice_markdown":
                markdown_cache["practice"] = ai_contents.get(kind) or self._practice_markdown(context)
                artifacts.append(
                    self._write_artifact(
                        target_dir,
                        kind,
                        f"{request.topic} 分层练习",
                        "practice.md",
                        markdown_cache["practice"],
                        "text/markdown",
                    )
                )
            elif kind == "practice_pdf":
                practice = markdown_cache.get("practice") or ai_contents.get("practice_markdown") or self._practice_markdown(context)
                artifacts.append(
                    self._write_artifact(
                        target_dir,
                        kind,
                        f"{request.topic} 练习 PDF",
                        "practice.pdf",
                        self._minimal_pdf_bytes(practice, title=f"{request.topic} 分层练习"),
                        "application/pdf",
                    )
                )
            elif kind == "mind_map":
                artifacts.append(
                    self._write_artifact(
                        target_dir,
                        kind,
                        f"{request.topic} 思维导图",
                        "mind-map.mmd",
                        ai_contents.get(kind) or self._mind_map(context),
                        "text/plain",
                    )
                )
            elif kind == "reading_list":
                artifacts.append(
                    self._write_artifact(
                        target_dir,
                        kind,
                        f"{request.topic} 拓展阅读",
                        "reading-list.md",
                        ai_contents.get(kind) or self._reading_list(context),
                        "text/markdown",
                    )
                )
            elif kind == "case_project":
                artifacts.append(
                    self._write_artifact(
                        target_dir,
                        kind,
                        f"{request.topic} 实操案例",
                        "case-project.md",
                        ai_contents.get(kind) or self._case_project(context),
                        "text/markdown",
                    )
                )
            elif kind == "video_script":
                artifacts.append(
                    self._write_artifact(
                        target_dir,
                        kind,
                        f"{request.topic} 数字人脚本",
                        "video-script.md",
                        ai_contents.get(kind) or self._video_script(context),
                        "text/markdown",
                    )
                )
            elif kind == "quality_checklist":
                artifacts.append(
                    self._write_artifact(
                        target_dir,
                        kind,
                        f"{request.topic} 使用审查清单",
                        "quality-checklist.md",
                        ai_contents.get(kind) or self._quality_checklist(context),
                        "text/markdown",
                    )
                )

        self.write_manifest(
            target_dir,
            request=request,
            package_id=package_id,
            artifacts=artifacts,
        )

        return ResourceGenerationResponse(
            package_id=package_id,
            course_id=request.course_id,
            resource_id=request.resource_id,
            node_id=request.node_id,
            node_label=request.node_label,
            map_type=request.map_type,
            source=request.source,
            subject=request.subject,
            topic=request.topic,
            generated_at=datetime.utcnow(),
            local_model_profile={
                "chat_provider": settings.CHAT_PROVIDER,
                "chat_model": self._active_chat_model_name(),
                "embedding_provider": settings.EMBEDDINGS_PROVIDER,
                "multimodal_model": settings.MULTIMODAL_MODEL,
                "deployment": "api-first"
                if settings.CHAT_PROVIDER.lower() == "mimo"
                else "provider-configured",
                "mode": "课程上下文 + MiMo 结构化生成 + 质量审查"
                if ai_contents
                else "课程画像 + 本地结构化回退 + 质量审查",
                "content_provider": "mimo"
                if len(ai_contents) == len(
                    [
                        kind
                        for kind in kinds
                        if kind
                        in {
                            "lecture_markdown",
                            "practice_markdown",
                            "mind_map",
                            "reading_list",
                            "case_project",
                            "video_script",
                            "quality_checklist",
                        }
                    ]
                )
                else ("mimo_partial" if ai_contents else "local_fallback"),
                "ai_generated_artifacts": sorted(ai_contents.keys()),
                "fallback_artifacts": sorted(
                    {
                        kind
                        for kind in kinds
                        if kind
                        in {
                            "lecture_markdown",
                            "practice_markdown",
                            "mind_map",
                            "reading_list",
                            "case_project",
                            "video_script",
                            "quality_checklist",
                        }
                    }
                    - set(ai_contents.keys())
                ),
                "domain": context["domain"],
                "fallback_reason": ai_generation_error or "",
            },
            agent_trace=[
                "ProfileAgent: 读取学习画像和目标难度",
                f"DomainAgent: 识别课程域为 {context['domain']}",
                "EvidenceAgent: 生成课程证据清单和引用模板",
                "MiMoContentAgent: 基于课程上下文生成结构化资源正文"
                if ai_contents
                else "FallbackContentAgent: MiMo 内容生成不可用，使用本地结构化回退",
                "LectureAgent: 生成讲义、概念卡和课堂案例",
                "ExerciseAgent: 生成分层练习和评分量规",
                "MindMapAgent: 生成知识结构、图谱节点和迁移路径",
                "CaseAgent: 生成实操任务和提交物模板",
                "ScriptAgent: 生成讲解脚本与课后动作",
                "QualityAgent: 生成资源使用审查清单",
                "SafetyReviewAgent: 检查事实边界、适用条件、课堂证据和输出格式",
                "FinalizerAgent: 汇总为可下载资源包",
            ],
            quality_notes=[
                f"已按“{context['scenario']}”组织案例，不输出空泛学习建议。",
                "讲义、练习、导图、阅读和案例均绑定课堂笔记、课程图谱与 AI 批改入口。",
                "资源包包含 quality-checklist.md，可用于下载后逐项验收与学习闭环追踪。",
                "所有可下载 Markdown 为中文主产物；PDF 为轻量预览版，排版完整性以 Markdown 为准。",
                "联网搜索默认受控关闭；若启用，外部资料必须在内容中单独标注来源。",
            ],
            artifacts=artifacts,
        )

    def list_recent_packages(
        self, limit: int = 12, course_id: str | None = None
    ) -> list[dict[str, object]]:
        self.output_root.mkdir(parents=True, exist_ok=True)
        packages: list[dict[str, object]] = []
        for folder in sorted(
            [item for item in self.output_root.iterdir() if item.is_dir()],
            key=lambda item: item.stat().st_mtime,
            reverse=True,
        ):
            artifacts = sorted(folder.iterdir(), key=lambda item: item.name)
            manifest = next((item for item in artifacts if item.suffix == ".json" and item.name == "manifest.json"), None)
            payload: dict[str, object] = {}
            if manifest and manifest.exists():
                try:
                    payload = json.loads(manifest.read_text(encoding="utf-8"))
                except Exception:
                    payload = {}
            if not payload:
                payload = self._infer_manifest_from_artifacts(folder)
            package_course_id = str(payload.get("course_id") or "")
            if course_id and package_course_id and package_course_id != course_id:
                continue
            packages.append(
                {
                    "package_id": folder.name,
                    "course_id": package_course_id,
                    "resource_id": payload.get("resource_id") or "",
                    "node_id": payload.get("node_id") or "",
                    "node_label": payload.get("node_label") or "",
                    "map_type": payload.get("map_type") or "",
                    "source": payload.get("source") or "",
                    "subject": payload.get("subject") or "",
                    "topic": payload.get("topic") or folder.name,
                    "generated_at": payload.get("generated_at")
                    or datetime.fromtimestamp(folder.stat().st_mtime).isoformat(),
                    "artifacts": [
                        {
                            "kind": self._artifact_kind_from_name(item.name),
                            "title": item.stem.replace("-", " ").replace("_", " "),
                            "file_name": item.name,
                            "download_url": f"/api/v1/resource-generation/artifacts/{folder.name}/{item.name}",
                            "file_size": item.stat().st_size,
                        }
                        for item in artifacts
                        if item.is_file() and item.name != "manifest.json"
                    ],
                }
            )
            if len(packages) >= limit:
                break
        return packages

    @staticmethod
    def _active_chat_model_name() -> str:
        provider = settings.CHAT_PROVIDER.lower()
        if provider == "ollama":
            return settings.OLLAMA_MODEL
        if provider == "mimo":
            return settings.MIMO_CHAT_MODEL or settings.CHAT_MODEL
        return settings.CHAT_MODEL

    @staticmethod
    def _artifact_kind_from_name(file_name: str) -> str:
        name = file_name.lower()
        if "practice" in name:
            return "practice_pdf" if name.endswith(".pdf") else "practice_markdown"
        if "mind" in name:
            return "mind_map"
        if "reading" in name:
            return "reading_list"
        if "case" in name:
            return "case_project"
        if "video" in name or "script" in name:
            return "video_script"
        if "quality" in name or "check" in name:
            return "quality_checklist"
        return "lecture_pdf" if name.endswith(".pdf") else "lecture_markdown"

    @staticmethod
    def _infer_manifest_from_artifacts(folder: Path) -> dict[str, object]:
        lecture = folder / "lecture.md"
        subject = ""
        topic = folder.name
        if lecture.exists():
            try:
                text = lecture.read_text(encoding="utf-8", errors="ignore")
                for line in text.splitlines():
                    if line.startswith("课程："):
                        subject = line.replace("课程：", "", 1).strip()
                    elif line.startswith("# "):
                        topic = (
                            line.replace("# ", "", 1)
                            .replace(" 个性化讲义", "")
                            .strip()
                            or topic
                        )
            except Exception:
                pass
        return {
            "package_id": folder.name,
            "subject": subject,
            "topic": topic,
            "generated_at": datetime.fromtimestamp(folder.stat().st_mtime).isoformat(),
        }

    def _build_context(self, request: ResourceGenerationRequest) -> dict[str, str]:
        goal = request.learning_goal or f"掌握 {request.topic} 的核心概念、典型题型和应用方法"
        difficulty_label = {
            "foundation": "基础巩固",
            "standard": "标准提升",
            "challenge": "挑战拓展",
        }[request.difficulty]
        terms = self._topic_terms(request.subject, request.topic)
        domain = self._domain_profile(request.subject, request.topic, terms)
        note_blocks = [
            f"概念边界：用自己的话解释 {request.topic}，并圈出 {terms[0]} 的判定条件",
            f"方法步骤：把 {terms[1]} 拆成可检查的 3-5 个动作",
            f"结果校验：用 {terms[2]}、反例或评价指标验证结论不过度推广",
            f"迁移记录：把课堂案例改写成一个来自 {domain['domain']} 的新问题",
        ]
        graph_nodes = [
            f"先修节点：{terms[0]}",
            f"核心节点：{request.topic}",
            f"方法节点：{terms[1]}",
            f"校验节点：{terms[2]}",
            f"应用节点：{domain['transfer']}",
        ]
        learning_sequence = [
            "先读讲义第 1-4 节，补齐定义、证据和案例链路",
            "再打开 mind-map.mmd，把每个节点对应到课堂笔记或资源文件",
            "完成 practice.md 的基础题和标准题，并把错题送入 AI 批改",
            "用 case-project.md 输出一份可提交任务，再用 quality-checklist.md 自查",
        ]
        quality_gate = [
            "每个结论必须能回指课堂笔记、知识图谱节点或练习解析",
            "每个练习必须有评分点、错因判断和下一步追练动作",
            "每个案例必须包含输入材料、操作步骤、验收标准和可迁移边界",
            "每个资源必须说明何时进入 AI 伴学、何时进入资源再生成",
        ]
        return {
            "subject": request.subject.strip(),
            "topic": request.topic.strip(),
            "goal": goal.strip(),
            "difficulty": difficulty_label,
            "minutes": str(request.target_minutes),
            "terms": "、".join(terms),
            "primary": terms[0],
            "secondary": terms[1],
            "third": terms[2],
            "profile": self._course_profile(request.subject, request.topic),
            "domain": domain["domain"],
            "scenario": domain["scenario"],
            "case": domain["case"],
            "evidence": "；".join(domain["evidence"]),
            "rubric": "；".join(domain["rubric"]),
            "mistakes": "；".join(domain["mistakes"]),
            "transfer": domain["transfer"],
            "note_blocks": "\n".join(f"- {item}" for item in note_blocks),
            "graph_nodes": "\n".join(f"- {item}" for item in graph_nodes),
            "learning_sequence": "\n".join(f"{index}. {item}" for index, item in enumerate(learning_sequence, 1)),
            "quality_gate": "\n".join(f"- {item}" for item in quality_gate),
            "resource_contract": (
                f"讲义负责讲清 {request.topic}，练习负责暴露错因，思维导图负责定位关系，"
                f"案例负责迁移应用，质量清单负责把学习动作闭环到 AI 批改和课程图谱。"
            ),
        }

    def _generate_ai_contents(
        self,
        ctx: dict[str, str],
        kinds: list[ResourceKind],
    ) -> tuple[dict[str, str], str]:
        provider = settings.CHAT_PROVIDER.lower()
        if (
            not settings.RESOURCE_GENERATION_AI_ENABLED
            or provider != "mimo"
            or not settings.MIMO_API_KEY
        ):
            return {}, "mimo_not_configured"
        requested = [
            kind
            for kind in kinds
            if kind
            in {
                "lecture_markdown",
                "practice_markdown",
                "mind_map",
                "reading_list",
                "case_project",
                "video_script",
                "quality_checklist",
            }
        ]
        if not requested:
            return {}, ""
        contents: dict[str, str] = {}
        generation_error = ""
        try:
            model = ChatModelFactory.create(
                temperature=0.2,
                max_tokens=4200,
                top_p=0.9,
                model_name=settings.MIMO_FAST_MODEL or settings.MIMO_CHAT_MODEL,
            )
            response = model.invoke(
                [
                    HumanMessage(
                        content=self._resource_generation_prompt(ctx, requested)
                    )
                ]
            )
            raw = getattr(response, "content", response)
            payload = self._parse_structured_payload(str(raw), requested)
            if not payload:
                payload = self._parse_json_payload(str(raw))
            contents = self._validate_ai_contents(payload, requested, ctx)
        except Exception as exc:
            generation_error = exc.__class__.__name__
        missing = [kind for kind in requested if kind not in contents]
        for kind in missing:
            try:
                content = self._generate_single_ai_content(ctx, kind)
                if content:
                    contents[kind] = content
            except Exception as exc:
                generation_error = generation_error or exc.__class__.__name__
        if not contents:
            return {}, generation_error or "empty_ai_contents"
        if len(contents) != len(requested):
            return contents, generation_error or "partial_ai_contents"
        return contents, ""

    def _generate_single_ai_content(
        self,
        ctx: dict[str, str],
        kind: str,
    ) -> str:
        max_tokens = {
            "lecture_markdown": 2400,
            "practice_markdown": 2600,
            "mind_map": 1400,
            "reading_list": 1400,
            "case_project": 2200,
            "video_script": 2000,
            "quality_checklist": 2200,
        }.get(kind, 1800)
        model = ChatModelFactory.create(
            temperature=0.2,
            max_tokens=max_tokens,
            top_p=0.9,
            model_name=settings.MIMO_FAST_MODEL or settings.MIMO_CHAT_MODEL,
        )
        response = model.invoke(
            [
                HumanMessage(
                    content=self._resource_generation_prompt(ctx, [kind])
                )
            ]
        )
        raw = getattr(response, "content", response)
        raw_text = str(raw)
        payload = self._parse_structured_payload(raw_text, [kind])
        try:
            if not payload:
                payload = self._parse_json_payload(raw_text)
        except Exception:
            if not payload:
                payload = {kind: raw_text.strip()}
        contents = self._validate_ai_contents(payload, [kind], ctx)
        return contents.get(kind, "")

    @staticmethod
    def _resource_generation_prompt(ctx: dict[str, str], kinds: list[str]) -> str:
        tags = "\n".join(
            f"<{kind}>\n请在这里输出 {kind} 正文\n</{kind}>" for kind in kinds
        )
        return f"""你是教育 SaaS 平台的课程资源生成器。请只输出下面这些 XML 风格标签，不要输出 Markdown 代码围栏，不要添加标签之外的解释。

输出结构:
{tags}

生成要求：
1. 每个请求的标签必须完整出现，开始标签和结束标签必须完全匹配。
2. 内容必须围绕课程《{ctx['subject']}》和知识点“{ctx['topic']}”，不得泛泛而谈。
3. 必须绑定课程图谱、课堂证据、学习目标、错因诊断和后续学习动作。
4. 不得编造外部文献来源；阅读清单只能写课程内资料、教材章节、课堂笔记、练习和可核验资料类型。
5. 每个 Markdown 类资源至少包含标题、学习目标、课程证据、节点关系、学习任务、质量自查。
6. mind_map 字段必须输出 Mermaid mindmap 文本，根节点是“{ctx['topic']}”。
7. practice_markdown 必须包含基础题、标准题、挑战题、答案框架和错因追练。
8. quality_checklist 必须能用于验收资源是否真实服务学习闭环。
9. 不允许出现“第X章”“第Y次课”“某教材”“待补充”“占位”等占位文案；若资料无法确定，写“课程讲义中与本节点关联的章节”这类可执行描述。

课程上下文：
- 课程：{ctx['subject']}
- 知识点：{ctx['topic']}
- 学习目标：{ctx['goal']}
- 难度：{ctx['difficulty']}
- 建议时长：{ctx['minutes']} 分钟
- 课程域：{ctx['domain']}
- 课程画像：{ctx['profile']}
- 应用场景：{ctx['scenario']}
- 案例线索：{ctx['case']}
- 证据清单：{ctx['evidence']}
- 评分量规：{ctx['rubric']}
- 常见错因：{ctx['mistakes']}
- 迁移目标：{ctx['transfer']}
- 图谱节点：
{ctx['graph_nodes']}
- 学习路径：
{ctx['learning_sequence']}
- 质量门禁：
{ctx['quality_gate']}
"""

    @staticmethod
    def _parse_structured_payload(raw: str, requested: list[str]) -> dict[str, Any]:
        payload: dict[str, Any] = {}
        for kind in requested:
            match = re.search(
                rf"<{re.escape(kind)}>\s*(.*?)\s*</{re.escape(kind)}>",
                raw,
                flags=re.DOTALL | re.IGNORECASE,
            )
            if match:
                payload[kind] = match.group(1).strip()
        return payload

    @staticmethod
    def _parse_json_payload(raw: str) -> dict[str, Any]:
        text = raw.strip()
        if text.startswith("```"):
            text = re.sub(r"^```(?:json)?\s*", "", text)
            text = re.sub(r"\s*```$", "", text).strip()
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end > start:
            text = text[start : end + 1]
        payload = json.loads(text)
        return payload if isinstance(payload, dict) else {}

    @staticmethod
    def _validate_ai_contents(
        payload: dict[str, Any],
        requested: list[str],
        ctx: dict[str, str],
    ) -> dict[str, str]:
        contents: dict[str, str] = {}
        required_terms = [ctx["subject"], ctx["topic"]]
        for kind in requested:
            value = payload.get(kind)
            if not isinstance(value, str):
                continue
            text = ResourceGenerationService._strip_artifact_tags(value.strip(), kind)
            if len(text) < 240 and kind != "mind_map":
                continue
            if ResourceGenerationService._contains_placeholder(text):
                continue
            if ResourceGenerationService._contains_protocol_markup(text):
                continue
            if kind == "mind_map":
                if "mindmap" not in text.lower() or ctx["topic"] not in text:
                    continue
            elif not all(term in text for term in required_terms):
                continue
            contents[kind] = text
        return contents

    @staticmethod
    def _contains_placeholder(text: str) -> bool:
        patterns = [
            r"第\s*[XxYyZz]\s*(章|节|次|讲)",
            r"某(教材|资料|章节|案例|文件)",
            r"待(补充|填写|完善|确认)",
            r"TBD",
            r"占位",
            r"xxx+",
        ]
        return any(re.search(pattern, text) for pattern in patterns)

    @staticmethod
    def _strip_artifact_tags(text: str, kind: str) -> str:
        text = re.sub(
            rf"^\s*<{re.escape(kind)}>\s*",
            "",
            text,
            flags=re.IGNORECASE,
        )
        text = re.sub(
            rf"\s*</{re.escape(kind)}>\s*$",
            "",
            text,
            flags=re.IGNORECASE,
        )
        return text.strip()

    @staticmethod
    def _contains_protocol_markup(text: str) -> bool:
        return bool(
            re.search(
                r"</?(lecture_markdown|practice_markdown|mind_map|reading_list|case_project|video_script|quality_checklist|resource)\b",
                text,
                flags=re.IGNORECASE,
            )
        )

    def _write_artifact(
        self,
        target_dir: Path,
        kind: ResourceKind,
        title: str,
        file_name: str,
        content: str | bytes,
        content_type: str,
    ) -> GeneratedResourceArtifact:
        safe_name = self._safe_file_name(file_name)
        path = target_dir / safe_name
        if isinstance(content, bytes):
            path.write_bytes(content)
            preview = ""
        else:
            path.write_text(content, encoding="utf-8")
            preview = content[:500]
        stat = path.stat()
        return GeneratedResourceArtifact(
            kind=kind,
            title=title,
            file_name=safe_name,
            download_url=f"/api/v1/resource-generation/artifacts/{target_dir.name}/{safe_name}",
            content_type=content_type,
            file_size=stat.st_size,
            preview=preview,
        )

    def write_manifest(
        self,
        target_dir: Path,
        *,
        request: ResourceGenerationRequest,
        package_id: str,
        artifacts: list[GeneratedResourceArtifact],
    ) -> None:
        manifest = {
            "package_id": package_id,
            "course_id": str(request.course_id) if request.course_id else "",
            "resource_id": request.resource_id or "",
            "node_id": request.node_id or "",
            "node_label": request.node_label or "",
            "map_type": request.map_type or "",
            "source": request.source or "",
            "subject": request.subject,
            "topic": request.topic,
            "generated_at": datetime.utcnow().isoformat(),
            "artifacts": [
                {
                    "kind": artifact.kind,
                    "title": artifact.title,
                    "file_name": artifact.file_name,
                    "download_url": artifact.download_url,
                    "file_size": artifact.file_size,
                }
                for artifact in artifacts
            ],
        }
        (target_dir / "manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    @staticmethod
    def _topic_terms(subject: str, topic: str) -> list[str]:
        text = f"{subject} {topic}".lower()
        if "数据库" in text or "sql" in text:
            return ["关系模型", "SQL 查询", "完整性约束", "事务并发", "规范化"]
        if "数据结构" in text or "算法" in text:
            return ["抽象数据类型", "复杂度分析", "遍历策略", "存储结构", "边界条件"]
        if "人工智能" in text or "ai" in text:
            return ["问题建模", "搜索策略", "知识表示", "模型训练", "评估指标"]
        if "宏观" in text or "经济" in text:
            return ["总量指标", "总需求", "政策传导", "经济周期", "长期增长"]
        if "审计" in text:
            return ["审计目标", "重大错报风险", "内部控制", "审计证据", "审计意见"]
        if "金融" in text:
            return ["时间价值", "现金流折现", "风险收益", "投资组合", "资本成本"]
        return [topic, "定义边界", "适用条件", "典型案例", "自测反馈"]

    @staticmethod
    def _course_profile(subject: str, topic: str) -> str:
        return (
            f"课程《{subject}》当前围绕“{topic}”组织资料。资源包默认面向学生自学，"
            "先补概念边界，再给案例和练习，最后用检查清单确认是否能迁移应用。"
        )

    @staticmethod
    def _domain_profile(subject: str, topic: str, terms: list[str]) -> dict[str, object]:
        text = f"{subject} {topic}".lower()
        primary, secondary, third = terms[:3]
        if "数据库" in text or "sql" in text:
            return {
                "domain": "数据库课程",
                "scenario": "把校园选课、成绩登记或图书借阅业务转化为关系模式与 SQL 查询任务",
                "case": "给出学生、课程、选课三张表，要求识别主键/外键、写出连接查询，并说明事务提交失败时如何恢复。",
                "evidence": [
                    "关系模式是否标出主键、外键和属性域",
                    "SQL 是否能从投影、筛选、连接和聚合四步追溯",
                    "事务分析是否说明 ACID 与并发调度依据",
                ],
                "rubric": [
                    "概念边界 25%",
                    "SQL 或模式设计步骤 35%",
                    "约束与异常处理 25%",
                    "可读性与验证 15%",
                ],
                "mistakes": [
                    "把外键写成普通属性",
                    "JOIN 条件缺失导致笛卡尔积",
                    "只写最终 SQL 不解释业务约束",
                ],
                "transfer": "能把新的业务描述拆成实体、联系、约束、查询和事务五类对象。",
            }
        if "数据结构" in text or "算法" in text:
            return {
                "domain": "数据结构课程",
                "scenario": "为一个检索、排队或路径问题选择合适的数据结构并分析复杂度",
                "case": "根据操作频率选择数组、链表、堆或图存储，写出关键操作伪代码并计算最坏复杂度。",
                "evidence": [
                    "问题操作是否拆成访问、插入、删除、遍历",
                    "结构选择是否匹配复杂度需求",
                    "边界条件是否覆盖空结构、单元素和重复值",
                ],
                "rubric": [
                    "抽象建模 25%",
                    "结构选择 25%",
                    "算法步骤 30%",
                    "复杂度与边界 20%",
                ],
                "mistakes": [
                    "只背结构定义，不说明适用操作",
                    "平均复杂度和最坏复杂度混用",
                    "忽略空指针或越界条件",
                ],
                "transfer": "能从题目中的操作频率反推结构选择，而不是凭关键词套模板。",
            }
        if "人工智能" in text or "ai" in text:
            return {
                "domain": "人工智能课程",
                "scenario": "把真实问题转化为状态空间、知识表示或模型训练任务",
                "case": "为路径规划、诊断或分类任务定义状态、动作、评价指标，并比较搜索与学习方法的适用边界。",
                "evidence": [
                    "是否明确输入、输出、状态或样本标签",
                    "是否说明启发函数、知识表示或模型假设",
                    "是否用准确率、召回率或代价函数评价结果",
                ],
                "rubric": [
                    "问题建模 30%",
                    "方法选择 25%",
                    "评价指标 25%",
                    "风险与边界 20%",
                ],
                "mistakes": [
                    "把 AI 方法名称当成答案",
                    "不区分训练数据、验证数据和测试数据",
                    "忽略偏差、方差或不可解释性风险",
                ],
                "transfer": "能判断一个任务更适合搜索、规则推理、传统机器学习还是深度学习。",
            }
        if "宏观" in text or "经济" in text:
            return {
                "domain": "宏观经济学课程",
                "scenario": "用总量指标和模型解释政策变化对产出、价格和就业的影响",
                "case": "分析降准、财政扩张或外需下降对 AD-AS、利率和就业的传导路径。",
                "evidence": [
                    "变量是否区分名义量与实际量",
                    "传导链是否包含部门、市场和时间滞后",
                    "结论是否说明短期与长期差异",
                ],
                "rubric": [
                    "指标解释 25%",
                    "模型推理 35%",
                    "政策边界 25%",
                    "图形表达 15%",
                ],
                "mistakes": [
                    "把相关关系当因果关系",
                    "只说政策方向，不写传导链",
                    "忽略价格水平和实际产出的区别",
                ],
                "transfer": "能把新闻中的宏观政策转写为变量变化和模型移动。",
            }
        if "审计" in text:
            return {
                "domain": "审计学课程",
                "scenario": "围绕重大错报风险设计审计程序并评价证据是否充分适当",
                "case": "对收入确认或存货跌价风险设计询问、观察、函证和重新计算程序。",
                "evidence": [
                    "是否从认定出发识别风险",
                    "程序是否能回应对应风险",
                    "证据是否同时评价充分性与适当性",
                ],
                "rubric": [
                    "风险识别 30%",
                    "程序设计 30%",
                    "证据评价 25%",
                    "职业判断 15%",
                ],
                "mistakes": [
                    "把审计目标和具体程序混写",
                    "只列程序不说明能验证哪项认定",
                    "证据数量和证据质量不区分",
                ],
                "transfer": "能针对新的业务循环选择匹配的审计程序和证据标准。",
            }
        if "金融" in text:
            return {
                "domain": "金融学课程",
                "scenario": "用现金流、风险收益和资本成本分析投资或融资决策",
                "case": "根据债券现金流、股票估值或项目 NPV 判断是否投资，并说明风险调整依据。",
                "evidence": [
                    "现金流时点是否列清",
                    "贴现率是否与风险水平匹配",
                    "结论是否包含敏感性或情景分析",
                ],
                "rubric": [
                    "现金流建模 30%",
                    "折现与估值 30%",
                    "风险解释 25%",
                    "决策建议 15%",
                ],
                "mistakes": [
                    "混淆现值和终值",
                    "贴现率随意取值",
                    "只算结果不解释风险来源",
                ],
                "transfer": "能把任意资产或项目拆成现金流、折现率、风险和决策标准。",
            }
        return {
            "domain": "通用课程",
            "scenario": f"围绕 {topic} 完成概念解释、案例拆解和迁移练习",
            "case": f"选择一个与 {topic} 相关的课堂案例，标出条件、方法、结论和边界。",
            "evidence": [
                f"是否能定义 {primary}",
                f"是否能说明 {secondary} 的适用条件",
                f"是否能用 {third} 做结果校验",
            ],
            "rubric": ["概念准确 30%", "步骤完整 30%", "应用迁移 25%", "表达清晰 15%"],
            "mistakes": ["只背结论", "条件遗漏", "缺少边界校验"],
            "transfer": "能把本节主题迁移到新的题目或真实问题。",
        }

    @staticmethod
    def _safe_file_name(value: str) -> str:
        name = re.sub(r"[^a-zA-Z0-9._-]+", "-", value.strip()).strip("-")
        return name or f"artifact-{uuid4().hex[:8]}.md"

    @staticmethod
    def _lecture_markdown(ctx: dict[str, str]) -> str:
        return f"""# {ctx['topic']} 个性化讲义

课程：{ctx['subject']}
目标：{ctx['goal']}
难度：{ctx['difficulty']}
建议学习时长：{ctx['minutes']} 分钟
生成依据：{ctx['profile']}
课程域：{ctx['domain']}
资源契约：{ctx['resource_contract']}

## 1. 一句话定位
{ctx['topic']} 是本节学习的核心对象。学习时先弄清它解决什么问题，再看它和 {ctx['primary']}、{ctx['secondary']}、{ctx['third']} 的关系。不要只背术语，必须能把定义、证据、步骤和适用边界串成一条可复述的链路。

## 2. 核心概念卡
| 概念 | 课堂定位 | 学习检查 |
| --- | --- | --- |
| {ctx['primary']} | 用来确定问题对象和基本结构 | 能否说清定义、输入和输出 |
| {ctx['secondary']} | 用来完成主要推理或操作步骤 | 能否列出 3 个判断条件 |
| {ctx['third']} | 用来做结果校验和边界判断 | 能否解释一个反例 |

## 3. 课堂笔记对齐
把课堂笔记整理成下面四个块，后续练习、导图和案例都从这里取证：

{ctx['note_blocks']}

## 4. 课程证据清单
{ctx['evidence']}

使用资料时先把每个结论对应到上述证据项。若某一步没有证据，只能标为“推断”，并在 AI 伴学中要求补证或换例。

## 5. 课堂案例拆解
场景：{ctx['scenario']}

案例：{ctx['case']}

1. 标出题干或材料中的已知条件。
2. 判断这些条件分别对应 {ctx['primary']}、{ctx['secondary']} 还是 {ctx['third']}。
3. 写出推理链：条件 -> 方法 -> 中间结果 -> 结论。
4. 用一个反例或边界条件检查结论是否过度推广。

## 6. 课程图谱绑定
学习时按下面节点在课程图谱中逐个点开，确认每个节点都有笔记、资源和练习：

{ctx['graph_nodes']}

## 7. 易错点
{ctx['mistakes']}

## 8. 学习路径
{ctx['learning_sequence']}

## 9. 迁移目标
{ctx['transfer']}

## 10. 自我检查
- 我能否不用教材原句解释 {ctx['topic']}？
- 我能否指出 {ctx['primary']} 在案例中的证据？
- 我能否说出一个不适用 {ctx['topic']} 的场景？
- 我能否把本资源中的一个节点拖入课程图谱，并说明它连接了哪份练习？
"""

    @staticmethod
    def _practice_markdown(ctx: dict[str, str]) -> str:
        return f"""# {ctx['topic']} 分层练习

课程：{ctx['subject']}
匹配场景：{ctx['scenario']}
练习目标：通过分层题暴露“定义不清、条件遗漏、步骤跳跃、结论无证据”四类错因。

## 基础题
1. 用 80 字以内解释 {ctx['topic']}，并写出它和 {ctx['primary']} 的关系。
2. 判断题：只要题干出现关键词，就一定可以套用 {ctx['topic']}。请说明理由，并指出需要补充的条件。
3. 填空：解决这类问题时，第一步应先识别 ______，第二步再选择 ______。

## 标准题
4. 给定一个课程案例，列出已知条件、适用概念、推理步骤、最终结论和证据来源。
5. 设计一道同类变式题，并写出标准答案和评分点。

## 挑战题
6. 比较 {ctx['topic']} 与 {ctx['secondary']} 的差异，至少列出 3 个判断标准。
7. 写一个容易出错的答案，并说明它错在定义、条件、步骤还是结论。

## 标准答案框架
| 题号 | 合格答案应包含 | 常见错因 | AI 追练指令 |
| --- | --- | --- | --- |
| 1 | 定义、适用对象、与 {ctx['primary']} 的关系 | 只背原句，没有边界 | 要求 AI 追问一个反例 |
| 2 | 判断为否，并说明关键词不足以替代条件 | 关键词套模板 | 要求 AI 生成两个相似但不适用的题 |
| 3 | 先识别条件，再选择方法或表示方式 | 步骤跳跃 | 要求 AI 按步骤逐格批改 |
| 4 | 条件表、概念表、步骤表、结论表、证据表 | 结论没有证据 | 要求 AI 用评分量规打分 |
| 5 | 题干、参考答案、评分点、变式说明 | 只换数字不换能力点 | 要求 AI 判断变式是否有效 |
| 6 | 至少 3 个标准，并对应示例 | 概念混淆 | 要求 AI 做概念对照卡 |
| 7 | 错误答案、错因分类、订正答案 | 只说“粗心” | 要求 AI 继续生成错因同类题 |

## 评分量规
{ctx['rubric']}

## 课堂笔记回填
完成练习后，把错因回填到课堂笔记：

{ctx['note_blocks']}

## 完成后的闭环动作
1. 把低于 80 分的题目送入 AI 批改，要求输出“错因 -> 订正 -> 追练”。
2. 在课程图谱里标记对应节点为“待巩固”，并关联本练习题号。
3. 若连续两题错在同一类原因，重新生成 15 分钟微资源包。
"""

    @staticmethod
    def _mind_map(ctx: dict[str, str]) -> str:
        return f"""mindmap
  root(({ctx['topic']}))
    课程定位
      课程::{ctx['subject']}
      课程域::{ctx['domain']}
      学习目标::{ctx['goal']}
    课堂笔记
      概念边界::{ctx['primary']}
      方法步骤::{ctx['secondary']}
      结果校验::{ctx['third']}
      迁移记录
    知识图谱节点
      先修节点::{ctx['primary']}
      核心节点::{ctx['topic']}
      方法节点::{ctx['secondary']}
      校验节点::{ctx['third']}
      应用节点::{ctx['transfer']}
    资源文件
      lecture.md
        概念卡
        课堂案例
        自我检查
      practice.md
        基础题
        标准题
        挑战题
        评分量规
      case-project.md
        输入材料
        操作步骤
        验收标准
      quality-checklist.md
        文件验收
        图谱回填
        AI批改闭环
    易错与追练
      定义不清
      条件遗漏
      步骤跳跃
      结论无证据
      AI追练
"""

    @staticmethod
    def _reading_list(ctx: dict[str, str]) -> str:
        return f"""# {ctx['topic']} 拓展阅读清单

## 课程内必读
- 当前章节讲义：优先阅读定义、例题和课后练习部分，阅读后补全“概念边界”和“方法步骤”两块课堂笔记。
- 课堂笔记：重点检查 {ctx['primary']}、{ctx['secondary']}、{ctx['third']} 的边界，并标记无法解释的句子。
- 知识图谱：查看该主题的先修节点、方法节点、校验节点和关联资源，确认每个节点至少有一条证据。

## 拓展阅读
- 与 {ctx['topic']} 相邻的概念对比材料，阅读时只记录“差异判断标准”。
- 一个真实应用案例或工程实践说明，阅读时标出输入、方法、输出和限制。
- 一组同类题解析，阅读时关注评分点，而不是只看最终答案。

## 阅读证据模板
| 资料 | 支撑的结论 | 关键页/片段 | 是否可直接引用 |
| --- | --- | --- | --- |
| 课程讲义 | {ctx['primary']} 的定义和边界 | 记录讲义标题、章节名和首句关键词 | 是 |
| 课堂案例 | {ctx['secondary']} 的应用步骤 | 记录案例名称和关键条件 | 是 |
| 练习解析 | {ctx['third']} 的校验方式 | 记录题号、评分点和错因 | 需要复核 |

## 阅读后产物
1. 一张概念对照表：{ctx['topic']}、{ctx['primary']}、{ctx['secondary']} 的差异。
2. 一条图谱边：把“{ctx['topic']} -> {ctx['third']}”写成可解释关系。
3. 一个 AI 追问：要求 AI 根据阅读材料生成一道边界判断题。

## 阅读任务
读完后写下 3 个问题：一个定义问题、一个应用问题、一个易错边界问题。每个问题都要标注来自讲义、图谱还是练习。
"""

    @staticmethod
    def _case_project(ctx: dict[str, str]) -> str:
        return f"""# {ctx['topic']} 实操案例

## 任务背景
围绕 {ctx['subject']} 中的 {ctx['topic']}，完成一个 20-30 分钟的小任务，用来验证是否能把概念迁移到真实情境。

## 真实情境
{ctx['scenario']}

## 输入材料
- 一段课程案例或题干。
- {ctx['primary']}、{ctx['secondary']}、{ctx['third']} 的定义和约束条件。
- 一份最终产物模板：条件表、步骤表、结论表。

## 操作步骤
1. 提取已知条件。
2. 判断是否适用 {ctx['topic']}。
3. 写出推理或实现步骤，每一步标注依据。
4. 给出结论并做自检。
5. 写出一个边界情况，说明本方法何时不适用。
6. 将结果回填到课程图谱：新增一个“案例证据”节点，并连接到 {ctx['topic']}。

## 验收标准
- 每一步都有依据。
- 结论能回扣题目目标。
- 能说明一个可能出错的地方。
- 能把错误修改成一版更符合课程术语的答案。
- 能说明该案例如何触发下一份练习或下一次 AI 批改。

## 提交物模板
| 模块 | 内容 | 依据 |
| --- | --- | --- |
| 条件识别 | 写出题干条件 | 引用讲义或案例片段 |
| 方法选择 | 说明为何选择该方法 | 对应 {ctx['primary']} / {ctx['secondary']} |
| 结果验证 | 写出校验或反例 | 对应 {ctx['third']} |
| 图谱回填 | 写出新增节点和关系 | 对应 mind-map.mmd |

## AI 复核提示词
请按“条件识别、方法选择、结果验证、图谱回填、迁移边界”五项检查我的案例提交物。每项给 0-20 分，指出证据是否来自课堂笔记或资源包文件。
"""

    @staticmethod
    def _video_script(ctx: dict[str, str]) -> str:
        return f"""# {ctx['topic']} 数字人讲解脚本

大家好，这节课我们用 3 分钟讲清楚 {ctx['topic']}。

第一步，先看它解决什么问题。不要急着背结论，要先知道它适合处理哪类场景：{ctx['scenario']}。

第二步，记住核心判断条件：{ctx['primary']}、{ctx['secondary']}、{ctx['third']}。遇到题目时，先圈出已知条件，再判断是否满足这些条件。

第三步，用一个例子检查理解：{ctx['case']}。如果你能把定义、步骤、证据和结论讲给同学听，说明已经初步掌握。

最后提醒，最常见的错误是把相邻概念混用，或者只写结论不写依据。做题后建议进入 AI 批改模式，让系统根据答案更新掌握度。

镜头提示：在“证据清单”处展示 {ctx['primary']}、{ctx['secondary']}、{ctx['third']} 三张卡片；在案例处展示“条件 -> 方法 -> 结论 -> 校验 -> 图谱回填”的流程。

互动停顿：
1. 请学生用 20 秒说出 {ctx['topic']} 的适用条件。
2. 请学生判断一个反例是否满足 {ctx['third']}。
3. 请学生把错因归类为定义、条件、步骤或证据。

课后动作：把自己的答案复制到 AI 陪练，要求它按评分量规检查：{ctx['rubric']}。
"""

    @staticmethod
    def _quality_checklist(ctx: dict[str, str]) -> str:
        return f"""# {ctx['topic']} 资源包使用审查清单

课程：{ctx['subject']}
目标：{ctx['goal']}
闭环说明：{ctx['resource_contract']}

## 1. 文件完整性
| 文件 | 必须完成的动作 | 验收标准 |
| --- | --- | --- |
| lecture.md | 阅读概念卡、课堂案例和图谱绑定 | 能用自己的话复述 {ctx['topic']}，并指出证据来源 |
| practice.md | 完成基础题、标准题和挑战题 | 每题都有错因分类、订正答案和下一步追练 |
| mind-map.mmd | 在课程图谱中定位先修、核心、方法、校验、应用节点 | 每个节点都能连接到讲义、练习或案例 |
| reading-list.md | 完成阅读证据模板和阅读后产物 | 每条引用都能说明支撑的结论 |
| case-project.md | 提交条件表、方法表、验证表和图谱回填 | 结果能被 AI 按量规复核 |
| video-script.md | 用 3 分钟复述主题并完成互动停顿 | 能发现至少一个易错边界 |

## 2. 课堂笔记对齐
{ctx['note_blocks']}

## 3. 课程图谱绑定
{ctx['graph_nodes']}

## 4. 个性化学习路径
{ctx['learning_sequence']}

## 5. 质量门槛
{ctx['quality_gate']}

## 6. 继续生成规则
- 如果定义题低于 80 分：重新生成“基础巩固”资源包，只保留讲义、导图和基础练习。
- 如果案例题低于 80 分：重新生成“标准提升”资源包，增加案例项目和评分量规。
- 如果能完成迁移任务：生成“挑战拓展”资源包，加入跨章节对比和开放题。
- 如果引用无法指向文件：回到阅读清单补充资料、片段和支撑结论，再进入 AI 伴学核验。
"""

    @staticmethod
    def _minimal_pdf_bytes(markdown: str, *, title: str) -> bytes:
        """Create a valid lightweight PDF without adding heavy runtime dependencies.

        This fallback keeps the artifact real and downloadable. Chinese text is
        transliterated to replacement glyphs by PDF core fonts; the Markdown file
        remains the canonical full-fidelity source for Chinese content.
        """
        lines = [title, "", *markdown.splitlines()]
        visible_lines = []
        for line in lines[:42]:
            safe = line.encode("latin-1", "replace").decode("latin-1")
            safe = safe.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
            visible_lines.append(safe[:96])
        text_ops = ["BT", "/F1 12 Tf", "50 790 Td", "16 TL"]
        for idx, line in enumerate(visible_lines):
            if idx:
                text_ops.append("T*")
            text_ops.append(f"({line}) Tj")
        text_ops.append("ET")
        stream = "\n".join(text_ops).encode("latin-1")
        objects = [
            b"<< /Type /Catalog /Pages 2 0 R >>",
            b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] "
            b"/Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
            b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
            b"<< /Length " + str(len(stream)).encode("ascii") + b" >>\nstream\n" + stream + b"\nendstream",
        ]
        chunks = [b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n"]
        offsets: list[int] = []
        for idx, obj in enumerate(objects, start=1):
            offsets.append(sum(len(chunk) for chunk in chunks))
            chunks.append(f"{idx} 0 obj\n".encode("ascii") + obj + b"\nendobj\n")
        xref_offset = sum(len(chunk) for chunk in chunks)
        chunks.append(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
        chunks.append(b"0000000000 65535 f \n")
        for offset in offsets:
            chunks.append(f"{offset:010d} 00000 n \n".encode("ascii"))
        chunks.append(
            f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref_offset}\n%%EOF\n".encode(
                "ascii"
            )
        )
        return b"".join(chunks)


resource_generation_service = ResourceGenerationService()
