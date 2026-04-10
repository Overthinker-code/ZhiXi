# 课堂行为分析功能说明

本文档介绍项目的课堂行为分析功能。

> 🚨 **当前版本：规则-Based（立即可用，无需训练）**
> 
> 基于YOLOv8-Pose提取关键点，使用**几何规则**判断行为：
> - 看手机：手腕靠近面部 + 低头
> - 睡觉：头部低于肩部或后仰  
> - 交谈：头部转向侧面
> - 离开：人体检测不完整
> - 专注：默认正常姿态
>
> **准确率：约60-75%，适合演示和比赛应急使用！**

---

## 🚀 快速开始（3分钟启动）

### 1. 安装依赖
```bash
pip install ultralytics opencv-python fastapi uvicorn pillow numpy
```

### 2. 启动服务（无需任何训练数据！）
```bash
uvicorn yolo:app --host 0.0.0.0 --port 8000
```

**看到以下输出表示成功：**
```
🚀 启动课堂行为检测服务 - 规则-Based版本
✅ 无需训练数据，无需LSTM权重，立即可用！
📊 准确率: 约60-75%（适合演示和比赛应急）
```

### 3. 测试
```bash
curl http://localhost:8000/health
curl http://localhost:8000/behaviors
```

**完成！无需下载数据集，无需训练模型，立即可用！**

---

## 📋 技术方案

### 为什么选择 YOLOv8-Pose + LSTM？

| 方案 | 准确率 | 速度 | 实时性 | 适用性 |
|------|--------|------|--------|--------|
| YOLOv8 (纯检测) | ⭐⭐ | ⚡⚡⚡ | ✅ | 只能定位，无法识别行为 |
| YOLOv8-Pose + 规则 | ⭐⭐⭐ | ⚡⚡⚡ | ✅ | 简单行为可以，复杂行为不准 |
| **YOLOv8-Pose + LSTM** | ⭐⭐⭐⭐ | ⚡⚡ | ✅ | **推荐**：时序建模，理解动作过程 |
| ST-GCN | ⭐⭐⭐⭐⭐ | ⚡⚡ | ✅ | 准确率高，但训练复杂 |
| Transformer (Video) | ⭐⭐⭐⭐⭐ | ⚡ | ❌ | 太慢，不适合实时课堂 |

### 方案架构

```
视频流/文件
    ↓
┌─────────────────────────────────────┐
│  Step 1: YOLOv8-Pose 姿态估计        │
│  - 检测人体位置                       │
│  - 提取17个关键点 (眼睛、肩膀、手等)   │
│  - 输出: (x1,y1), (x2,y2), ..., (x17,y17) │
└─────────────────────────────────────┘
    ↓ 连续16帧
┌─────────────────────────────────────┐
│  Step 2: LSTM 时序建模               │
│  - 输入: 16帧 × 34维 (17点×2坐标)     │
│  - 双向LSTM学习动作时序特征            │
│  - 输出: 5类行为概率                  │
└─────────────────────────────────────┘
    ↓
行为识别结果 (专注学习/查看手机/睡觉等)
```

### 行为类别

| ID | 行为 | 得分 | 说明 | 判断依据 |
|----|------|------|------|----------|
| 0 | 专注学习 | +1.0 | 学习状态良好 | 头部朝向屏幕/书本，手部在桌面 |
| 1 | 查看手机 | -0.5 | 注意力分散 | 手部抬起靠近面部，低头 |
| 2 | 与他人交谈 | -0.3 | 可能影响他人 | 头部转向侧面，嘴部活动 |
| 3 | 睡觉 | -1.0 | 未在学习 | 头部长时间低下或后仰，静止 |
| 4 | 离开座位 | -0.8 | 未在学习区域 | 人体不在检测框内或位置异常 |

---

## 📁 文件结构

### 姿态估计与行为识别服务

| 文件路径 | 说明 |
|---------|------|
| `yolo.py` | **YOLOv8-Pose + LSTM 服务入口** |

