# DataAgent — 数据智能体

基于大语言模型的企业级自然语言数据查询与分析系统，让所有人都能用"说人话"的方式获取和理解数据。

## 快速开始（Docker Compose）

```bash
# 1. 复制环境变量配置
cp backend/.env.example backend/.env
# 编辑 backend/.env，填入 LLM_API_KEY 等必填项

# 2. 启动所有服务（PostgreSQL + Redis + Backend + Frontend + 测试用MySQL）
docker compose up -d

# 3. 初始化系统数据库
docker compose exec backend alembic upgrade head

# 4. 访问系统
#   前端界面:  http://localhost:3000
#   API 文档:  http://localhost:8000/docs
```

## 配置说明

系统核心配置通过 `backend/.env` 进行管理，主要包含以下内容：

- **LLM 配置**
  - `LLM_PROVIDER`: 使用的模型服务商，可选 `openai` / `claude` / `deepseek`
  - `LLM_API_KEY`: 模型 API 密钥
  - `LLM_MODEL`: 具体模型名称（如 `gpt-4o`, `claude-3-5-sonnet-20240620`）
  - `LLM_BASE_URL`: （可选）API 代理地址

- **系统存储**
  - `SYSTEM_DB_URL`: PostgreSQL 数据库连接串（例如：`postgresql+asyncpg://dataagent:dataagent@postgres:5432/dataagent`）
  - `REDIS_URL`: Redis 连接串（例如：`redis://redis:6379/0`）

- **安全与认证**
  - `JWT_SECRET`: 用于签发 JWT 的密钥，请使用强随机字符串
  - `JWT_ALGORITHM`: JWT 签名算法，默认 `HS256`

## 架构说明

系统架构主要分为前端展示、后端编排引擎和基础设施层。核心数据流（NL-to-SQL）如下：

1. **意图理解**: 接收用户自然语言问题，结合对话历史判断意图。
2. **上下文构建**: 语义层引擎（Semantic Engine）加载数据源 Schema、业务术语、表关联关系和枚举映射。
3. **SQL 生成**: 大语言模型（LLM）基于 Schema 和语义上下文生成 SQL 查询。
4. **安全校验**: SQLValidator 进行 AST 解析，拒绝 DML/DDL 等危险操作，并强制注入 `LIMIT` 限制。
5. **查询执行**: QueryExecutor 通过只读连接向目标数据库下发查询。
6. **图表与洞察**: LLM 结合返回的数据结果集，生成可阅读的洞察摘要，并推荐适配的图表类型（如柱状图、折线图等）。
7. **流式响应**: Backend 通过 Server-Sent Events (SSE) 向前端流式下发 SQL、数据和洞察结果。

## 本地开发

### 后端 (FastAPI)

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # 填写配置

# 启动（需要 PostgreSQL & Redis 已运行）
uvicorn app.main:app --reload --port 8000
```

### 前端 (Next.js)

```bash
cd frontend
npm install
npm run dev   # http://localhost:3000
```

## 项目结构

```text
DataAgent/
├── backend/              # Python FastAPI 后端
│   ├── app/
│   │   ├── main.py       # 应用入口 + 路由注册
│   │   ├── config.py     # 配置（环境变量）
│   │   ├── api/          # REST 路由层
│   │   ├── core/         # 核心业务：LLM / Agent / 语义层 / 对话管理
│   │   ├── connectors/   # 数据库连接器（MySQL...）
│   │   ├── models/       # SQLAlchemy ORM 模型
│   │   └── auth/         # JWT & RBAC
│   └── alembic/          # 数据库迁移
├── frontend/             # Next.js 14 前端
│   ├── src/app/          # 页面路由
│   ├── src/components/   # UI 组件（Chat / Results / Admin）
│   └── src/lib/          # API 客户端 & TypeScript 类型
└── docker-compose.yml    # 容器编排文件
```

## 默认账户

首次运行 `alembic upgrade head` 后，系统自动创建超级管理员：

| 用户名 | 密码 | 角色 |
|--------|------|------|
| admin  | admin123 | admin |

**强烈建议：** 在部署上线后立即登录并修改管理员密码。

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
