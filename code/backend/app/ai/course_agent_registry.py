from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from app.ai.chat_runtime import AgentName


ExecutionKind = Literal["chat", "resource_workflow", "knowledge_graph"]
TutorMode = Literal["tutor", "homework_review", "resource_generation", "deep_research"]


@dataclass(frozen=True)
class CourseAgentContract:
    key: str
    label: str
    category: str
    description: str
    execution_kind: ExecutionKind
    worker_agent: AgentName | None
    mode: TutorMode
    allowed_tools: tuple[str, ...]
    outputs: tuple[str, ...]
    starter_actions: tuple[str, ...]
    instruction: str
    requires_course_context: bool = True
    requires_attachment: bool = False

    def public_dict(self) -> dict[str, object]:
        return {
            "key": self.key,
            "label": self.label,
            "category": self.category,
            "description": self.description,
            "executionKind": self.execution_kind,
            "mode": self.mode,
            "outputs": list(self.outputs),
            "starterActions": list(self.starter_actions),
            "requirements": {
                "courseContext": self.requires_course_context,
                "attachment": self.requires_attachment,
            },
            "capabilities": list(self.allowed_tools),
        }


def _contract(
    key: str,
    label: str,
    category: str,
    description: str,
    *,
    worker_agent: AgentName | None,
    allowed_tools: tuple[str, ...],
    outputs: tuple[str, ...],
    starter_actions: tuple[str, ...],
    instruction: str,
    execution_kind: ExecutionKind = "chat",
    mode: TutorMode = "tutor",
    requires_attachment: bool = False,
) -> CourseAgentContract:
    return CourseAgentContract(
        key=key,
        label=label,
        category=category,
        description=description,
        execution_kind=execution_kind,
        worker_agent=worker_agent,
        mode=mode,
        allowed_tools=allowed_tools,
        outputs=outputs,
        starter_actions=starter_actions,
        instruction=instruction,
        requires_attachment=requires_attachment,
    )


