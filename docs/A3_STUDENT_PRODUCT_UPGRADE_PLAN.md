# 智屿 A3 学生端产品升级审计与实施方案

审计日期：2026-07-10
审计范围：学生端页面、AI 伴学、课程 RAG、资源生成、课程资料、知识图谱、学习路径、学情画像、安装与构建链路。

## 1. 结论摘要

智屿当前已经具备较完整的学生端视觉外壳、可用的 MiMo 对话链路、SSE 事件消费、课程工作区和多类资源文件生成能力。当前主要问题不是“页面不够多”，而是部分页面所展示的业务闭环强于后端真实证据：

1. AI 对话的 LangGraph 编排是真实的，但资源工坊的多智能体轨迹主要是生成后拼装的标签，不是可观测的独立 Agent 运行。
2. 资源包已建立用户、课程和课程资料记录；知识节点、学习路径和画像事件关系仍未持久化。
3. 课程列表、课程资料、图谱和学情页面仍混有静态场景数据、本地缓存或模拟进度，界面没有统一标明数据来源。
4. 默认哈希向量只能作为降级检索，不能作为比赛答辩中的“语义 RAG”证据。
5. 学生端已经有大量动画代码。下一阶段应建立克制的动效规范并删除无意义循环动画，而不是继续分散增加动画。

因此实施原则是：**先让业务证据与页面承诺一致，再做学生端体验精修；动效只表达真实状态变化。**

## 2. 与 A3 评分项的对应判断

| 评分项 | 当前基础 | 主要缺口 | 优先级 |
| --- | --- | --- | --- |
| 创新价值与实用性 35% | 对话、画像、资源、图谱、路径的产品概念完整 | 缺少一次运行可追踪的资源多智能体证据和前后画像变化 | P0 |
| 功能实现及技术要求 45% | MiMo 真调用、SSE、附件 RAG、文件产物已有 | 资源未入库、图谱关联非持久化、路径和画像更新缺少事务证据 | P0 |
| 配套文档 10% | 已有合规和测试文档 | 开源清单不完整，部分实现状态描述高于实际代码 | P1 |
| 演示视频与 PPT 10% | 首页和课程页已有较成熟视觉 | 学生首页偏营销页，Golden Path 还不能以同一 run_id 连续证明 | P1 |

## 3. 当前技术栈与运行基线

### 3.1 前端

- Vue 3、Vue Router、Pinia、TypeScript、Vite 3。
- 主组件库为 Arco Design Vue；仓库中仍同时存在少量 Element Plus 和 Ant Design Vue。
- ECharts、MarkdownIt、Highlight.js、KaTeX。
- 未使用 Tailwind、shadcn/ui、Framer Motion；现有动效主要为 CSS transition/keyframes。
- 已有 `components/chat/*` 和 `components/zy/*` 两套业务组件基础。

### 3.2 后端

- FastAPI、SQLModel/SQLAlchemy、PostgreSQL、Alembic。
- LangChain、LangGraph、Chroma、MiMo OpenAI-compatible API。
- 文档解析支持 PDF、Word、PPT、Markdown 和代码文本。
- 可选课堂行为检测、数字人、Celery/Redis、MediaPipe/YOLO/MuseTalk。

### 3.3 当前验证基线

- `npm run type:check`：通过。
- `npm run build`：通过，存在 Sass legacy API 和依赖内部 `eval` 警告。
- 1280x800 实测核心学生页面未发生文档级横向溢出。
- 主要生产包：Markdown 1505 KiB、ECharts 1026 KiB、Arco 949 KiB，首访分包仍有明显优化空间。
- 当前数据库有 6 门课程、1 条画像、1 条学习路径、0 条 `resource` 记录。

## 4. 学生端页面审计

