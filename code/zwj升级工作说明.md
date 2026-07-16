# 智屿（Zhiyu）课堂行为检测系统 — 技术架构全景

> 本文档基于当前代码库状态（2026-04-26）整理，覆盖前端、后端、CV 服务三条主线的技术选型、模块划分、数据流与关键设计决策。

---

## 一、整体架构概览

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              前端层（Vue3 + Vite）                            │
│  ┌───────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐ │
│  │  课堂监控面板  │  │  学生学情页面  │  │  AI对话助手   │  │   教师工作台/仪表盘   │ │
│  │ (实时监控/WebSocket) │ │(学情诊断/报告)│ │(RAG/大模型) │ │  (数据可视化)       │ │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘  └──────────┬──────────┘ │
└─────────┼────────────────┼────────────────┼───────────────────┼────────────┘
          │                │                │                   │
          │ HTTP REST      │ HTTP REST      │ HTTP SSE          │ HTTP REST
          │ /api/v1/...    │ /api/v1/...    │ /api/v1/chat/...  │ /api/v1/dashboard...
          │                │                │                   │
┌─────────┼────────────────┼────────────────┼───────────────────┼────────────┐
│         ▼                ▼                ▼                   ▼            │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │                    后端层（FastAPI + SQLModel + SQLite）                 │ │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐ │ │
│  │  │行为分析服务│  │学情诊断服务│  │AI对话引擎 │  │预警规则引擎│  │RAG知识库 │ │ │
│  │  │behavior_ │  │learning_ │  │chat_     │  │alert_rule│  │rag_      │ │ │
│  │  │analysis   │  │report    │  │engine    │  │_engine    │  │service   │ │ │
│  │  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘ │ │
│  │       │             │             │             │             │       │ │
│  │       └─────────────┴─────────────┴─────────────┴─────────────┘       │ │
│  │                              SQLModel ORM                              │ │
│  │                         SQLite (zhixi.db)                              │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                    ▲                                       │
│                                    │ HTTP (port 8001)                       │
│                                    │                                        │
│  ┌─────────────────────────────────┼─────────────────────────────────────┐ │
│  │                     CV 服务层（YOLOv8-Pose, port 8001）                 │ │
│  │  ┌─────────────────┐  ┌─────────────────┐  ┌───────────────────────┐  │ │
│  │  │   行为检测管线    │  │  教育学行为分析器  │  │   大模型行为分类器      │  │ │
│  │  │  yolo.py        │  │ educational_    │  │ llm_classifier.py     │  │ │
│  │  │  (YOLOv8-Pose)  │  │ behavior.py     │  │ (Qwen2.5-VL-3B-Instruct)│ │ │
│  │  └─────────────────┘  └─────────────────┘  └───────────────────────┘  │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 核心设计理念

1. **前后端分离**：前端 Vue3 SPA，后端 FastAPI RESTful API，CV 服务独立进程
2. **双路径检测**：WebSocket 实时流（MediaPipe 人脸）+ HTTP 上传分析（YOLO 全身姿态）
3. **从看见到理解**：CV 几何规则检测 → 教育学语义解码 → 大模型语义复核 → 学情诊断联动
4. **数据闭环**：检测结果 → 持久化 → 学情诊断 → 复习计划/错题整理/教学建议

---

## 二、前端层（Vue3 + ArcoDesign + Vite）

### 2.1 技术栈

| 层级 | 技术 | 版本 | 用途 |
|------|------|------|------|
| 框架 | Vue 3 | ^3.3 | 响应式 UI |
| 构建 | Vite | ^5.x | 开发服务器 + 打包 |
| UI 组件 | ArcoDesign Vue | ^2.x | 企业级组件库 |
| 状态管理 | Pinia | ^2.x | 全局状态 |
| 路由 | Vue Router | ^4.x | 单页路由 |
| HTTP | Axios | ^1.x | API 请求 |
| 图表 | ECharts | ^5.x | 数据可视化 |
| 国际化 | Vue I18n | ^9.x | 多语言支持 |

### 2.2 目录结构（`code/education/course/src`）

