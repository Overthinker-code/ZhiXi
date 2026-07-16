# 学生端桌面无障碍与 P0 UltraQA 验收记录

日期：2026-07-14
范围：网页端（1280×800、1440×900，以及 1280 桌面窗口 200% 缩放的 640 CSS px 等效重排）；移动端明确不在本轮范围。
状态：Cycle 1 完成，P0 通过。

## Goal and success criteria

- 目标：修复学情图表与桌面端无障碍阻断项，验收真实 ResourceRun、课程图谱、课程 Agent 和语义 RAG。
- 停止条件：所有 P0 必须场景通过；`partial_success`、`degraded`、回退或空产物不得误报为完整成功。
- 安全边界：不覆盖既有脏工作区，不输出密钥，不做移动端或 AI 伴学视觉重构。
- 说明：当前环境没有 `omx` CLI；UltraQA 生命周期与证据由本文件和可复跑脚本记录，不伪造 CLI 状态。

## Scenario matrix

| ID | 场景 | 实际结果 | 状态 | 主要证据 |
| --- | --- | --- | --- | --- |
| UQ01 | 键盘浏览课程、资源工坊、画像和图谱 | 真实学生登录态 19 个实际页面各巡检 55 个 Tab 停靠点；除一轮遍历结束时浏览器自然回到文档边界外，无隐藏焦点、空名称或缺失焦点指示 | passed | `keyboard-audit-summary.js`、最终 JSON、静态审计 0 findings |
| UQ02 | 画像 null、空数组、单点、0/100、NaN、标签长度不一致 | 显示值被规范化；无浮点长尾、NaN/Infinity 或虚假历史雷达 | passed | `learning-portrait-*.test.ts`、`portrait-chart-fixed-final.png` |
| UQ03 | 快速重复生成、A/B 不同请求冲突 | 幂等键与唯一活动 run 生效；B 的 409 不再自动接管 A，只有显式查看后恢复 A 的请求和产物 | passed | `resource-run-ab-audit.js`：POST=1、显式查看前 GET=0、resume=1、B goal 未泄露 |
| UQ04 | 预览/Agent 窗口 Tab、Shift+Tab、Escape | 对话框焦点陷阱、Escape 关闭和触发器焦点恢复均已实现并实测 | passed | Agent 浏览器验收、静态审计 allowlist 仅保留有说明的 dismissal backdrop |
| UQ05 | Unicode、超长输入、提示注入、越权附件和路径样式文本 | 输入边界、课程授权、附件 owner/session/course、UUID 路径和内容安全均有测试 | passed | 后端完整测试与 security/RAG 专项测试 |
| UQ06 | 生成中取消、核心包提交边界、恢复 | fence 后才关联 package；持久化后取消为 `partial_success` 并保留可恢复包，不误报 cancelled/completed | passed | `test_resource_package_service.py` 第二 Session 取消注入 |
| UQ07 | 过期租约、缺失/损坏结果、陈旧运行 | attempt/lease/fencing 与 corrupt package 409 生效；截断和等长篡改均拒绝 | passed | ResourceRun/Package 专项测试 |
| UQ08 | SSE 停止和迟到事件 | 停止后不再接收/展示；切换角色、关闭或新请求后迟到事件按 sessionToken/requestId 丢弃 | passed | Agent 状态测试与真实浏览器流式验收 |
| UQ09 | HTTP 200 + partial_success、空 artifact、坏 result_url | UI 明确显示部分成功；成功包要求完整 artifact set，下载前校验 manifest/size/SHA-256 | passed | 资源包服务测试、真实 Word/PDF 下载检查 |
| UQ10 | 测试输出含 PASS 但进程非零 | 全部以进程退出码和断言为准；本轮曾因错误 npm 脚本名退出 1，已识别并用正确命令重跑 | passed | 最终命令均 exit 0 |
| UQ11 | 潜在 flaky | 资源、RAG、图谱、Agent 先专项后完整套件复跑；浏览器 A/B、下载和 axe 独立复跑 | passed | 后端 89 targeted + 300 full；前端 5 组测试多次通过 |
| UQ12 | 脏工作区 | 前后持续检查 status/diff，不 reset、不覆盖无关改动 | passed | `git status --short`、`git diff --check` |
| UQ13 | 色觉差异 | 折线使用不同线型/点型，雷达有当前/历史语义，饼图带纹理与文字摘要；全色盲截图可读 | passed | `portrait-chart-fixed-achromatopsia.png` |
| UQ14 | 屏幕阅读器代理 | 真实学生登录态 19 个实际页面 axe WCAG 2/2.1/2.2 A/AA 无 critical/serious；图表有摘要/数据表 | passed | `axe-audit-summary.js` 与最终 JSON |

