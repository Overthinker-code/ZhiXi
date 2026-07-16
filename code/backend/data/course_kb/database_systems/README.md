# 数据库系统原理最小完整知识库

这组资料用于 A3 比赛的课程级 RAG 演示，包含课程大纲、事务讲义、练习与答案、索引实验和术语表，共 5 个 Markdown 文件。内容由项目组原创编写，采用 CC BY 4.0；技术事实以 `manifest.json` 中记录的 PostgreSQL 18 官方文档为核对来源。没有把网页正文复制进仓库。

外部来源及许可：

- PostgreSQL Transactions: <https://www.postgresql.org/docs/current/tutorial-transactions.html>
- PostgreSQL Transaction Isolation: <https://www.postgresql.org/docs/current/transaction-iso.html>
- PostgreSQL Using EXPLAIN: <https://www.postgresql.org/docs/current/using-explain.html>
- PostgreSQL Constraints: <https://www.postgresql.org/docs/current/ddl-constraints.html>
- PostgreSQL License: <https://www.postgresql.org/about/licence/>

从 `code/backend` 目录重复执行种子与评测：

```bash
../.venv/bin/python scripts/seed_database_course_kb.py
../.venv/bin/python scripts/evaluate_course_rag.py
```

种子脚本为每个文件使用稳定 `file_id`，写入前删除旧版本，因此重复执行不会累积重复片段。当前默认 `hash` provider 只被标记为降级的确定性向量；评测结果衡量的是词法检索，不能作为“语义向量召回”证据。配置真实 embedding provider 后，服务会改用语义向量与词法融合排序。
