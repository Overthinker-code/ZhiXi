# 软件工程导论课程知识库

本目录对应比赛要求中的“至少一门完整高校专业课程初始知识库/文档集”。

原始资料来源于仓库根目录的 `原始资料/`，包含：

- `course_outline.md`：课程大纲，覆盖软件工程导论主要章节；
- `学习笔记/`：13 章学习笔记 Markdown；
- `课后习题/`：13 章课后习题 Markdown；
- `入库数据/chunks.jsonl`：面向 RAG 的知识点切片；
- `入库数据/questions.jsonl`：结构化题库；
- `PPT/`：课堂 PPT/PDF 课件资料；
- `教材PDF/`：教材与学习辅导参考资料。

入库脚本：

```powershell
cd C:\Users\Eileen\ZhiYu-main\code\backend
..\.venv\Scripts\python.exe scripts\seed_software_engineering_course_kb.py
```

当前入库策略：

- 知识点切片与题库全量写入系统级 RAG；
- PPT 与教材文件先以“资料索引”写入，保留原始文件路径，避免一次性解析大量 PDF 导致本地启动和检索变慢；
- 脚本使用稳定 `file_id`，重复运行会先删除旧版本，再写入新版本，不会产生重复切片。
