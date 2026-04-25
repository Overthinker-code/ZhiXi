# zwj（后端2）工作说明

> **负责人**：后端2 —— 张伟杰  
> **负责模块**：实时行为检测 WebSocket 接口 + 前端对接

---

## 一、任务范围

根据《智屿项目升级任务分工说明》，后端2仅负责以下两项任务，**其他模块未触碰**：

| 任务 | 内容 | 最终状态 |
|------|------|---------|
| 任务A | WebSocket 实时接口 `WS /api/v1/behavior/ws/realtime` | ✅ 已完成 |
| 任务B | 本地接入 CV 模块（人脸检测 + 抬头/低头/缺席判断） | ✅ 已完成 |
| 前端对接 | 按全组统一规范完成 WebSocket 前端对接 | ✅ 已补齐 |

## 二、工作过程说明

### 第一阶段：完成后端接口（初始交付）

完成内容：
- 新建 `app/services/behavior_ws.py` —— 人脸检测 + 姿态估计（初版使用 OpenCV Haar，后替换为 MediaPipe FaceDetector）
- 修改 `app/api/routes/behavior_analysis.py` —— 新增 `@router.websocket("/ws/realtime")`

**存在的问题**：
- 未定义 Pydantic 数据模型，直接返回裸 `dict`，**不符合规范 3.3**
- 前端完全未对接，**不符合规范 3.1（前端 api 层）和 3.2（composable 层）**

### 第二阶段：修复后端规范问题

按规范 3.3 要求补充数据模型：

- `FrameMessage` —— 前端帧消息模型
- `AnalysisMessage` —— 后端分析结果模型
- `PersonResult` —— 单个人员检测模型
- `SummaryResult` —— 统计摘要模型

后端 `analyze_frame()` 方法改为返回 `AnalysisMessage` Pydantic 模型，WebSocket 处理改用 `FrameMessage.model_validate()` 验证输入。

### 第三阶段：补齐前端对接

按规范 3.1 和 3.2 完成前端三层架构：

| 层级 | 文件 | 职责 |
|------|------|------|
| API 层 | `src/api/behavior-analysis-ws.ts` | WebSocket 客户端封装、消息类型定义、自动重连 |
| Composable 层 | `src/composables/useBehaviorWebSocket.ts` | 连接状态管理、帧发送定时器、结果聚合 |
| 组件层 | `src/views/course/monitor/components/behavior-detection-panel.vue` | 摄像头采集、Canvas 绘制检测框、UI 展示 |

### 第四阶段：主舞台全面切换 WebSocket（新增）

**问题**：主舞台原有行为分析走的是旧 HTTP 接口 `POST /behavior/analyze/image`，需要 YOLO 8001 服务，且不符合规范 3.1（裸 HTTP）。

**修改**：`src/views/course/monitor/index.vue`

| 修改项 | 旧逻辑 | 新逻辑 |
|--------|--------|--------|
| 分析方式 | `captureMainStageAndAnalyze` → HTTP `analyzeImage` → 等 YOLO 返回 | `getMainStageFrame` → WebSocket 发送帧 → 实时接收结果 |
| 定时器 | `mainStageInterval` 每 3 秒轮询 | `useBehaviorWebSocket` 每 500ms 自动发帧 |
| 数据格式 | `currentResult` 旧格式（`behavior`, `confidence`, `color`） | `wsState.persons` 新格式（`track_id`, `status`, `score`） |
| 错误状态 | 无 UI 提示 | 新增 `.stage-error-toast` 浮层显示 `wsState.errorMessage` |
| 是否需要 YOLO | ✅ 需要 | ❌ **不需要** |

**规范修复**：
- 删除 `captureMainStageAndAnalyze` 旧方法
- 删除 `mainStageInterval` 定时器
- 删除 `currentResult` 旧状态
- 主舞台 HUD 指标改为读取 `wsState.focusedCount / unfocusedCount / absentCount`
- 绘制框逻辑 `drawMainStageBoxes` 适配新格式 |

---

## 三、修改文件清单

### 后端文件

