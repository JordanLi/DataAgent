# DataAgent — 数据智能体

基于大语言模型的企业级自然语言数据查询与分析系统，让所有人都能用"说人话"的方式获取和理解数据。

## 快速开始（Docker Compose）

```bash
# 1. 复制环境变量配置
cp backend/.env.example backend/.env
# 编辑 backend/.env，填入 LLM_API_KEY 等必填项

# 2. 启动所有服务（PostgreSQL + Redis + Backend + Frontend）
docker compose up -d

# 3. 初始化数据库
docker compose exec backend alembic upgrade head

# 4. 访问
#   前端界面:  http://localhost:3000
#   API 文档:  http://localhost:8000/docs
```

## 本地开发

### 后端

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # 填写配置

# 启动（需要 PostgreSQL & Redis 已运行）
uvicorn app.main:app --reload --port 8000
```

### 前端

```bash
cd frontend
npm install
npm run dev   # http://localhost:3000
```

## 项目结构

```
DataAgent/
├── backend/              Python FastAPI 后端
│   ├── app/
│   │   ├── main.py       应用入口 + 路由注册
│   │   ├── config.py     配置（环境变量）
│   │   ├── api/          REST 路由层
│   │   ├── core/         核心业务：LLM / Agent / 语义层 / 对话管理
│   │   ├── connectors/   数据库连接器（MySQL...）
│   │   ├── models/       SQLAlchemy ORM 模型
│   │   └── auth/         JWT & RBAC
│   └── alembic/          数据库迁移
├── frontend/             Next.js 14 前端
│   └── src/
│       ├── app/          页面路由
│       ├── components/   UI 组件（Chat / Results / Admin）
│       └── lib/          API 客户端 & TypeScript 类型
└── docker-compose.yml
```

## 默认账户

首次运行 `alembic upgrade head` 后，系统自动创建：

| 用户名 | 密码 | 角色 |
|--------|------|------|
| admin  | admin123 | admin |

登录后立即修改密码。

## 技术栈

| 层 | 技术 |
|----|------|
| LLM 编排 | 自研 Agent（OpenAI / Claude / DeepSeek 可切换） |
| 后端框架 | Python 3.11 + FastAPI + SQLAlchemy 2 |
| 系统数据库 | PostgreSQL 16 |
| 缓存 | Redis 7 |
| 前端框架 | Next.js 14 (App Router) + TypeScript |
| UI 组件 | Tailwind CSS + Radix UI |
| 图表 | ECharts 5 |
| 容器化 | Docker Compose |
