from __future__ import annotations


GENERIC_SUBJECTS = {
    "",
    "未分类",
    "通用学习",
    "个性化学习",
    "当前学习目标",
    "AI专项练习",
    "专项练习",
}

SUBJECT_KEYWORDS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("计算机组成原理", ("计算机组成", "组成原理", "cpu", "cache", "流水线", "指令系统", "存储器")),
    ("计算机网络", ("计算机网络", "tcp", "udp", "拥塞控制", "ip协议", "路由", "网络协议")),
    ("数据库", ("数据库", "事务", "acid", "sql", "索引", "并发控制", "mvcc")),
    ("数据结构与算法", ("数据结构", "算法", "链表", "二叉树", "排序", "图算法")),
    ("操作系统", ("操作系统", "进程", "线程", "死锁", "虚拟内存", "文件系统")),
    ("机器学习", ("机器学习", "深度学习", "神经网络", "回归", "分类", "聚类")),
    ("人工智能", ("人工智能", "大模型", "llm", "智能体", "agent", "知识图谱")),
    ("软件工程", ("软件工程", "需求分析", "软件测试", "设计模式", "uml")),
    ("程序设计", ("python", "java", "c++", "程序设计", "编程", "代码")),
    ("高等数学", ("高等数学", "微积分", "极限", "导数", "积分")),
    ("线性代数", ("线性代数", "矩阵", "向量", "特征值")),
    ("概率论与数理统计", ("概率论", "数理统计", "随机变量", "概率分布")),
)


def resolve_resource_subject(subject: str | None, *context: object) -> str:
    """Return an explicit subject, or infer one consistently from resource context."""
    explicit = str(subject or "").strip()
    if explicit and explicit not in GENERIC_SUBJECTS:
        return explicit[:80]

    searchable = " ".join(str(value or "") for value in (explicit, *context)).lower()
    for canonical, keywords in SUBJECT_KEYWORDS:
        if any(keyword.lower() in searchable for keyword in keywords):
            return canonical
    return "未分类"