```
src/
├── api/                    # API 接口封装
├── components/             # 通用组件
│   ├── float-ai/           # AI 悬浮球组件
│   ├── state/              # Empty/Error/Loading 状态组件
│   └── ...
├── layout/                 # 页面布局
├── router/                 # 路由配置
├── stores/                 # Pinia 状态管理
├── views/                  # 页面级组件
│   ├── course/
│   │   ├── courselist/     # 课程列表
│   │   ├── courseone/      # 课程详情（含 ClassMode, PlatUse）
│   │   ├── coursevideo/    # 视频播放（含知识图谱、思维导图、AI 问答面板）
│   │   └── monitor/        # ⭐课堂监控面板（行为检测核心）
│   │       ├── behavior-detection-panel.vue    # 行为检测面板（上传/实时）
│   │       ├── attendance-grid.vue             # 出勤网格
│   │       ├── MonitorHudCharts.vue            # HUD 图表
│   │       └── ...
│   ├── chat/               # AI 对话助手（RAG + Agent）
│   ├── digital-human/      # 数字人模块
│   ├── profile/
│   │   └── learning-data/  # ⭐学生学情页面（课堂行为数据展示）
│   ├── user/study/         # 学习档案、复习计划、错题列表
│   └── dashboard/          # 教师工作台
└── App.vue
```

### 2.3 核心页面

#### 课堂监控面板 (`course/monitor/index.vue`)
- **实时检测**：WebSocket 连接后端 `/api/v1/behavior-analysis/ws/realtime`，每帧上传 base64 图像
- **上传分析**：调用后端 `/api/v1/behavior-analysis/analyze/image` 或 `/analyze/video`
- **Canvas 绘制**：叠加检测框 + 行为标签（第一行原始行为，第二行 LEI + 认知状态）
- **课堂报告**：展示教育学分析报告（理论框架、三维投入、注意力动态、布鲁姆分布、教学建议）

#### 学生学情页面 (`profile/learning-data/index.vue`)
- **AI 学情诊断**：一键生成诊断报告、错题整理、复习计划
- **课堂行为数据卡片**：展示 LEI、走神率、主导认知层次、教师备注（有数据时显示，无数据时空状态）

---

## 三、后端层（FastAPI + SQLModel + SQLite）

### 3.1 技术栈

| 层级 | 技术 | 版本 | 用途 |
|------|------|------|------|
| Web 框架 | FastAPI | ^0.110 | RESTful API + WebSocket |
| ORM | SQLModel | ^0.0.x | 类型安全的数据库模型 |
| 数据库 | SQLite | 内置 | 开发环境数据存储 |
| 迁移 | Alembic | ^1.x | 数据库迁移 |
| 认证 | JWT (python-jose) | ^3.x | Token 认证 |
| 异步 | asyncio / celery | - | 异步任务队列 |
| AI | LangChain / OpenAI API | - | 大模型对话、RAG |
| 向量化 | sentence-transformers | - | 文本嵌入 |

### 3.2 目录结构（`code/backend/app`）

```
app/
├── main.py                 # FastAPI 应用入口，注册所有路由
├── core/
│   ├── config.py           # 配置管理
│   ├── db.py               # 数据库引擎 + 会话管理
│   ├── security.py         # JWT / 密码哈希
│   └── enums.py            # 枚举定义
├── models/                 # SQLModel 数据库模型
│   ├── base.py             # 基础模型
│   ├── user.py             # 用户表
│   ├── chat.py             # 对话记录
│   ├── chat_thread.py      # 对话线程
│   ├── user_memory_profile.py  # 用户记忆画像
│   ├── item.py             # 物品/资源
│   ├── message.py          # 消息
│   ├── business_tables.py  # 业务表代理（从 models.py 动态加载）
│   └── ...
├── api/
│   ├── routes/             # 业务路由（behavior_analysis, courses, login...）
│   └── v1/endpoints/       # API v1 端点（ai_metrics, alerts, chat, dashboard, learning_report...）
├── services/               # ⭐核心业务逻辑
│   ├── behavior_analysis.py    # 行为分析服务（连接 YOLO，透传 + 持久化）
│   ├── behavior_ws.py          # WebSocket 实时行为检测（MediaPipe 人脸）
│   ├── alert_rule_engine.py    # 课堂预警规则引擎
│   ├── learning_report_service.py  # 学情诊断服务（联动课堂行为数据）
│   ├── rag_service.py          # RAG 知识库服务
│   ├── chat_engine.py          # AI 对话引擎
│   └── ...
├── ai/                     # AI 相关模块
│   ├── chat_engine.py
│   ├── chat_models.py
│   ├── chat_runtime.py
│   ├── structured_output.py
│   └── chat_tools.py
├── providers/              # 数据提供者抽象
├── schemas/                # Pydantic 请求/响应模型
├── worker/                 # Celery 异步任务
└── tests/                  # 测试用例
```