| 页面 | 当前状态 | 真实度问题 | 目标 |
| --- | --- | --- | --- |
| `/assistant` | 视觉成熟的品牌首页 | 1200+、98%、50+、10万+ 为无来源展示；登录后仍像营销站 | 改为学生学习工作台，保留一屏品牌表达 |
| `/tutor` | 极简对话布局、真实 SSE | 课程列表仍来自后端常量；历史标题重复；流程事件与真实资源运行未统一 | 成为通用 AI 助手，按意图自动调用课程工具 |
| `/course/list` | 课程封面和筛选完整 | API 失败时静默保留 `scenarioCourses`，进度/教师/评分含场景数据 | 真实种子课程 + 明确离线/演示标识 |
| `/course/:id/content` | 视频为主视觉，课程上下文较完整 | 全局侧栏、章节栏、工具区同时存在，1280 下密度高；小智入口重复 | 一主栏、一章节栏、可收起 inspector，仅保留一个即时助手入口 |
| `/course/resource-generation` | 三段式工作台完整，单一生成接口 | 同步请求期间没有 ResourceRun SSE；图谱与路径仍待核验 | 统一 ResourceRun SSE，结果、文件和关系来自同一运行 |
| `/course/:id/resources` | 内置资料和用户生成包均可预览 | 内置材料仍来自前端场景数据；生成包已由数据库按用户读取 | 将内置课程资料通过种子脚本正式入库 |
| `/course/:id/knowledge` | 当前 6 节点布局无重叠 | 节点状态主要在 localStorage；资源关系为文本启发式匹配 | 后端图谱关系 + 点击扩展相邻节点 + 稳定自动布局 |
| `/profile/learning-data` | 空态清晰 | 缺失数据时出现固定 88/72 和客户端模拟进度 | 显示真实画像版本、证据、变化原因和更新时间 |

## 5. P0：先修正业务事实

### 5.1 建立真实 Resource Generation Run

新增一个统一编排，不再让前端同时调用 `/resource-workshop/packages` 和 `/resource-generation/packages`。

建议状态：

```text
created -> profiling -> retrieving -> planning -> generating
        -> reviewing -> persisting -> linking_graph
        -> updating_path -> updating_profile -> completed
```

真实 Agent 划分：

1. `ProfileAgent`：读取当前画像版本、薄弱点、学习偏好和目标。
2. `EvidenceRetrieverAgent`：检索课程资料、用户附件和可选联网来源。
3. `ResourcePlannerAgent`：输出资源类型、目标能力、难度和引用计划。
4. `LectureAgent`、`QuizAgent`、`MindMapAgent`、`CaseAgent`、`ReadingAgent`、`VideoScriptAgent`：按计划并行或分批生成。
5. `CitationSafetyAgent`：逐资源检查引用覆盖、难度匹配、幻觉风险和内容安全。
6. `PackageAssemblerAgent`：生成文件、清单和预览。
7. `LearningUpdateAgent`：写回图谱关系、学习路径和画像事件。

每一步必须保存：`status`、`started_at`、`finished_at`、`model`、`input_summary`、`output_summary`、`citations`、`error_code`。前端只展示这些产品化摘要，不展示模型原始思维链。

### 5.2 数据表与事务边界

新增正式 Alembic migration：

- `resource_generation_run`
- `resource_generation_step`
- `generated_resource_package`
- `generated_resource_artifact`
- `resource_knowledge_link`
- `profile_update_event`
- `learning_path_update_event`

资源生成完成条件：文件写入成功、数据库资源记录写入成功、所有权验证成功。图谱和路径更新失败时运行应标记 `partial_success`，允许重试对应步骤，不能对前端显示全成功。

### 5.3 Golden Path 统一证据账本

每次演示使用同一个 `run_id` 串联：

```text
chat_session_id
  -> retrieval/citation ids
  -> resource_generation_run.id
  -> generated_resource_package.id
  -> resource_knowledge_link ids
  -> learning_path_update_event.id
  -> profile_update_event.id
```

答辩页面应能打开“本次学习记录”，查看每一步的时间、输入摘要、输出和证据来源。这个页面比继续增加抽象宣传文案更有评分价值。

### 5.4 真实课程知识库

至少完整构造“数据库系统原理”一门课程：

- 课程大纲、4-6 章课件、讲义、实验、习题、参考答案、术语表。
- 每个文件拥有 `course_id/chapter_id/knowledge_point_ids/source/page/chunk_id`。
- 提供可重复执行的种子脚本，不能依赖开发者本机 Chroma 目录。
- 另外 2 门课程可以保留较小样例，但 UI 必须标注资料覆盖度。

## 6. RAG 升级方案

### 6.1 当前问题

- `.env.example` 默认 `EMBEDDINGS_PROVIDER=hash`。
- 哈希向量只能做确定性降级，中文语义召回能力不足。
- AI 课程上下文接口当前由 `ai_chat.py` 常量维护，未直接读取课程数据库。

### 6.2 目标检索管线

