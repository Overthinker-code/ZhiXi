# 智屿学生端安全最佳实践审查

日期：2026-07-16
范围：学生端网页、FastAPI、PostgreSQL、资源/知识库文件、AI 与 WebSocket 入口。

## 结论

本轮已补齐比赛演示所需的主要防护：显式主机/CORS 边界、请求与上传限额、登录/找回密码限流、稳定错误码与 request ID、AI 并发/速率/超时预算、WebSocket 鉴权与消息限额、生成资源所有权和路径完整性验证。自动化与真实 API 探针均未发现这些已覆盖路径的 P0 绕过。

这不等于“零风险”或“已达到互联网生产环境完整防护”。浏览器 token 仍是 localStorage 架构，CSP 未部署；ChromaDB 有尚无修复版本的已知公告。视频读取/下载与数字人 job/media 的对象级授权缺口已在本轮关闭，并通过跨用户与票据篡改测试。

## 已落地控制（含代码位置）

| 控制 | 当前实现 | 代码证据 |
| --- | --- | --- |
| 生产配置 fail-closed | access token 默认 60 分钟；生产要求非通配 TrustedHost/CORS，禁止代码沙箱和 mock 路由；本地空密钥只生成临时随机值。 | `code/backend/app/core/config.py:37-65,162-190` |
| 主机、CORS 与通用响应头 | FastAPI 注册 TrustedHost、请求体限额、AI 预算和安全头；CORS 仅允许显式 origin/method/header。响应增加 `nosniff`、`DENY` frame、referrer/permissions policy 与 `no-store`。 | `code/backend/app/main.py:105-143`；`code/backend/app/core/http_security.py:100-124` |
| HTTP 请求体限制 | 同时检查 Content-Length 和实际流式接收字节，超过阈值返回 413；默认请求 26 MiB。 | `code/backend/app/core/http_security.py:18-98`；`code/backend/app/core/config.py:49-50` |
| 上传文件边界 | 文件名只取 basename 并清洗；扩展名/MIME/文件签名相互校验；分块读取超过 25 MiB 即 413；存储名随机化。 | `code/backend/app/core/upload_security.py:36-101`；`code/backend/app/core/config.py:199-200` |
| 图像输入 | 只接受 PNG/JPEG/WebP base64/data URL，限制字符数，严格解码并核验文件头，不接受远程 URL。 | `code/backend/app/api/v1/endpoints/resource_workshop.py:43-70` |
| 登录与找回密码 | 登录/找回按 IP + 账户摘要双桶限流；认证错误使用稳定业务码和 request_id；未知邮箱找回统一 202 文案，并把邮件发送放入后台任务，避免枚举。 | `code/backend/app/core/auth_rate_limit.py:13-84`；`code/backend/app/api/routes/login.py:29-58,80-145,154-192` |
| 请求追踪 | 接受合规的入站 request ID 或生成 UUID；结构化错误返回 code/message/request_id，响应暴露 `X-Request-ID`。 | `code/backend/app/core/request_ids.py:12-26`；`code/backend/app/api/routes/login.py:90-119` |
| AI 资源预算 | 按已验证 JWT 用户/客户端 IP 和 endpoint class 计算；限制身份数、请求频率、单用户并发和 SSE/同步超时。 | `code/backend/app/core/http_security.py:127-290`；`code/backend/app/core/config.py:54-61` |
| WebSocket | 优先使用 `Sec-WebSocket-Protocol` 传 JWT；query token 仅本地可选；校验 origin、用户 active 状态、消息大小、每秒速率和 idle timeout。 | `code/backend/app/api/routes/behavior_analysis.py:320-354,357-452`；`code/backend/app/core/config.py:62-65` |
| 生成资源 IDOR/路径 | 包与产物下载先验证 owner/admin；非法或编码路径统一 404；文件路径必须位于指定 package 目录并通过 manifest/hash 验证后才返回。 | `code/backend/app/api/v1/endpoints/resource_generation.py:150-199`；`code/backend/app/api/routes/resources.py:59-91,510-547` |
| 资源写操作 | 更新、删除只允许上传者或管理员；资源交互以 `score=None` 写行为证据，不能伪造掌握度。 | `code/backend/app/api/routes/resources.py:105-125,424-507` |
| 证据门禁 | 资源生成只在存在可验证课程引用时允许宣称“来自课程资料”；资源暴露不自动提高掌握度。 | `code/backend/app/services/resource_generation_service.py:709-730`；`code/backend/app/services/resource_package_service.py:1144-1150` |
| 视频对象授权 | 列表、详情与下载按上传者、管理员或学生所在教学班过滤；不存在与无权限统一返回 404，避免对象枚举。 | `code/backend/app/api/routes/videos.py`；`code/backend/app/tests/api/routes/test_student_object_authorization.py` |
| 数字人对象授权 | 任务生成时以 0600 原子 sidecar 绑定 owner；job、works、media、script 均校验 owner/admin。播放 URL 使用 10 分钟、绑定单文件的签名票据，篡改或跨用户复用均拒绝。 | `code/backend/app/services/digital_human_service.py`；`code/backend/app/api/routes/digital_human.py`；`code/backend/app/tests/api/routes/test_student_object_authorization.py` |