### 3.3 核心服务

#### 行为分析服务 (`services/behavior_analysis.py`)

```python
# 主要方法
analyze_image(image_data: bytes)        → 分析单张图片 → 持久化
analyze_video(video_data: bytes)        → 分析视频 → 持久化
extract_pose_from_image(image_data)     → 调用 YOLO /analyze/frame
analyze_realtime_frame(image_data)      → WebSocket 实时帧分析
get_behavior_definitions()              → 返回行为定义列表

# 持久化方法
_cache_educational_data(result)         → 缓存供预警引擎消费
_persist_behavior_summary(result)       → 写入 CourseEngagementRecord + BehaviorSummaryRecord
```

#### WebSocket 实时检测服务 (`services/behavior_ws.py`)

基于 **MediaPipe FaceDetector** + **FaceLandmarker**，处理前端实时视频流：
- 人脸检测：MediaPipe `FaceDetector`（blaze_face_short_range 模型）
- 面部关键点：MediaPipe `FaceLandmarker`（468 个面部关键点 + blendshapes）
- 姿态估计：基于面部关键点推导头部姿态（俯仰/偏航/翻滚角）
- 教育学参数：从头部姿态推导 LEI、布鲁姆层次、认知状态
- 输出：`AnalysisMessage`（PersonResult + SummaryResult + EducationalMetrics）

#### 预警规则引擎 (`services/alert_rule_engine.py`)

```python
# 5 类预警规则
1. group_contagion       → 社会传染指数 > 0.5（群体分心聚集）
2. attention_trough      → 注意力周期低谷 + 下降趋势
3. cognitive_shallow     → 认知深度 < 0.45（低阶思维占比高）
4. individual_overload   → 个体注意力异常下降(偏离<-0.35) + LEI < 0.5
5. class_mind_wandering  → 课堂走神率 > 30%

# 频率控制：同类型预警 30 秒冷却期，最多返回 3 条（按严重程度排序）
```

#### 学情诊断服务 (`services/learning_report_service.py`)

```python
# 核心联动：课堂行为数据注入大模型 Prompt
_get_recent_behavior_context(user_id)   → 查询最近 3 节课 BehaviorSummaryRecord

# Prompt 中的行为判断规则
- LEI < 0.4 且走神率高 → 风险等级上调
- LEI > 0.7 且认知深度高 → 风险等级下调
- 布鲁姆停留在 remembering/understanding → 建议高阶思维训练

# 输出
build_report() → LearningReport（含 classroom_behavior_summary）
build_review_plan() → 复习计划（结合课堂注意力数据）
build_mistake_digest() → 错题整理（结合走神时段归因）
```

### 3.4 数据库表结构

#### 核心业务表（`app/models.py`）

| 表名 | 用途 |
|------|------|
| `User` | 用户账户 |
| `Course` | 课程信息 |
| `Student` / `Teacher` | 学生/教师档案 |
| `Chat` / `ChatThread` | 对话记录与线程 |
| `UserMemoryProfile` | 用户长期学习画像 |
| `Video` | 课程视频 |
| `Resource` | 教学资源 |
| `Assignment` / `Submission` | 作业与提交 |
| `LearningActivity` | 学习活动记录 |

#### 行为检测专用表（`app/models.py`）

**`BehaviorSummaryRecord`** — 课堂行为分析摘要记录（联动 1/2/4/7）
```python
id: UUID (PK)
student_id: UUID (FK → student.id, 可选，当前为 NULL 表示课堂整体)
tc_id: UUID (FK → tc.id, 可选)
course_id: UUID (FK → course.id, 可选)
session_date: datetime            # 记录时间（默认 utcnow）

# 课堂整体指标
avg_lei: float                    # 平均学习投入指数
avg_cognitive_depth: float        # 平均认知深度
mind_wandering_rate: float        # 走神率
contagion_index: float            # 社会传染指数
on_task_rate: float               # 目标行为率

# 布鲁姆认知层次分布（JSON 字符串）
bloom_distribution: str           # {"remembering":0.2, "understanding":0.5, ...}
cognitive_state_distribution: str # {"shallow_attention":3, ...}

# 教学建议存档
pedagogical_suggestions: str      # JSON 数组

# 个体画像快照
student_profiles_snapshot: str    # JSON: {student_id: {lei, bei, cei, ...}}

# 数据来源标识
source_type: str                  # "video_analysis" / "realtime_ws"
analysis_duration_sec: float      # 分析时长（秒）
```

