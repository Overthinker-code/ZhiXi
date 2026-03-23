# 知曦系统架构分析文档

> 生成时间：2026-03-22  
> 分析对象：`/zhiXi/code`（生产版本）  
> 系统定位：面向高等教育场景的 AI 智能教学辅助平台

---

## 1. 整体架构解构

### 1.1 技术栈全景

```
┌─────────────────────────────────────────────────────────┐
│                      前端 Frontend                        │
│   Vue 3 + TypeScript + Vite + Arco Design Pro            │
│   Pinia 状态管理  │  Vue Router  │  vue-i18n 国际化       │
│   ECharts 图表   │  markdown-it  │  Axios HTTP          │
└──────────────────────────────┬──────────────────────────┘
                               │ REST API / SSE
┌──────────────────────────────▼──────────────────────────┐
│                     后端 Backend                          │
│            FastAPI (Python) + SQLModel ORM               │
│   JWT 认证  │  CORS 中间件  │  Alembic 数据库迁移         │
│             Sentry 错误监控（生产环境）                    │
└────────┬────────────────────────────────────┬───────────┘
         │                                    │
┌────────▼────────┐                ┌──────────▼──────────┐
│   SQLite/PG DB  │                │   AI 服务层           │
│  SQLModel 模型  │                │  LangChain + LangGraph│
│  Alembic 迁移   │                │  RAG + Vector Store  │
└─────────────────┘                │  YOLO 行为分析        │
                                   │  vLLM / Ollama 本地   │
                                   └─────────────────────┘
```

### 1.2 目录结构

```
zhiXi/code/
├── education/
│   └── course/                  # 前端项目根目录
│       ├── src/
│       │   ├── api/             # HTTP 请求封装（10个模块）
│       │   ├── views/           # 页面视图（12个功能模块）
│       │   ├── store/           # Pinia 状态管理
│       │   ├── router/          # 路由配置 + 路由守卫
│       │   ├── components/      # 公共组件
│       │   ├── layout/          # 布局骨架
│       │   ├── hooks/           # Composition API 钩子
│       │   ├── locale/          # i18n 国际化资源
│       │   └── utils/           # 工具函数
│       └── config/              # Vite 构建配置
└── backend/
    ├── app/
    │   ├── main.py              # FastAPI 应用入口
    │   ├── models.py            # 全量 SQLModel 数据模型（613行）
    │   ├── crud.py              # 基础 CRUD 操作
    │   ├── utils.py             # 后端工具函数
    │   ├── api/
    │   │   └── routes/          # 13个 API 路由模块
    │   ├── ai/
    │   │   └── chat_service.py  # LangGraph AI 对话引擎（366行）
    │   ├── services/
    │   │   ├── rag_service.py       # RAG 检索服务（17894B）
    │   │   ├── behavior_analysis.py # YOLO 行为分析（9995B）
    │   │   ├── chat_model_factory.py
    │   │   ├── embedding_factory.py
    │   │   ├── rag_tools.py
    │   │   ├── document_processor.py
    │   │   ├── vector_store.py
    │   │   └── vector_store_factory.py
    │   ├── core/                # 配置、安全、数据库核心
    │   ├── models/              # 细分模型（Chat、ChatThread）
    │   ├── schemas/             # Pydantic 请求/响应模式
    │   └── providers/           # LLM 提供商适配层
    ├── vllm.py                  # vLLM 本地推理启动脚本
    └── yolo.py                  # YOLO 视觉识别脚本
```

### 1.3 数据模型关系图

```
UD (大学-院系)
  ├── Teacher (教师)    ──────────────── TC (教学班)
  ├── Course (课程)     ─────────────────┤
  └── Student (学生)                   ├── CoursePlan (周计划)
       └── StudentTC ──────────────────┘
              │         TC ────── Video (课程视频)
              │
       LearningActivity (学习行为轨迹)
       ChatLog          (AI 问答记录)
       Alert            (预警记录)
       Submission        (作业提交)

User (系统用户)
  ├── Message (系统消息)
  ├── Log (操作日志)
  ├── Video (上传视频)
  └── HelpDocument (帮助文档)

Chat / ChatThread (AI 对话会话)
Resource          (课程资源)
Assignment        (作业)
```

### 1.4 AI 对话流水线（LangGraph）

```
START
  │
  ▼
chatbot_node  ──→ (有工具调用?) ──→ tools_node
  ▲                                    │
  │          summarize_node ◄──────────┘
  │               │
  └───────────────┘
  │
  ▼
human_gate (中断/确认)
  │
  ▼
END
```

**三大工具（Tools）：**

