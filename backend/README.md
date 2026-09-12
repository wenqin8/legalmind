# LegalMind Backend

第 1 周第 5 天后端：FastAPI、SQLAlchemy、Alembic、Argon2 密码哈希、JWT 登录，以及受保护的同步法律问答链路。

当前问答只调用配置的模型适配器，尚未接入 RAG、LangGraph 或 Redis。系统只持久化用户和会话归属，不保存聊天正文或多轮上下文；回答会明确显示无可核验来源及非法律意见提示。

## 本地准备

需要 Python 3.11 或更高版本；当前验收环境为 Python 3.12.12。

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt

if (-not (Test-Path .env)) {
    Copy-Item .env.example .env
}
```

本地 `.env` 至少需要配置随机的 JWT 密钥。可运行以下幂等脚本生成并写入密钥；脚本不会打印密钥，已有合格值时不会覆盖：

```powershell
.\.venv\Scripts\python.exe scripts\ensure_local_jwt_secret.py
```

密钥不得少于 32 个字符，也不得写入 `.env.example`、代码、测试、日志或 Git。

真实 DeepSeek 联调还需要：

```dotenv
LEGALMIND_LLM_BACKEND=deepseek
LEGALMIND_DEEPSEEK_API_KEY=your-local-key
```

自动化测试始终注入确定性假模型，不访问 DeepSeek，也不消耗模型额度。

## 数据库迁移

默认数据库为 `backend/data/legalmind.db`。该文件及 SQLite 的 WAL/SHM 文件均被 Git 忽略。运行 API 前应用迁移：

```powershell
.\.venv\Scripts\python.exe -m alembic upgrade head
```

配置 `LEGALMIND_DATABASE_URL=postgresql+psycopg://...` 后可切换 PostgreSQL。不要把带数据库密码的 URL 提交到仓库或输出到日志。

## 启动

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

- 健康检查：`GET http://127.0.0.1:8000/api/v1/health`
- 注册：`POST http://127.0.0.1:8000/api/v1/auth/register`
- 登录：`POST http://127.0.0.1:8000/api/v1/auth/login`
- 当前用户：`GET http://127.0.0.1:8000/api/v1/auth/me`
- 同步问答：`POST http://127.0.0.1:8000/api/v1/chat/send`
- 开发文档：`http://127.0.0.1:8000/docs`

健康检查、注册和登录为公开接口。`/auth/me` 与 `/chat/send` 必须携带登录取得的 `Authorization: Bearer <token>`；任意或伪造的 Bearer 值不会被接受。访问其他用户的会话 UUID 与不存在的会话统一返回 404，并且不会调用模型。

生产环境会关闭 Swagger、ReDoc 和 OpenAPI 文档端点，并要求配置至少 32 字符的 JWT 密钥。

## 测试

```powershell
.\.venv\Scripts\python.exe -m pytest
```

测试覆盖注册与规范化唯一性、Argon2 哈希、JWT 必需声明与篡改拒绝、活跃用户回查、会话隔离、统一错误、模型超时、模型失败无孤立会话、日志脱敏及 Alembic 升降级/模型一致性。

M1 冻结前实测结果：89 项测试全部通过，`compileall` 通过，`pip check` 无依赖冲突；Alembic 在全新隔离 SQLite 上完成升级、一致性检查、降级和重新升级。
