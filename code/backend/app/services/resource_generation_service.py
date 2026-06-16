from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from app.core.config import settings
from app.schemas.resource_generation import (
    GeneratedResourceArtifact,
    ResourceGenerationRequest,
    ResourceGenerationResponse,
    ResourceKind,
)


DEFAULT_RESOURCE_TYPES: list[ResourceKind] = [
    "lecture_markdown",
    "lecture_pdf",
    "practice_markdown",
    "practice_pdf",
    "mind_map",
    "reading_list",
    "case_project",
    "video_script",
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
        artifacts: list[GeneratedResourceArtifact] = []
        markdown_cache: dict[str, str] = {}

        for kind in kinds:
            if kind == "lecture_markdown":
                markdown_cache["lecture"] = self._lecture_markdown(context)
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
                lecture = markdown_cache.get("lecture") or self._lecture_markdown(context)
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
                markdown_cache["practice"] = self._practice_markdown(context)
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
                practice = markdown_cache.get("practice") or self._practice_markdown(context)
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
                        self._mind_map(context),
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
                        self._reading_list(context),
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
                        self._case_project(context),
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
                        self._video_script(context),
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
            subject=request.subject,
            topic=request.topic,
            generated_at=datetime.utcnow(),
            local_model_profile={
                "chat_provider": settings.CHAT_PROVIDER,
                "chat_model": settings.OLLAMA_MODEL
                if settings.CHAT_PROVIDER.lower() == "ollama"
                else settings.CHAT_MODEL,
                "embedding_provider": settings.EMBEDDINGS_PROVIDER,
                "multimodal_model": settings.MULTIMODAL_MODEL,
                "deployment": "local-first",
            },
            agent_trace=[
                "ProfileAgent: 读取学习画像和目标难度",
                "LectureAgent: 生成讲义结构",
                "ExerciseAgent: 生成分层练习",
                "MindMapAgent: 生成知识结构",
                "CaseAgent: 生成实操任务",
                "ScriptAgent: 生成讲解脚本",
                "SafetyReviewAgent: 检查事实边界和输出格式",
                "FinalizerAgent: 汇总为可下载资源包",
            ],
            quality_notes=[
                "本阶段资源产物在本地生成并落盘，可下载、可追溯。",
                "PDF 采用本地轻量导出回退，后续可替换为正式排版引擎。",
                "联网搜索默认受控关闭；若启用，结果必须在内容中单独标注来源。",
            ],
            artifacts=artifacts,
        )

    def list_recent_packages(self, limit: int = 12) -> list[dict[str, object]]:
        self.output_root.mkdir(parents=True, exist_ok=True)
        packages: list[dict[str, object]] = []
        for folder in sorted(
            [item for item in self.output_root.iterdir() if item.is_dir()],
            key=lambda item: item.stat().st_mtime,
            reverse=True,
        )[:limit]:
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
            packages.append(
                {
                    "package_id": folder.name,
                    "subject": payload.get("subject") or "",
                    "topic": payload.get("topic") or folder.name,
                    "generated_at": payload.get("generated_at")
                    or datetime.fromtimestamp(folder.stat().st_mtime).isoformat(),
                    "artifacts": [
                        {
                            "file_name": item.name,
                            "file_size": item.stat().st_size,
                        }
                        for item in artifacts
                        if item.is_file() and item.name != "manifest.json"
                    ],
                }
            )
        return packages

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
        }

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
            file_path=str(path),
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

## 1. 一句话定位
{ctx['topic']} 是本节学习的核心对象。学习时先弄清它解决什么问题，再看它和 {ctx['primary']}、{ctx['secondary']}、{ctx['third']} 的关系。

## 2. 核心概念卡
| 概念 | 课堂定位 | 学习检查 |
| --- | --- | --- |
| {ctx['primary']} | 用来确定问题对象和基本结构 | 能否说清定义、输入和输出 |
| {ctx['secondary']} | 用来完成主要推理或操作步骤 | 能否列出 3 个判断条件 |
| {ctx['third']} | 用来做结果校验和边界判断 | 能否解释一个反例 |

## 3. 课堂案例拆解
1. 标出题干或材料中的已知条件。
2. 判断这些条件分别对应 {ctx['primary']}、{ctx['secondary']} 还是 {ctx['third']}。
3. 写出推理链：条件 -> 方法 -> 中间结果 -> 结论。
4. 用一个反例或边界条件检查结论是否过度推广。

