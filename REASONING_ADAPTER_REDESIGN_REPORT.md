# Reasoning Adapter Redesign Report

## 背景

智屿 `/tutor` 页面使用 MiMo 2.5 API 作为底层模型能力。MiMo 在部分流式响应中会通过 `reasoning_content`、`reasoning` 或 `thinking` 字段返回原生思考片段。如果这些片段直接进入前端 LiveProcess，会暴露供应商原生语境，例如小米生态、米家、HyperOS、智能家居等内容，不符合“智屿智能教育平台 / AI 伴学”的产品定位。

本次改造目标是：后端保留原始 reasoning 作为内部诊断数据，但前端只接收智屿产品语境下的 `process_delta`，展示“理解问题、选择能力、准备上下文、检索课程资料、组织回答、校验输出”等可解释执行过程。

## 原始 reasoning 接收位置

- `code/backend/app/ai/chat_engine.py`
  - 在流式模型响应中读取 `additional_kwargs` 内的 `reasoning_content`、`reasoning`、`thinking`。
  - 生成内部 `reasoning_token` 事件。
- `code/backend/app/api/v1/endpoints/ai_chat.py`
  - `/api/v1/ai/chat/stream` 消费 `stream_chat_events()`。
  - 改造前曾把 `reasoning_token` 转成前端可见 reasoning 事件。

## 新增转换层

新增文件：

- `code/backend/app/services/reasoning_adapter.py`

核心对象：

- `ReasoningAdapterContext`
  - 保存用户问题、mode、tools、courseContext、retrievalStatus、citationStatus。
- `normalize_reasoning_to_product_process(raw_reasoning, context)`
  - 将底层 raw reasoning 转成智屿产品化 `ProcessDelta`。
- `ReasoningProcessNormalizer`
  - 持有 `internal_raw_reasoning`，仅供后端内部诊断。
  - 按阶段去重，避免前端堆叠大量重复过程。
- `guard_answer_delta`
  - 对最终回答正文进行供应商人格偏移检测。
- `guarded_fallback_answer`
  - 当回答偏移时，改用智屿 AI 伴学能力说明。

## 阶段白名单

前端只允许展示以下阶段：

- `understand_problem`
- `select_capability`
- `prepare_context`
- `retrieve_knowledge`
- `call_tool`
- `plan_answer`
- `generate_answer`
- `verify_output`
- `update_learning_profile`
- `suggest_next_step`

旧事件中的 `intent`、`context`、`retrieve`、`compose`、`verify` 等都会在后端映射到上述白名单。

## 供应商语境过滤

默认过滤以下供应商语境词，除非用户明确询问相关主题：

- 小米
- 米家
- HyperOS
- MIUI
- 澎湃OS
- 手机
- 手环
- 电视
- 智能家居
- 生态设备
- 售后
- 系统优化
- 官方发布
- 小米助手
- 我是小米
- 小爱

当 raw reasoning 命中过滤词时，后端触发产品化重写，例如：

- 通用问答：`已识别为通用问答，将以智屿学习助手能力组织回答。`
- 课程问答：`正在结合课程资料与学习上下文，整理可引用依据。`
- 作业批改：`正在识别题目、分析解题步骤，并准备生成错因反馈。`
- 资料生成：`正在规划讲义、练习题、思维导图和代码案例等资源结构。`
- 深度研究：`正在制定检索计划、筛选来源，并组织研究报告结构。`

## SSE 协议调整

前端不再接收 raw reasoning。

保留和新增的前端事件：

- `process_delta`
- `phase_started`
- `phase_updated`
- `phase_finished`
- `answer_delta`
- `citation`
- `safety_check`
- `process_sanitized`
- `run_finished`

不向前端发送：

- `raw_reasoning_delta`
- 未处理的 `reasoning_content`
- 未处理的 `thinking`

`process_sanitized` 表示后端检测到供应商语境或身份偏移，并已完成过程整理。

## 前端消费方式

涉及文件：

- `code/education/course/src/components/chat/useTutorStream.ts`
- `code/education/course/src/components/chat/ChatLayout.vue`
- `code/education/course/src/components/chat/LiveProcessPanel.vue`

改造点：

