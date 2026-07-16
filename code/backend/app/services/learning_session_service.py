import re
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.chat_thread import ChatThread


@dataclass(frozen=True)
class LearningSessionAnalysis:
    title: str
    course: str
    knowledge_point: str
    intent: str


_COURSE_KEYWORDS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("数据库", ("数据库", "sql", "事务", "隔离级别", "锁机制", "范式", "索引")),
    ("计算机网络", ("计算机网络", "tcp", "udp", "拥塞控制", "路由", "网络协议")),
    ("机器学习", ("机器学习", "决策树", "神经网络", "深度学习", "模型训练", "特征工程")),
    ("数据结构", ("数据结构", "二叉树", "链表", "栈", "队列", "图算法", "排序算法")),
    ("Python", ("python", "pytorch", "pandas", "numpy", "django", "fastapi")),
    ("高等数学", ("高等数学", "微积分", "导数", "积分", "极限", "级数")),
    ("线性代数", ("线性代数", "矩阵", "特征值", "向量空间")),
)

_KNOWLEDGE_KEYWORDS = (
    "事务隔离", "隔离级别", "并发控制", "二阶段锁", "锁机制", "TCP拥塞控制",
    "拥塞控制", "决策树", "神经网络", "深度学习", "二叉树", "关系模型",
    "SQL", "数据库事务", "索引", "范式", "微积分", "矩阵", "特征值",
)


def _compact_topic(text: str) -> str:
    cleaned = re.sub(r"\s+", "", text or "")
    cleaned = re.sub(r"[，。！？；,.!?：:（）()\[\]{}]", "", cleaned)
    cleaned = re.sub(
        r"^(为什么|怎么|如何|请|帮我|我想|我不会|我还是不理解|能不能|给我|根据我的)",
        "",
        cleaned,
    )
    cleaned = re.sub(r"(是什么|怎么做|如何理解|帮我讲解|一下)$", "", cleaned)
    return cleaned[:18] or "学习主题"


def analyze_learning_session(first_query: str) -> LearningSessionAnalysis:
    query = (first_query or "").strip()
    lowered = query.lower()
    course = "通用学习"
    for candidate, keywords in _COURSE_KEYWORDS:
        if any(keyword.lower() in lowered for keyword in keywords):
            course = candidate
            break

    knowledge_point = next(
        (keyword for keyword in _KNOWLEDGE_KEYWORDS if keyword.lower() in lowered),
        _compact_topic(query),
    )
    if re.search(r"计划|复习安排|备考|学习路径", query):
        intent, suffix = "learning_plan", "学习计划"
    elif re.search(r"练习|习题|测试|测验|刷题", query):
        intent, suffix = "practice", "专项练习"
    elif re.search(r"项目|案例|代码|实操|实现", query):
        intent, suffix = "project_practice", "项目实践"
    elif re.search(r"不理解|不会|讲解|为什么|是什么|原理", query):
        intent, suffix = "concept_understanding", "理解学习"
    elif re.search(r"总结|复习|梳理", query):
        intent, suffix = "review", "复习"
    else:
        intent, suffix = "general_learning", "学习"

    title_course = course if course != "通用学习" else "学习"
    title = f"{title_course}-{knowledge_point}{suffix}"
    return LearningSessionAnalysis(
        title=title[:80],
        course=course,
        knowledge_point=knowledge_point[:200],
        intent=intent,
    )


class LearningSessionService:
    def record_turn(
        self,
        db: Session,
        *,
        thread: ChatThread,
        first_query: str,
    ) -> ChatThread:
        now = datetime.now(timezone.utc)
        thread.last_message_at = now
        thread.session_status = thread.session_status or "active"
        if not (thread.title or "").strip() or thread.title == "新对话":
            analysis = analyze_learning_session(first_query)
            thread.title = analysis.title
            thread.course = analysis.course
            thread.knowledge_point = analysis.knowledge_point
            thread.intent = analysis.intent
            thread.session_metadata = {
                **(thread.session_metadata or {}),
                "title_source": "first_message_analysis",
                "analyzed_at": now.isoformat(),
            }
        db.add(thread)
        db.commit()
        db.refresh(thread)
        return thread


learning_session_service = LearningSessionService()
