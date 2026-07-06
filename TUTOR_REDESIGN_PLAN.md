# /tutor 学习问答页审计与渐进式重构计划

更新时间：2026-07-06

## 1. 审计范围

本次只做代码审计与实施计划，不进行大规模页面重构。

已检查目录：

- 前端路由：`code/education/course/src/router/routes/modules/tutor.ts`
- 前端页面：`code/education/course/src/views/chat/ChatView.vue`
- 前端聊天主体：`code/education/course/src/views/chat/LegacyAssistantPanel.vue`
- Composer：`code/education/course/src/views/chat/components/ChatInput.vue`
- 消息渲染：`code/education/course/src/views/chat/components/ChatMessage.vue`
- Reasoning / 引用 / follow-up：`ReasoningBlock.vue`、`CitationArea.vue`、`FollowUpActions.vue`
- Chat hook：`code/education/course/src/hooks/useChat.ts`
- API 封装：`code/education/course/src/api/rag.ts`、`resource-generation.ts`
- 会话 store：`code/education/course/src/store/chat.js`
- 后端 chat endpoint：`code/backend/app/api/v1/endpoints/chat.py`
- 后端 chat engine：`code/backend/app/ai/chat_engine.py`
- 后端 agent / tool 配置：`chat_runtime.py`、`chat_tools.py`
- RAG：`code/backend/app/services/rag_service.py`
- 附件上传：`code/backend/app/api/v1/endpoints/file.py`
- 资源生成：`code/backend/app/services/resource_generation_service.py`
- 学习画像：`code/backend/app/services/user_memory_profile_service.py`
- 登录与数据库配置：`login.py`、`core/config.py`

## 2. 当前页面结构

`/tutor` 路由：

- `tutor.ts` 将 `/tutor` 挂到 `DEFAULT_LAYOUT` 下。
- 子页面实际渲染 `@/views/chat/ChatView.vue`。

当前渲染层次：

```text
DEFAULT_LAYOUT
  -> ChatView.vue
      -> 顶部 context-strip：小智伴学 / 学习画像 / 课程资料 / 协作状态
      -> LegacyAssistantPanel.vue
          -> chat-header：新对话 / 当前标题 / 设置
          -> messages-container
          -> ChatInput.vue
          -> SettingsPanel / DialogEdit / DeveloperPanel
      -> a-drawer：画像 / 资料 / 智能体
      -> ReferenceFileUploadDialog
```

核心问题：真实聊天主体被外层“工作台信息条”包住，页面视觉重心从对话输入框转移到了状态卡和后台式指标上。

## 3. 当前页面问题

1. 视觉不符合主流大模型应用
   - 首屏有显眼的“小智伴学 / 学习画像 / 课程资料 / 协作状态”工作台 strip。
   - 中央输入框不是页面主角。
   - 空白态仍是“开始对话吧 + quick chips”，更像功能面板，不像 ChatGPT / Gemini 的中心化问答入口。

2. 布局层次过重
   - `ChatView.vue` 和 `LegacyAssistantPanel.vue` 各自有一套 header / shell / card。
   - `LegacyAssistantPanel` 命名已经说明它是历史面板，但现在仍是主渲染体。
   - drawer 中已有上下文能力，但外层又把画像、资源、协作状态直接暴露在顶部。

3. 功能入口语义不够严谨
   - `联网搜索` 是真实 active tool 开关，但是否实际搜索取决于后端 agent 路由和工具调用，前端无法保证每次启用都会产生联网证据。
   - `深度思考` 同时加入 `activeTools: ["deep_thinking"]` 和 `reasoningEnabled`，但后端没有名为 `deep_thinking` 的 tool；真正生效的是 `reasoning_enabled` 和思考流逻辑。
   - `批改` 会传 `tool_mode=exercise_grading`，后端支持 `grading_agent`，但输出仍是自然语言，不是结构化评分对象。
   - 空白态 quick chips 会真实发 chat，但只是 prompt 文本，不代表真实 mode。
   - `/tutor` 页面没有“一等”的资源生成入口，资源生成能力存在于资源工坊 API 和页面中。
   - “深度研究”当前没有独立 UI mode 和后端 schema，只能近似用 `web_search + doc_researcher + reasoning` 拼出来。

4. 功能与展示耦合
   - 多智能体 timeline、reasoning、citation、follow-up 都直接堆在消息卡内。
   - 对话页应该默认简洁，仅在用户展开时展示 evidence / agent trace / profile update。