- `useTutorStream.ts` 只对 `answer_delta` 做增量合并。
- `process_delta`、`phase_updated` 直接交给 LiveProcess 按阶段更新，避免拼接污染。
- `ChatLayout.vue` 对 `reasoning_delta` 仅保留兼容空分支，不再渲染为 timeline。
- `LiveProcessPanel.vue` 统一使用“处理过程 / 正在处理 / 已完成处理”产品文案。

## System Prompt 约束

`/api/v1/ai/chat/stream` 的 system prompt 已明确注入：

- AI 身份为“智屿智能教育平台”的 AI 伴学助手。
- 服务场景为高校课程学习、课程资料问答、作业辅导、资源生成、学习路径规划、学情分析和深度研究。
- 不得自称小米助手。
- 不得主动介绍小米生态、米家、HyperOS、MIUI、手机、手环、电视、智能家居、售后或系统优化能力，除非用户明确询问。

## 测试样例

新增测试：

- `code/backend/app/tests/services/test_reasoning_adapter.py`

覆盖：

- raw reasoning 包含“小米手机、米家App、HyperOS、智能家居”时，输出的 `ProcessDelta` 不包含供应商词。
- 连续相同阶段摘要去重。
- 回答正文出现供应商人格时被拦截，并回退到智屿能力说明。

当前验证命令：

```bash
cd /Users/xsp/Documents/GitHub/ZhiXi/code/backend
ZHIXI_SKIP_DB_TEST_FIXTURE=1 ../.venv/bin/python -m pytest app/tests/services/test_reasoning_adapter.py -q
../.venv/bin/python -m py_compile app/api/v1/endpoints/ai_chat.py app/services/reasoning_adapter.py app/ai/chat_engine.py app/tests/conftest.py
```

## 仍然 fallback 的地方

- Embedding 当前健康检查显示为 hash fallback，课程 RAG 语义效果不如真实 embedding provider。
- 旧版后端事件 `phase_updated`、`tool_delta` 仍保留兼容，但供应商相关 thought 已接入 Reasoning Adapter。
- `reasoning_delta` 前端兼容分支仍存在，但不渲染内容，用于避免旧流事件导致前端报错。

## 本地验收结果

已完成：

- `npm run type:check` 通过。
- `ZHIXI_SKIP_DB_TEST_FIXTURE=1 ../.venv/bin/python -m pytest app/tests/services/test_reasoning_adapter.py -q` 通过。
- `../.venv/bin/python -m py_compile app/api/v1/endpoints/ai_chat.py app/services/reasoning_adapter.py app/ai/chat_engine.py app/tests/conftest.py` 通过。
- FastAPI 已用当前代码重启，`GET /api/v1/readyz` 返回 `status: ready`、`db: ok`、MiMo chat/multimodal reachable。
- 真实调用 `POST /api/v1/ai/chat/stream`，问题为“你能做什么？”：
  - SSE 事件中未出现 `raw_reasoning_delta`。
  - SSE 事件中未出现 `reasoning_delta`。
  - SSE 文本中未出现 `reasoning_content` 或 `thinking`。
  - SSE 文本中未出现“小米、米家、HyperOS、MIUI、澎湃OS、智能家居、生态设备、售后、系统优化、官方发布、小米助手、我是小米”等供应商语境词。
  - 流中出现 `process_delta` 和 `process_sanitized`，说明后端完成了过程整理和供应商语境过滤。
  - 最终回答以“智屿智能教育平台的 AI 伴学助手”为身份，并介绍了高校学习支持能力。
- 使用临时 Playwright 浏览器脚本打开 `http://127.0.0.1:5174/tutor`，登录 `student@example.com / student123456` 后发送“你能做什么？”：
  - 页面文本中未出现供应商语境词。
  - LiveProcess 显示“已完成处理”。
  - 最终回答包含“智屿”身份。
  - 最终回答覆盖课程、作业、资料、学习路径、学情、深度研究等教育能力。

注意：

- 首次未带隔离变量直接运行 pytest 时，项目全局 `app/tests/conftest.py` 会在 teardown 清理真实 PostgreSQL 用户表，因现有 `learning_path` 外键触发失败。已增加 `ZHIXI_SKIP_DB_TEST_FIXTURE=1`，用于纯服务单测时跳过数据库夹具；默认测试行为不变。