COURSE_AGENT_CONTRACTS: dict[str, CourseAgentContract] = {
    item.key: item
    for item in (
        _contract(
            "resource",
            "资料助手",
            "资料科研",
            "依据课程证据生成可编辑、可下载、可继续核验的学习资料包。",
            worker_agent=None,
            allowed_tools=("knowledge_base",),
            outputs=("讲义", "练习", "思维导图", "阅读清单"),
            starter_actions=("生成本章复习包", "按薄弱点生成分层练习", "生成 Word 与 PDF 讲义"),
            instruction="通过资源运行链路执行规划、生成、质量审查、持久化和图谱关联。",
            execution_kind="resource_workflow",
            mode="resource_generation",
        ),
        _contract(
            "research",
            "AI 科研助手",
            "资料科研",
            "把课程主题转成研究问题、检索策略和带来源边界的阅读清单。",
            worker_agent="web_research_agent",
            allowed_tools=("knowledge_base", "web_search", "search_uploaded_document"),
            outputs=("检索式", "研究问题", "阅读框架", "引用清单"),
            starter_actions=("把当前主题拆成研究问题", "生成可复现的检索式", "核验一项外部事实"),
            instruction="优先课程与上传资料；需要外部新事实时再联网，并区分课程证据与外部来源。",
            mode="deep_research",
        ),
        _contract(
            "practice",
            "AI 陪练",
            "学习助手",
            "根据章节与学习状态逐题陪练，等待作答后再反馈和追练。",
            worker_agent="quiz_master",
            allowed_tools=("knowledge_base",),
            outputs=("分层题", "提示", "错因反馈", "追练"),
            starter_actions=("从一道基础题开始", "针对当前薄弱点出题", "继续上一题的变式训练"),
            instruction=(
                "一次只推进一个清晰练习回合；首次出题只允许输出题干、选项和作答邀请。"
                "学生作答前严禁输出提示、解析、术语映射、Undo/Redo 对照或任何可推断正确选项的信息；"
                "没有学生作答时不得直接伪造评分或掌握度变化。"
            ),
        ),
        _contract(
            "reader",
            "AI 阅读助手",
            "自学中心",
            "围绕课程资料或上传文档生成可追溯摘要、问题清单与阅读路径。",
            worker_agent="doc_researcher",
            allowed_tools=("knowledge_base", "search_uploaded_document"),
            outputs=("摘要", "问题清单", "引用依据", "阅读路径"),
            starter_actions=("概括当前资料的论证结构", "列出三个关键问题", "按引用定位解释一个概念"),
            instruction="每个材料性结论必须能回指课程片段或上传文档；未上传资料时明确提示可用范围。",
        ),
        _contract(
            "writer",
            "智能编写",
            "效率工具",
            "基于课程证据组织报告、实验说明和学习复盘，并交付文档文件。",
            worker_agent=None,
            allowed_tools=("knowledge_base", "search_uploaded_document"),
            outputs=("报告", "复盘", "讨论稿", "实验说明"),
            starter_actions=("生成课程报告提纲", "把学习记录整理成复盘", "生成实验说明文档"),
            instruction="使用资源工作流生成结构化正文并输出 Word/PDF，不虚构引用与实验结果。",
            execution_kind="resource_workflow",
            mode="resource_generation",
        ),
        _contract(
            "graph",
            "课程知识图谱",
            "自学中心",
            "探索章节、知识点、资源、练习与能力目标的真实关联。",
            worker_agent=None,
            allowed_tools=("knowledge_base",),
            outputs=("知识关系", "前置路径", "资源证据", "学习动作"),
            starter_actions=("定位当前章节的前置知识", "查看薄弱节点关联资料", "从节点启动伴学"),
            instruction="进入课程图谱交互工作区；图谱伴学对话由检索智能体绑定当前节点执行。",
            execution_kind="knowledge_graph",
        ),
        _contract(
            "video",
            "视频理解",
            "学习助手",
            "结合课堂视频、截图和课程上下文提炼讲解结构与复习节点。",
            worker_agent="tutor_agent",
            allowed_tools=("knowledge_base",),
            outputs=("讲解结构", "关键节点", "复习点", "疑问清单"),
            starter_actions=("分析一张课堂截图", "整理这段讲解的结构", "生成视频复习清单"),
            instruction="必须基于用户实际提供的图像或文字线索；没有媒体内容时先请求补充。",
            requires_attachment=True,
        ),
        _contract(
            "formula",
            "公式识别",
            "效率工具",
            "识别公式并输出标准 LaTeX、符号解释、推导步骤与适用条件。",
            worker_agent="knowledge_mentor",
            allowed_tools=("knowledge_base",),
            outputs=("LaTeX", "符号解释", "推导步骤", "适用条件"),
            starter_actions=("识别并解释这条公式", "检查我的推导", "给出一个公式应用例题"),
            instruction="公式必须使用标准 LaTeX；无法辨认图片细节时不得猜测符号。",
        ),
        _contract(
            "grade",
            "作业批改",
            "学习助手",
            "按得分点、错因、订正步骤和下一题建议形成结构化反馈。",
            worker_agent="grading_agent",
            allowed_tools=("knowledge_base", "search_uploaded_document"),
            outputs=("评分点", "错因", "订正步骤", "下一题"),
            starter_actions=("批改我粘贴的答案", "按评分点检查附件", "只提示错因不展示答案"),
            instruction="没有题目与学生答案时不得给分；反馈结论必须说明使用了哪些输入。",
            mode="homework_review",
            requires_attachment=True,
        ),
        _contract(
            "planner",
            "学习规划师",
            "自学中心",
            "依据真实课程进度、待办与薄弱方向生成可调整的学习计划。",
            worker_agent="planner",
            allowed_tools=("knowledge_base",),
            outputs=("学习日程", "优先级", "检查点", "复盘提示"),
            starter_actions=("规划今天的 45 分钟", "按考试日期倒排计划", "重排本周未完成任务"),
            instruction="区分已知进度与推断；缺少期限或可用时间时先提出最少必要问题。",
        ),
        _contract(
            "checker",
            "作业审阅",
            "效率工具",
            "检查课程作业的引用、结构与高相似表达风险，给出可验证的修改建议。",
            worker_agent="safety_review_agent",
            allowed_tools=("knowledge_base", "search_uploaded_document"),
            outputs=("风险片段", "引用提醒", "结构问题", "修改建议"),
            starter_actions=("检查我上传的作业", "只检查引用是否完整", "检查结论是否超出证据"),
            instruction="不得声称完成全网查重；只能报告当前课程库与上传材料范围内的审阅结果。",
            requires_attachment=True,
        ),
        _contract(
            "translator",
            "术语翻译",
            "效率工具",
            "结合课程语境给出术语中英互译、定义、例句和易混提醒。",
            worker_agent="knowledge_mentor",
            allowed_tools=("knowledge_base",),
            outputs=("术语表", "双语解释", "例句", "易混提醒"),
            starter_actions=("翻译本章核心术语", "解释两个易混术语", "生成双语复习卡"),
            instruction="优先使用当前课程语境，不把一般词典义当作唯一专业定义。",
        ),
    )
}


def get_course_agent_contract(key: str | None) -> CourseAgentContract | None:
    normalized = (key or "").strip().lower()
    return COURSE_AGENT_CONTRACTS.get(normalized) if normalized else None


def list_course_agent_contracts() -> list[CourseAgentContract]:
    return list(COURSE_AGENT_CONTRACTS.values())