5. 后端能力已较完整，但前端没有统一抽象
   - `ChatStreamRequest` 已支持 `thread_id`、`active_tools`、`current_file_id`、`image_base64_list`、`tool_mode`、`route_context`、`reasoning_enabled`。
   - 前端 `ChatSendOptions` 只定义了 `chat | exercise_grading | image_tutoring`，缺少 `course_qa`、`deep_research`、`resource_generation` 等产品级 mode。

## 4. 需要删除或隐藏的 UI

第一阶段隐藏，不直接删除，便于回滚：

- `ChatView.vue` 中顶部 `.context-strip`
  - “小智伴学”
  - “学习画像”
  - “课程资料”
  - “协作状态”
- `LegacyAssistantPanel.vue` 中过重的 `.chat-header`
  - 当前标题 pill 可弱化为左侧会话栏中的当前会话标题。
  - 设置按钮迁移到 composer 右侧或右侧 drawer。
- 空白态中的浅层 quick chips
  - 保留 3-4 个真实 mode 示例，但点击后必须设置明确 `toolMode` / `activeTools` / `routeContext`，不只是发送文本。
- 消息区默认显示的完整 AgentCollaborationTimeline
  - 默认折叠到“查看过程”。
  - 右侧 drawer 显示 agent trace。
- token / speed 默认展示
  - 移到开发者面板或调试 drawer，避免答辩界面后台感。

## 5. 新页面组件结构建议

不推翻架构，建议先拆出新组件包裹现有 hook：

```text
ChatView.vue
  -> TutorChatShell.vue
      -> TutorSidebar.vue
          - 新对话
          - 会话历史
          - 可折叠
      -> TutorMain.vue
          -> TutorEmptyState.vue
          -> TutorMessageList.vue
              -> ChatMessage.vue 复用并简化默认展示
          -> TutorComposer.vue
      -> TutorContextDrawer.vue
          - 当前课程上下文
          - 引用证据
          - 学习画像
          - Agent trace
          - 生成资源包
```

推荐先保留 `useChat.ts`、`chatStore`、`ChatMessage.vue`，只替换 `ChatView.vue + LegacyAssistantPanel.vue + ChatInput.vue` 的布局和默认显示策略。

## 6. 当前按钮真实链路判断

| 前端入口 | 当前实现 | 后端真实链路 | 结论 |
| --- | --- | --- | --- |
| 新对话 | `chatStore.enterDraftSession()`；首条发送时 `createChatThread()` | `/api/chat/threads` | 真实会话，但新建时先是本地 draft |
| 普通聊天 | `useChat.sendMessage()` | `/api/chat/stream` 或 `/api/chat/` | 真实 |
| 流式回答 | `createAssistantChatStream()` | `/api/v1/chat/stream` SSE | 真实 |
| 会话历史 | `fetchChatThreads()` / `fetchChatHistory()` | `/api/chat/threads`、`/chat/history/{thread_id}` | 真实 |
| 联网搜索 | `activeTools += web_search` + prompt | `chat_tools.search_web` / DuckDuckGoSearchRun | 半真实：工具存在，但是否调用由 agent 决定 |
| 深度思考 | `reasoningEnabled=true`，同时塞入 `deep_thinking` active tool | `stream_chat_events()` 中 `_stream_model_reasoning()` | 部分真实：reasoning 生效；`deep_thinking` 不是后端 tool |
| 批改 | `tool_mode=exercise_grading` + 批改 prompt | `grading_agent`，`ChatRequest.tool_mode` | 真实但输出未结构化 |
| 图片提问 | base64 传 `image_base64_list` | `vision_client` / `MULTIMODAL_PROVIDER=mimo` | 真实 |
| 文档上传 | `uploadThreadFile()` | `/api/v1/file/upload` -> `rag_service.process_uploaded_file(scope=thread)` | 真实 |
| 挂载课程资料 | `mountedFile/currentFileId` | `search_uploaded_document` 或 route context | 真实但依赖 `rag_bindable` |
| 划词提问 | `askSelectionQuery()` | `/api/chat/selection-query` | 真实 |
| 引用证据 | `CitationArea` 消费 citations | `chat_engine` 生成 `final_citations` | 真实但取决于 RAG 命中和模型标注 |
| 点赞/点踩 | `submitChatFeedback()` | `/api/chat/feedback` | 真实，失败静默 |
| 资源生成 | `/tutor` 内无一等入口 | `/api/resource-generation/packages` 存在 | 后端真实，当前 tutor 未打通为 composer action |
| 深度研究 | 无独立 mode | 可组合 web_search/doc_researcher/reasoning | 当前不是独立真实产品能力 |
| 学习画像更新 | 回答保存后 `schedule_memory_profile_refresh()` | `user_memory_profile_service.refresh_profile()` | 真实，best-effort |