| 文件 | 操作 | 说明 |
|------|------|------|
| `code/backend/app/services/behavior_ws.py` | **新建** | 实时检测核心服务 + Pydantic 数据模型 |
| `code/backend/app/api/routes/behavior_analysis.py` | **修改** | 新增 WebSocket endpoint `/ws/realtime` |

### 前端文件

| 文件 | 操作 | 说明 |
|------|------|------|
| `code/education/course/src/api/behavior-analysis-ws.ts` | **新建** | WebSocket 客户端封装，符合规范 3.1 |
| `code/education/course/src/composables/useBehaviorWebSocket.ts` | **新建** | WebSocket 状态管理 composable，符合规范 3.2 |
| `code/education/course/src/views/course/monitor/components/behavior-detection-panel.vue` | **重写** | 实时检测面板，摄像头 + WS + Canvas 绘制 |
| `code/education/course/src/views/course/monitor/index.vue` | **修改** | 主舞台行为分析从旧 HTTP 全面切换为 WebSocket |

---

## 四、WebSocket 接口规范

### 连接地址

```
WS /api/v1/behavior/ws/realtime?course_id=<uuid>&token=<jwt>
```

### 前端 → 后端

```json
{
  "type": "frame",
  "frame_id": 101,
  "timestamp": 1713580000,
  "image_base64": "data:image/jpeg;base64,..."
}
```

### 后端 → 前端

```json
{
  "type": "analysis",
  "frame_id": 101,
  "timestamp": 1776690910,
  "persons": [
    {
      "track_id": "person_1",
      "bbox": [917, 109, 1069, 261],
      "status": "focused",
      "score": 0.97
    }
  ],
  "summary": {
    "focused_count": 2,
    "unfocused_count": 0,
    "absent_count": 0
  }
}
```

### 状态枚举

| 状态值 | 含义 | 前端颜色 |
|--------|------|---------|
| `focused` | 正常抬头、专注 | 🟢 绿色 |
| `unfocused` | 低头或转头离开帧 | 🟡 黄色 |
| `absent` | 检测不到人脸 | 🔴 红色 |

---

## 五、规范对照表

| 规范条目 | 状态 | 说明 |
|---------|------|------|
| 3.1 接口挂在 `/api/v1` | ✅ | WebSocket 地址 `/api/v1/behavior/ws/realtime` |
| 3.1 字段 `snake_case` | ✅ | 全部字段使用 `snake_case` |
| 3.1 前端统一走 `src/api/*.ts` | ✅ | `src/api/behavior-analysis-ws.ts` 统一封装 WebSocket 客户端 |
| 3.1 错误走 `detail` | ✅ | 错误消息通过 `detail` 字段返回 |
| 3.2 不用 mock | ✅ | 直接对接真实后端接口 |
| 3.2 不用 `setTimeout` 假装进度 | ✅ | 真实帧发送与结果接收 |
| 3.2 状态逻辑在 composable | ✅ | `useBehaviorWebSocket.ts` 管理全部连接状态 |
| 3.2 加载中/空状态/失败状态 UI | ✅ | 组件内实现完整状态 UI |
| 3.3 先定义数据模型 | ✅ | 4 个 Pydantic 模型约束前后端数据格式 |
| 3.3 返回结构稳定 | ✅ | 模型保证字段和类型不变 |

---

## 六、技术选型说明

### 为什么采用 MediaPipe FaceDetector？

项目最终采用了 **MediaPipe Tasks API**（`mediapipe>=0.10.33`）实现人脸检测，而非旧版 `solutions` API。主要考虑如下：

- **官方推荐**：MediaPipe Tasks API 是新版官方推荐接口，支持更稳定的模型加载与推理流程。
- **轻量高效**：选用 `blaze_face_short_range.tflite` 模型，单帧推理速度快，适合实时 WebSocket 场景。
- **与后端兼容**：通过 `mediapipe.tasks.python.vision.FaceDetector` 直接调用，无需额外启动独立服务，与 FastAPI 后端集成简单。

**具体实现**：

