# 知曦系统 · 前端方案 VB 文档
## Vision & Blueprint Document — Frontend Architecture

> **版本：** v1.0  
> **日期：** 2026-03-22  
> **适用范围：** 知曦 Agent 驱动的个性化学习支持系统（前端全栈方案重构）  
> **阅读对象：** 前端工程师、后端工程师、测试工程师、产品经理

---

## 目录

1. [整体架构概览](#1-整体架构概览)
2. [核心技术栈与选型理由](#2-核心技术栈与选型理由)
3. [关键变量与状态管理设计](#3-关键变量与状态管理设计)
4. [与后端对接规范](#4-与后端对接规范)
5. [创新点实现方案](#5-创新点实现方案)
6. [本地运行与调试指南](#6-本地运行与调试指南)
7. [后续扩展建议](#7-后续扩展建议)

---

## 1. 整体架构概览

### 1.1 系统定位

**知曦**（SMART CLASS）是一个面向高等教育场景的 Agent 驱动个性化学习支持系统，核心能力包括：
- **多模态行为识别**：YOLO11 驱动的课堂行为感知与预警
- **RAG 知识问答**：基于本地向量库 + DeepSeek-R1 的智能答疑
- **课程资源管理**：视频、文档、课程计划统一管理
- **学情可视化**：ECharts 多维度学习数据分析
- **个性化学习路径**：LangGraph Agent 工作流驱动

### 1.2 重构后前端架构分层

```mermaid
graph TB
    subgraph UI["🎨 UI 展示层"]
        V1[课程管理视图] 
        V2[AI 对话视图]
        V3[学情分析视图]
        V4[用户/权限视图]
        V5[行为监控视图]
    end

    subgraph Logic["⚙️ 逻辑层 (Composition API)"]
        H1[useChat Hook]
        H2[useRAG Hook]
        H3[useBehavior Hook]
        H4[useAuth Hook]
        H5[useCourse Hook]
    end

    subgraph State["🗂️ 状态层 (Pinia)"]
        S1[userStore - 用户上下文]
        S2[chatStore - 对话线程]
        S3[settingStore - 全局设置]
        S4[courseStore - 课程数据]
    end

    subgraph Data["📡 数据通信层"]
        A1[api/rag.ts - RAG & Chat]
        A2[api/user.ts - 用户认证]
        A3[api/visualization.ts - 图表数据]
        A4[interceptor.ts - 全局拦截器]
        A5[SSE 流式接收器]
    end

    subgraph Infra["🔧 基础设施层"]
        I1[Vite 构建工具]
        I2[TypeScript 类型系统]
        I3[Arco Design Pro 组件库]
        I4[vue-i18n 国际化]
        I5[Mock Service Worker]
    end

    UI --> Logic
    Logic --> State
    Logic --> Data
    State --> Data
    Data --> Infra
```

### 1.3 模块职责说明

| 层级 | 模块 | 职责 |
|------|------|------|
| **UI 展示层** | `src/views/` | 页面级视图组件，仅负责模板渲染和事件触发，不含业务逻辑 |
| **逻辑层** | `src/hooks/` | Composition API 封装业务逻辑，可跨组件复用，如 `useChat`、`useRAG` |
| **状态层** | `src/store/` | Pinia Store 管理全局/跨页面状态，按领域划分 |
| **通信层** | `src/api/` | 封装所有 HTTP 请求和 SSE 流，统一错误处理、认证注入 |
| **基础设施层** | `config/`、`plugins/` | 构建配置、插件注册、开发工具链 |

### 1.4 对比原架构的改进点

| 维度 | 原架构 | 重构后 |
|------|--------|--------|
| **管理员鉴权** | 硬编码 `admin@example.com` | 后端 `is_superuser` 字段驱动 |
| **持久化策略** | 全量 `persist: true`（含消息体） | 仅持久化元信息，消息按需拉取 |
| **SSE 处理** | 直接 XHR 裸写在 `rag.ts` | 封装为 `useSSEStream Hook` 统一管理 |
| **错误处理** | 分散在各组件 `catch` 块 | 统一在 `interceptor.ts` + 全局错误边界 |
| **模块划分** | ChatView 同时管理文件和对话逻辑 | 拆分为 `FileManagerPanel` + `ChatPanel` |
| **类型安全** | 部分 API 函数返回 `any` | 全量 TypeScript 类型覆盖 |

---

## 2. 核心技术栈与选型理由

### 2.1 技术栈总览

| 分类 | 技术 | 版本要求 | 选型理由 |
|------|------|---------|---------|
| **框架** | Vue 3 | ^3.2.40 | Composition API 支持更细粒度的逻辑复用，与 LangGraph 流式响应结合自然 |
| **语言** | TypeScript | ^4.8.4 | 对 RAG API 复杂类型（`StreamPreviewEvent`、`AssistantSettings`）提供编译期保障 |
| **构建工具** | Vite | ^3.2.5 | 热更新极快，适合 AI 功能迭代频繁的研发节奏 |
| **UI 组件库** | Arco Design Pro Vue | ^2.57.0 | 已深度集成，Table/Upload/Modal 组件覆盖文件管理核心场景 |
| **状态管理** | Pinia | ^2.0.23 | 相比 Vuex 更符合 Composition API 风格，DevTools 支持好，类型推导完整 |
| **HTTP 客户端** | Axios | ^0.24.0 | 拦截器链成熟，已有 JWT 注入和响应规范化逻辑 |
| **图表** | ECharts + vue-echarts | ^5.6.0 / ^6.2.3 | 支持学情热力图、行为分布图、课程访问量等复杂可视化需求 |
| **Markdown 渲染** | markdown-it + 插件 | ^14.1.0 | AI 回答内容富文本渲染，支持数学公式扩展 |
| **国际化** | vue-i18n | ^9.2.2 | 已有中英切换基础，支持未来多语言扩展 |
| **动画** | animate.css | ^4.1.1 | 轻量，用于消息气泡入场动效 |
| **代码高亮** | highlight.js | ^11.11.1 | AI 回答中代码块语法高亮 |
| **Mock** | mockjs + MSW（新增） | — | 开发阶段脱离后端独立运行 |
| **持久化** | pinia-plugin-persistedstate | ^3.x | 精细化控制持久化字段，替代裸 `persist: true` |

### 2.2 重点选型说明

#### Pinia + `pinia-plugin-persistedstate`
原有 `persist: true` 会将完整对话消息序列化到 localStorage，随着用户持续使用可能超出 5MB 上限并导致解析性能下降。重构后：
```ts
// chatStore 精细化持久化
persist: {
  pick: ['conversations', 'currentConversationId'],
  // conversations 数组元素不含 messages 字段
  serializer: {
    serialize: (state) => JSON.stringify({
      conversations: state.conversations.map(c => ({
        id: c.id, title: c.title, createdAt: c.createdAt
      })),
      currentConversationId: state.currentConversationId,
    }),
    deserialize: JSON.parse
  }
}
```

#### SSE 流式接收统一封装
`rag.ts` 中的 `uploadReferenceFileWithPreview` 使用裸 XHR，且 `createAssistantChat` 为普通 POST（无流式）。重构后提供统一的 `useSSEStream` Hook：
```ts
// hooks/useSSEStream.ts
export function useSSEStream(url: string, body: object) {
  const data = ref<string>('')
  const isDone = ref(false)
  const error = ref<Error | null>(null)
  // ...封装 XHR 或 fetch EventSource
  return { data, isDone, error, start, abort }
}
```

---

## 3. 关键变量与状态管理设计

### 3.1 全局状态树（State Map）

```mermaid
graph LR
    Root["Pinia Root Store"]
    Root --> US["userStore<br/>用户上下文"]
    Root --> CS["chatStore<br/>对话线程"]
    Root --> SS["settingStore<br/>全局设置"]
    Root --> CoS["courseStore<br/>课程数据（新增）"]

    US --> U1["id: string"]
    US --> U2["email: string"]
    US --> U3["role: 'admin'|'teacher'|'student'"]
    US --> U4["isSuperuser: boolean ← 后端字段"]
    US --> U5["token: string（内存，不持久化）"]

    CS --> C1["conversations: ConvMeta[]"]
    CS --> C2["currentConversationId: string"]
    CS --> C3["isLoading: boolean"]
    CS --> C4["assistantSettings: AssistantSettings"]

    SS --> ST1["theme: 'light'|'dark'"]
    ST1 --> ST2["locale: 'zh-CN'|'en-US'"]
    ST1 --> ST3["promptKey: string"]

    CoS --> CO1["currentCourseId: string"]
    CoS --> CO2["courseList: CourseMeta[]"]
    CoS --> CO3["currentWeek: number"]
```

### 3.2 关键状态变量详解

#### `userStore`

| 变量 | 类型 | 持久化 | 说明 |
|------|------|--------|------|
| `id` | `string` | ✅ | 用户 UUID，用于 API 鉴权和 RAG 上下文过滤 |
| `email` | `string` | ✅ | 显示用 |
| `role` | `string` | ✅ | 前端路由权限守卫依据 |
| `isSuperuser` | `boolean` | ✅ | **取代硬编码 email 判断**，来自 `/users/me` 的 `is_superuser` 字段 |
| `token` | `string` | ❌（内存） | JWT Token，仅存内存，避免 XSS 窃取；通过 `interceptor.ts` 注入请求头 |

> ⚠️ **安全改进**：Token 不存 localStorage，刷新页面后由 `interceptor.ts` 拦截 401 重定向登录。

#### `chatStore`

| 变量 | 类型 | 持久化字段 | 说明 |
|------|------|-----------|------|
| `conversations` | `ConvMeta[]` | `id, title, createdAt`（不含messages） | 对话元信息列表，消息按需从后端拉取 |
| `currentConversationId` | `string` | ✅ | 当前激活 thread_id |
| `isLoading` | `boolean` | ❌ | 全局 AI 响应加载态 |
| `assistantSettings` | `AssistantSettings` | ❌（每次 mount 刷新） | 来自 `/chat/settings`，含 `prompt_options`、`rag_k_options` |
| `messages`（局部） | `ChatRecord[]` | ❌ | 键入当前对话后动态加载，不进 Store，存组件本地 ref |

#### `settingStore`（新增/重构）

| 变量 | 类型 | 说明 |
|------|------|------|
| `theme` | `'light' \| 'dark'` | 已有主题切换，统一收口 |
| `locale` | `'zh-CN' \| 'en-US'` | 国际化语言设置 |
| `promptKey` | `string` | 上次使用的 Prompt 模式，持久化方便快速恢复 |
| `ragK` | `3 \| 4 \| 5` | RAG 检索 K 值，用户可调 |
| `strictMode` | `boolean` | 严格引用模式开关 |

### 3.3 状态流（State Flow）

#### 场景：发送 AI 消息

```mermaid
sequenceDiagram
    participant User as 用户
    participant CP as ChatPanel.vue
    participant Hook as useChat Hook
    participant Store as chatStore
    participant API as api/rag.ts
    participant BE as 后端 /chat/

    User->>CP: 输入问题 + 点击发送
    CP->>Hook: sendMessage(text)
    Hook->>Store: setIsLoading(true)
    Hook->>Store: addMessage({ role:'user', content:text })
    Hook->>API: createAssistantChat(text, threadId, options)
    API->>BE: POST /chat/ { thread_id, user_input, rag_k, ... }
    BE-->>API: { response, tool_calls }
    API-->>Hook: ChatRecord
    Hook->>Store: addMessage({ role:'assistant', content:response })
    Hook->>Store: setIsLoading(false)
    Store-->>CP: currentMessages 响应式更新
    CP->>User: 渲染 AI 回答
```

---

## 4. 与后端对接规范

### 4.1 API 基础约定

```ts
// src/api/interceptor.ts 配置
axios.defaults.baseURL = import.meta.env.VITE_API_BASE_URL  // e.g. http://localhost:8000
axios.defaults.timeout = 30000  // 普通接口 30s
// Chat 接口单独设置 timeout: 0（等待流式响应）
```

| 项目 | 规范 |
|------|------|
| **Base URL** | `VITE_API_BASE_URL`（开发: `http://localhost:8000`，生产: 由运维配置） |
| **API 版本前缀** | `/api/v1`（根据 `settings.API_V1_STR`） |
| **认证方式** | Bearer JWT Token，`Authorization: Bearer <token>` |
| **Content-Type** | JSON 接口：`application/json`；文件上传：`multipart/form-data` |
| **响应格式** | 原始 FastAPI 响应（非 ArcoStyle包装），`interceptor.ts` 自动规范化 |
| **错误响应** | `{ detail: string }` 或 HTTP 状态码，前端统一展示 Toast |
| **超时重试** | 普通接口：单次超时直接提示；Chat 接口：不超时，手动取消 |

### 4.2 核心接口一览

#### 认证模块

```ts
// 登录 —— OAuth2 表单格式（必须用 URLSearchParams）
POST /login/access-token
Content-Type: application/x-www-form-urlencoded
Body: username=xxx&password=xxx
Response: { access_token: string, token_type: "bearer" }

// 获取当前用户信息
GET /users/me
Authorization: Bearer <token>
Response: {
  id: string,        // UUID
  email: string,
  full_name: string,
  is_active: boolean,
  is_superuser: boolean,  // ← 前端权限判断依据
  created_at: string
}
```

#### RAG 知识库模块

```ts
// 文件列表
GET /rag/files?scope=all|system|personal
Authorization: Bearer <token>
Response: { files: ReferenceFile[] }

// 文件上传（SSE 流式预览）
POST /rag/upload/preview
Content-Type: multipart/form-data
Body: FormData { file, preview_chars, preview_chunks, chunk_preview_chars, scope }
Response: text/event-stream（逐行 data: {...} JSON）

// 删除文件
DELETE /rag/files/{file_id}

// 提交向量化
POST /rag/upload/commit  Body: { file_id }
// 取消向量化
POST /rag/upload/cancel  Body: { file_id }
```

#### AI 对话模块

```ts
// 发起对话（同步，支持 RAG + 工具调用）
POST /chat/
Body: {
  thread_id: string,      // 对话会话 ID
  user_input: string,     // 用户输入
  system_prompt?: string, // 自定义系统提示
  rag_k?: 3|4|5,          // RAG 检索数量
  prompt_key?: string,    // 预设风格: tutor/exam/concise/socratic
  strict_mode?: boolean   // 严格引用模式
}
Response: { response: string, tool_calls: object[] }

// 对话历史
GET /chat/history/{thread_id}
Response: ChatRecord[]

// 获取 AI 运行时配置（可用模型、prompt 选项等）
GET /chat/settings
Response: AssistantSettings

// Thread CRUD
POST   /chat/threads        Body: { title?, thread_id? }
GET    /chat/threads
PUT    /chat/threads/{id}   Body: { title }
DELETE /chat/threads/{id}
```

### 4.3 典型接口调用示例

#### 登录流程

```ts
// src/views/login/index.vue
import { login } from '@/api/user'
import { useUserStore } from '@/store'

async function handleLogin(form: { username: string; password: string }) {
  try {
    const res = await login(form)
    const token = res.data.token  // 来自 access_token 映射
    
    const userStore = useUserStore()
    userStore.setToken(token)  // 仅存 Pinia 内存，不写 localStorage
    
    // 立即拉取用户信息（含 is_superuser）
    await userStore.fetchUserInfo()
    
    router.push('/')
  } catch (e) {
    // interceptor 已 Toast 报错，此处可做表单重置
  }
}
```

#### 发送 AI 对话

```ts
// src/hooks/useChat.ts
import { createAssistantChat, fetchChatHistory } from '@/api/rag'
import { useChatStore } from '@/store'

export function useChat() {
  const chatStore = useChatStore()

  async function sendMessage(text: string) {
    chatStore.setIsLoading(true)
    chatStore.addMessage({ role: 'user', content: text })
    
    // 乐观插入等待消息
    chatStore.addMessage({ role: 'assistant', content: '', pending: true })

    try {
      const settings = chatStore.assistantSettings
      const result = await createAssistantChat(text, chatStore.currentConversationId, {
        ragK: settings.rag_k_default,
        promptKey: settings.default_prompt_key,
        strictMode: false,
      })
      // 更新最后一条消息内容
      chatStore.updateLastMessage(result.response, '', 0, 0)
    } catch (e) {
      chatStore.updateLastMessage('⚠️ 请求失败，请稍后重试', '', 0, 0)
    } finally {
      chatStore.setIsLoading(false)
    }
  }

  return { sendMessage }
}
```

### 4.4 前端 Mock 方案

开发阶段脱离后端时，使用 **Mock Service Worker (MSW)** 拦截请求：

```ts
// src/mock/handlers.ts
import { http, HttpResponse } from 'msw'

export const handlers = [
  // 登录 mock
  http.post('/login/access-token', () =>
    HttpResponse.json({ access_token: 'mock-jwt-token', token_type: 'bearer' })
  ),

  // 用户信息 mock
  http.get('/users/me', () =>
    HttpResponse.json({
      id: 'mock-uuid-001',
      email: 'teacher@zhixi.edu',
      is_superuser: false,
      full_name: '张老师',
    })
  ),

  // Chat mock（含延迟模拟推理时间）
  http.post('/chat/', async ({ request }) => {
    await new Promise(r => setTimeout(r, 1200))
    return HttpResponse.json({
      response: '这是一个 Mock AI 回答：根据您的问题，RAG检索到相关内容如下...',
      tool_calls: [],
    })
  }),

  // RAG 文件列表
  http.get('/rag/files', () =>
    HttpResponse.json({
      files: [
        { file_id: 'f001', name: '数据结构讲义.pdf', size: 204800, scope: 'system', can_manage: false },
        { file_id: 'f002', name: '我的笔记.md', size: 10240, scope: 'personal', can_manage: true },
      ]
    })
  ),
]
```

```ts
// src/main.ts（开发环境启用）
if (import.meta.env.DEV && import.meta.env.VITE_MOCK === 'true') {
  const { worker } = await import('./mock/browser')
  await worker.start({ onUnhandledRequest: 'bypass' })
}
```

---

## 5. 创新点实现方案

### 5.1 💡 行为预警实时推送（WebSocket / SSE）

**背景：** YOLO11 行为分析已有服务端能力（`behavior_analysis.py`），但当前仅通过 AI 工具调用触发，缺乏持续流式推送。

**实现路径：**

```mermaid
graph LR
    Camera["📷 摄像头帧"] --> BE_YOLO["后端 YOLO 分析"]
    BE_YOLO --> BE_Alert["生成 Alert 记录"]
    BE_Alert --> SSE["GET /alerts/stream (SSE)"]
    SSE --> FE_Hook["useAlertStream Hook"]
    FE_Hook --> Notice["Arco Notification 弹窗"]
    FE_Hook --> Dashboard["学情看板实时更新"]
```

**前端实现：**
```ts
// src/hooks/useAlertStream.ts
export function useAlertStream(tcId: string) {
  const alerts = ref<Alert[]>([])
  let eventSource: EventSource | null = null

  function connect() {
    const token = getToken()
    eventSource = new EventSource(
      `${import.meta.env.VITE_API_BASE_URL}/alerts/stream?tc_id=${tcId}&token=${token}`
    )
    eventSource.onmessage = (e) => {
      const alert: Alert = JSON.parse(e.data)
      alerts.value.unshift(alert)
      // 高严重度预警弹窗通知
      if (alert.severity === 'high') {
        Notification.warning({ title: '⚠️ 学情预警', content: alert.reason })
      }
    }
    eventSource.onerror = () => eventSource?.close()
  }

  onMounted(connect)
  onUnmounted(() => eventSource?.close())

  return { alerts }
}
```

**潜在风险：** EventSource 不支持自定义Header传Token；规避方案：Token 通过 URL query 参数传递，或后端改为 WebSocket 协议。

**验证方式：** 后端模拟发送预警事件，前端看板内检查是否在 200ms 内出现 Notification 弹窗且 `alerts` 列表更新。

---

### 5.2 💡 个性化学习诊断报告卡

**背景：** `ChatLog`、`LearningActivity`、`CoursePlan` 数据已有，缺少前端展示入口。

**实现路径：**
1. 后端提供 `GET /students/{id}/learning-report` 接口，返回 Markdown 格式诊断报告
2. 前端学生个人页新增「AI 学习诊断」卡片，渲染 markdown-it 输出
3. 薄弱知识点以 ECharts 词云/雷达图展示

```ts
// src/views/profile/LearningReport.vue（片段）
const reportHtml = ref('')

async function loadReport() {
  const res = await axios.get(`/students/${userId}/learning-report`)
  reportHtml.value = markdownIt.render(res.data.markdown)
}
```

**潜在风险：** 报告生成依赖 LLM，响应慢（3-8秒）；对策：前端加骨架屏 + 后端异步生成 + 轮询结果。

**验证方式：** 调用接口后渲染报告，核查是否包含「薄弱知识点」、「建议学习路径」两个核心段落。

---

### 5.3 💡 Prompt 模式用户反馈闭环

**背景：** 已有 `tutor/exam/concise/socratic` 4种预设，缺乏效果采集机制。

**实现路径：**
```
AI 回答气泡 → 👍/👎 按钮 → POST /chat/feedback → 后台满意度统计图表
```

**前端实现（消息气泡组件）：**
```vue
<!-- src/components/chat/MessageBubble.vue -->
<template>
  <div class="bubble-wrapper">
    <div class="bubble-content" v-html="renderedContent" />
    <div v-if="message.role === 'assistant'" class="feedback-row">
      <a-button
        size="mini" type="text"
        :status="feedback === 'up' ? 'success' : 'normal'"
        @click="submitFeedback('up')"
      >👍</a-button>
      <a-button
        size="mini" type="text"
        :status="feedback === 'down' ? 'danger' : 'normal'"
        @click="submitFeedback('down')"
      >👎</a-button>
    </div>
  </div>
</template>

<script setup lang="ts">
const feedback = ref<'up' | 'down' | null>(null)

async function submitFeedback(rating: 'up' | 'down') {
  feedback.value = rating
  await axios.post('/chat/feedback', {
    record_id: props.message.id,
    rating,
    prompt_key: chatStore.assistantSettings.default_prompt_key,
  })
}
</script>
```

**验证方式：** 提交反馈后 `/chat/feedback` 返回 200，Admin 看板中对应 Prompt 模式的满意度计数 +1。

---

### 5.4 💡 视频课程智能切片导航

**背景：** `Video` 模型已有 `file_path`、`week`，PPT 中展示了「可选择不同知识点观看」的功能构想。

**实现路径：**
1. 后端 Whisper 转录后按知识点分段，返回 `{ timestamps: [{start, end, topic}] }`
2. 前端视频播放页增加「章节导航」侧边栏
3. 点击章节跳转到对应时间戳

```ts
// src/views/course/coursevideo/VideoPlayer.vue（片段）
const chapters = ref<Chapter[]>([])

onMounted(async () => {
  const res = await axios.get(`/videos/${videoId}/chapters`)
  chapters.value = res.data
})

function seekToChapter(start: number) {
  videoRef.value!.currentTime = start
  videoRef.value!.play()
}
```

**潜在风险：** Whisper 转录耗时，大文件处理需后台任务队列；前端用轮询或 SSE 获取转录进度。

---

## 6. 本地运行与调试指南

### 6.1 前置要求

| 工具 | 版本 | 说明 |
|------|------|------|
| Node.js | ≥ 14.0.0 | .nvmrc 中指定，建议用 nvm 管理 |
| pnpm | ≥ 7.x | 推荐使用（已有 pnpm-lock.yaml） |
| Python | 3.10+ | 后端运行需要 |

### 6.2 前端启动步骤

```bash
# 1. 进入前端目录
cd /Users/a111/zhiXi/code/education/course

# 2. 安装依赖（三选一）
pnpm install
# 或
yarn install
# 或
npm install

# 3. 配置环境变量
cp .env.example .env   # 若无 .env.example 则手动创建

# 4. 启动开发服务器
pnpm dev
# 默认启动在 http://localhost:5173
```

### 6.3 .env 文件配置说明

```bash
# .env（前端开发环境）
# ──────────────────────────────────────────────────
# 后端 API 地址（开发时指向本地 FastAPI）
VITE_API_BASE_URL=http://localhost:8000

# 是否启用 MSW Mock（true=拦截请求，false=请求真实后端）
VITE_MOCK=false

# 应用标题（显示在浏览器 Tab）
VITE_APP_TITLE=知曦 SMART CLASS

# 本地开发 Vite 端口
VITE_PORT=5173
```

```python
# backend/.env（后端环境）
# ──────────────────────────────────────────────────
# LLM 提供商：ollama（本地）或 openai/deepseek（云端）
CHAT_PROVIDER=ollama
CHAT_MODEL=deepseek-r1:7b
OLLAMA_MODEL=deepseek-r1:7b

# 数据库连接（SQLite 或 PostgreSQL）
DATABASE_URL=sqlite:///./zhixi.db
# DATABASE_URL=postgresql://user:pass@localhost:5432/zhixi

# JWT 密钥（生产环境请用随机长字符串）
SECRET_KEY=your-secret-key-here

# CORS 允许的前端地址
BACKEND_CORS_ORIGINS=["http://localhost:5173","http://localhost:3000"]

# Sentry（生产监控，开发可留空）
SENTRY_DSN=

# vLLM 推理地址（如本地部署 vLLM）
VLLM_BASE_URL=http://localhost:8080/v1
```

### 6.4 后端启动步骤

```bash
# 1. 进入后端目录
cd /Users/a111/zhiXi/code/backend

# 2. 创建并激活虚拟环境
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

# 3. 安装依赖
pip install -r requirements.txt

# 4. 初始化数据库
python backend_pre_start.py

# 5. 启动 FastAPI 开发服务器
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# API 文档地址：http://localhost:8000/docs
```

### 6.5 常见问题排查清单

| 问题现象 | 排查步骤 |
|---------|---------|
| **跨域 CORS 报错** | 检查后端 `.env` 中 `BACKEND_CORS_ORIGINS` 是否包含前端地址；确认后端已启动；查看 Network 面板 Response Headers 中 `Access-Control-Allow-Origin` |
| **401 Unauthorized** | Token 是否过期（默认8小时）；检查 `interceptor.ts` 中 `getToken()` 是否返回有效值；清除 localStorage 重新登录 |
| **`/chat/` 请求超时** | Chat 接口 `timeout: 0` 属正常（等待 LLM 推理）；若 5 分钟以上无响应，检查后端 Ollama/vLLM 进程是否存活 |
| **热更新失效** | 删除 `node_modules/.vite` 缓存目录，重启 `pnpm dev` |
| **ECharts 图表空白** | 确认容器 DOM 有明确高度（`height: 400px`）；检查数据接口是否返回正确格式 |
| **文件上传进度不更新** | SSE 连接需后端 `Content-Type: text/event-stream`；检查后端 `/rag/upload/preview` 响应头；确认没有代理缓存（Nginx 需配置 `X-Accel-Buffering: no`） |
| **Pinia 状态重置** | `persist: true` 依赖 `pinia-plugin-persistedstate`；检查 `main.ts` 中是否注册该插件 |
| **构建产物路径 404** | 检查 `vite.config.prod.ts` 中 `base` 配置是否与部署子路径匹配 |

---

## 7. 后续扩展建议

### 7.1 🚀 引入 LangGraph 持久化 Checkpointer，对齐前后端会话状态

**背景：** 当前后端使用 `MemorySaver`，进程重启后 LangGraph 对话状态丢失，前端 `chatStore` 持久化的 `thread_id` 无法恢复历史上下文。

**方向：** 后端切换至 `PostgresSaver`（`langgraph-checkpoint-postgres`），前端在刷新页面后可通过 `thread_id` + `/chat/history/{id}` 完整恢复对话历史，提升连贯性体验。

**优先级：** 高，涉及用户核心体验。

---

### 7.2 📊 沉淀教育场景专属组件库

**背景：** 随着课程管理、学情分析、AI对话等模块功能稳定，其中「AI 消息气泡」、「文件上传进度面板」、「学情雷达图」、「周计划时间线」等组件具备通用性。

**方向：**
- 将上述组件抽取为独立 npm 包（如 `@zhixi/edu-components`）
- 使用 Vite Library Mode 发布
- 支持其他学校/课程系统接入，助力推广

**优先级：** 中，建议在 v2.0 迭代时启动。

---

### 7.3 🔒 渐进式 PWA 支持（离线优先 + 桌面安装）

**背景：** 知曦面向校园网环境，网络质量不稳定时学生无法访问课程资料和历史对话。

**方向：**
1. 使用 `vite-plugin-pwa` 注册 Service Worker
2. 缓存策略：课程资源（静态文件）Cache First；API 数据（Network First + 本地 IndexedDB 回退）
3. 支持 Chrome/Safari 桌面/手机安装为 App
4. 离线时展示"已缓存"的课程计划和历史对话记录

**实施步骤：**
```bash
pnpm add -D vite-plugin-pwa
```
```ts
// vite.config.ts
import { VitePWA } from 'vite-plugin-pwa'
plugins: [
  VitePWA({
    registerType: 'autoUpdate',
    workbox: {
      globPatterns: ['**/*.{js,css,html,woff2}'],
      runtimeCaching: [{
        urlPattern: /^https:\/\/.*\/rag\/files/,
        handler: 'NetworkFirst',
        options: { cacheName: 'rag-files' }
      }]
    }
  })
]
```

**优先级：** 中，在移动端推广前建议完成。

---

*文档结束 | 如需针对具体模块深入讨论，欢迎进一步沟通。*

---

> **版本历史**
> | 版本 | 日期 | 变更描述 |
> |------|------|---------|
> | v1.0 | 2026-03-22 | 初稿，基于现有代码库全面分析并重构方案 |
