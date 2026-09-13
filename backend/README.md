# LegalMind Backend

第 1 周第 5 天后端：FastAPI、SQLAlchemy、Alembic、Argon2 密码哈希、JWT 登录，以及受保护的同步法律问答链路。

当前问答只调用配置的模型适配器，尚未接入 RAG、LangGraph 运行工作流或 Redis 消息历史。`langchain`、`langgraph`、`chromadb`、`redis` 和 `psycopg` 已按第一周计划加入运行依赖，并完成安装、导入和基础设施连通验收；这只表示环境就绪，不表示后续业务逻辑已经接入。系统只持久化用户和会话归属，不保存聊天正文或多轮上下文；回答会明确显示无可核验来源及非法律意见提示。

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

已保留 `LEGALMIND_DATABASE_URL=postgresql+psycopg://...` 的业务数据库配置入口。M1 已对 PostgreSQL 17.11 实例完成独立 `SELECT 1` 连通验收，但应用迁移和业务表仍只在 SQLite 验证；切换业务库将在后续里程碑单独执行。不要把带数据库密码的 URL 提交到仓库或输出到日志。

## 基础设施连通验收

先生成仅保存在 `backend/.env` 的本地 PostgreSQL/Redis 密钥和连接配置：

```powershell
.\.venv\Scripts\python.exe scripts\ensure_local_infrastructure_secrets.py
```

Docker Desktop 可用时，在仓库根目录启动 PostgreSQL 与 Redis，再运行统一 smoke test：

```powershell
docker compose --env-file backend\.env -f compose.infrastructure.yml up -d --wait
cd backend
.\.venv\Scripts\python.exe -m scripts.smoke_infrastructure
```

smoke test 会分别执行 PostgreSQL 查询、Redis `PING` 与带 TTL 的临时键往返、Chroma 本地持久化写入与向量查询；Redis 键和 Chroma 探针集合在结束时按精确标识删除。脚本只输出通过状态和服务版本，不输出连接 URL 或密码。

本次 M1 在 Docker 生效前使用 Windows 原生 PostgreSQL 17.11 和 Memurai Developer 4.1.7（Redis API 7.2.11）完成相同验收。Windows 的 WSL 与虚拟机平台功能已启用，但系统需重启后才生效；Docker Desktop 的正式容器化验收仍按第 4 周执行。

## 启动

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

- 健康检查：`GET http://127.0.0.1:8000/api/v1/health`
- 注册：`POST http://127.0.0.1:8000/api/v1/auth/register`
- 登录：`POST http://127.0.0.1:8000/api/v1/auth/login`
- 当前用户：`GET http://127.0.0.1:8000/api/v1/auth/me`
- 同步问答：`POST http://127.0.0.1:8000/api/v1/chat/send`
- 删除会话：`DELETE http://127.0.0.1:8000/api/v1/chat/history/{session_id}`
- 开发文档：`http://127.0.0.1:8000/docs`

健康检查、注册和登录为公开接口。`/auth/me`、`/chat/send` 与删除会话接口必须携带登录取得的 `Authorization: Bearer <token>`；任意或伪造的 Bearer 值不会被接受。访问或删除其他用户的会话 UUID 与不存在的会话统一返回 404，并且不会调用模型。当前删除操作只删除关系库中的会话归属；Redis 消息正文尚未接入。

生产环境会关闭 Swagger、ReDoc 和 OpenAPI 文档端点，并要求配置至少 32 字符的 JWT 密钥。

## 测试

```powershell
.\.venv\Scripts\python.exe -m pytest
```

测试覆盖注册与规范化唯一性、Argon2 哈希、JWT 必需声明与篡改拒绝、活跃用户回查、会话隔离、统一错误、模型超时、模型失败无孤立会话、日志脱敏及 Alembic 升降级/模型一致性。

M1 最终验收实测结果：运行依赖全部可导入，PostgreSQL 17.11、Redis API 7.2.11 和 Chroma 持久化 smoke test 全部通过，94 项后端测试全部通过，`compileall` 通过，`pip check` 无依赖冲突；Alembic 已在全新隔离 SQLite 上完成升级、一致性检查、降级和重新升级。完整证据见 [第一周 M1 验收记录](../docs/acceptance/week1-m1.md)。

交接后会话删除补丁的当前回归结果为 95 项后端测试全部通过。