**`CourseEngagementRecord`** — 课程质量评估记录（联动 6）
```python
id: UUID (PK)
course_id: UUID (FK → course.id)
tc_id: UUID (FK → tc.id, 可选)
session_date: datetime            # 记录时间

# 课堂整体指标
avg_lei: float
avg_cognitive_depth: float
mind_wandering_rate: float
contagion_index: float

# 布鲁姆分布与认知状态
bloom_distribution: str
cognitive_state_distribution: str

# 时序数据
lei_timeline: str                 # JSON 数组: [{"minute":1, "lei":0.82}, ...]

# 教学建议
pedagogical_suggestions: str

# 注意力周期相位
attention_cycle_phase: str        # "peak" / "trough" / "rising" / "declining"
class_attention_trend: str        # "stable" / "declining" / "crisis"

# 参与人数
student_count: int
```

**`StudentBehaviorAlert`** — 基于 CV 的真实行为预警记录（替代 mock 数据）
```python
id: UUID (PK)
student_id: UUID (FK → student.id, 可选)
tc_id: UUID (FK → tc.id, 可选)
alert_time: datetime              # 预警时间
reason: str                       # 预警原因描述
severity: str                     # "low" / "medium" / "high"
alert_type: str                   # "individual_overload" / "group_contagion" / 
                                  # "attention_trough" / "cognitive_shallow" / "class_mind_wandering"

# 触发时的指标快照
trigger_lei: float
trigger_attention_deviation: float
trigger_contagion_index: float

# 处理状态
resolved: bool                    # 是否已处理
resolved_at: datetime             # 处理时间
```

---

## 四、CV 服务层（YOLOv8-Pose + 教育学 + 大模型复核）

### 4.1 技术栈

| 组件 | 技术 | 版本 | 用途 |
|------|------|------|------|
| 目标检测 | Ultralytics YOLOv8-Pose | ^8.x | 人体检测 + 17 关键点姿态估计 |
| 深度学习 | PyTorch | 2.6.0+cu124 | GPU 加速推理 |
| 大模型 | Qwen2.5-VL-3B-Instruct | - | 视觉-语言模型，复核行为分类 |
| 模型下载 | ModelScope | - | 国内镜像下载大模型 |
| 图像处理 | OpenCV + Pillow + NumPy | - | 图像预处理与可视化 |
| 运行环境 | conda `zy_yolo` | Python 3.11 | 独立环境 |

### 4.2 目录结构（`code/cv/code`）

```
cv/code/
├── yolo.py                     # ⭐主服务：YOLOv8-Pose + 行为分类 + API
├── educational_behavior.py     # ⭐教育学行为分析器（理论模型实现）
├── llm_classifier.py           # ⭐大模型行为分类器（Qwen2.5-VL 复核）
├── behavior_ws.py              # WebSocket 实时检测（后端调用，非独立服务）
├── download_model_ms.py        # ModelScope 模型下载脚本
├── demo_educational.py         # 教育学模块演示
└── quick_collect_and_train.py  # 数据收集与训练脚本
```

### 4.3 YOLO 服务主模块 (`yolo.py`)

#### API 端点

| 端点 | 方法 | 用途 |
|------|------|------|
| `GET /` | 服务状态 | 健康检查 |
| `GET /health` | 健康检查 | 模型加载状态 |
| `GET /behaviors` | 行为定义 | 返回 BEHAVIOR_LABELS |
| `POST /analyze/frame` | 单帧分析 | 分析单张图片，返回所有人检测框 + 行为 |
| `POST /analyze/video` | 视频分析 | 滑动窗口分析视频，返回时序行为 + 汇总 |
| `POST /analyze/stream` | 流式分析 | 接收关键点序列（34维），返回行为分类 |

#### 核心配置参数

```python
DETECTOR_CONF = 0.22        # 检测器置信度阈值（已修复硬编码问题）
POSE_CONF = 0.3             # 姿态估计置信度阈值
POSE_IMGSZ = 1280           # 姿态估计输入分辨率（已从 640 提升到 1280）
USE_DUAL_STAGE = False      # 双阶段模式（检测器→Pose，默认关闭）
USE_LLM_CLASSIFY = True     # 大模型复核（默认启用）
SEQUENCE_LENGTH = 16        # 时序分析窗口长度
```

