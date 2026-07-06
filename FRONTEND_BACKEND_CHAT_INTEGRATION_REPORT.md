# FRONTEND_BACKEND_CHAT_INTEGRATION_REPORT

更新时间：2026-07-06

## 前端状态到请求体映射

| 入口 | 请求体变化 |
| --- | --- |
| 联网搜索 | `tools.webSearch=true` |
| 深度思考：深度 | `reasoning.level="deep"` |
| 作业批改 | `mode="homework_review"`，`tools.homeworkReview=true` |
| 资料生成 | `mode="resource_generation"`，`tools.resourceGeneration=true`，`resourceRequest.types=[...]` |
| 深度研究 | `mode="deep_research"`，`tools.deepResearch=true`，`tools.webSearch=true`，`reasoning.level="deep"` |
| 课程上下文 | `courseContext.courseId/chapterId/knowledgePointIds/useCourseRag` |
| 上传附件 | 先 `POST /api/v1/ai/attachments`，再把 `{fileId,type,name}` 放入 `attachments` |

## SSE 消费

`ChatLayout.vue` 已处理：

- `session_created`
- `message_started`
- `agent_started`
- `agent_finished`
- `retrieval_started`
- `retrieval_result`
- `reasoning_summary_delta`
- `answer_delta`
- `citation`
- `artifact_started`
- `artifact_finished`
- `safety_check`
- `profile_update`
- `done`
- `error`

## UI 状态

- 流式中发送按钮切换为“停止”。
- 停止生成调用 `AbortController.abort()`。
- 网络或后端错误会显示错误文本并保留重试入口。
- `RESOURCE_GENERATION_FAILED` 会保留已有回答，并在工具轨迹中标记资源生成失败。

## 仍需加强

- 深度研究建议后续拆成后台 job，避免长 SSE 占用。
- Citation 去重目前只做轻量追加，后续可按 `file_id/chunk_id` 去重。