## 7. 需要新增或收敛的后端接口

原则：优先复用现有 `/api/chat/stream`，少增接口。

### 7.1 推荐扩展 ChatStreamRequest

新增字段：

```json
{
  "mode": "course_qa | homework_grading | deep_research | resource_generation | image_tutoring | general",
  "capabilities": {
    "web_search": true,
    "course_rag": true,
    "deep_reasoning": true,
    "resource_generation": false
  },
  "course_context": {
    "course_id": "...",
    "section_id": "...",
    "resource_id": "...",
    "knowledge_node_id": "..."
  },
  "artifact_request": {
    "resource_types": ["lecture_markdown", "practice_markdown", "mind_map"],
    "target_minutes": 30
  }
}
```

作用：

- 替代前端把“模式”塞进自然语言 prompt。
- 保留 `tool_mode` 兼容旧代码，但逐步迁移到更明确的 `mode`。
- `deep_thinking` 不再作为 active tool，而是 `capabilities.deep_reasoning`。

### 7.2 新增资源生成桥接接口

可选新增：

- `POST /api/v1/chat/{thread_id}/resource-packages`

内部复用 `resource_generation_service.generate()`，自动带上：

- 当前用户
- 当前 thread 最近一问一答
- course_id / node_id / topic
- 学习画像摘要

目标：让“生成配套资源”在 `/tutor` 中是真实 action，不只是跳转。

### 7.3 新增深度研究 endpoint 或 mode

可先不新增 endpoint，只新增 `mode=deep_research`：

- 强制启用 `web_search`
- 强制启用 `knowledge_base`
- 如果有 `current_file_id`，启用 `search_uploaded_document`
- final payload 返回：
  - sources
  - evidence
  - course_relevance
  - uncertainty

当前 DuckDuckGo 工具只能返回摘要字符串，后续若要比赛演示更可信，应封装结构化 search provider。

### 7.4 学习画像显式刷新接口

已有：

- `GET /api/learning-report/me?refresh=true`
- `POST /api/learning-report/actions/diagnose`

建议在 chat final 后追加轻量事件：

- final SSE payload 增加 `profile_update_summary`
- 或新增 `GET /api/chat/threads/{thread_id}/learning-impact`

## 8. 需要复用的已有服务

- 会话与历史
  - `chat_thread_provider`
  - `chat_provider`
  - `chatStore`

- 聊天与流式输出
  - `ChatRequest`
  - `chat_service()`
  - `stream_chat_events()`
  - `createAssistantChatStream()`

- RAG
  - `rag_service.query_knowledge_base()`
  - `rag_service.search_uploaded_document()`
  - `file.py /upload`

- 多智能体
  - `AGENT_CONFIG`
  - `TOOL_KEYS_BY_AGENT`
  - `profile_agent`
  - `retrieval_agent`
  - `web_research_agent`
  - `tutor_agent`
  - `grading_agent`
  - `safety_review_agent`

- 资源生成
  - `ResourceGenerationRequest`
  - `resource_generation_service.generate()`
  - `resource-generation.ts`

- 学情画像
  - `user_memory_profile_service`
  - `learning_report_service`
  - `schedule_memory_profile_refresh`

- 视觉/图片
  - `vision_client`
  - `image_base64_list`

## 9. 分阶段实现计划

### Phase 0：保持现状可回滚

- 不删除 `LegacyAssistantPanel.vue`。
- 新增 `TutorChatShell.vue` 或在 `ChatView.vue` 增加 feature flag。
- 当前可回滚方式：路由仍指向 `ChatView.vue`，切换 shell 条件即可。

验收：

- `/tutor` 可打开。
- `student@example.com / student123456` 可登录。
- 普通聊天可流式返回。

### Phase 1：视觉收敛为 ChatGPT / Gemini 风格

前端：

- 隐藏 `ChatView.vue` 顶部 `.context-strip`。
- `LegacyAssistantPanel` 改为极简三栏：
  - 左侧：窄会话栏，可折叠。
  - 中央：最大宽度 760-860px 的消息区。
  - 底部：居中 sticky composer。
  - 右侧：默认隐藏 drawer，点击 composer 工具后打开。
- 空白态改为：
  - 中央一句主标题。
  - 大输入框。
  - 真实 mode chips：课程问答、批改、深度研究、生成资源。
- 默认隐藏 agent timeline，仅保留“查看过程”。

不改后端。

验收：

- `npm run type:check`。
- Playwright 截图：空白态、对话态。