#### 单帧分析流程 (`analyze_frame`)

```
输入: 单帧图像 (UploadFile)
  │
  ├── 1. 人体检测 + 姿态估计
  │      └─ extract_all_persons(frame)
  │         └─ pose_model(frame, imgsz=POSE_IMGSZ)  [YOLOv8-Pose 单阶段]
  │         └─ 若姿态失败，保留检测框，根据宽高比猜测行为
  │
  ├── 2. 大模型批量复核（可选）
  │      └─ llm_batch_classify(frame, persons)
  │         └─ crop 每个人像 → 拼成 n×n 大图 → Qwen2.5-VL 推理 → 解析 JSON
  │
  ├── 3. 规则分类（每人独立）
  │      └─ RuleBasedBehaviorClassifier.classify_single_frame(keypoints, bbox)
  │         ├─ check_phone_usage()      → 手腕靠近面部 + 低头
  │         ├─ check_sleeping()         → 头部低于肩部 / 后仰 / 眼睛不可见
  │         ├─ check_talking()          → 头部转向侧面（耳高差异）
  │         ├─ check_leaving()          → 关键点 < 8
  │         └─ default → 专注学习
  │
  ├── 4. 大模型覆盖（若与规则不同）
  │      └─ llm_results[person_id] → 覆盖 behavior_id
  │
  ├── 5. 教育学语义解码
  │      └─ EducationalBehaviorAnalyzer.decode_posture_education(keypoints, raw_behavior)
  │         ├─ head_pose: up/front/down/tilted/backward
  │         ├─ gaze_direction: forward/down_reading/down_sleeping/side/up
  │         ├─ body_lean: 躯干倾斜角度
  │         ├─ hand_position: resting/writing/raised/near_face/unknown
  │         ├─ bloom_level: REMEMBERING → CREATING
  │         └─ cognitive_state: DEEP_PROCESSING / MIND_WANDERING / ...
  │
  ├── 6. 教育学语义反向修正
  │      └─ 若规则分类为"专注"，但语义信号强烈：
  │         ├─ gaze_direction="down_sleeping" + hand="resting" → 修正为"睡觉"
  │         ├─ hand_position="near_face" + head_pose="down" → 修正为"查看手机"
  │         └─ gaze_direction="down_sleeping" + hand≠"writing" → 修正为"睡觉"
  │
  ├── 7. 置信度融合
  │      └─ fuse_confidence(detector_conf, behavior_conf, pose_quality, bbox_quality)
  │
  ├── 8. 时序平滑（TemporalBehaviorSmoother）
  │      └─ 滑动窗口投票，减少单帧抖动
  │
  └── 9. 课堂指标计算
         └─ calculate_classroom_metrics(analyzed_persons, edu_report)
            ├─ attention_score = 0.44*专注率 + 0.24*行为得分 + 0.16*平均置信度
            │                     + 0.16*时序稳定度 - 0.18*严重行为率 - 0.10*分心率
            └─ 附加 educational 子字典（BEI/CEI/EEI/LEI、布鲁姆分布、教学建议）

输出: JSON {status, persons[], overall_score, learning_status, classroom_metrics, ...}
```

#### 行为标签定义 (`BEHAVIOR_LABELS`)

| ID | 行为名称 | 得分 | 颜色 | 描述 |
|----|---------|------|------|------|
| 0 | 专注学习 | 0.85 | #10b981 | 正常学习姿态 |
| 1 | 查看手机 | 0.25 | #ef4444 | 手持手机，低头 |
| 2 | 离开座位 | 0.10 | #f97316 | 人体检测不完整 |
| 3 | 睡觉 | 0.15 | #8b5cf6 | 头部低垂或后仰 |
| 4 | 举手发言 | 0.75 | #f59e0b | 手臂举起 |
| 5 | 其他（默认） | 0.50 | #64748b | 无法判断 |

### 4.4 教育学行为分析器 (`educational_behavior.py`)

基于四大教育学理论的实现：

#### 理论模型

| 理论 | 实现 | 输出指标 |
|------|------|---------|
| **Fredricks 三维学习投入模型** | 行为/认知/情感三维评估 | BEI / CEI / EEI / LEI |
| **Bloom 认知分类法（修订版）** | 根据手部位置 + 头部姿态映射 | 布鲁姆层次分布 |
| **持续性注意力动态模型** | 15-20 分钟周期性波动 | 注意力周期相位、偏离度 |
| **社会传染理论** | 分心行为空间聚集性分析 | 传染指数、聚集区域 |

