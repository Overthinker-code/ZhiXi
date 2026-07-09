# 智屿 AI 伴学实时处理过程重构报告

## 结论

已将 `/tutor` 的“实时处理过程 / 思考过程 / 工具调用过程”从后台监控式左右分栏，改为每条 assistant message 顶部的轻量 `LiveProcessBar` + 单列 `LiveProcessStream`。

当前实现基于真实后端 SSE 事件驱动，不使用前端 `setTimeout` 伪造固定步骤。

## 真实 SSE 验证

测试命令：

```bash
curl -N -D /tmp/zhixi_sse_headers_complete.txt \
  -H "Authorization: Bearer <student-token>" \
  -H "Content-Type: application/json" \
  -H "Accept: text/event-stream" \
  -X POST http://127.0.0.1:8001/api/v1/ai/chat/stream \
  -d '{"message":"一句话解释数据库索引。","mode":"tutor","courseContext":{"knowledgePointIds":[],"useCourseRag":false},"tools":{"webSearch":false,"courseRag":false,"deepResearch":false,"homeworkReview":false,"resourceGeneration":false,"citationRequired":false},"reasoning":{"level":"fast","showSummary":true,"showProcess":true},"attachments":[],"resourceRequest":{"types":[],"difficulty":"normal","target":""}}'
```

响应头：

```text
HTTP/1.1 200 OK
cache-control: no-cache, no-transform
x-accel-buffering: no
content-type: text/event-stream; charset=utf-8
```

事件顺序摘要：

```text
session_created -> run_started -> message_started -> phase_started -> phase_delta
-> phase_finished -> tool_result -> answer_delta -> suggestions -> safety_check
-> profile_update -> run_finished -> done
```

验证点：

- `phase_started` index: 3
- `answer_delta` index: 14
- `run_finished` index: 56
- `done` index: 57
- `<think>` / `</think>` 泄漏: false

## 前端事件映射

| SSE 事件 | 前端行为 |
| --- | --- |
| `run_started` | 创建 `liveProcess`，300ms 内显示状态 pill |
| `phase_started` | 新增或更新阶段项，展示短标题和自然语言摘要 |
| `phase_delta` | 追加到当前阶段文本 |
| `phase_finished` | 阶段标记为 done，圆点变 check |
| `tool_started` | 显示“正在工具调用”状态 |
| `tool_delta` | 追加工具执行摘要 |
| `tool_result` | 工具标记完成，并将检索结果映射为引用候选 |
| `reasoning_delta` | 追加到轻量“思考摘要”，过滤内部 agent 名称和 `<think>` 标记 |
| `answer_delta` | 节流追加到 assistant 正文，显示 shimmer/渐显输出 |
| `citation` | 追加到引用证据列表 |
| `safety_check` | 显示引用、安全检查结果 |
| `run_finished` / `done` | 状态改为 done，并自动折叠为“已完成处理” |
| `error` | 状态改为 error，显示轻量错误和重试按钮 |

## 性能优化

- 新增 `useTutorStream.ts`，使用 `requestAnimationFrame` + 50ms flush 合并 SSE 更新。
- `answer_delta` 与 `reasoning_delta` 在前端队列中合并，避免每个 token 都触发全页面重排。
- `LiveProcessStream` 最多展示最近 12 个关键项，完整事件不全部渲染。
- `ChatMain` 只在用户接近底部时自动滚动，用户向上阅读时暂停跟随。
- `answer_delta` 到达后正文区使用轻量 shimmer 和渐显动画，避免长时间空白。
- `run_finished/done` 后自动折叠过程流，避免挤压正文。

## 后端修复

- `/api/v1/ai/chat/stream` 已返回 `text/event-stream`。
- 增加 `run_started`、`phase_started`、`phase_delta`、`phase_finished`、`tool_started`、`tool_delta`、`tool_result`、`reasoning_delta`、`answer_delta`、`citation`、`safety_check`、`run_finished`、`error` 等事件支持。
- 增加 MiMo reasoning 分流兼容：当供应商把 `</think>` 后正文放入 `reasoning_content` 时，后端将其转为 `answer_delta`，避免前端回答区空白。
- 清洗 `<think>` / `</think>`、内部 agent 名称和系统链路文本，不展示完整不可控 chain-of-thought。

## 截图产物

- `output/playwright/live-process-running-collapsed.png`
- `output/playwright/live-process-running-expanded.png`
- `output/playwright/live-process-answer-emerging.png`
- `output/playwright/live-process-tool-call.png`
- `output/playwright/live-process-finished.png`
- `output/playwright/live-process-error.png`

## 验证命令

```bash
cd code/education/course
npm run type:check
```

结果：通过。

```bash
cd code/backend
../.venv/bin/python -m py_compile app/api/v1/endpoints/ai_chat.py app/ai/chat_engine.py
```

结果：通过。

## 仍然存在的 fallback / 限制

- 当前 embedding provider 为 deterministic hash fallback，`/api/v1/readyz` 标记为 degraded；比赛演示建议配置真实 embedding provider，以提升课程 RAG 命中率。
- 当 MiMo 供应商无法提供稳定字段级 reasoning 时，后端只展示经过清洗的“处理摘要”，不展示完整内部推理链。
- 错误态截图使用 Playwright 控制的 SSE error route 验证 UI 行为；正常 running、expanded、answer、tool、finished 截图均走真实后端。

## 下一步建议

- 给 `course_retriever` 增加更强的课程资料索引与同义词召回，减少“知识库暂未找到直接匹配片段”。
- 将 `LiveProcessStream` 的事件归并规则继续细化，按任务模式展示不同过程摘要。
- 为停止生成补充后端取消任务记录，便于演示审计。
