# TUTOR_ACCEPTANCE_REPORT

Generated: 2026-07-06T08:51:38.018Z
Frontend: http://127.0.0.1:5174
Backend: http://127.0.0.1:8001

| Test | Status | Evidence |
| --- | --- | --- |
| backend login | PASS | 真实 token 已获取 |
| /tutor empty | PASS | /Users/xsp/Documents/GitHub/ZhiXi/output/tutor-acceptance-20260706/tutor-empty.png |
| context drawer | PASS | /Users/xsp/Documents/GitHub/ZhiXi/output/tutor-acceptance-20260706/tutor-course-context-open.png |
| chat streaming | PASS | /Users/xsp/Documents/GitHub/ZhiXi/output/tutor-acceptance-20260706/tutor-chat-streaming.png |
| chat finished | PASS | /Users/xsp/Documents/GitHub/ZhiXi/output/tutor-acceptance-20260706/tutor-chat-finished-with-citations.png |
| resource artifact | PASS | /Users/xsp/Documents/GitHub/ZhiXi/output/tutor-acceptance-20260706/tutor-resource-artifact.png |
| homework mode panel | PASS | /Users/xsp/Documents/GitHub/ZhiXi/output/tutor-acceptance-20260706/tutor-homework-review.png |
| deep research mode | PASS | /Users/xsp/Documents/GitHub/ZhiXi/output/tutor-acceptance-20260706/tutor-deep-research.png |
| request payload captured | PASS | {"sessionId":"f59c7d659c8f4d8fae0b096eb66d1149","message":"围绕 ER 模型生成讲义、练习题和思维导图。","mode":"resource_generation","actionId":"resource_generation","courseContext":{"courseId":"c1111111-1111-4111-9111-111111111101","chapterId":"ch3","knowledgePointIds":["er-model"],"useCourseRag":true},"tools":{"webSearch":false,"deepResearch":false,"homeworkReview":false,"resourceGeneration":true,"citationRequired":true},"reasoning":{"level":"balanced","showSummary":true},"attachments":[],"resourceRequest":{"types |

## Notes

- Script uses a real backend login and opens the real `/tutor` page.
- If backend model calls are slow, resource and finished-chat screenshots may take up to 120 seconds.
- Captured request payloads are summarized in the table to verify mode/tools/reasoning mapping.