#### 核心类

```python
class BehavioralEvent          # 单帧行为事件（姿态语义）
class StudentEngagementProfile # 学生时序画像（累积 BEI/CEI/EEI/LEI）
class ClassroomEngagementReport# 课堂群体报告
class EducationalBehaviorAnalyzer:
    - decode_posture_education(keypoints, raw_behavior) → BehavioralEvent
    - update_student_profile(track_id, event)          → 更新时序画像
    - generate_classroom_report()                      → 群体聚合报告
    - _calculate_contagion_index()                     → 社会传染指数
    - _generate_pedagogical_suggestions()              → 教学建议
```

#### 关键指标计算

```python
# 学习投入指数（Learning Engagement Index）
LEI = 0.35 * BEI + 0.40 * CEI + 0.25 * EEI

# 注意力偏离度 = 当前 LEI - 个人注意力基线
# 异常下降标记：连续 3 帧偏离度 < -0.2

# 社会传染指数 = 分心人员空间聚类的平均密度
# 高传染 → 提示教学节奏或知识点难度问题
```

### 4.5 大模型行为分类器 (`llm_classifier.py`)

```python
# 模型：Qwen2.5-VL-3B-Instruct（约 7GB，通过 ModelScope 国内镜像下载）
# 加载路径：优先从 model_path.txt 读取本地路径，否则 fallback 到 HuggingFace 在线

llm_batch_classify(frame, persons):
    1. crop 每个人像区域（根据 bbox + padding）
    2. padding 到统一尺寸 (target_w=220, target_h=280)
    3. 拼成 n×n 大图（默认 3×2，最多 6 人）
    4. 构造 Prompt：
       "请观察图中每个学生，判断其行为：
        0=专注学习, 1=查看手机, 2=离开座位, 3=睡觉, 4=举手发言, 5=其他
        输出 JSON: {'0': '专注学习', '1': '查看手机', ...}"
    5. 调用 Qwen2.5-VL 推理
    6. 解析 JSON 输出 → {person_id: (behavior_id, reason)}
```

> **设计意图**：大模型负责"看"人像理解语义（高语义理解），YOLO 负责"定位"人体（高精度检测），两者互补解决教室场景下睡觉/玩手机的漏检问题。

---

## 五、两条独立检测路径

### 5.1 路径对比

| 维度 | 路径 A：WebSocket 实时流 | 路径 B：HTTP 上传分析 |
|------|------------------------|---------------------|
| **入口** | 前端监控面板 WebSocket | 前端上传图片/视频 |
| **传输** | WebSocket 二进制帧 | HTTP POST multipart |
| **CV 模型** | MediaPipe FaceDetector + FaceLandmarker | YOLOv8-Pose |
| **检测范围** | 人脸（面部关键点 + blendshapes） | 全身姿态（17 个 COCO 关键点） |
| **行为分类** | 基于面部姿态的几何规则 | 基于全身姿态的几何规则 + 大模型复核 |
| **教育学参数** | 头部姿态推导 LEI/布鲁姆 | 全身姿态解码 + 时序累积画像 |
| **大模型** | ❌ 无 | ✅ Qwen2.5-VL 批量复核 |
| **适用场景** | 实时监控、低延迟 | 课后分析、高精度 |
| **后端服务** | `behavior_ws.py` | `behavior_analysis.py` → YOLO 服务 |

### 5.2 数据流向

#### 路径 A：WebSocket 实时流
```
前端摄像头 → base64 编码 → WebSocket → 后端 behavior_ws.py
  → MediaPipe 人脸检测 → 面部关键点 → 头部姿态估计
  → 几何规则分类（focused/unfocused/absent）
  → 教育学参数推导（LEI/布鲁姆/认知状态）
  → AnalysisMessage → WebSocket 回传前端
  → 前端 Canvas 绘制 + HUD 图表更新
```