## Commands and final results

- `../.venv/bin/python -m pytest -q`：`300 passed`。
- P0 安全、RAG、资源专项：`89 passed`。
- `npm run test:student`：5 组通过。
- `npm run type:check`：通过。
- `npm run build` 与 `node scripts/check-build-boundaries.mjs`：通过；首屏 JS `960,613 B < 1,500,000 B`，ECharts/Markdown 保持懒加载。
- `node scripts/audit-student-accessibility.mjs`：20 个目标文件，0 findings；10 项框架/遮罩 allowlist 均有原因。
- 19 个实际学生页面 axe：critical/serious 共 0，且最终 URL 与待测路由逐项一致。
- 19 个实际学生页面、1,045 个 Tab 停靠点：隐藏焦点、空名称和缺失焦点指示均为 0。
- 200% 等效重排：19 个实际学生页面均无文档级横向溢出、控制台错误或请求失败。
- 深健康检查：schema `011`；MiMo chat、MiMo vision 与 Ollama embedding 均真实可达；`capability_status=available`。
- 语义 RAG：6/6 正例 Recall@4，引用元数据率 100%；3/3 无关/攻击请求拒答；跨课程隔离通过。
- 真实资源下载：同一资源包的 `lecture.docx`、`practice.docx`、`lecture.pdf`、`practice.pdf` 均返回 200，MIME 与 `PK`/`%PDF` 文件头有效。
- 已审计并回填 16 个历史资源包、76 个 artifact 的 SHA-256（新增 67 条摘要）；缺 SHA 的持久化包 fail-closed。

## Failures found and fixed

1. Axios 错误拦截器曾把结构化错误替换为普通 `Error`，导致 ResourceRun 409 的 code/run_id 丢失；现保留原 Axios error 和后端 detail。
2. 深视觉探针失败时曾保留文本探针的 reachable=true；现 vision probe 为权威信号，失败/异常均降级。
3. 附件 RAG 曾依赖向量后端 filter；现输出前再次强制核对 owner、course、file_id 和 thread_id。
4. 预览缓存和资源 artifact 的 symlink 检查曾发生在 resolve 之后；现对原始 candidate 先拒绝符号链接。
5. 旧资源包只有 size 校验；现完成摘要回填，API 对缺失/不匹配 digest 均拒绝。
6. 学情图表存在浮点长尾、数组错位、单靠颜色和无历史却绘制对照的问题；已统一规范化并补充非颜色编码、摘要和数据表。
7. 顶部导航、课程工作区、空状态与表单控件存在多处 AA 对比度/标签问题；已逐页修复并通过 19 个实际学生页面复跑。
8. 资源包目录和 `manifest.json` 过去只依赖解析后路径约束；现对原始路径先拒绝符号链接，并有独立回归用例。
9. 管理员态审计曾把学生专属页面重定向到伴学首页；最终脚本改为真实学生会话并强制检查最终 URL，旧证据不再作为结论依据。
10. 学情首页的屏幕阅读器文本曾扩张横向滚动范围，课程内容页选择器和三处搜索框存在键盘焦点缺陷；已修复并在 200% 与键盘门禁中复验。

## Residual risks

- 自动 axe/键盘代理不等于 NVDA/JAWS/VoiceOver 的正式人工认证；比赛演示前仍建议做一次真实 VoiceOver 朗读彩排。
- 当前本地开发配置会警告测试型短密钥；比赛部署必须从 `.env.competition.example` 注入独立强密钥和数据库密码，不能复用本地开发值。
- Python/SQLModel 仍有 `datetime.utcnow()` 与 Pydantic class Config 的弃用警告；不影响本轮 P0，但应在依赖升级前清理。
- 移动端未验收，且不属于本轮通过结论。

## Evidence

- `output/playwright/accessibility-2026-07-14/axe-audit-summary.js`
- `output/playwright/accessibility-2026-07-14/keyboard-audit-summary.js`
- `output/playwright/accessibility-2026-07-14/desktop-200pct-audit.js`
- `output/playwright/accessibility-2026-07-14/resource-run-ab-audit.js`
- `output/playwright/accessibility-2026-07-14/resource-run-ab-isolation.png`
- `output/playwright/accessibility-2026-07-14/resource-download-integrity-audit.js`
- `output/playwright/accessibility-2026-07-14/student-desktop-p0-final-results.json`
- `output/rag-evaluation-qwen3-embedding-2026-07-14.json`
- `output/benchmark-p0-final-2026-07-14.json`