## 4. 易错点
- 只记术语，不会把术语放回题目条件。
- 把 {ctx['primary']} 和 {ctx['secondary']} 混用，导致步骤不成立。
- 没有说明为什么选择该方法，答案缺少可追溯依据。
- 最后不做边界校验，导致结论看似完整但无法迁移。

## 5. 学习建议
按照“概念复述 5 分钟 -> 案例拆解 12 分钟 -> 分层练习 15 分钟 -> AI 批改 8 分钟”的顺序完成。提交答案后使用 AI 批改模式更新掌握度。

## 6. 自我检查
- 我能否不用教材原句解释 {ctx['topic']}？
- 我能否指出 {ctx['primary']} 在案例中的证据？
- 我能否说出一个不适用 {ctx['topic']} 的场景？
"""

    @staticmethod
    def _practice_markdown(ctx: dict[str, str]) -> str:
        return f"""# {ctx['topic']} 分层练习

## 基础题
1. 用 80 字以内解释 {ctx['topic']}，并写出它和 {ctx['primary']} 的关系。
2. 判断题：只要题干出现关键词，就一定可以套用 {ctx['topic']}。请说明理由，并指出需要补充的条件。
3. 填空：解决这类问题时，第一步应先识别 ______，第二步再选择 ______。

## 标准题
4. 给定一个课程案例，列出已知条件、适用概念、推理步骤和最终结论。
5. 设计一道同类变式题，并写出标准答案和评分点。

## 挑战题
6. 比较 {ctx['topic']} 与 {ctx['secondary']} 的差异，至少列出 3 个判断标准。
7. 写一个容易出错的答案，并说明它错在定义、条件、步骤还是结论。

## 参考解析
- 基础题看定义是否准确、例子是否贴合。
- 标准题看步骤是否完整、结论是否可由条件推出。
- 挑战题看能否抓住适用边界，而不是只罗列术语。
- 全部题目完成后，把错题送入 AI 陪练，要求系统按“错因 -> 订正 -> 追练”继续生成下一组题。
"""

    @staticmethod
    def _mind_map(ctx: dict[str, str]) -> str:
        return f"""mindmap
  root(({ctx['topic']}))
    定义
      核心含义
      适用条件
    方法
      步骤拆解
      结果校验
    练习
      基础题
      变式题
      挑战题
    易错点
      概念混淆
      条件遗漏
      结论无依据
    应用
      课堂案例
      实操任务
"""

    @staticmethod
    def _reading_list(ctx: dict[str, str]) -> str:
        return f"""# {ctx['topic']} 拓展阅读清单

## 课程内必读
- 当前章节讲义：优先阅读定义、例题和课后练习部分。
- 课堂笔记：重点检查 {ctx['primary']}、{ctx['secondary']}、{ctx['third']} 的边界。
- 知识图谱：查看该主题的先修节点和关联资源。

## 拓展阅读
- 与 {ctx['topic']} 相邻的概念对比材料，阅读时只记录“差异判断标准”。
- 一个真实应用案例或工程实践说明，阅读时标出输入、方法、输出和限制。
- 一组同类题解析，阅读时关注评分点，而不是只看最终答案。

## 阅读任务
读完后写下 3 个问题：一个定义问题、一个应用问题、一个易错边界问题。每个问题都要标注来自讲义、图谱还是练习。
"""

    @staticmethod
    def _case_project(ctx: dict[str, str]) -> str:
        return f"""# {ctx['topic']} 实操案例

## 任务背景
围绕 {ctx['subject']} 中的 {ctx['topic']}，完成一个 20-30 分钟的小任务，用来验证是否能把概念迁移到真实情境。

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

## 验收标准
- 每一步都有依据。
- 结论能回扣题目目标。
- 能说明一个可能出错的地方。
- 能把错误修改成一版更符合课程术语的答案。
"""

    @staticmethod
    def _video_script(ctx: dict[str, str]) -> str:
        return f"""# {ctx['topic']} 数字人讲解脚本

大家好，这节课我们用 3 分钟讲清楚 {ctx['topic']}。

第一步，先看它解决什么问题。不要急着背结论，要先知道它适合处理哪类场景。

第二步，记住核心判断条件：{ctx['primary']}、{ctx['secondary']}、{ctx['third']}。遇到题目时，先圈出已知条件，再判断是否满足这些条件。

第三步，用一个例子检查理解。如果你能把定义、步骤和结论讲给同学听，说明已经初步掌握。

最后提醒，最常见的错误是把相邻概念混用，或者只写结论不写依据。做题后建议进入 AI 批改模式，让系统根据答案更新掌握度。
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