```text
query rewrite
  -> course/attachment permission filter
  -> BM25 or character n-gram lexical retrieval
  -> semantic embedding retrieval
  -> reciprocal-rank fusion
  -> cross-encoder or LLM lightweight rerank
  -> citation threshold and coverage check
```

部署策略：

- 比赛演示：使用明确配置的真实语义 embedding provider。
- 仅本地 API 模式：允许 `hash`，健康检查必须返回 `degraded`，UI 不得称为语义检索。
- 没有达到最低相关度时返回 `RAG_EMPTY`，让用户上传资料或开启联网检索。

## 7. 学生端信息架构升级

### 7.1 登录后顶部导航

保留：`首页 / AI 伴学 / 课程 / 资源 / 学情`。
移除学生登录态中的：`解决方案 / 价格 / 关于我们`。这些内容可保留在未登录品牌页。

### 7.2 `/assistant` 学生首页

首屏只保留三个焦点：

1. 今日学习目标和一个主输入框。
2. “继续学习”主任务。
3. 画像驱动的下一步建议。

第二屏展示：今日路径、最近资源、薄弱知识点和课程图谱预览。删除没有真实统计来源的平台规模数字。

### 7.3 `/tutor`

- 保持当前极简布局，不恢复工作台式顶部统计。
- 通用问答默认不启用课程 RAG；由后端意图分类和可解释的工具选择触发。
- 输入附件后显示文件解析状态和可检索片段数。
- 流程区展示真实 phase/tool 事件；首个 `answer_delta` 到达后自动折叠为一行。
- 引用采用 Perplexity 式编号与来源摘要；点击不打断当前阅读位置。
- 资源卡使用同一 package 数据，支持预览、下载和资料库位置回链。

### 7.4 课程内容页

- 章节栏保留，课程总导航在 1280 下折叠为图标模式。
- 右侧统计改为 drawer，不与视频长期争夺宽度。
- 只保留一个“小智”入口；打开时自动带入 `course_id/section_id/current_timestamp/selected_text`。
- AI 助学动作以同一状态机显示 `idle/running/success/error`，结果直接进入课程资料。

### 7.5 资源工坊

- 左侧配置采用渐进披露：基础配置默认可见，高级参数折叠。
- 中间只显示真实 Agent stepper，不预先画满成功流水线。
- 右侧资源预览随 `artifact_finished` 增量出现。
- 完成区显示 5 个独立事实：已生成、已审查、已入库、已关联图谱、已回写路径。
- 视频资源在学生侧至少提供脚本、分镜、配音或最终视频中的真实一种，不跳转到教师专属路由。

### 7.6 知识图谱

- 当前阶段继续使用现有 Vue + SVG 画布，不引入 React Flow 或新的重型依赖。
- 首屏按当前节点只展示一阶邻居；二阶关系收敛为 `+N`，点击节点后重新计算一阶关系和稳定分层布局。
- 节点采用选中、邻居、折叠关系三级视觉层级；前后置、关联和证据关系使用不同线型，并避免连线穿过节点卡片。
- 右侧 inspector 收敛为学习证据、关联资源、下一步三个标签，不再堆叠所有状态面板。
- 1440×900 与 1280×800 已实测无横向溢出和节点矩形碰撞；概念图与验收截图位于 `output/graph-concept/`。
- 后续仍需用后端 `GET /graph/nodes/{id}/neighbors?depth=1` 替换当前课程场景数据，并把资源、证据和路径关系持久化。

### 7.7 学情档案

- 六维画像显示值、置信度、证据数、最近更新时间。
- 每轮对话后只在真正产生画像变化时显示“画像已更新”。
- 提供前后 diff，例如“ER 模型掌握度 42% -> 56%，依据：练习 3、问答 1”。
- 数据不足时显示空态，不显示固定 88%、72% 等占位成绩。

## 8. 动效系统

当前仓库约有 348 处 animation/transition 声明，但只有约 21 处 reduced-motion 处理。升级方向是统一和删减。

### 8.1 Token

```css
--motion-fast: 120ms;
--motion-normal: 180ms;
--motion-slow: 240ms;
--ease-standard: cubic-bezier(0.2, 0, 0, 1);
--ease-emphasized: cubic-bezier(0.2, 0.8, 0.2, 1);
```

### 8.2 允许的动效

