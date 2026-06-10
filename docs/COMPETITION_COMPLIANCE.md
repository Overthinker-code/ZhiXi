# 智屿 A3 赛题合规说明

## 赛题功能对标

| 赛题要求 | 实现位置 | 状态 |
|----------|----------|------|
| 对话式学习画像（≥6维） | `user_memory_profile_service.py`、伴学侧栏、学情档案雷达图 | 已实现 |
| 多智能体协同资源生成（≥5类） | LangGraph 伴学 + `resource_workshop` Agent 链 | 已实现 |
| 个性化学习路径 | `learning_path` API、学情档案「学习路径」Tab | 已实现 |
| 智能辅导 | `ChatView` / RAG / 流式 / 划词 | 已实现 |
| 学习效果评估 | `learning_report_service`、课堂 CV 联动 | 已实现 |
| 防幻觉 / 内容安全 | `safety_review_agent`、RAG 引用 | 已实现 |
| 讯飞相关工具 | `CHAT_PROVIDER=iflytek` + `IFLYTEK_*` 配置（可选） | 架构预留 |

## 讯飞接入（可选）

在 `code/.env` 中配置：

```env
CHAT_PROVIDER=iflytek
IFLYTEK_APP_ID=your_app_id
IFLYTEK_API_KEY=your_api_key
IFLYTEK_API_SECRET=your_api_secret
IFLYTEK_SPARK_MODEL=generalv3.5
```

未配置密钥时自动回退至 `ollama`。

## Golden Path 演示脚本

1. **Seed 演示数据**（后端目录）  
   ```bash
   python scripts/seed_demo_learning.py --email student@example.com
   python scripts/seed_competition_demo.py --students 120 --behavior-days 30
   ```

2. **学生 AI 伴学** → `/tutor`：多智能体协作时间线 + 可折叠思考过程 + 流式输出

3. **学情档案** `/profile/learning-data`（仅学生）→ 诊断 → 雷达图 → 学习路径

4. **教师班级学情** `/profile/class-insights` → 汇总卡片 + 预警趋势

5. **资源工坊** `/course/resource-generation` → Agent 分步舞台 → 资源卡片

6. **RAG 上传问答**：伴学侧栏上传讲义 → 提问 → 引用卡片

7. **冒烟/Golden Path**  
   ```bash
   PYTHONPATH=. python3 scripts/golden_path_smoke.py --base-url http://127.0.0.1:8001
   ```

## Mock 路由

生产环境默认关闭 Mock API。开发环境可在 `code/.env` 设置：

```env
ENABLE_MOCK_ROUTES=true
```

## 开源组件

- Vue 3 / Arco Design Pro — MIT
- FastAPI / LangChain / LangGraph — 见各项目 LICENSE
- Chroma — Apache 2.0
- MuseTalk — 见 `code/backend/MuseTalk/README.md`
- YOLO (Ultralytics) — AGPL-3.0

答辩文档中须显著标注上述依赖及协议。