| 工具名 | 功能 |
|--------|------|
| `query_knowledge_base` | RAG 检索本地向量知识库 |
| `search_web` | DuckDuckGo 实时联网搜索 |
| `analyze_student_behavior` | YOLO 分析学生行为图像（Base64） |

---

## 2. 关键变量分析

### 2.1 后端全局变量（`chat_service.py`）

| 变量名 | 类型 | 作用 |
|--------|------|------|
| `DEFAULT_PROMPT_KEY` | `str = "tutor"` | 默认 Prompt 模式，决定 AI 回答风格 |
| `PROMPT_PRESETS` | `dict[str, dict]` | 4 种预设 Prompt 字典：`tutor`/`exam`/`concise`/`socratic` |
| `search` | `DuckDuckGoSearchRun` | 联网搜索工具实例（全局单例） |
| `rag_service` | `RAGService` | RAG 检索服务全局实例 |
| `base_llm` / `llm` | LangChain Chat Model | 核心语言模型实例；非 Ollama 时绑定 tools |
| `tools` | `list` | 注册到 LLM 的工具列表（3个） |
| `graph` | `StateGraph` | 编译后的 LangGraph 对话状态图（含 MemorySaver） |
| `builder` | `StateGraph` | 构建期状态图（运行时已编译为 `graph`，应避免暴露） |
| `_CITATION_RE` | `re.Pattern` | 用于解析 `[citation:x]` 格式的正则表达式 |

### 2.2 LangGraph 状态变量（`State` TypedDict）

| 字段名 | 类型 | 作用 |
|--------|------|------|
| `messages` | `Annotated[list, add_messages]` | 完整消息历史，由 LangGraph 自动 append 管理 |
| `control` | `Literal["wait_for_human", "continue"]` | 控制流标志位：区分等待人工确认还是继续执行 |

### 2.3 前端 Pinia Store 变量（`chat.js`）

| 变量名 | 类型 | 作用 |
|--------|------|------|
| `conversations` | `ref([])` | 所有对话列表，每项含 `id/title/messages/createdAt` |
| `currentConversationId` | `ref('')` | 当前激活对话的 thread_id |
| `isLoading` | `ref(false)` | 全局加载状态，控制 UI 加载提示 |
| `currentConversation` | `computed` | 从 `conversations` 中派生当前对话对象 |
| `currentMessages` | `computed` | 从 `currentConversation` 派生当前消息列表 |

### 2.4 前端视图层关键变量（`ChatView.vue`）

| 变量名 | 类型 | 作用 |
|--------|------|------|
| `activeTab` | `ref('files')` | 当前激活 Tab（`files` / `chat`） |
| `showUploadModal` | `ref(false)` | 控制上传对话框显示状态 |
| `files` | `ref<ReferenceFile[]>([])` | 已加载的参考文件列表 |
| `loadingFiles` | `ref(false)` | 文件列表加载状态 |
| `scopeFilter` | `ref<ReferenceScopeFilter>('all')` | 文件范围筛选（`all`/`system`/`personal`） |
| `isAdmin` | `computed` | 基于 `userStore.role` 派生的管理员权限标志 |
| `columns` | `array` | 文件列表表格列定义（含自定义 render） |

### 2.5 API 接口关键常量（`rag.ts`）

| 类型/接口名 | 核心字段 | 说明 |
|------------|----------|------|
| `ReferenceFile` | `file_id`, `name`, `size`, `scope`, `can_manage` | RAG 参考文件元数据 |
| `ChatThread` | `thread_id`, `title`, `created_at`, `updated_at` | AI 对话会话 |
| `ChatRecord` | `thread_id`, `user_input`, `response`, `created_at` | 单条对话记录 |
| `AssistantSettings` | `provider`, `model`, `rag_k_options`, `prompt_options` | AI 助手运行时配置 |
| `StreamPreviewEvent` | `stage`, `message`, `chunks_preview` | 文件上传 SSE 流事件（8种 stage） |

### 2.6 后端核心配置变量（`core/config.py` 推断）

| 变量名 | 作用 |
|--------|------|
| `settings.CHAT_PROVIDER` | LLM 提供商（`ollama` / 云端服务） |
| `settings.CHAT_MODEL` | 云端模型名称 |
| `settings.OLLAMA_MODEL` | 本地 Ollama 模型名称 |
| `settings.SENTRY_DSN` | Sentry 监控 DSN（生产环境） |
| `settings.API_V1_STR` | API 版本前缀（如 `/api/v1`） |
| `settings.PROJECT_NAME` | FastAPI 应用名称（OpenAPI 文档标题） |
| `settings.all_cors_origins` | 允许的 CORS 来源列表 |

---

