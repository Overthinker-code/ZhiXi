"""Add a unified subject dimension to all resource sources.

Revision ID: 020
Revises: 019
Create Date: 2026-07-15
"""

from alembic import op
import sqlalchemy as sa


revision = "020"
down_revision = "019"
branch_labels = None
depends_on = None


TABLES = (
    "resource",
    "external_resource",
    "personalized_resource_recommendation",
)


def _has_column(inspector: sa.Inspector, table: str, column: str) -> bool:
    return any(item["name"] == column for item in inspector.get_columns(table))


def _backfill_keywords(table: str) -> None:
    text = "lower(coalesce(title, '') || ' ' || coalesce(knowledge_point, ''))"
    rules = (
        ("计算机组成原理", ("计算机组成", "组成原理", "cpu", "cache", "流水线", "指令系统")),
        ("计算机网络", ("计算机网络", "tcp", "udp", "拥塞控制", "网络协议")),
        ("数据库", ("数据库", "事务", "acid", "sql", "索引", "mvcc")),
        ("数据结构与算法", ("数据结构", "算法", "链表", "二叉树", "排序")),
        ("操作系统", ("操作系统", "进程", "线程", "死锁", "虚拟内存")),
        ("机器学习", ("机器学习", "深度学习", "神经网络", "回归", "聚类")),
        ("人工智能", ("人工智能", "大模型", "llm", "agent", "知识图谱")),
    )
    for subject, keywords in rules:
        condition = " OR ".join(f"{text} LIKE '%{keyword.lower()}%'" for keyword in keywords)
        op.execute(sa.text(
            f"UPDATE {table} SET subject = :subject "
            f"WHERE subject = '未分类' AND ({condition})"
        ).bindparams(subject=subject))


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    for table in TABLES:
        if not inspector.has_table(table) or _has_column(inspector, table, "subject"):
            continue
        op.add_column(
            table,
            sa.Column("subject", sa.String(length=80), nullable=False, server_default="未分类"),
        )
        op.create_index(f"ix_{table}_subject", table, ["subject"])

    inspector = sa.inspect(op.get_bind())
    if inspector.has_table("resource") and _has_column(inspector, "resource", "subject"):
        if inspector.has_table("course"):
            op.execute(sa.text(
                "UPDATE resource SET subject = coalesce((SELECT name FROM course "
                "WHERE course.id = resource.course_id), subject) WHERE course_id IS NOT NULL"
            ))
        if inspector.has_table("generated_resource_package"):
            op.execute(sa.text(
                "UPDATE resource SET subject = coalesce((SELECT subject FROM generated_resource_package "
                "WHERE generated_resource_package.id = resource.package_id), subject) "
                "WHERE package_id IS NOT NULL AND subject = '未分类'"
            ))
        if inspector.has_table("knowledge_graph"):
            op.execute(sa.text(
                "UPDATE resource SET subject = coalesce((SELECT course FROM knowledge_graph "
                "WHERE knowledge_graph.resource_id = resource.id), subject) "
                "WHERE subject = '未分类'"
            ))

    for table in TABLES:
        if inspector.has_table(table) and _has_column(inspector, table, "subject"):
            _backfill_keywords(table)


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    for table in reversed(TABLES):
        if inspector.has_table(table) and _has_column(inspector, table, "subject"):
            op.drop_index(f"ix_{table}_subject", table_name=table)
            op.drop_column(table, "subject")
