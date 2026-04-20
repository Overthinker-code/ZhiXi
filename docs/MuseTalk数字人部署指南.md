# 智屿数字人部署指南（Edge-TTS + MuseTalk + Celery）

## 1. 目标架构

我们保留现有项目主链路：

- FastAPI 负责接收前端请求并返回 `task_id`
- Celery 负责异步排队和执行重任务
- Redis 负责队列和结果存储
- Edge-TTS 负责文本转语音
- MuseTalk 负责嘴型驱动与视频生成

这样前端接口和现有的轮询逻辑都不用推翻，仍然可以保持“提交任务 -> 轮询状态 -> 返回视频地址”的闭环。

## 2. 当前仓库已完成的适配

仓库已经完成以下改造：

- 数字人引擎改为可配置：`DIGITAL_HUMAN_ENGINE=musetalk|wav2lip`
- 默认主引擎切到 `musetalk`
- Celery 任务会先调用 `edge-tts` 生成音频，再调用 MuseTalk 推理
- 支持单独配置 MuseTalk 的 Conda 环境、Python、模型路径、模板配置
- 保留 Wav2Lip 作为回退方案，便于过渡期兜底
- 仍然可以通过现有的 `python run_backend_stack.py` 维持单命令启动主后端和 Celery

## 3. 服务器目录准备

以下目录建议保持和当前项目一致：

```bash
cd ~/workspace/ZhiXI/code/backend
mkdir -p digital_human_assets
mkdir -p digital_human_inputs
mkdir -p digital_human_outputs
mkdir -p digital_human_outputs/musetalk_runs
```

说明：

- `digital_human_assets/` 放老师头像图和待机视频
- `digital_human_inputs/` 放上传的 PPT/PDF 等中间文件
- `digital_human_outputs/` 放最终生成的视频
- `digital_human_outputs/musetalk_runs/` 放 MuseTalk 每次任务的中间结果，便于排错

## 4. 部署 MuseTalk 项目本体

### 4.1 创建独立 Conda 环境

```bash
conda create -n MuseTalk python=3.10 -y
conda activate MuseTalk
```

### 4.2 安装 PyTorch

按 MuseTalk README 推荐，优先使用 CUDA 11.8 对应版本：

```bash
pip install torch==2.0.1 torchvision==0.15.2 torchaudio==2.0.2 --index-url https://download.pytorch.org/whl/cu118
```

### 4.3 获取 MuseTalk 源码

如果服务器直接 `git clone` 失败，不要卡在这里，直接用上传方案：

#### 方案 A：本地下载 ZIP 后上传到服务器

1. 在本地电脑打开 `https://github.com/TMElyralab/MuseTalk`
2. 点击 `Code -> Download ZIP`
3. 解压后得到 `MuseTalk/`
4. 用你现在的远程开发工具或 SFTP，把整个 `MuseTalk/` 上传到：

```text
~/workspace/ZhiXI/code/backend/MuseTalk
```

#### 方案 B：本地先 git clone，再上传目录

```bash
git clone https://github.com/TMElyralab/MuseTalk.git
```

然后把本地的 `MuseTalk/` 整个传到服务器同样的位置。

上传完成后，服务器上应能看到：

```bash
ls ~/workspace/ZhiXI/code/backend/MuseTalk
```

至少应包含：

- `configs/`
- `scripts/`
- `models/`（如果你后面已经放好权重）
- `requirements.txt`

### 4.4 安装 MuseTalk 依赖

```bash
cd ~/workspace/ZhiXI/code/backend/MuseTalk
pip install -r requirements.txt
pip install --no-cache-dir -U openmim
mim install mmengine
mim install "mmcv==2.0.1"
mim install "mmdet==3.1.0"
mim install "mmpose==1.1.0"
```

### 4.5 安装 FFmpeg

```bash
sudo apt-get update
sudo apt-get install -y ffmpeg
ffmpeg -version
```

如果 `ffmpeg -version` 有输出，就说明这一步正常。

## 5. 下载并摆放权重

你必须把 MuseTalk README 里提到的权重全部放到 `models/` 下，尤其是：

- `models/musetalkV15/unet.pth`
- `models/musetalkV15/musetalk.json`
- `models/sd-vae/*`
- `models/whisper/*`
- `models/dwpose/*`
- `models/syncnet/*`
- `models/face-parse-bisent/*`

推荐最终目录结构如下：

```text
~/workspace/ZhiXI/code/backend/MuseTalk/models/
├── musetalkV15
│   ├── musetalk.json
│   └── unet.pth
├── syncnet
│   └── latentsync_syncnet.pt
├── dwpose
│   └── dw-ll_ucoco_384.pth
├── face-parse-bisent
│   ├── 79999_iter.pth
│   └── resnet18-5c106cde.pth
├── sd-vae
│   ├── config.json
│   └── diffusion_pytorch_model.bin
└── whisper
    ├── config.json
    ├── pytorch_model.bin
    └── preprocessor_config.json
```

建议做法：

