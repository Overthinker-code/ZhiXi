# 智屿

智能教学辅助系统 - 基于 AI 的教育平台

## 项目结构

```
ZhiYu/
├── code/
│   ├── backend/                 # 后端服务 (FastAPI + Python)
│   │   ├── app/
│   │   │   ├── api/             # API 路由
│   │   │   ├── core/            # 核心配置
│   │   │   ├── models/          # 数据库模型
│   │   │   ├── providers/       # 业务逻辑层
│   │   │   ├── schemas/         # Pydantic 模型
│   │   │   └── ai/              # AI 服务集成
│   │   └── alembic/             # 数据库迁移
│   │
│   └── education/
│       └── course/              # 前端应用 (Vue 3 + TypeScript)
│           ├── src/
│           │   ├── api/         # API 接口
│           │   ├── components/  # 组件
│           │   ├── hooks/       # 组合式函数
│           │   ├── store/       # Pinia 状态管理
│           │   ├── views/       # 页面视图
│           │   └── router/      # 路由配置
│           └── config/          # Vite 配置
│
├── arch.md                      # 架构文档
├── frontend_vb.md               # 前端升级文档
└── README.md                    # 项目说明
```

## 技术栈

### 后端
- **框架**: FastAPI
- **数据库**: MySQL (SQLAlchemy ORM)
- **迁移工具**: Alembic
- **AI 集成**: DeepSeek API

### 前端
- **框架**: Vue 3 + TypeScript
- **构建工具**: Vite
- **UI 组件库**: Arco Design Vue
- **状态管理**: Pinia
- **路由**: Vue Router

## 快速开始

### 环境要求
- Node.js >= 14.0.0
- Python >= 3.10
- MySQL >= 8.0

### 后端启动

```bash
cd code/backend

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/macOS
# venv\Scripts\activate   # Windows

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env
# 编辑 .env 文件配置数据库连接等

# 数据库迁移
alembic upgrade head

# 启动服务
uvicorn app.main:app --reload
```

### 前端启动

```bash
cd code/education/course

# 安装依赖
npm install

# 启动开发服务器
npm run dev

# 构建生产版本
npm run build

# 类型检查
npm run type:check
```

## 主要功能

- **智能对话**: AI 辅助教学对话系统
- **课程管理**: 课程资源管理与展示
- **实时监控**: 课堂行为实时监控与预警
- **用户中心**: 用户信息管理与权限控制
- **RAG 检索**: 知识库检索增强生成

## API 文档

启动后端服务后访问:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## 开发规范

- 遵循 PEP 8 (Python) 和 ESLint (TypeScript) 编码规范
- 使用 Git Flow 分支管理策略
- 提交信息遵循 Conventional Commits 规范

## 许可证

MIT License