**yolo.py 核心组件：**
- `pose_model`: YOLOv8-Pose 模型（提取17个关键点）
- `BehaviorLSTM`: 双向LSTM网络（时序行为识别）
- 关键参数：
  - `SEQUENCE_LENGTH=16`: 16帧为一个分析窗口（约0.5秒@30fps）
  - `INPUT_SIZE=34`: 17个关键点 × 2坐标(x,y)
  - `HIDDEN_SIZE=128`: LSTM隐藏层大小

### 后端文件

| 文件路径 | 说明 |
|---------|------|
| `backend/app/api/routes/behavior_analysis.py` | 行为分析 REST API 路由 |
| `backend/app/services/behavior_analysis.py` | 行为分析服务（调用YOLO服务） |
| `backend/app/api/main.py` | API 路由注册 |
| `backend/app/core/config.py` | 配置文件 |

### 训练相关文件

| 文件路径 | 说明 |
|---------|------|
| `prepare_sav_dataset.py` | **SAV数据集预处理脚本** - 从视频提取姿态序列 |
| `train_sav_lstm.py` | **LSTM训练脚本** - 使用SAV数据训练行为识别模型 |

### 前端文件

| 文件路径 | 说明 |
|---------|------|
| `education/course/src/api/behavior-analysis.ts` | 前端 API 调用接口 |
| `education/course/src/views/course/monitor/components/behavior-detection-panel.vue` | 行为检测面板组件 |

---

## 🚀 快速开始：使用SAV数据集训练模型

### 数据集放置位置

```
项目根目录/
├── SAV/                          # SAV数据集目录（下载后放在这里）
│   ├── videos/                   # 原始视频文件
│   ├── frame_list/
│   │   ├── train.csv            # 训练集视频列表
│   │   └── val.csv              # 验证集视频列表
│   └── annotations/
│       ├── train.csv            # 训练集标注
│       └── val.csv              # 验证集标注
├── sav_pose_data/               # 预处理后的姿态数据（自动生成）
│   ├── train.pkl
│   └── val.pkl
├── prepare_sav_dataset.py       # 预处理脚本
├── train_sav_lstm.py           # 训练脚本
└── behavior_lstm.pth           # 训练好的模型（训练后生成）
```

### 第一步：下载SAV数据集

1. **访问 SAV 项目主页**: https://github.com/Ritatanz/SAV
2. **按照README指引下载数据**:
   - 下载视频文件（通过提供的链接列表）
   - 下载标注文件
   - 下载训练/验证列表
3. **将数据放在 `./SAV/` 目录下**

### 第二步：预处理（提取姿态序列）

```bash
# 安装依赖
pip install ultralytics torch pandas pickle-mixin

# 运行预处理脚本
python prepare_sav_dataset.py \
    --sav_path ./SAV \
    --output ./sav_pose_data \
    --seq_length 16 \
    --model yolov8n-pose.pt
```

**参数说明：**
- `--sav_path`: SAV数据集路径
- `--output`: 输出目录（将生成 train.pkl 和 val.pkl）
- `--seq_length`: 序列长度，默认16帧（约0.5秒）
- `--model`: YOLOv8-Pose模型，可选 yolov8n/s/m-pose

**处理时间：** 取决于视频数量和GPU，通常需要 **1-3小时**

**输出文件：**
```
sav_pose_data/
├── train.pkl    # 训练集姿态序列
└── val.pkl      # 验证集姿态序列
```

### 第三步：训练LSTM模型

```bash
# 开始训练
python train_sav_lstm.py \
    --data_dir ./sav_pose_data \
    --output_dir ./sav_lstm_output \
    --epochs 100 \
    --batch_size 64 \
    --lr 0.001 \
    --hidden_size 128
```

**参数说明：**
- `--epochs`: 训练轮数（默认100）
- `--batch_size`: 批次大小（根据GPU内存调整）
- `--hidden_size`: LSTM隐藏层大小（默认128，可选256）
- `--lr`: 学习率（默认0.001）

**训练过程：**
- 每10轮打印验证准确率
- 自动保存最佳模型
- 支持早停（20轮不提升自动停止）
- 自动生成训练曲线和混淆矩阵

**训练完成后，你会得到：**
```
sav_lstm_output/
├── best_model.pth           # 最佳模型（带训练状态）
├── behavior_lstm.pth        # 部署用模型（yolo.py加载）
├── model_config.json        # 模型配置
├── training_history.png     # 训练曲线
└── confusion_matrix.png     # 混淆矩阵
```