1. 在本地浏览器把权重分别下载好
2. 本地整理成 `models/` 目录
3. 直接整个上传到服务器 `~/workspace/ZhiXI/code/backend/MuseTalk/models/`

## 6. 准备数字人素材

项目代码已经支持两种素材源：

- 优先使用待机视频：`teacher_idle.mp4`
- 如果没有待机视频，则回退使用静态正脸图：`teacher_face.jpg`

请把素材放到：

```text
~/workspace/ZhiXI/code/backend/digital_human_assets/
```

建议至少准备：

- `teacher_face.jpg`

如果想做更像商业数字人的效果，再额外准备：

- `teacher_idle.mp4`

说明：

- `teacher_face.jpg` 适合先快速打通链路
- `teacher_idle.mp4` 更适合后续升级成“有轻微眨眼、呼吸、头部微动”的真实数字人

## 7. 修改项目 `.env`

打开项目根目录的 `.env`，补上或覆盖下面这组配置。

如果你的项目根目录是 `~/workspace/ZhiXI/code`，则可以参考：

```env
REDIS_BROKER_URL=redis://127.0.0.1:6379/0
REDIS_RESULT_BACKEND=redis://127.0.0.1:6379/1

DIGITAL_HUMAN_ENGINE=musetalk
DIGITAL_HUMAN_EDGE_TTS_VOICE=zh-CN-YunxiNeural
DIGITAL_HUMAN_RENDER_TIMEOUT_SECONDS=1800
DIGITAL_HUMAN_CELERY_ENABLED=true

DIGITAL_HUMAN_MUSETALK_DIR=/root/workspace/ZhiXI/code/backend/MuseTalk
DIGITAL_HUMAN_MUSETALK_CONDA_BIN=/root/miniconda3/bin/conda
DIGITAL_HUMAN_MUSETALK_CONDA_ENV=MuseTalk
DIGITAL_HUMAN_MUSETALK_PYTHON=
DIGITAL_HUMAN_MUSETALK_TEMPLATE_CONFIG=/root/workspace/ZhiXI/code/backend/MuseTalk/configs/inference/test.yaml
DIGITAL_HUMAN_MUSETALK_UNET_MODEL_PATH=/root/workspace/ZhiXI/code/backend/MuseTalk/models/musetalkV15/unet.pth
DIGITAL_HUMAN_MUSETALK_UNET_CONFIG_PATH=/root/workspace/ZhiXI/code/backend/MuseTalk/models/musetalkV15/musetalk.json
DIGITAL_HUMAN_MUSETALK_VERSION=v15
DIGITAL_HUMAN_MUSETALK_EXTRA_ARGS=
DIGITAL_HUMAN_MUSETALK_RESULT_DIR=/root/workspace/ZhiXI/code/backend/digital_human_outputs/musetalk_runs

DIGITAL_HUMAN_FFMPEG_PATH=
DIGITAL_HUMAN_FACE_IMAGE=/root/workspace/ZhiXI/code/backend/digital_human_assets/teacher_face.jpg
DIGITAL_HUMAN_IDLE_VIDEO=/root/workspace/ZhiXI/code/backend/digital_human_assets/teacher_idle.mp4
```

注意：

- 如果你没有 `teacher_idle.mp4`，这一项可以先写着，文件不存在时系统会自动回退到 `teacher_face.jpg`
- 如果你不确定 Conda 路径，可以执行 `which conda`
- 如果你已经知道 MuseTalk 环境中的 Python 绝对路径，也可以直接填 `DIGITAL_HUMAN_MUSETALK_PYTHON`，这样项目会绕过 `conda run`

例如：

```bash
conda activate MuseTalk
which python
```

如果输出是 `/root/miniconda3/envs/MuseTalk/bin/python`，那么你也可以改成：

```env
DIGITAL_HUMAN_MUSETALK_PYTHON=/root/miniconda3/envs/MuseTalk/bin/python
```

这时 `DIGITAL_HUMAN_MUSETALK_CONDA_BIN` 和 `DIGITAL_HUMAN_MUSETALK_CONDA_ENV` 只作为备用即可。

## 8. 先单独验证 MuseTalk 能不能跑

这一步非常重要，建议先不要直接进项目联调。

### 8.1 用 Edge-TTS 生成一条测试音频

回到你平时跑项目的 Python 环境：

```bash
cd ~/workspace/ZhiXI/code/backend
edge-tts --text "大家好，欢迎来到智屿课堂。" --voice zh-CN-YunxiNeural --write-media digital_human_outputs/test.wav
```

### 8.2 复制一份 MuseTalk 推理配置模板

```bash
cp ~/workspace/ZhiXI/code/backend/MuseTalk/configs/inference/test.yaml \
   ~/workspace/ZhiXI/code/backend/MuseTalk/configs/inference/test_local.yaml
```

然后手动编辑 `test_local.yaml`。注意官方模板是多任务格式，你要改的是 `task_0` 下面的字段：

- `task_0.video_path`
- `task_0.audio_path`

例如：