#### 路径 B：HTTP 上传分析
```
前端上传图片/视频 → HTTP POST → 后端 behavior_analysis.py
  → 转发至 YOLO 服务 (port 8001)
  → YOLOv8-Pose 检测 + 姿态估计
  → 大模型批量复核（Qwen2.5-VL）
  → 规则分类 + 教育学语义解码 + 反向修正
  → 时序平滑 + 课堂指标计算
  → 返回 JSON（persons + classroom_metrics + educational_report）
  → 后端 _cache_educational_data() + _persist_behavior_summary()
  → 前端 Canvas 绘制 + 课堂报告面板
```

---

## 六、数据联动闭环

### 6.1 七重联动

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         数据联动闭环（七重联动）                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   联动1: CV检测 → 学情诊断                                                    │
│   ┌─────────┐    BehaviorSummaryRecord    ┌─────────────┐                   │
│   │ YOLO服务 │ ──────────────────────────→ │ 学情诊断服务  │                   │
│   └─────────┘    (LEI/走神率/布鲁姆)        │ (大模型Prompt)│                   │
│                                             └─────────────┘                   │
│                                                                             │
│   联动2: CV检测 → 复习计划                                                    │
│   ┌─────────┐    注意力低谷时段标记          ┌─────────────┐                   │
│   │ YOLO服务 │ ──────────────────────────→ │ 复习计划生成  │                   │
│   └─────────┘    (走神时段 → 薄弱知识点归因)  │ (优先级调整)  │                   │
│                                             └─────────────┘                   │
│                                                                             │
│   联动3: CV检测 → 实时预警                                                    │
│   ┌─────────┐    educational_report         ┌─────────────┐                   │
│   │ YOLO服务 │ ──────────────────────────→ │ 预警规则引擎  │                   │
│   └─────────┘    (传染指数/注意力相位)        │ (4类规则评估) │                   │
│                                             └─────────────┘                   │
│                                                                             │
│   联动4: CV检测 → 学习画像                                                    │
│   ┌─────────┐    engagement_profile         ┌─────────────┐                   │
│   │ YOLO服务 │ ──────────────────────────→ │ 用户记忆画像  │                   │
│   └─────────┘    (BEI/CEI/EEI时序累积)       │ (长期追踪)    │                   │
│                                             └─────────────┘                   │
│                                                                             │
│   联动5: CV检测 → 错题归因                                                    │
│   ┌─────────┐    走神时段与错题时间关联       ┌─────────────┐                   │
│   │ YOLO服务 │ ──────────────────────────→ │ 错题整理服务  │                   │
│   └─────────┘                               │ (注意力归因)  │                   │
│                                             └─────────────┘                   │
│                                                                             │
│   联动6: CV检测 → 课程质量评估                                                │
│   ┌─────────┐    CourseEngagementRecord     ┌─────────────┐                   │
│   │ YOLO服务 │ ──────────────────────────→ │ 教师仪表盘    │                   │
│   └─────────┘    (课程级 LEI 趋势)           │ (数据可视化)  │                   │
│                                             └─────────────┘                   │
│                                                                             │
│   联动7: CV检测 → 学生端展示                                                  │
│   ┌─────────┐    classroom_behavior_summary  ┌─────────────┐                   │
│   │ YOLO服务 │ ──────────────────────────→ │ 我的学情页面  │                   │
│   └─────────┘    (LEI/走神率/教师备注)        │ (课堂行为卡片)│                   │
│                                             └─────────────┘                   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 6.2 持久化时序

```
YOLO 分析完成
    │
    ├── 1. _cache_educational_data(result)
    │      └─ 缓存 educational_report + engagement_profile（供预警引擎消费）
    │
    └── 2. _persist_behavior_summary(result, course_id, tc_id)
           └─ 后台线程执行：
              ├─ CourseEngagementRecord 写入（课程级指标）
              └─ BehaviorSummaryRecord 写入（课堂行为摘要）
                  └─ student_id = NULL（当前无身份识别，存储课堂整体数据）
```

---

## 七、服务启动与运行

### 7.1 启动顺序

```bash
# 1. 启动 YOLO 服务（conda 环境 zy_yolo）
conda activate zy_yolo
cd code/cv/code
python yolo.py
# → 监听 http://127.0.0.1:8001

# 2. 启动后端服务
cd code/backend
uvicorn app.main:app --reload --port 8000
# → 监听 http://127.0.0.1:8000

# 3. 启动前端开发服务器
cd code/education/course
npm run dev
# → 监听 http://localhost:5173
```

### 7.2 环境配置