- 页面进入：opacity + translateY(8px)，180ms。
- 可点击卡片：translateY(-2px) + 轻微阴影。
- 按钮按压：scale(0.98)，不改变布局。
- Drawer/Popover：160-200ms，点击外部关闭并恢复焦点。
- SSE 状态：running 轻微 pulse；done 只做一次颜色过渡。
- 图谱：节点展开和 inspector 更新 180-240ms，边只在首次出现时绘制。
- Skeleton：仅真实请求期间显示。

### 8.3 禁止的动效

- 无业务含义的永久漂浮、发光和图标循环跳动。
- 所有卡片统一飞入。
- 大面积 blur、粒子、3D 背景。
- 用计时器伪造 Agent 或学情进度。

所有非必要动效必须由 `prefers-reduced-motion` 关闭。新增统一 `motion.css` 和 `useReducedMotion`，逐步替换页面内重复 keyframes。

## 9. 独立工程升级任务

### 9.1 安装与依赖

1. 将依赖拆为 `requirements-core.txt`、`requirements-ai.txt`、`requirements-vision.txt`、`requirements-dev.txt`。
2. 学生端标准启动只安装 core + ai；Torch、Ultralytics、MediaPipe、MuseTalk 改为教师/数字人可选依赖。
3. 明确声明 `langgraph`、`langchain-chroma` 和 `pypdf`；移除重复包、标准库 `asyncio` 和未使用的 psycopg2 驱动。
4. 提供 `scripts/bootstrap-local.sh`：检查 Python/Node/PostgreSQL、复制 `.env`、安装依赖、迁移、种子和健康检查。
5. CI 在全新目录执行 `npm ci` 和最小 Python 安装，避免只在开发者现有 venv 中通过。

### 9.2 数据库与迁移

- 禁止长期同时依赖 `create_all()` 与 Alembic。
- 将现有 SQLModel 表补齐 migration，然后应用启动只执行 Alembic 或在部署阶段执行迁移。
- 后端 `readyz` 需要检查数据库 revision，而不只是连接成功。

### 9.3 配置与权限

- 本地启动脚本生成 `SECRET_KEY`，生产/比赛配置拒绝 `changethis`。
- 附件、生成资源、画像和学习路径均按 `user_id` 做读取授权。
- 下载使用 Authorization header，不在 URL query 中传 token。
- 上传限制扩展名、MIME、文件大小并清洗文件名。

### 9.4 构建体积

短期不直接升级 Vite 主版本，先做：

1. 只在聊天页面加载 MarkdownIt/Highlight/KaTeX。
2. ECharts 使用按需模块而不是完整 bundle。
3. 清理学生端未使用的 Element Plus/Ant Design Vue 页面依赖。
4. 压缩 1.4-1.8 MiB 的 PNG 头像和 banner，提供 WebP/AVIF。
5. 设置构建预算：单异步 JS gzip < 250 KiB；学生首页首屏 JS gzip < 350 KiB。

## 10. 分阶段实施顺序

### Phase 0：事实对齐与回归基线（1-2 天）

- 固化核心页面截图、请求体和 SSE 契约测试。
- 标记所有 mock/preview/fallback 来源。
- 移除固定学情占位值和模拟计时器。
- 完成依赖、预启动和数据库 readiness 修正。

验收：类型检查、后端测试、真实 MiMo tutor 流、1280/1440 截图均通过。

### Phase 1：真实资源多智能体（3-5 天）

- 建表和 migration。
- 实现 ResourceGenerationRun、Agent 事件和 SSE。
- 统一两套生成接口。
- 资源写入资料库并绑定用户/课程。

验收：断开模型时明确失败；成功时数据库、文件、SSE 和页面状态一致。

### Phase 2：图谱、路径、画像回写（3-4 天）

- 持久化知识节点和资源关系。
- 实现邻居增量展开。
- 路径和画像产生版本化 update event。

验收：同一 `run_id` 可查到资源、图谱、路径和画像事件。

### Phase 3：学生端信息架构与视觉精修（3-5 天）

- 学生首页工作台化。
- 精简课程内容页栏位和小智入口。
- 统一资源工坊和学情档案视觉语言。
- 落地 motion token 和 reduced-motion。

验收：1280x800 无遮挡；1440x900 首屏焦点不超过 3 个；无伪进度动画。

### Phase 4：RAG 与内容可信度（2-4 天）

- 导入完整数据库课程知识库。
- 混合检索、rerank、引用覆盖和 `RAG_EMPTY`。
- 记录检索评测集和命中率。