```yaml
task_0:
  video_path: /root/workspace/ZhiXI/code/backend/digital_human_assets/teacher_face.jpg
  audio_path: /root/workspace/ZhiXI/code/backend/digital_human_outputs/test.wav
```

如果你准备好了待机视频，也可以把 `task_0.video_path` 改成：

```yaml
task_0:
  video_path: /root/workspace/ZhiXI/code/backend/digital_human_assets/teacher_idle.mp4
  audio_path: /root/workspace/ZhiXI/code/backend/digital_human_outputs/test.wav
```

### 8.3 单独运行 MuseTalk 推理

```bash
conda activate MuseTalk
cd ~/workspace/ZhiXI/code/backend/MuseTalk
python -m scripts.inference \
  --inference_config configs/inference/test_local.yaml \
  --result_dir /root/workspace/ZhiXI/code/backend/digital_human_outputs/musetalk_manual_test \
  --unet_model_path models/musetalkV15/unet.pth \
  --unet_config models/musetalkV15/musetalk.json \
  --version v15
```

如果这一条能成功产出 mp4，说明 MuseTalk 本体已经可以使用。

## 9. 回到项目主链路测试

### 9.1 确认 Redis 正常

```bash
redis-cli ping
```

应返回：

```text
PONG
```

### 9.2 启动项目

你希望保留“一个终端就能跑”的体验，这一点当前代码已经支持。

进入后端目录后执行：

```bash
cd ~/workspace/ZhiXI/code/backend
python run_backend_stack.py
```

这条命令会负责：

- 跑后端预启动脚本
- 启动 Celery worker
- 启动 uvicorn

前提是：

- 你当前用于跑项目的 Python 环境里已经装好了后端依赖
- `.env` 里的 MuseTalk 路径和 Conda/Python 路径都正确

## 10. 接口验证方式

### 10.1 提交文本转视频任务

拿到登录态后，请求：

```http
POST /api/v1/digital-human/jobs/text-to-video
```

请求体示例：

```json
{
  "text": "大家好，欢迎来到智屿课堂，今天我们讲二分查找。",
  "voice_id": "zh-CN-YunxiNeural",
  "digital_human_id": "teacher-default",
  "title": "二分查找导学"
}
```

成功后会返回：

```json
{
  "task_id": "xxxx",
  "status": "pending",
  "message": "已加入渲染队列"
}
```

### 10.2 轮询任务状态

```http
GET /api/v1/digital-human/jobs/{task_id}
```

典型状态包括：

- `pending`
- `processing`
- `success`
- `failed`

### 10.3 播放生成结果

状态成功后，接口会返回：

```json
{
  "status": "success",
  "video_url": "/api/digital-human/media/{task_id}.mp4"
}
```

前端直接把 `video_url` 填给 `<video>` 即可。

## 11. 常见问题排查

### 11.1 `git clone` 失败

你现在遇到的就是这类问题。最直接的解决方式不是继续和服务器网络较劲，而是：

1. 本地下载 MuseTalk 源码 ZIP
2. 本地下载模型权重
3. 一次性上传到服务器对应目录

### 11.2 `未检测到 Conda 命令`

执行：

```bash
which conda
```

把输出路径写进：

```env
DIGITAL_HUMAN_MUSETALK_CONDA_BIN=/你的/conda/绝对路径
```

### 11.3 `MuseTalk 已执行，但未找到 mp4`

说明脚本可能没有成功落盘最终结果。优先检查：

- `digital_human_outputs/musetalk_runs/{task_id}/`
- MuseTalk 控制台日志
- 模板 YAML 是否把 `video_path` 和 `audio_path` 指到真实文件

### 11.4 显存不够或速度太慢

可以先尝试：

- 用更短脚本做联调
- 优先使用静态图 `teacher_face.jpg` 打通链路
- 等主链路稳定后，再切到 `teacher_idle.mp4`

### 11.5 模板配置与官方仓库版本不一致

当前项目实现采用的是：

- 以官方 `test.yaml` 为模板
- 项目运行时动态覆写 `video_path` 和 `audio_path`

如果你后面拉的是别的 MuseTalk 分支，发现模板字段有变化，优先改：

- `DIGITAL_HUMAN_MUSETALK_TEMPLATE_CONFIG`
- 模板 YAML 本身

代码层不需要大改。

## 12. 下一步建议

推荐按这个顺序推进：

1. 先把 MuseTalk 仓库和权重上传到服务器
2. 单独跑通一次 MuseTalk 手工推理
3. 再补齐 `.env`
4. 然后用 `python run_backend_stack.py` 跑整个项目
5. 最后从前端 Studio 页面走完整轮询闭环

## 13. 进阶升级方向

如果你们后面追求更强的真实感，可以继续走两步：

1. 用 `teacher_idle.mp4` 替代 `teacher_face.jpg`
2. 赛前预生成更高质量的老师待机视频，再由 MuseTalk 在运行时只负责嘴型同步

这样效果会明显优于“静态图开口说话”。
