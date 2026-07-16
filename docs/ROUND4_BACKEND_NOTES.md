# Round 4 Backend Notes

## SSE 契约（向后兼容）

| 事件 | 说明 |
|------|------|
| `reasoning_token` | 人类可读推理 prose |
| `reasoning_action` | 工具/检索动作卡片 `{ action, title, detail, items? }` |
| `thought` / `phase` | 调试/折叠用；bootstrap 阶段默认不产生 `reasoning_token` |

静默 stage：`pipeline_start`, `kb_inject`, `tool_policy`, `web_policy`, `cache`, `tool_run`, `demo_mode`

## 部署

```bash
cd /path/to/ZhiXi
git pull origin main
pip install docling pymupdf
# 或 pip install -r code/requirements.txt
python code/backend/scripts/run_backend_stack.py  # 或现有 systemd/进程管理
python code/backend/scripts/smoke_functional_test.py
```

## 专项验证

1. SSE 中无固定开场白「用户刚发来一个问题…」
2. 触发检索/联网时出现 `reasoning_action`
3. 上传 docx/pdf 响应含 `extraction_method`, `preview_snippet`, `chunks > 0`
4. 数学问题 `final` 中公式为 `$...$` / `$$...$$`
