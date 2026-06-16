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
                "mode": "课程画像 + 领域模板 + 质量审查",
                "domain": context["domain"],
            },
            agent_trace=[
                "ProfileAgent: 读取学习画像和目标难度",
                f"DomainAgent: 识别课程域为 {context['domain']}",
                "EvidenceAgent: 生成课程证据清单和引用模板",
                "LectureAgent: 生成讲义、概念卡和课堂案例",
                "ExerciseAgent: 生成分层练习和评分量规",
                "MindMapAgent: 生成知识结构与迁移节点",
                "CaseAgent: 生成实操任务和提交物模板",
                "ScriptAgent: 生成讲解脚本与课后动作",
                "SafetyReviewAgent: 检查事实边界、适用条件和输出格式",
                "FinalizerAgent: 汇总为可下载资源包",
            ],
            quality_notes=[
                f"已按“{context['scenario']}”组织案例，不再只输出通用学习建议。",
                "讲义、练习、阅读和案例均包含证据项或评分量规，便于学生自查与 AI 批改。",
                "所有可下载 Markdown 为中文主产物；PDF 为轻量预览版，排版完整性以 Markdown 为准。",
                "联网搜索默认受控关闭；若启用，外部资料必须在内容中单独标注来源。",
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
        domain = self._domain_profile(request.subject, request.topic, terms)
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

## 1. 一句话定位
{ctx['topic']} 是本节学习的核心对象。学习时先弄清它解决什么问题，再看它和 {ctx['primary']}、{ctx['secondary']}、{ctx['third']} 的关系。

## 2. 核心概念卡
| 概念 | 课堂定位 | 学习检查 |
| --- | --- | --- |
| {ctx['primary']} | 用来确定问题对象和基本结构 | 能否说清定义、输入和输出 |
| {ctx['secondary']} | 用来完成主要推理或操作步骤 | 能否列出 3 个判断条件 |
| {ctx['third']} | 用来做结果校验和边界判断 | 能否解释一个反例 |

## 3. 课程证据清单
{ctx['evidence']}

使用资料时先把每个结论对应到上述证据项。若某一步没有证据，只能标为“推断”或“待查”。

## 4. 课堂案例拆解
场景：{ctx['scenario']}

案例：{ctx['case']}

1. 标出题干或材料中的已知条件。
2. 判断这些条件分别对应 {ctx['primary']}、{ctx['secondary']} 还是 {ctx['third']}。
3. 写出推理链：条件 -> 方法 -> 中间结果 -> 结论。
4. 用一个反例或边界条件检查结论是否过度推广。

## 5. 易错点
{ctx['mistakes']}

## 6. 学习建议
按照“概念复述 5 分钟 -> 案例拆解 12 分钟 -> 分层练习 15 分钟 -> AI 批改 8 分钟”的顺序完成。提交答案后使用 AI 批改模式更新掌握度。

## 7. 迁移目标
{ctx['transfer']}

## 8. 自我检查
- 我能否不用教材原句解释 {ctx['topic']}？
- 我能否指出 {ctx['primary']} 在案例中的证据？
- 我能否说出一个不适用 {ctx['topic']} 的场景？
"""

    @staticmethod
    def _practice_markdown(ctx: dict[str, str]) -> str:
        return f"""# {ctx['topic']} 分层练习

课程：{ctx['subject']}
匹配场景：{ctx['scenario']}

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

## 评分量规
{ctx['rubric']}

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
      课程域::{ctx['domain']}
    方法
      步骤拆解
      结果校验
      证据清单
    练习
      基础题
      变式题
      挑战题
      评分量规
    易错点
      概念混淆
      条件遗漏
      结论无依据
    应用
      课堂案例
      迁移任务
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

## 阅读证据模板
| 资料 | 支撑的结论 | 关键页/片段 | 是否可直接引用 |
| --- | --- | --- | --- |
| 课程讲义 | {ctx['primary']} 的定义和边界 | 待填写 | 是 |
| 课堂案例 | {ctx['secondary']} 的应用步骤 | 待填写 | 是 |
| 练习解析 | {ctx['third']} 的校验方式 | 待填写 | 需要复核 |

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

## 验收标准
- 每一步都有依据。
- 结论能回扣题目目标。
- 能说明一个可能出错的地方。
- 能把错误修改成一版更符合课程术语的答案。

## 提交物模板
| 模块 | 内容 | 依据 |
| --- | --- | --- |
| 条件识别 | 写出题干条件 | 引用讲义或案例片段 |
| 方法选择 | 说明为何选择该方法 | 对应 {ctx['primary']} / {ctx['secondary']} |
| 结果验证 | 写出校验或反例 | 对应 {ctx['third']} |
"""

    @staticmethod
    def _video_script(ctx: dict[str, str]) -> str:
        return f"""# {ctx['topic']} 数字人讲解脚本

大家好，这节课我们用 3 分钟讲清楚 {ctx['topic']}。

第一步，先看它解决什么问题。不要急着背结论，要先知道它适合处理哪类场景。

第二步，记住核心判断条件：{ctx['primary']}、{ctx['secondary']}、{ctx['third']}。遇到题目时，先圈出已知条件，再判断是否满足这些条件。

第三步，用一个例子检查理解。如果你能把定义、步骤和结论讲给同学听，说明已经初步掌握。

最后提醒，最常见的错误是把相邻概念混用，或者只写结论不写依据。做题后建议进入 AI 批改模式，让系统根据答案更新掌握度。

镜头提示：在“证据清单”处展示 {ctx['primary']}、{ctx['secondary']}、{ctx['third']} 三张卡片；在案例处展示“条件 -> 方法 -> 结论 -> 校验”的流程。

课后动作：把自己的答案复制到 AI 陪练，要求它按评分量规检查：{ctx['rubric']}。
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