验收：20-30 个课程问题有可复现 Recall@K、引用正确率和无答案拒答结果。

### Phase 5：比赛材料与一键验收（2-3 天）

- 完善开源软件名称、版本、来源、许可证和用途。
- 明确科大讯飞相关工具的真实使用位置，未实际接入不得宣称。
- 一键 Playwright 截图、Golden Path 测试、7 分钟演示脚本和故障降级预案。

## 11. 7 分钟演示建议

1. 00:00-00:40：学生首页展示画像和今天的任务。
2. 00:40-02:00：进入 AI 伴学，提出课程问题，展示真实检索、引用和 SSE。
3. 02:00-03:30：基于本轮薄弱点生成 6 类资源，展示真实 Agent 运行。
4. 03:30-04:30：打开资源包预览，证明已入课程资料库。
5. 04:30-05:30：打开图谱，点击节点展开关联资源和证据。
6. 05:30-06:20：展示学习路径已更新，以及下一步任务。
7. 06:20-07:00：展示画像前后变化、质量审查和防幻觉记录。

## 12. 验收矩阵

### 功能

- 登录、用户信息和会话全部来自后端。
- 普通问答、课程 RAG、附件、联网、作业批改、资源生成、深度研究请求体不同。
- 资源生成至少 5 类，且每类有真实文件或可预览内容。
- 资源入库、图谱关联、路径回写、画像更新可由数据库查询证明。

### 体验

- 首个状态事件 < 500ms；普通问答首个可见回答目标 < 3s。
- 资源生成长任务持续有真实事件，连续空白不超过 2s。
- 1280x800、1440x900 无横向溢出、遮挡和不可见主操作。
- 所有 popover/drawer 支持点击外部、Esc、焦点返回。
- reduced-motion 模式关闭非必要动画。

### 质量

- `npm ci`、`npm run type:check`、`npm run build` 通过。
- 后端全量 pytest 通过。
- Alembic 从空数据库升级到 head 通过。
- Playwright 覆盖 13 个核心页面和 Golden Path。
- 工作树不保留截图、日志、临时资源包或缓存。

## 13. 风险与回滚

- 资源编排以新 endpoint 并行上线，旧接口保留一个迭代，前端由 feature flag 切换。
- 新数据表只新增，不先删除现有文件目录；提供一次性回填脚本。
- 图谱先保留当前实现作为 `legacy`，新画布按课程开关灰度。
- 设计升级按页面提交，每个提交必须附 1280/1440 前后截图。
- 不在资源编排、依赖大升级和视觉重构三个方向同时改同一文件。

## 14. 本轮不做的事情

- 不全面更换 Vue、FastAPI、数据库或组件库。
- 不引入重型 3D、粒子背景或全站动画框架。
- 不把模型原始 chain-of-thought 暴露给用户。
- 不以 preview token、localStorage 或固定计时器伪装真实业务成功。
- 不在没有实际调用记录时宣称使用某个 Agent、模型或科大讯飞能力。

## 15. 2026-07-10 实施与验证记录

### 已完成

