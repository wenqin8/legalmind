# LegalMind Backend

第 2 周 M2 后端：在既有认证和同步问答链路上，新增可重复法律数据导入、固定本地 Embedding、Chroma/BM25/RRF 混合检索及受保护的案例 API。

当前问答只调用配置的模型适配器，尚未接入 RAG、LangGraph 运行工作流或 Redis 消息历史。`langchain`、`langgraph`、`chromadb`、`redis` 和 `psycopg` 已按第一周计划加入运行依赖，并完成安装、导入和基础设施连通验收；这只表示环境就绪，不表示后续业务逻辑已经接入。系统只持久化用户和会话归属，不保存聊天正文或多轮上下文；回答会明确显示无可核验来源及非法律意见提示。

第二周已完成严格案例/法条 Schema、三张知识表及可逆迁移、规范化/哈希/确定性 UUID 和事务化 JSONL 导入。16 条演示案例会形成 64 个知识块，并以固定 BGE 或测试假向量写入 `legal_knowledge_v1`；成功后状态为 `indexed`。法条结构与导入入口已完成，但未填充未经核验的法条语料。

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

已保留 `LEGALMIND_DATABASE_URL=postgresql+psycopg://...` 的业务数据库配置入口。第二周已在 PostgreSQL 17.11 随机临时 schema 中完成迁移、JSONB 类型、16 条导入和幂等复验，并确认 schema 精确清理；日常运行仍按本周基线使用 SQLite。不要把带数据库密码的 URL 提交到仓库或输出到日志。

## 导入演示案例

迁移后运行以下幂等命令。法条结构和 `--legal-provisions <jsonl>` 入口已提供，但第二周不内置未经核验的法条语料。

```powershell
.\.venv\Scripts\python.exe -m scripts.import_legal_data
```

## 建立案例索引

默认使用固定的 `BAAI/bge-small-zh-v1.5`，revision 为 `7999e1d3359715c523056ef9478215996d62a620`，512 维、CPU、L2 归一化。查询添加“为这个句子生成表示以用于检索相关文章：”，文档不加前缀。首次运行会下载权重到被 Git 忽略的 `data/models`，启动 API 和健康检查不会加载模型。

```powershell
.\.venv\Scripts\python.exe -m scripts.index_legal_data
```

自动化测试通过 `LEGALMIND_EMBEDDING_BACKEND=fake` 注入确定性中文字符 n-gram 向量。假向量只用于测试，不得替代真实 M2 量化验收。

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
- 案例搜索：`POST http://127.0.0.1:8000/api/v1/cases/search`
- 案例详情：`GET http://127.0.0.1:8000/api/v1/cases/{case_id}`
- 开发文档：`http://127.0.0.1:8000/docs`

健康检查、注册和登录为公开接口。`/auth/me`、聊天、会话删除和案例接口必须携带登录取得的 `Authorization: Bearer <token>`。案例详情只返回 `indexed` 关系库来源；检索排序分数不表示法律结论置信度，所有演示详情固定提示“课程演示合成数据，不是真实判例或法律依据”。

生产环境会关闭 Swagger、ReDoc 和 OpenAPI 文档端点，并要求配置至少 32 字符的 JWT 密钥。

## 测试

```powershell
.\.venv\Scripts\python.exe -m pytest
```

测试覆盖既有认证/聊天能力，以及 Schema 不变量、事务导入、确定性分块、向量元数据兼容、失败清理、BM25/RRF、过滤、Top-K、来源回查、案例 API 和错误/日志净化。

真实评估与 PostgreSQL 隔离验收：

```powershell
.\.venv\Scripts\python.exe -m scripts.evaluate_week2_retrieval --output ..\docs\acceptance\week2-retrieval-evaluation.json
.\.venv\Scripts\python.exe -m scripts.verify_postgres_week2
```

M1 最终验收实测结果：运行依赖全部可导入，PostgreSQL 17.11、Redis API 7.2.11 和 Chroma 持久化 smoke test 全部通过，94 项后端测试全部通过，`compileall` 通过，`pip check` 无依赖冲突；Alembic 已在全新隔离 SQLite 上完成升级、一致性检查、降级和重新升级。完整证据见 [第一周 M1 验收记录](../docs/acceptance/week1-m1.md)。

第二周最终结果见 [`docs/acceptance/week2-m2.md`](../docs/acceptance/week2-m2.md)。案例检索尚未接入聊天回答，Redis 消息历史、LangGraph、SSE、文书 API 和前端案例页面仍属于第三、四周范围。