## 验证证据

### 自动化与依赖审计

- 后端最终快照：**400 passed**。
- 前端：类型检查、6 组学生端测试、生产构建、可访问性静态审计和 bundle 边界均通过；初始 JS 968,354/1,500,000 bytes。
- `npm audit --omit=dev`：0；全依赖审计 9（7 moderate、2 high），均在开发/构建工具链。
- `pip check`：通过。
- `pip-audit`：ChromaDB 1.5.9 命中 `PYSEC-2026-311`，上游当前没有可用修复版本。
- Golden Path：**22 pass / 0 fail / 1 degraded / 0 skip**，记录于 `docs/qa/golden-path-final-2026-07-16.json`；未配置 Qwen 图像密钥的路径保持 degraded，hash embedding 亦由健康接口按 degraded 展示。

### 真实 API/文件探针

- 错误密码：HTTP 400，稳定 `AUTH_CREDENTIALS_INVALID`，包含 request_id；不暴露账户是否存在。
- 未知邮箱找回：HTTP 202，与已知邮箱使用相同用户文案。
- 未认证生成产物下载：401；编码路径穿越：404。
- 生成包 GET 只返回有权限包，并回填实际 resource_id。
- PDF 下载后验证为 `%PDF-1.4`、3 页、非零大小；DOCX/PDF 四个产物均在数据库和文件系统存在。
- 学生访问教师路径：403。
- 第二普通用户不能读取其他用户的视频、数字人任务或媒体；无权限与不存在均为 404。数字人合法签名播放成功，偷取或篡改票据失败。
- Quiz 真实提交只把匹配课程图谱的聚合评分计入画像；6 条自由文本题目标签保留 `score=None`，防止掌握度污染。

## 残余风险与优先级

### P0/P1：比赛部署前状态

- 本轮识别的视频/数字人 IDOR 与 Quiz 内容质量 P0/P1 已关闭：对象访问矩阵自动化通过；最终 Quiz 经真实鼠标提交、DB/画像回读通过；11 个历史错域资源已隔离。当前没有已知未关闭的学生端 P0/P1。

### P2：生产化架构

1. **浏览器 token/localStorage**：短时 token 降低窗口但无法抵御 XSS 读取。建议迁移为 SameSite/HttpOnly/Secure cookie + CSRF 策略，或至少配套严格 CSP 与刷新令牌轮换。
2. **CSP 未部署**：现有 `X-Frame-Options` 等响应头有效，但没有 `Content-Security-Policy`。前端含 Markdown/图表/流式内容，建议以 report-only 采样后收紧 `script-src/style-src/connect-src/img-src`，禁止不必要的 inline/eval。
3. **单节点内存限流**：Auth/AI limiter 是单进程内存结构，多 worker/多实例无法共享；生产应迁移 Redis 原子限流与全局并发租约。
4. **ChromaDB 公告**：1.5.9 的 `PYSEC-2026-311` 尚无修复版本。当前仅嵌入式使用、未暴露 Chroma server，降低但不消除风险；继续隔离端口/文件权限，固定数据目录并跟踪上游修复。
5. **hash embedding 降级**：当前未配置语义 embedding provider 时使用 hash embedding，只适合作为可用性回退，不应在答辩中表述为完整语义检索质量。
6. **开发依赖债务**：完整 npm audit 仍有 9 个开发/构建链漏洞。不要使用 `npm audit fix --force` 跨大版本；应在独立分支升级 Vite/vue-tsc/MockJS 并复跑浏览器链路。

## 上线门禁

- 最终 commit 上重新执行后端全测、前端类型检查/学生测试/生产构建、生产依赖审计与 Golden Path（本地最终快照已完成，部署环境仍需重跑）。
- Quiz 真实生成—逐题点击—提交—API/DB/profile 回读及唯一答案/解析抽查已完成。
- 11 个历史错域资源已隔离；画像仅吸收匹配课程/知识节点的可信评分。
- video 与 digital-human 已使用第二普通用户完成 401/403/404/签名票据矩阵回归。
- 记录 Qwen 图像密钥和 embedding provider 的部署状态；未配置时必须继续显示 degraded，禁止伪装为完整成功。
