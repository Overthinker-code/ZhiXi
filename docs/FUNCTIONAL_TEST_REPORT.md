# 智屿全功能验收测试报告

**测试时间（UTC）**：2026-06-10  
**测试环境**：本机前端代理 → SSH 隧道 `http://127.0.0.1:18001` → 学校服务器后端  
**自动化脚本**：[`code/backend/scripts/smoke_functional_test.py`](../code/backend/scripts/smoke_functional_test.py)  
**原始 JSON**：[`docs/smoke_report_baseline.json`](./smoke_report_baseline.json)

---

## 1. 环境快照

| 组件 | 状态 | 说明 |
|------|------|------|
| `/api/v1/healthz` | OK | chat `qwen3:14b`、multimodal `/models` 可达 |
| `/api/v1/readyz` | OK | PostgreSQL 正常 |
| Ollama 文本模型 | OK | 伴学纯文本流式对话正常 |
| Ollama 视觉模型 | **FAIL（推理层）** | `/models` 可达，但 VL 推理失败或空返回；资源工坊走 OCR fallback |
| YOLO `:8002` | 未在本机探测 | 行为分析 API 200（可能 OpenCV/YOLO 后端 fallback） |
| 数字人 Celery/MuseTalk | OK | `digital-human/health` ready=true |
| 学习路径 API | **未部署** | 远程返回 404（本地代码已有，需同步服务器） |
| RAG Embeddings | **FAIL** | 上传 smoke.txt 500 |

**重要说明**：多模态 P0 修复已合入**本地代码库**（见第 4 节），当前隧道所连**远程后端仍为旧版本**，需重新部署后复测。

---

## 2. 自动化冒烟结果汇总

| 指标 | 数量 |
|------|------|
| pass | 17 |
| fail | 2 |
| degraded | 1 |
| skip | 1 |

### 2.1 详细结果

| 模块 | 结果 | 说明 |
|------|------|------|
| 登录 / users/me | pass | 注册测试账号后可正常鉴权 |
| 伴学文本流式 | pass | SSE 正常，多 Agent thought 可见 |
| **伴学多模态** | **fail** | 回复含「无法识别图片」类模板；与用户截图现象一致 |
| 学情报告 GET | pass | 有 summary |
| 学情 diagnose | pass | 可能部分走模板（`possibly_template`） |
| 学情 review-plan / mistake-digest | pass | HTTP 200 |
| 学习路径 GET | skip | 远程 404，端点未上线 |
| 资源工坊 packages | pass | HTTP 200（`generation_mode` 字段未返回） |
| 资源工坊 grade | pass | LLM/启发式批改 score=4.6 |
| **资源工坊 image** | **degraded** | `source=fallback`，VL 未成功 |
| RAG upload | fail | HTTP 500（Embeddings/Chroma 链） |
| 行为 analyze/image | pass | multipart 上传成功 |
| 教师 dashboard 四项 | pass | stats / alerts / popular / distribution |
| 数字人 health | pass | MuseTalk 权重与 fallback 就绪 |

---

## 3. Golden Path 手工验收（7 条）

基于 API 冒烟 + 代码审查；UI 需在部署新后端后复验。

| # | 路径 | API/行为 | 结论 |
|---|------|----------|------|
| 1 | `/login` | access-token + users/me | **通过**（测试账号） |
| 2 | `/assistant/chat` 上传图片 | `image_base64_list` + `image_tutoring` | **失败**（与自动化一致） |
| 3 | `/profile/learning-data` | learning-report 三 action | **部分通过**（诊断可能模板化） |
| 4 | `/course/resource-generation` | packages / grade / image | **部分通过**（图像 degraded） |
| 5 | `/course/monitor` | behavior cameras + WS | **待 UI 复验**（API 单帧 200） |
| 6 | `/digital-human/text-to-video` + `/my` | job 创建与轮询 | **health 就绪**（完整渲染待 UI 跑通） |
| 7 | `/dashboard/workplace` | teacher dashboard API | **API 通过**（前端 scenario 回落需 UI 区分） |

---

## 4. 多模态专项分析

### 4.1 现象