- 后端默认安装拆分为核心、开发、可选文档/视觉和 YOLO 四组；在全新虚拟环境中完成核心依赖安装、应用导入和 Uvicorn 启动验证。
- 默认 `pytest` 发现范围限定为 `app/tests` 与 `tests`，不再误收集 MuseTalk 自检脚本；加入资源持久化事务测试后结果为 `100 passed`。
- 前端 `npm ci`、`npm run type:check`、`npm run build` 通过，生产依赖审计为 0 个漏洞。
- 学生端 1440×900 的 11 个入口和 1280×800 的 8 个核心入口完成 Playwright 实测，均无文档级横向溢出或页面脚本错误。
- `/dashboard/workplace` 页面及教师统计接口当前返回 200；学生访问 `/course/monitor` 会按角色策略回到学生首页。
- `/tutor` 普通问答完成真实 MiMo SSE 验证：约 7 秒出现可见正文，Markdown 表格与 KaTeX 正常，最终请求完整结束。
- 普通问答不再携带默认数据库课程 ID；从课程页面携带 `courseId/chapterId/prompt` 进入时会恢复草稿并显式启用课程 RAG。
- 工具菜单、思考强度菜单和上下文抽屉支持互斥展开、点击外部关闭、Esc 关闭与焦点返回；隐藏抽屉不再保留可访问焦点。
- 首页移除没有数据来源的平台规模、满意度、院校和用户数量，改为可由当前功能验证的能力标签。
- 已登录学生顶部导航改为 `首页 / AI 伴学 / 课程中心 / 资源工坊 / 学情档案`，营销入口不再占用学生主工作区。
- 全局动效 token 收敛为 120/180/220ms、8px 入场位移和 36ms stagger；`prefers-reduced-motion` 实测可关闭非必要动画。
- 课堂小智支持 Esc 关闭，资源工坊隐藏重复悬浮入口；课程页专注度图表改为容器获得尺寸后初始化，消除 ECharts 零尺寸告警。
- 资源工坊已停止并发调用两套 package API；一次正式生成只发送一个 `/api/resource-generation/packages` POST，预览、文件下载和 package ID 来自同一后端响应。
- 资源正文按类型使用最多 4 个受控并行 Agent 调用 MiMo；相同 9 文件请求从约 142 秒降至约 34 秒。返回轨迹会逐类标明 `MiMo 生成完成` 或 `本地结构化回退完成`，不再把回退包装成模型成功。
- 后端 recent packages 会恢复文本预览、内容类型、清单标题和下载地址，并严格按 `course_id` 过滤；清空 localStorage 后仍能从后端恢复资源包。
- 课程资料页生成记录改为先预览后下载，预览抽屉展示每个真实文件摘要，并保留 AI 复核与图谱核验入口；1280px 实测无横向溢出。
- 课程内资源工坊不再把不相关的全局画像第一薄弱点强行作为知识点，默认改为当前课程首个核心概念；全局弱点只在全局工坊兜底。
- 新增 Alembic `006` 和 `generated_resource_package` 表，现有 `resource` 表增加可空 `package_id`；标准启动顺序改为 readiness、Alembic、种子、应用。
- 新增统一 `ResourcePackageService`：课程内生成成功后同时写入包元数据和每个课程 `Resource` 行，清单、数据库或文件任一步失败都会回滚并删除本轮临时目录。
- 资源工坊和 `/api/ai/resources/from-chat` 已复用同一持久化服务；响应明确区分 `package_persisted` 与 `resources_persisted`，前端不再通过文案猜测是否入库。
- recent packages 改为数据库按 `user_id/course_id` 查询，不再合并 localStorage 结果；生成文件下载只接受 Authorization header，其他学生查询不到记录且下载返回 404。
- 真实 MiMo 最小生成已验证：返回 `content_provider=mimo`、`resources_persisted`、1 个数据库资源行；课程资料页可恢复、预览和下载同一文件，资源工坊刷新后仍显示入库状态。
- PostgreSQL 隔夜启动失败定位为陈旧 `postmaster.pid`，确认 PID 已被系统进程复用且 5432 无监听后完成备份清理；Homebrew PostgreSQL、后端 8001 和前端 5174 已恢复运行。
- Playwright 在 1440×900 验证课程资料、资源包预览和资源工坊恢复，无文档级横向溢出；截图位于 `output/phase-resource-persistence/`。
- 课程图谱完成独立视觉重构：首屏聚焦图谱、节点按一阶关系渐进展开，二阶关系以 `+N` 折叠；加入关系标签、缩略图、画布工具、掌握状态图例和三标签证据 inspector。Playwright 已验证节点点击、搜索、脉络视图及 1440×900/1280×800 无横向溢出和节点碰撞。

### 仍未完成

- Resource Generation Run、步骤表及同一 `run_id` 的图谱/路径/画像事件仍属于下一阶段 P0；资源包与课程资料入库已完成。
- 当前正式资源生成仍是同步 HTTP 请求，页面只能展示“服务端处理中”和完成后的真实轨迹；尚未实现 ResourceRun SSE 增量事件与取消/重试单步。
- 资源文件仍落在受控后端目录，数据库保存包、资源、课程和所有权元数据；比赛演示前仍需对象存储策略、图谱关系表和删除整个资源包的事务接口。
- 当前 embedding provider 仍为可重复但语义能力有限的 hash 降级模式，比赛演示前必须接入语义向量并完成检索评测。
- 当前本机 `.env` 仍使用弱开发密钥，正式演示配置必须更换；代码中 `datetime.utcnow()` 和 Sass legacy API 警告需要分批消除。
- 课程图谱视觉与前端交互层已完成本阶段重构；真实邻居查询、图谱关系表、资源关系回写及跨刷新后端状态仍未完成。