### Phase 2：前端 mode 抽象

新增前端类型：

```ts
type TutorMode =
  | 'general'
  | 'course_qa'
  | 'homework_grading'
  | 'deep_research'
  | 'resource_generation'
  | 'image_tutoring';
```

改造：

- `ChatInput.vue` -> `TutorComposer.vue`
- 不再只发 `mode: 'chat' | 'exercise_grading'`
- 每个 chip 设置确定的 `TutorMode` 和 capabilities。
- `深度思考` 从 active tool 中移除，只传 `reasoningEnabled`。

验收：

- 课程问答：`mode=course_qa`，启用 `knowledge_base`。
- 批改：`mode=homework_grading`，后端兼容到 `tool_mode=exercise_grading`。
- 深度研究：启用 `web_search + knowledge_base + reasoningEnabled`。
- 资源生成：触发资源生成 action 或跳转工坊并携带上下文。

### Phase 3：后端 mode 对齐

后端：

- 扩展 `ChatStreamRequest` 和 `ChatRequest`，支持 `mode` / `capabilities` / `course_context`。
- 保留 `tool_mode` 兼容旧前端。
- 根据 mode 做明确 agent routing：
  - `course_qa` -> retrieval_agent + tutor_agent + safety_review_agent
  - `homework_grading` -> grading_agent + retrieval_agent
  - `deep_research` -> retrieval_agent + web_research_agent + safety_review_agent
  - `resource_generation` -> retrieval_agent + resource_generation_service
  - `image_tutoring` -> tutor_agent + vision

验收：

- SSE final 返回 `mode`、`route_trace`、`citations`、`profile_update_summary`。
- 失败时返回明确 error event，不静默 fallback。

### Phase 4：资源生成闭环进 tutor

前端：

- AI 回答底部加“生成配套资源”。
- 点击后打开右侧 drawer：
  - 自动填 topic/course/node。
  - 可选择讲义/练习/导图/阅读/案例/视频脚本。
  - 调用真实 `generateResourcePackage()`。

后端：

- 复用 `/api/resource-generation/packages`。
- 可选新增 thread-context wrapper endpoint。

验收：

- `/tutor` 回答后可生成资源包。
- 课程资料页 recent packages 可读到。
- 图谱核验可带 packageId 跳转。

### Phase 5：深度研究可信化

后端：

- 将 `search_web` 从字符串工具升级为结构化来源列表。
- final payload 增加：
  - `web_sources`
  - `source_quality`
  - `course_alignment`
  - `uncertainty`

前端：

- 右侧 drawer 展示来源卡。
- 默认回答正文不堆来源细节。

## 10. 风险与回滚方案

### 风险 1：视觉改造影响现有聊天稳定性

回滚：

- 保留 `LegacyAssistantPanel.vue`。
- 新 shell 使用 feature flag。
- 出问题时 `ChatView.vue` 直接恢复 `<LegacyAssistantPanel />`。

### 风险 2：mode 新字段破坏旧后端

回滚：

- 前端继续传旧字段 `tool_mode`、`active_tools`、`reasoning_enabled`。
- 后端新增字段全部 optional。

### 风险 3：联网搜索不可控或慢

回滚：

- deep research mode 失败时返回明确错误。
- 不用假装成功，不启用 silent fallback。
- 可以在演示中默认关闭 deep research，只展示普通课程问答链路。

### 风险 4：资源生成耗时长

回滚：

- `/tutor` 中先打开 drawer 并显示进度。
- 生成超时可保留工坊跳转。
- 保持资源工坊原页面可独立演示。

### 风险 5：学习画像刷新同步阻塞

现状 `schedule_memory_profile_refresh()` 在 Celery 不可用时会 fallback sync。

回滚：

- chat final 不等待画像刷新结果。
- 学情页仍可手动点击“更新诊断”。

## 11. 首轮实施建议

建议下一步只做 Phase 1 + Phase 2 的前端渐进式改造：

1. 新建 `TutorChatShell.vue`，复用 `useChat()`。
2. 新建 `TutorComposer.vue`，保留现有上传、Enter、Shift+Enter、composition guard。
3. 在 `ChatView.vue` 用新 shell 替代当前工作台 strip。
4. 把画像/资源/agent trace 移入右侧 drawer。
5. 保持原 `LegacyAssistantPanel.vue` 不删，作为回滚。
6. `npm run type:check`。
7. Playwright 截图：
   - `/tutor` 空白态
   - `/tutor` 对话态
   - composer 打开附件/工具菜单
   - 右侧 drawer 展开

