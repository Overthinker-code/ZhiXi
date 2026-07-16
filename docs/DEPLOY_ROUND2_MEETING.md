# 智屿部署演练 · 多智能体会议记录

**会议主题**：部署后全盘验收结论与第三轮改进方向
**参与角色**：项目经理、DevOps 工程师、后端工程师、前端工程师、评审员、答辩顾问
**依据数据**：[`smoke_report_post_deploy.json`](./smoke_report_post_deploy.json)

---

## 一、部署演练结果（已完成）

| 步骤 | 状态 | 说明 |
|------|------|------|
| 本地代码审核 + commit | ✅ | `98e81c8` 主迭代包；`90a0a97` LearningPath 启动修复；`1620587` 小图放大（待 push） |
| `git push` → GitHub | ✅（部分） | 主包与 hotfix 已推送；最后一 commit 因网络超时曾 scp 热更新到服务器 |
| 服务器 `git pull` | ✅ | `/root/workspace/ZhiXI` @ `90a0a97` + scp vision_client |
| 后端重启 | ✅ | `run_backend_stack.py`，8001 正常 |
| 全盘 smoke | ✅ **20/21 pass** | 见下表 |

### 部署后冒烟（vs 部署前）

| 项目 | 部署前 | 部署后 |
|------|--------|--------|
| vision_probe | 误报 reachable / 500 | **probe_ok=true**，「纯红色图片」 |
| chat_stream_multimodal | **FAIL** | **PASS**（识别纯红图 + 合理说明） |
| resource_workshop_image | degraded (OCR) | **PASS** (qwen3-vl) |
| learning_path/me | 404 skip | **PASS** has_path |
| rag_upload | FAIL 500 | **仍 FAIL 500** |

**综合可用性**：58 → **72 / 100**（多模态已打通；RAG 仍阻塞文档链）

---

## 二、会议发言摘要

> **项目经理**：部署链路已跑通：push → pull → 重启 → smoke。答辩 Demo 最大风险「看图说话」已解除，但 RAG 上传必须进 P0。

> **DevOps**：根因链清晰：① 代码未解析 `reasoning` 字段；② health 只查 `/models`；③ Ollama 对 1×1 图 panic（`width/height must be > 32`）。第三项已通过 `normalize_image_ref` 放大至 64px 解决。建议 healthz 长期保留 `vision_probe`。

> **后端工程师**：伴学多模态现返回 `vision_status=ok`（debug 可见）。资源工坊与伴学共用 `vision_client`。剩余：`rag/upload` 500，需查 embeddings 入库链。

> **前端工程师**：本地前端无需 redeploy 即可验收（隧道代理）。建议 P1 在多模态降级时 UI 提示；教师台 scenario 回落加徽章。

> **评审员**：赛题「多模态辅导」现可演示。RAG 若答辩需要「上传讲义问答」，必须修；若 Demo 路径不含 RAG，可降为 P1。

> **答辩顾问**：Golden Path 建议：登录 → 伴学**上传真实截图**（非 1×1）→ 学情诊断 → 资源工坊图像题解 → 数字人 health 展示。避免只测 smoke 小图。

---

## 三、共识决策

1. **第三轮 P0（48h）**：修复 `rag/upload` 500；将 `1620587` 推上 GitHub 并与服务器 git 对齐（勿长期 scp 漂移）。
2. **第三轮 P1（1 周）**：学情 LLM 超时 25s；教师台演示标识；伴学降级 UI；资源包 `generation_mode` 展示。
3. **第三轮 P2**：数字人克隆真实化；课堂摄像头 ENV 化；隐藏 Arco 模板路由。
4. **工程化**：smoke 进 CI；Playwright Golden Path。

---

## 四、Git 提交记录

```
90a0a97 Fix LearningPath model startup on server
98e81c8 Fix multimodal vision pipeline and ship A3 iteration bundle
1620587 Upscale tiny images before Qwen3-VL calls (local, 建议 push)
```

---

## 五、你本地可立即验证

1. 确保 SSH 隧道：`ssh -L 127.0.0.1:18001:127.0.0.1:8001 root@10.102.64.23`
2. 打开 `/assistant/chat`，上传**真实截图**提问
3. 查看 healthz：`curl http://127.0.0.1:18001/api/v1/healthz` → `vision_probe.probe_ok: true`