- 模型文件：`blaze_face_short_range.tflite`（首次运行时自动从 Google Storage 下载并缓存到本地）
- 检测输出：人脸边界框 `bbox` + 6 个归一化关键点（左右眼、鼻尖、左右嘴角、左右耳）
- 姿态估计：基于关键点几何关系计算头部姿态，判定 `focused` / `unfocused` / `absent`

**架构设计**：

```python
# BehaviorWebSocketService 核心方法
#   _detect_faces()   —— MediaPipe FaceDetector 检测人脸
#   _estimate_pose()  —— 基于关键点几何规则判断头部姿态
# 输出格式（AnalysisMessage / PersonResult / SummaryResult）保持稳定，
# 后续如需更换为 YOLOv8-Pose 或其他检测器，只需重写上述两个方法即可
```

### 检测逻辑（MediaPipe FaceDetector）

基于 MediaPipe 返回的 6 个关键点（左右眼、鼻尖、嘴、左右耳）进行几何判断：

| 状态 | 判定条件 |
|------|---------|
| `focused` | 鼻尖相对于眼睛中心垂直偏移正常（`nose_offset_y ≤ 0.30`），左右眼高度差小（`eye_height_diff ≤ 0.06`），人脸占比正常（`face_area_ratio ≥ 0.005`） |
| `unfocused` | **低头**：鼻尖明显下沉（`nose_offset_y > 0.30`）；**转头**：左右眼 y 坐标差异大（`eye_height_diff > 0.06`）；**远离**：人脸占比过小（`face_area_ratio < 0.005`） |
| `absent` | 画面中没有检测到任何人脸 |

---

## 七、启动与验证

### 需要启动的服务

**后端主服务（必须）**：

```powershell
cd D:\ZhiXi\code\backend
.\ZhiXi_venv\Scripts\Activate.ps1
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**前端（必须）**：

```powershell
cd D:\ZhiXi\code\education\course
npm run dev
```

**YOLO 服务（不需要）**：

WebSocket 实时检测不依赖 8001 端口的 YOLO 服务，**只启动后端 8000 + 前端即可**。

### 验证步骤

**方式一：主舞台自动检测（推荐）**
1. 打开前端页面，进入课堂监控
2. 点击底部 Dock 栏"🎥 开启视频" → 选择"本地摄像头"
3. 摄像头启动后，**自动**开始 WebSocket 实时行为分析
4. 主舞台 Canvas 上实时绘制检测框
5. 左上角 HUD 显示：专注 / 不专注 / 缺席人数
6. 如果连接出错，左上角显示红色错误浮层

**方式二：侧边栏检测面板**
1. 点击底部 Dock 栏"🤖 AI 行为检测"
2. 右侧滑出面板，点击"开启实时行为检测"
3. 浏览器请求摄像头权限，允许
4. 面板内显示实时检测画面和统计

---

## 八、常见问题

**Q：点击开启后提示"无法访问摄像头"？**
A：确保浏览器允许摄像头权限，且使用 `localhost` 或 `https` 访问（`http` 在非 localhost 下无法调用 getUserMedia）。

**Q：连接成功了但没有检测框？**
A：检测框只在检测到人脸时绘制。确保画面中有人脸正对摄像头。如果光线太暗或人脸太小，Haar 级联可能检测不到。

**Q：WebSocket 断开自动重连吗？**
A：会。客户端内置自动重连机制，最多重试 5 次，间隔 2 秒。手动点击"停止检测"后不再重连。

---

## 九、需上传/提交的文件清单

以下文件为本人的全部修改，提交时请确保包含：

### 后端（2 个文件）

```
code/backend/app/services/behavior_ws.py          ← 新建
code/backend/app/api/routes/behavior_analysis.py  ← 修改（新增 WebSocket 路由）
```

### 前端（4 个文件）

```
code/education/course/src/api/behavior-analysis-ws.ts                        ← 新建
code/education/course/src/composables/useBehaviorWebSocket.ts                ← 新建
code/education/course/src/views/course/monitor/components/behavior-detection-panel.vue  ← 重写
code/education/course/src/views/course/monitor/index.vue                     ← 修改（主舞台切 WebSocket）
```
