# 智屿本地启动说明

## 目录

- 前端目录：`code/education/course`
- 后端目录：`code/backend`
- 后端配置文件：`code/.env`
- 前端本地代理示例：`code/education/course/.env.development.example`

不要在 `code/education` 目录执行 `npm install`。真正的前端 `package.json` 在 `code/education/course`。

## 前端依赖

推荐 Node.js 20 LTS。Node.js 24 当前可以运行，但会出现一些旧依赖的 deprecation warning。

```bash
cd code/education/course
npm ci
npm run dev
```

默认前端地址：

```text
http://127.0.0.1:5174/
```

前端开发代理默认指向：

```text
http://127.0.0.1:8001/api/v1
```

## 后端依赖

默认依赖只包含学生端、AI 对话、RAG、资源生成和轻量课堂分析所需内容，不再强制安装 Torch/YOLO/Docling。

```bash
cd code
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

需要运行测试、类型检查或提交钩子时安装开发依赖：

```bash
pip install -r requirements-dev.txt
```

核心后端测试只收集 `app/tests` 和 `tests`，不会误运行可选的 MuseTalk 自检脚本：

```bash
cd backend
../.venv/bin/python -m pytest -q
```

需要 Docling 或 MediaPipe 时再安装：

```bash
pip install -r requirements-optional.txt
```

YOLO 是独立服务，按需安装：

```bash
pip install -r cv/requirements.txt
```

## 环境变量

复制并编辑：

```bash
cp code/.env.example code/.env
```

至少确认：

```text
POSTGRES_SERVER=127.0.0.1
POSTGRES_PORT=5432
POSTGRES_USER=postgres
POSTGRES_PASSWORD=...
POSTGRES_DB=zhixi
MIMO_API_KEY=...
```

## 数据库

本地需要 PostgreSQL。确认 5432 已监听：

```bash
lsof -nP -iTCP:5432 -sTCP:LISTEN
```

如果没有数据库，先创建：

```bash
createdb zhixi
```

## 启动后端

```bash
cd code/backend
../.venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8001
```

也可以使用统一入口；默认只启动 FastAPI，不要求 Redis 或 YOLO：

```bash
cd code/backend
../.venv/bin/python run_backend_stack.py
```

需要数字人队列和课堂 YOLO 时显式开启：

```bash
START_CELERY_SERVICE=true START_YOLO_SERVICE=true ../.venv/bin/python run_backend_stack.py
```

轻量健康检查：

```bash
curl http://127.0.0.1:8001/api/v1/readyz
```

深度模型探测会真实调用 MiMo，只有需要排查模型连通性时再运行：

```bash
curl http://127.0.0.1:8001/api/v1/readyz?deep=true
```

## 常见问题

### 前端一直转圈

先看 Vite 终端是否出现：

```text
http proxy error ... ECONNREFUSED 127.0.0.1:8001
```

如果出现，说明前端正常，问题是后端 8001 没启动、启动失败，或被慢请求卡住。

验证：

```bash
curl -X POST http://127.0.0.1:8001/api/v1/login/access-token \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  --data-urlencode 'username=student@example.com' \
  --data-urlencode 'password=student123456'
```

### npm install 很慢或失败

之前依赖里包含 `vite-plugin-imagemin`，会下载 `gifsicle/mozjpeg/optipng/pngquant` 等二进制，国内网络容易失败。该依赖已经移除，正确的 `code/education/course/package-lock.json` 现在应随代码提交，组员使用 `npm ci` 即可。
