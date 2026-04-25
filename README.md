# 智屿智能教育平台

智屿是一个面向课堂教学、学生伴学和教学资源生产的 AI 教育平台。项目采用“本地 Mac 跑前端、服务器跑后端”的开发方式，核心能力包括智能伴学对话、RAG 知识库问答、实时课堂行为检测、课程资源管理、教师工作台、学情档案和数字人视频生成。

## 当前运行方式

### 本地前端

```bash
cd code/education/course
npm install
npm run dev
```

前端开发服务会读取 `code/education/course/.env.development`，通过 Vite 代理把 `/api` 转发到后端的 `/api/v1`。如需切换后端地址，修改：

```env
VITE_DEV_API_PROXY_TARGET=http://<backend-host>:8001
VITE_AXIOS_TIMEOUT_MS=120000
```

### 服务器后端

后端推荐使用单入口启动：

```bash
cd code/backend
python run_backend_stack.py
```

该入口会统一拉起：

- FastAPI 主服务：`0.0.0.0:8001`
- YOLO 行为检测服务：`127.0.0.1:8002`
- Celery Worker：数字人生成、学情记忆刷新等异步任务

常用健康检查：

```bash
curl http://127.0.0.1:8001/api/v1/healthz
curl http://127.0.0.1:8002/health
```

## 技术栈

### 前端

- Vue 3 + TypeScript
- Vite 3
- Arco Design Vue + Element Plus
- Pinia 状态管理
- Vue Router
- ECharts / vue-echarts
- markdown-it

### 后端

- FastAPI
- SQLModel / SQLAlchemy
- Alembic
- PostgreSQL
- Redis + Celery
- LangChain / LangGraph
- Ollama 或兼容 OpenAI 的模型服务
- Chroma 向量库

### 视觉与多媒体

- YOLO11 / YOLOv8-Pose 课堂行为检测
- MuseTalk + Edge-TTS 数字人视频生成
- WebSocket / SSE 实时通信

## 目录结构

```text
ZhiXi/
├── code/
│   ├── backend/                 # FastAPI 后端、Celery、数字人任务、RAG、AI 对话
│   │   ├── app/
│   │   │   ├── api/             # API 路由
│   │   │   ├── ai/              # 智能伴学、Agent 编排、结构化输出
│   │   │   ├── core/            # 配置、数据库、安全
│   │   │   ├── models/          # 数据模型
│   │   │   ├── schemas/         # 请求/响应 Schema
│   │   │   ├── services/        # RAG、行为检测、数字人、学情报告等服务
│   │   │   └── worker/          # Celery 任务
│   │   ├── MuseTalk/            # 数字人引擎
│   │   └── run_backend_stack.py # 后端一键启动入口
│   ├── cv/                      # YOLO 行为检测服务和模型权重
│   └── education/course/        # 前端应用
│       ├── config/              # Vite 配置
│       └── src/
│           ├── api/             # 前端 API 封装
│           ├── components/      # 公共组件
│           ├── composables/     # 组合式逻辑
│           ├── hooks/           # 业务 Hooks
│           ├── router/          # 路由和菜单
│           ├── store/           # Pinia Store
│           ├── utils/           # 工具函数
│           └── views/           # 页面模块
├── docs/                        # 少量保留的专项文档
└── README.md                    # 当前主维护文档
```

## 核心功能

### 智能伴学

位置：`code/education/course/src/views/chat`

- 支持多轮 AI 对话、流式输出、RAG 检索、引用和置信度展示。
- 回答完成后生成 3 个学生第一人称追问胶囊，点击后直接进入下一轮学习对话。
- 对模型偶发的 `<think>` / `<analysis>` 标签做前后端双重清洗，避免内部标签进入主气泡。

主要后端文件：

- `code/backend/app/ai/chat_engine.py`
- `code/backend/app/api/v1/endpoints/chat.py`
- `code/backend/app/services/rag_service.py`

### 实时课堂行为检测

位置：