- 用户上传截图提问 → AI 回答「当前图片内容无法被识别…」，LangGraph 仍执行多步推理（如 42 步）。
- 自动化测试：`chat_stream_multimodal` **fail**，回复含「无法识别图片」。

### 4.2 根因（已确认）

1. **架构**：伴学采用「VL 预处理 → 文本 LLM」两阶段，非端到端多模态对话。
2. **解析缺陷（旧代码）**：`_build_image_context` 只读 `message.content`；Ollama Qwen3-VL 常把结果放在 `reasoning`/`thinking`。
3. **健康检查误报**：旧 `healthz` 仅 GET `/models`，不执行真实视觉推理。
4. **无 OCR fallback**：资源工坊有 Tesseract fallback，伴学对话没有。
5. **远程实测**：VL 调用曾出现 `500 Internal Server Error`（可能与 Ollama 参数兼容有关）。

### 4.3 已实施修复（本地代码，待部署）

| 文件 | 改动 |
|------|------|
| [`vision_response.py`](../code/backend/app/services/vision_response.py) | 统一解析 content / reasoning / thinking |
| [`vision_client.py`](../code/backend/app/services/vision_client.py) | 多模型重试、`think:false` 兼容重试、OCR fallback |
| [`chat_engine.py`](../code/backend/app/ai/chat_engine.py) | 接入 vision_client；`debug_mode` 输出 vision_status |
| [`resource_workshop.py`](../code/backend/app/api/v1/endpoints/resource_workshop.py) | 共用 vision 解析 |
| [`health.py`](../code/backend/app/api/v1/endpoints/health.py) | 增加 `vision_probe` 真实推理探测 |
| [`test_vision_response.py`](../code/backend/tests/services/test_vision_response.py) | 单元测试 4 项通过 |

**部署后复测命令**：

```bash
cd code/backend
PYTHONPATH=. python3 scripts/smoke_functional_test.py \
  --base-url http://127.0.0.1:18001 \
  --email <your-email> --password '<password>' \
  --output docs/smoke_report_post_deploy.json
```

---

## 5. 赛题功能对标（实测更新）

| 赛题要求 | 实测结论 |
|----------|----------|
| 智能辅导 / 多 Agent | **通过**（文本对话、thought 链完整） |
| **多模态 / 图像题解** | **未通过**（远程旧版；修复待部署） |
| 对话式学习画像 | **部分通过**（有数据，诊断可能模板） |
| 个性化学习路径 | **未部署到远程**（本地已实现） |
| 资源生成 ≥5 类 | **部分通过**（packages OK，深度偏模板） |
| RAG 知识库 | **失败**（上传 500） |
| 课堂行为 CV | **部分通过**（单帧 API OK） |
| 数字人 | **基础设施就绪**（health OK，渲染待 E2E） |
| 教师工作台 | **API 通过**（演示数据混入风险仍在） |

---

## 6. 综合评分（答辩可用性）

| 阶段 | 分数（估） | 说明 |
|------|------------|------|
| 修复前（本次远程实测） | **58 / 100** | 多模态 fail、RAG fail、路径未部署 |
| 部署 P0 修复 + 路径 + RAG 修复后 | **68–72 / 100** | 多模态与 health _probe 可信 |
| 完成 P1 backlog 后 | **75–80 / 100** | 去演示化、超时与 UI 标识 |

### 答辩高风险项

1. **多模态**：答辩前必须部署 vision 修复并现场演示上传截图。
2. **RAG 上传 500**：需检查服务器 Ollama embeddings（`nomic-embed-text`）与 Chroma 目录权限。
3. **学习路径 404**：需将含 `learning_path` 的后端同步到服务器。
4. **资源工坊图像 fallback**：与伴学同源 VL，部署后应一并改善。

---

## 7. 复测清单（部署后）

- [ ] `healthz.models.multimodal_model.vision_probe.probe_ok === true`
- [ ] `chat_stream_multimodal` smoke **pass**
- [ ] `resource_workshop_image` 至少 `source=qwen3-vl` 或 OCR 有有效 extracted_text
- [ ] `learning_path/me` 非 404
- [ ] `rag_upload` **pass**
- [ ] 前端 `/assistant/chat` 上传用户截图，回答描述图片内容而非「无法识别」
