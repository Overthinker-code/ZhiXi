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
   `python scripts/seed_demo_learning.py --email admin@example.com`

2. **伴学对话** → 展示多 Agent 轨迹与流式输出

3. **学情档案** `/profile/learning-data` → 诊断动画 → 雷达图 → 学习路径 Tab

4. **资源工坊** `/course/resource-generation` → Agent 分步舞台 → 资源卡片

5. **（可选）课堂监控** → 行为数据 → 学情页更新

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