### 第四步：部署模型

```bash
# 将训练好的模型复制到项目根目录
cp sav_lstm_output/behavior_lstm.pth ./behavior_lstm.pth

# 启动YOLO服务
uvicorn yolo:app --host 0.0.0.0 --port 8000
```

**看到以下输出表示成功：**
```
✅ LSTM 权重加载成功: behavior_lstm.pth
   模型已就绪，可以进行行为识别
```

---

## 🔌 API 接口

### YOLO 服务接口 (端口8000)

#### 1. 分析单帧姿态
```http
POST /analyze/frame
Content-Type: multipart/form-data

file: <图片文件>
```

**响应示例：**
```json
{
  "status": "success",
  "keypoints": [
    [0.5, 0.3],   // nose
    [0.48, 0.28], // left_eye
    [0.52, 0.28], // right_eye
    // ... 共17个点
  ],
  "keypoint_names": ["nose", "left_eye", "right_eye", ...]
}
```

#### 2. 分析视频行为
```http
POST /analyze/video
Content-Type: multipart/form-data

file: <视频文件>
sample_interval: 1  // 采样间隔，默认每1帧
```

**响应示例：**
```json
{
  "status": "success",
  "overall_behavior": "专注学习",
  "overall_score": 0.85,
  "learning_status": "学习状态优秀",
  "predictions": [
    {
      "class_id": 0,
      "behavior": "专注学习",
      "confidence": 0.92,
      "score": 1.0,
      "timestamp": 2.5,
      "frame_range": [0, 16]
    },
    {
      "class_id": 1,
      "behavior": "查看手机",
      "confidence": 0.88,
      "score": -0.5,
      "timestamp": 5.0,
      "frame_range": [8, 24]
    }
  ],
  "video_info": {
    "total_frames": 1800,
    "valid_frames": 1500,
    "fps": 30,
    "duration": 60.0,
    "analysis_windows": 94
  }
}
```

#### 3. 分析连续帧序列（实时流）
```http
POST /analyze/stream
Content-Type: application/json

{
  "frames": [
    [x1, y1, x2, y2, ..., x17, y17],  // 第1帧，34个值
    [x1, y1, x2, y2, ..., x17, y17],  // 第2帧
    ...
    [x1, y1, x2, y2, ..., x17, y17]   // 第16帧
  ]
}
```

**响应示例：**
```json
{
  "status": "success",
  "class_id": 0,
  "behavior": "专注学习",
  "confidence": 0.89,
  "score": 1.0,
  "description": "学习状态良好",
  "color": "#52c41a",
  "all_probabilities": {
    "专注学习": 0.89,
    "查看手机": 0.05,
    "与他人交谈": 0.03,
    "睡觉": 0.02,
    "离开座位": 0.01
  }
}
```

#### 4. 获取行为定义
```http
GET /behaviors
```

#### 5. 健康检查
```http
GET /health
```

### 后端 API 接口 (端口8001)

后端接口与之前保持一致，详见 `backend/app/api/routes/behavior_analysis.py`。

---

## 🚀 启动方法

### 1. 安装依赖

```bash
# 安装 YOLOv8 和 PyTorch
pip install ultralytics torch torchvision

# 如果需要 GPU 支持
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118
```

### 2. 启动 YOLOv8-Pose + LSTM 服务

```bash
# 进入项目目录
cd ZhiXi

# 方式1：使用默认配置（CPU）
uvicorn yolo:app --host 0.0.0.0 --port 8000

# 方式2：指定模型和参数
YOLO_MODEL_PATH=yolov8s-pose.pt LSTM_HIDDEN_SIZE=256 uvicorn yolo:app --host 0.0.0.0 --port 8000

# 方式3：使用 GPU（如果可用）
CUDA_VISIBLE_DEVICES=0 uvicorn yolo:app --host 0.0.0.0 --port 8000
```

**验证服务：**
```bash
curl http://localhost:8000/health
```

### 3. 配置后端

在 `.env` 文件中添加：