## 3. 重构建议

### 3.1 🔴 高优先级：后端模型文件拆分

**问题：** `models.py` 单文件包含 613 行、20+ 数据模型，职责严重混杂（用户系统、教育体系、消息、日志、文档、AI日志）。

**建议：** 按业务域拆分为子模块，与 `app/models/` 目录（已存在 Chat、ChatThread）保持一致：
```
app/models/
  ├── user.py          # User, UserBase, UserPublic, ...
  ├── education.py     # UD, Teacher, Course, TC, Student, StudentTC
  ├── course_content.py # Video, CoursePlan, Assignment, Submission, Resource
  ├── message.py       # Message, MessageType, MessageStatus
  ├── activity.py      # LearningActivity, ChatLog, Alert, Log
  ├── document.py      # HelpDocument, DocumentCategory
  └── auth.py          # Token, TokenPayload, NewPassword
```

**预期效果：** 降低单文件认知负担；避免循环导入；提升可维护性和代码回顾效率。

---

### 3.2 🔴 高优先级：消除 `models.py` 底部重复 Relationship 定义

**问题：** 文件末尾（第 600–609 行）重复声明了已在类体内定义的 Relationship：
```python
# 末尾（多余）
User.videos = Relationship(back_populates="uploader")
UD.teachers = Relationship(back_populates="ud")
...
```
这些等同于类内已有的 `Relationship` 定义，会造成覆盖行为，存在潜在 bug。

**建议：** 删除末尾重复 Relationship 块（第 600–609 行），仅保留类体内定义。

**预期效果：** 消除潜在 ORM 覆盖 bug，减少 40+ 行冗余代码。

---

### 3.3 🟡 中优先级：`chat_service.py` 中的全局单例资源初始化

**问题：** `rag_service`、`base_llm`、`llm`、`graph` 等在模块顶层直接初始化，导致：
- 单测难以 Mock
- 启动时即建立模型连接，影响冷启动时间
- 提供商切换逻辑（`ollama` vs 云端）分散

**建议：** 封装为工厂函数并使用 `functools.lru_cache` 延迟初始化，或使用 FastAPI 的 `lifespan` 事件统一管理：
```python
from functools import lru_cache

@lru_cache(maxsize=1)
def get_chat_graph():
    ...
    return builder.compile(checkpointer=MemorySaver())
```

**预期效果：** 支持懒加载；单测可 patch；生产启动更快。

---

### 3.4 🟡 中优先级：前端 Pinia Store 持久化范围过宽

**问题：** `chat.js` 中 `persist: true` 会将全部 `conversations`（含完整消息记录）序列化到 localStorage，随着对话增多可能超出存储上限（5MB）。

**建议：** 使用 `pinia-plugin-persistedstate` 的 `pick` 选项仅持久化元信息，消息从后端 `thread_id` 动态拉取：
```js
persist: {
  pick: ['conversations', 'currentConversationId'],
  // conversations 中仅保存 { id, title, createdAt }，不含 messages
}
```

**预期效果：** 避免 localStorage 超限；减少序列化开销；消息始终来自权威数据源。

---

### 3.5 🟡 中优先级：`ChatView.vue` 中管理员判断逻辑硬编码

**问题：**
```ts
const isAdmin = computed(() =>
  userStore.role === 'admin' ||
  (userStore.email || '').toLowerCase() === 'admin@example.com'
)
```
将 `admin@example.com` 写死在前端是不安全的伪鉴权。

**建议：** 后端 `/users/me` 接口直接返回 `is_superuser` 字段（`models.py` 中已有），前端仅依据 `userStore.isSuperuser` 判断，删除 email 硬编码逻辑。

**预期效果：** 消除安全隐患；代码清晰；权限控制集中在后端。

---

### 3.6 🟢 低优先级：`interceptor.ts` 中请求超时配置补充

**问题：** `code` 版本已在 `interceptor.ts` 设置 `axios.defaults.timeout = 100000`，但 chat 对话请求使用独立 `timeout: 0`（无限等待）。 `code 2` 版本无任何全局超时。

**建议：** 统一通过 Axios 实例配置（而非全局 defaults）管理超时，为不同接口（普通 API / 流式 Chat）建立明确策略：
```ts
const chatAxios = axios.create({ timeout: 0 });    // streaming
const apiAxios  = axios.create({ timeout: 30000 }); // normal API
```

**预期效果：** 防止普通 API 请求因超时未设置而永久挂起；架构更清晰。

---

## 4. 创新机会

### 4.1 💡 学习行为实时预警闭环