**YOLO 服务环境变量**（`code/cv/code/.env`）
```bash
DETECTOR_CONF=0.22
POSE_CONF=0.3
POSE_IMGSZ=1280
USE_DUAL_STAGE=false
USE_LLM_CLASSIFY=true
LLM_MODEL_PATH=/path/to/local/model   # 自动从 model_path.txt 读取
```

**后端环境变量**（`code/backend/.env`）
```bash
DATABASE_URL=sqlite:///zhixi.db
OPENAI_API_KEY=sk-...
```

---

## 八、关键技术决策与权衡

### 8.1 为什么用两条独立检测路径？

| 考量 | WebSocket 实时 | HTTP 上传 |
|------|---------------|-----------|
| **延迟要求** | < 200ms，不能传大图 | 可接受 1-3s |
| **带宽** | 每帧 base64 传输，需压缩 | 一次上传完整图片/视频 |
| **模型选择** | MediaPipe 轻量人脸检测（~10MB） | YOLOv8-Pose（~50MB）+ Qwen2.5-VL（7GB） |
| **检测粒度** | 人脸级别（focused/unfocused） | 全身级别（6 类行为 + 教育学参数） |
| **硬件需求** | CPU 即可运行 | 需 GPU（RTX 4060 8GB） |

### 8.2 为什么用大模型复核？

- **YOLO-Pose 的局限**：几何规则对"低头看手机 vs 低头写字"、"趴桌睡觉 vs 趴桌休息"难以区分
- **大模型的优势**：Qwen2.5-VL 具有视觉语义理解能力，能看人像 crop 判断真实行为
- **成本权衡**：3B 参数量在 RTX 4060 上推理约 1-2s/批次， classrooms ≤ 6 人场景可接受
- **Fallback 机制**：模型加载失败自动回退到规则分类，不影响主流程

### 8.3 为什么单阶段模式默认？

- **双阶段问题**：检测器 crop → 再 Pose，会过滤掉教室后排小目标（检测器 conf 0.22 但仍可能漏）
- **单阶段优势**：YOLOv8-Pose 直接全图推理，imgsz=1280 保证后排人员也能被检测
- **精度权衡**：单阶段可能引入更多 false positive，但通过姿态质量评分和时序平滑过滤

### 8.4 为什么用 SQLite？

- 开发阶段快速迭代，无需配置 PostgreSQL/MySQL
- 单文件数据库，易于备份和迁移
- 生产环境可无缝迁移到 PostgreSQL（SQLModel 兼容）

---

## 九、已知问题与待办

### 当前活跃问题

| 问题 | 影响 | 状态 |
|------|------|------|
| 前端 TypeScript 类型错误（`$t` 未定义、模块找不到） | Vite HMR 可能失效，不影响运行 | 待修复 |
| YOLO 服务无学生身份识别 | BehaviorSummaryRecord.student_id 始终为 NULL | 设计如此（当前聚焦行为检测） |
| 大模型首次加载慢 | 启动后首次推理需 5-10s 加载模型 | 可接受（延迟加载） |

### 后续优化方向

1. **学生身份绑定**：结合人脸识别或学号输入，实现个人级行为追踪
2. **多摄像头支持**：教室前后双摄，扩大覆盖范围
3. **边缘部署**：将 YOLO 推理迁移到边缘设备（Jetson/Jetson Orin）
4. **增量学习**：收集教师标注反馈，微调行为分类器
5. **大模型量化**：INT4/INT8 量化 Qwen2.5-VL，降低显存占用

---

## 十、快速索引

### 关键文件速查

| 功能 | 文件路径 |
|------|---------|
| YOLO 服务主程序 | `code/cv/code/yolo.py` |
| 教育学行为分析器 | `code/cv/code/educational_behavior.py` |
| 大模型分类器 | `code/cv/code/llm_classifier.py` |
| 后端行为分析服务 | `code/backend/app/services/behavior_analysis.py` |
| WebSocket 实时检测 | `code/backend/app/services/behavior_ws.py` |
| 预警规则引擎 | `code/backend/app/services/alert_rule_engine.py` |
| 学情诊断服务 | `code/backend/app/services/learning_report_service.py` |
| 前端行为检测面板 | `code/education/course/src/views/course/monitor/components/behavior-detection-panel.vue` |
| 前端学情页面 | `code/education/course/src/views/profile/learning-data/index.vue` |
| 后端 API 路由 | `code/backend/app/api/routes/behavior_analysis.py` |
| 数据库模型 | `code/backend/app/models.py` |