- 前端：`code/education/course/src/views/course/monitor`
- 后端：`code/backend/app/api/routes/behavior_analysis.py`
- YOLO 服务：`code/cv/code/yolo.py`

当前检测栈：

- `run_backend_stack.py` 自动启动 YOLO 服务。
- 默认使用 `yolo11m.pt` 作为人体检测器，配合 `yolov8n-pose.pt` 做姿态分析。
- 后端通过 `/api/v1/behavior/*` 和 WebSocket 接口提供课堂检测能力。

### 教师工作台

位置：`code/education/course/src/views/dashboard/workplace`

当前主链路已接真实后端接口：

- `/dashboard/teacher/stats`
- `/dashboard/teacher/alerts-trend`
- `/dashboard/teacher/popular`
- `/dashboard/teacher/content-distribution`

### 学情档案与复习计划

位置：

- `code/education/course/src/views/profile/learning-data`
- `code/education/course/src/views/user/study`
- `code/backend/app/services/learning_report_service.py`

能力：

- 学情摘要
- 薄弱点分析
- 复习建议
- AI 生成复习计划

### 数字人创作舱

位置：

- 前端：`code/education/course/src/views/digital-human`
- 后端：`code/backend/app/api/routes/digital_human.py`
- 服务：`code/backend/app/services/digital_human_service.py`

能力：

- 文本生成数字人视频
- PPT/PDF 生成讲解视频
- Celery 异步任务
- 前端轮询任务状态和进度
- MuseTalk 主引擎，Wav2Lip 可作为回退方案

## 常用接口

```text
POST /api/v1/login/access-token
GET  /api/v1/users/me
GET  /api/v1/healthz

POST /api/v1/chat/
POST /api/v1/chat/stream
GET  /api/v1/chat/settings
GET  /api/v1/chat/threads

GET  /api/v1/dashboard/teacher/stats
GET  /api/v1/dashboard/teacher/alerts-trend
GET  /api/v1/dashboard/teacher/popular
GET  /api/v1/dashboard/teacher/content-distribution

GET  /api/v1/behavior/cameras
GET  /api/v1/behavior/behaviors/definitions
WS   /api/v1/behavior/ws/realtime

POST /api/v1/digital-human/jobs/text-to-video
POST /api/v1/digital-human/jobs/ppt-to-video
GET  /api/v1/digital-human/jobs/{task_id}
```

## 验证命令

### 前端

```bash
cd code/education/course
npm run type:check
npm run build
```

### 后端

```bash
python -m py_compile $(git ls-files 'code/backend/app/**/*.py' 'code/backend/*.py' ':!:code/backend/app/tests/**')
```

### 服务器健康检查

```bash
curl http://127.0.0.1:8001/api/v1/healthz
curl http://127.0.0.1:8002/health
```

## 维护约定

1. 前端新增业务接口必须放在 `src/api/*`，页面不要直接写裸请求。
2. 后端新增功能优先按 `api -> schemas -> services -> models` 分层。
3. 运行时产物不要提交到 Git，包括：
   - `code/.venv/`
   - `code/backend/vector_db/`
   - `code/backend/digital_human_inputs/`
   - `code/backend/digital_human_outputs/`
   - `code/backend/digital_human_assets/`
   - `code/backend/models/`
4. 数字人、YOLO、RAG 这类重服务优先保持单入口可启动，避免分散脚本。
5. 清理旧文档时，以本 README 为主文档；专项文档只保留仍然有部署或接口价值的内容。

## 当前已知事项

- 服务器 CUDA 驱动较旧时，YOLO 会自动走 CPU，功能可用但速度会慢一些。
- 前端生产构建中 Sass legacy API 和 eval 警告来自现有依赖/插件，不影响当前构建产物。
- `code/backend/MuseTalk/` 是数字人引擎目录，保留其原始 README 和模型说明，方便后续升级。

## 推荐提交前检查

```bash
git status --short
cd code/education/course && npm run type:check && npm run build
cd -
python -m py_compile $(git ls-files 'code/backend/app/**/*.py' 'code/backend/*.py' ':!:code/backend/app/tests/**')
```