**现状：** `LearningActivity`、`ChatLog`、`Alert` 表已建立，`behavior_analysis.py` 提供基于 YOLO 的单帧图像分析能力，但数据之间缺乏自动关联。

**创新点：** 构建完整预警闭环——

```
摄像头帧 → YOLO 行为识别 → LearningActivity 写库
          ↓                      ↓
       实时检测             规则引擎/ML 模型
       "走神/睡眠"          → Alert 生成
                            → WebSocket 推送教师端
                            → AI 助手主动发起对话
```

**实施思路：**
1. 后端增加 WebSocket 端点，实时推送预警
2. 教师端 Dashboard 接入实时预警流
3. AI 助手的 `analyze_student_behavior` 工具结果自动写入 `LearningActivity`
4. 规则引擎（如连续 3 分钟低分）触发 `Alert` 并推送

---

### 4.2 💡 基于 RAG 的个性化学习路径推荐

**现状：** RAG 系统已具备知识检索能力，`CoursePlan` 记录了周目标和重点，但两者尚未结合。

**创新点：** 利用学生的 `ChatLog`（历史问题模式）+ `LearningActivity`（行为数据）+ `CoursePlan`（课程进度），生成个性化学习建议：

```
学生 ChatLog 聚类分析
       ↓
识别薄弱知识点（如"期末冲刺近3周查了30次"）
       ↓
RAG 检索对应知识片段
       ↓
AI 生成个性化学习路线 Markdown
       ↓
前端"我的学习计划"页展示
```

**实施思路：**
1. 新增 `/students/{id}/learning-report` API，调用 LLM + RAG 生成报告
2. 前端在学生个人页新增"AI 学习诊断"卡片
3. 支持教师批量查看班级薄弱分布热力图（ECharts 已引入）

---

### 4.3 💡 多模态文档解析增强

**现状：** `document_processor.py` 已有文档解析能力，`rag_service.py` 支持向量检索，但仅限文本型文件。

**创新点：** 支持 PDF 扫描件 OCR、PPT 图片提取、视频字幕自动转写并入库：

```
Video.file_path（已有）
       ↓
Whisper 语音转文字
       ↓
分块 → 向量化 → Chroma/FAISS
       ↓
学生可直接用自然语言查询"第3周课程中讲到的..."
```

**实施思路：**
1. `document_processor.py` 增加 `video_to_transcript()` 方法，调用 `faster-whisper`
2. 视频上传后异步触发转录任务（用 `BackgroundTasks`）
3. 转录结果 chunks 写入 RAG 向量库，标记 `source=video`、`tc_id`、`week`

---

### 4.4 💡 4种 Prompt 模式的用户效果反馈闭环

**现状：** 已有 `tutor`/`exam`/`concise`/`socratic` 4 种 Prompt 预设，由用户手动选择，但没有效果数据收集机制。

**创新点：** 在 AI 回答后增加"👍 / 👎"评价，结合用户身份和 Prompt 类型统计满意度：

```
Chat 响应展示
       ↓
用户点击 👍/👎
       ↓
POST /chat/feedback { thread_id, record_id, rating, prompt_key }
       ↓
统计看板：哪种 Prompt 模式满意度最高？
       ↓
自动为不同用户推荐最优 Prompt 模式（协同过滤）
```

**实施思路：**
1. 新增 `ChatFeedback` 数据模型（`record_id`, `user_id`, `rating`, `prompt_key`）
2. 后端增加 `POST /chat/feedback` 接口
3. 前端消息气泡下方增加轻量评价按钮
4. Admin 后台展示各 Prompt 模式满意度对比图

---

### 4.5 💡 替换 LangGraph MemorySaver 为持久化 Checkpointer

**现状：** `graph.compile(checkpointer=MemorySaver())` 使用内存存储对话状态，进程重启或多进程部署时所有 Thread 状态丢失。

**创新点：** 接入 LangGraph 官方 `PostgresSaver` 或 `SQLiteSaver`，实现跨进程、跨重启的对话状态持久化：

```python
from langgraph.checkpoint.postgres import PostgresSaver

with PostgresSaver.from_conn_string(settings.DATABASE_URL) as checkpointer:
    graph = builder.compile(checkpointer=checkpointer)
```

**实施思路：**
1. `requirements.txt` 添加 `langgraph-checkpoint-postgres`
2. 配置 `settings.DATABASE_URL` 指向已有 PostgreSQL 实例
3. 删除 `MemorySaver` 依赖，`graph` 改为在 FastAPI `lifespan` 中初始化

**预期效果：** 多 Worker 部署时对话上下文不丢失；支持历史 Thread 回放；生产级可靠性。

---

*文档结束 | 如需针对某模块深入分析，可进一步展开。*