```env
# YOLO 姿态估计服务配置
YOLO_SERVICE_HOST=http://localhost
YOLO_SERVICE_PORT=8000
YOLO_MODEL_PATH=yolov8n-pose.pt

# LSTM 配置（可选，yolo服务使用）
LSTM_HIDDEN_SIZE=128
LSTM_NUM_LAYERS=2
SEQUENCE_LENGTH=16
```

### 4. 启动后端服务

```bash
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8001
```

### 5. 启动前端

```bash
cd education/course
npm run dev
```

---

## ⚙️ 配置说明

### 环境变量

| 变量名 | 说明 | 默认值 |
|-------|------|--------|
| `YOLO_MODEL_PATH` | YOLOv8-Pose 模型文件 | `yolov8n-pose.pt` |
| `LSTM_WEIGHTS_PATH` | LSTM 预训练权重 | `behavior_lstm.pth` |
| `LSTM_HIDDEN_SIZE` | LSTM 隐藏层大小 | `128` |
| `LSTM_NUM_LAYERS` | LSTM 层数 | `2` |
| `SEQUENCE_LENGTH` | 分析窗口帧数 | `16` |
| `YOLO_SERVICE_HOST` | YOLO 服务地址 | `http://localhost` |
| `YOLO_SERVICE_PORT` | YOLO 服务端口 | `8000` |

### 模型选择建议

| 模型 | 大小 | 速度 | 精度 | 适用场景 |
|------|------|------|------|----------|
| `yolov8n-pose.pt` | 6MB | ⚡⚡⚡ 最快 | ⭐⭐⭐ | **推荐**：边缘设备、实时检测 |
| `yolov8s-pose.pt` | 23MB | ⚡⚡ 快 | ⭐⭐⭐⭐ | 服务器部署 |
| `yolov8m-pose.pt` | 68MB | ⚡ 中等 | ⭐⭐⭐⭐⭐ | 高精度需求 |

下载命令：
```python
from ultralytics import YOLO

# 首次使用会自动下载
model = YOLO("yolov8n-pose.pt")
```

---

## 📝 使用说明

### 关键点说明

YOLOv8-Pose 检测17个关键点（COCO格式）：

```
0: 鼻子 (nose)
1: 左眼 (left_eye)      2: 右眼 (right_eye)
3: 左耳 (left_ear)      4: 右耳 (right_ear)
5: 左肩 (left_shoulder) 6: 右肩 (right_shoulder)
7: 左肘 (left_elbow)    8: 右肘 (right_elbow)
9: 左手腕 (left_wrist)  10: 右手腕 (right_wrist)
11: 左髋 (left_hip)     12: 右髋 (right_hip)
13: 左膝 (left_knee)    14: 右膝 (right_knee)
15: 左踝 (left_ankle)   16: 右踝 (right_ankle)
```

**关键判断依据：**
- **看手机**：右手腕/左手腕关键点靠近鼻子，头部低下
- **睡觉**：鼻子关键点长时间低于肩膀关键点
- **交谈**：头部转向（左右耳与肩膀的相对位置变化）
- **专注学习**：头部正对前方，手部在桌面区域

---

## 🔧 训练自己的 LSTM 模型（可选）

> 💡 **推荐使用SAV数据集**（详见上面的"🚀 快速开始"），如要使用自己的数据，参考以下流程。

### 1. 准备数据集

收集并标注课堂行为视频数据：

```
dataset/
├── focused/          # 专注学习
│   ├── video1.mp4
│   ├── video2.mp4
│   └── ...
├── phone/            # 查看手机
├── talking/          # 与他人交谈
├── sleeping/         # 睡觉
└── away/             # 离开座位
```

### 2. 数据预处理

```python
from ultralytics import YOLO
import cv2
import numpy as np

pose_model = YOLO("yolov8n-pose.pt")

def extract_sequence(video_path, seq_length=16):
    """从视频提取姿态序列"""
    cap = cv2.VideoCapture(video_path)
    frames = []
    
    while len(frames) < seq_length:
        ret, frame = cap.read()
        if not ret:
            break
        
        # 姿态估计
        results = pose_model(frame)
        if results[0].keypoints is not None:
            keypoints = results[0].keypoints.xy[0].flatten()  # (34,)
            frames.append(keypoints)
    
    cap.release()
    return np.array(frames) if len(frames) == seq_length else None
```

