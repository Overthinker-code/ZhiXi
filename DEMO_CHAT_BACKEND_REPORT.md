# DEMO_CHAT_BACKEND_REPORT

更新时间：2026-07-06

## 后端启动

- PostgreSQL：本机 `127.0.0.1:5432` 已监听。
- FastAPI：`cd code/backend && ../.venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8001`
- 健康检查：`GET /api/v1/healthz` 返回 `status=ok`，MiMo chat 与 multimodal provider 均显示 configured/reachable。

## 新增 AI Chat 接口

- `POST /api/v1/ai/sessions`
- `GET /api/v1/ai/sessions`
- `GET /api/v1/ai/sessions/{session_id}`
- `DELETE /api/v1/ai/sessions/{session_id}`
- `GET /api/v1/ai/sessions/{session_id}/messages`
- `POST /api/v1/ai/chat/stream`
- `POST /api/v1/ai/attachments`
- `GET /api/v1/ai/attachments/{file_id}`
- `GET /api/v1/ai/context/courses`
- `GET /api/v1/ai/context/course/{course_id}`
- `POST /api/v1/ai/resources/from-chat`
- `POST /api/v1/ai/profile/update-from-chat`

## 已验证

| 用例 | 结果 | 说明 |
| --- | --- | --- |
| 登录 | 通过 | `student@example.com / student123456` 可获取真实 JWT |
| 课程上下文 | 通过 | `/api/v1/ai/context/courses` 返回数据库系统原理课程与章节 |
| tutor 模式 | 通过 | `/api/v1/ai/chat/stream` 返回 `session_created/message_started/agent_started/retrieval_started/answer_delta/done` |
| homework_review 缺附件 | 通过 | 返回 `ATTACHMENT_PARSE_FAILED`，不会假装批改 |
| resource_generation | 通过 | 返回 `artifact_started/artifact_finished`，生成包 `rg_20260706073203_af987aec` |
| profile update | 已修复阻塞 | 修复 `ChatThread.user_id` varchar 与 UUID 比较导致的画像刷新失败 |

## curl 示例

```bash
TOKEN=$(curl -sS -X POST http://127.0.0.1:8001/api/v1/login/access-token \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  --data 'username=student@example.com&password=student123456' \
  | python -c 'import json,sys; print(json.load(sys.stdin)["access_token"])')

curl -N -X POST http://127.0.0.1:8001/api/v1/ai/chat/stream \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  --data '{"message":"用一句话解释 ER 模型的作用","mode":"tutor","actionId":"course_qa","courseContext":{"courseId":"c1111111-1111-4111-9111-111111111101","chapterId":"ch3","knowledgePointIds":["er-model"],"useCourseRag":true},"tools":{"webSearch":false,"deepResearch":false,"homeworkReview":false,"resourceGeneration":false,"citationRequired":true},"reasoning":{"level":"fast","showSummary":true},"attachments":[],"resourceRequest":{"types":["lecture_note"],"difficulty":"normal","target":"ER 模型"}}'
```

## 剩余风险

- 深度研究当前复用现有 `web_research_agent + web_search + reasoning`，不是独立后台任务队列；长问题可能耗时较长。
- 资源生成真实调用 MiMo，完整包生成可能需要 60-120 秒。
- 当前附件图片走 `/api/v1/ai/attachments` 本地存储后转 base64；文档走 RAG 解析。