### 3. 训练 LSTM

```python
import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader

class BehaviorDataset(Dataset):
    def __init__(self, sequences, labels):
        self.sequences = sequences  # (N, 16, 34)
        self.labels = labels        # (N,)
    
    def __len__(self):
        return len(self.sequences)
    
    def __getitem__(self, idx):
        return torch.FloatTensor(self.sequences[idx]), torch.LongTensor([self.labels[idx]])

# 训练
model = BehaviorLSTM(input_size=34, hidden_size=128, num_classes=5)
criterion = nn.CrossEntropyLoss()
optimizer = torch.optim.Adam(model.parameters(), lr=0.001)

for epoch in range(100):
    for batch_seq, batch_label in dataloader:
        optimizer.zero_grad()
        output = model(batch_seq)
        loss = criterion(output, batch_label.squeeze())
        loss.backward()
        optimizer.step()
    
    if epoch % 10 == 0:
        torch.save(model.state_dict(), f"behavior_lstm_epoch{epoch}.pth")
```

### 4. 部署模型

将训练好的权重保存为 `behavior_lstm.pth`，放在 `yolo.py` 同级目录，服务启动时会自动加载。

---

## ⚠️ 注意事项

### 1. 模型权重问题

**首次使用时的警告：**
```
⚠️ LSTM 权重加载失败: ...，使用随机初始化
警告: 随机初始化的模型预测结果无意义，需要训练后使用
```

**解决方法（按推荐顺序）：**
- 方案A：使用SAV数据集训练（推荐，详见"🚀 快速开始"）
- 方案B：使用自己的数据训练
- 方案B：使用规则-based 分类作为临时方案
- 方案C：联系我们获取预训练权重

### 2. 姿态检测失败

如果视频中检测不到人体，可能原因：
- 学生离摄像头太远
- 光照不足
- 严重遮挡

建议：调整摄像头角度和位置，确保能清晰看到学生上半身。

### 3. 序列长度

`SEQUENCE_LENGTH=16` 意味着需要连续16帧（约0.5秒@30fps）都有姿态检测结果才能进行行为识别。

如果学生短暂离开画面，会导致序列中断。建议：
- 降低 `SEQUENCE_LENGTH` 到 8（精度会下降）
- 使用滑动窗口缓存最近的有效帧

### 4. 多人场景

当前实现默认只处理检测到的第一个人（通常是面积最大的）。如果需要同时检测多人：
- 修改 `extract_pose_keypoints` 函数返回所有人的关键点
- 为每个人维护独立的 LSTM 序列
- 后端支持多人并发分析

---

## 🐛 故障排查

### YOLO 服务无法启动

```bash
# 检查依赖
pip list | grep ultralytics

# 检查模型下载
python -c "from ultralytics import YOLO; YOLO('yolov8n-pose.pt')"

# 查看详细错误
uvicorn yolo:app --log-level debug
```

### LSTM 预测结果随机

```bash
# 检查权重文件是否存在
ls -la behavior_lstm.pth

# 检查权重加载日志
# 应该看到: ✅ LSTM 权重加载成功: behavior_lstm.pth
# 如果看到: ⚠️ LSTM 权重加载失败，需要训练模型
```

### 后端无法连接 YOLO 服务

```bash
# 检查 YOLO 服务是否运行
curl http://localhost:8000/health

# 检查后端配置
grep -n "YOLO" backend/app/core/config.py
```

---

## 📚 相关文档

- [YOLOv8 Pose 官方文档](https://docs.ultralytics.com/tasks/pose/)
- [PyTorch LSTM 文档](https://pytorch.org/docs/stable/generated/torch.nn.LSTM.html)
- [COCO Keypoints 格式](https://cocodataset.org/#format-data)

---

## 📝 更新日志

### 2024-04-10 - v2.0 重大更新
- ✅ 重构为 YOLOv8-Pose + LSTM 方案
- ✅ 添加时序行为识别能力
- ✅ 支持视频片段分析
- ✅ 支持实时流分析
- ✅ 添加滑动窗口视频分析

### 2024-04-10 - v1.0
- ✅ 初始版本：YOLO 目标检测 + 简单分类

---

如有问题，请联系开发团队。
