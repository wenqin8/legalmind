# LegalMind Backend

第三周 M3：已接入 LangChain 意图合同、LangGraph 三分支、演示 RAG 与引用约束、三类固定文书、Redis 多轮历史及实时 SSE。后端保留 JWT、统一外壳和案例 API；日常数据库仍为 SQLite。

现有 16 条冻结合成案例和 64 个块保持不变。补充开发新增四领域 60 条官方条文、版本过滤、独立适用性检查、问答事实状态与文书逐轮收集/冲突确认。法条采用本地核验快照，不宣称实时最新；演示资料仅支持场景整理。见 [扩展说明](../docs/legal-multiturn.md)、[扩展验收](../docs/acceptance/legal-multiturn.md) 和 [API 合同](../docs/api-contract.md)。

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

自动化测试注入确定性假模型和测试存储，不访问 DeepSeek；真实存储与模型另用下方显式验收命令。默认 Fake 模型不能确认检索证据时返回依据不足，不伪装真实 RAG 回答。运行聊天、历史和会话列表还必须启动 Redis；故障返回 SESSION_STORE_UNAVAILABLE，不降级为内存历史。

## 数据库迁移

默认数据库为 `backend/data/legalmind.db`。该文件及 SQLite 的 WAL/SHM 文件均被 Git 忽略。运行 API 前应用迁移：

```powershell
.\.venv\Scripts\python.exe -m alembic upgrade head
```

当前迁移头为 `20260918_0004`，新增可空 `legal_provisions.verification`（SQLite JSON / PostgreSQL JSONB）；此前 `0003` 已增加 `generated_documents` 和 `conversations.history_commit_id`。已有开发库须先备份再升级，不重建或清空原有数据；不要对有用数据直接运行降级命令。PostgreSQL 兼容性、隔离 schema 升降级及法条 JSONB 往返已经验证，日常仍使用 SQLite。不要把带密码的 URL 提交到仓库或输出到日志。

官方条文需要单独手动导入，不会混入冻结案例向量集合：

```powershell
.\.venv\Scripts\python.exe -m scripts.import_verified_laws --check-only
.\.venv\Scripts\python.exe -m scripts.import_verified_laws
.\.venv\Scripts\python.exe -m scripts.evaluate_legal_retrieval --output ../docs/acceptance/legal-retrieval-evaluation.json
```

版本更新方法、核验日期与状态截止日的区别见 [法条资料说明](data/legal/README.md)。导入命令不负责联网核验，清单必须先由维护者核对官方来源。没有核验元数据的旧法条不会被用于回答。

2026-09-18 本机默认 SQLite 已按用户授权完成上述升级，升级前一致备份位于 `tmp/backups/legalmind-pre-m3-20260917T192538Z-a395569b.db`（相对仓库根目录）。Redis PING 和默认配置的真实 HTTP 冒烟通过，原有用户、会话、案例、分块和向量均保留，详见 [默认环境报告](../docs/acceptance/week3-default-environment-smoke.json)。其他环境仍应检查自己的迁移版本；已有 indexed 数据不需要重新导入或重建索引来完成本次升级。

## 导入演示案例

迁移后运行以下幂等案例命令，不改冻结案例/查询/标签。旧 `--legal-provisions <jsonl>` 入口只导入来源基础信息，实际用于问答的已核验法条使用上述 `import_verified_laws` 命令。

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
- 流式问答：`POST http://127.0.0.1:8000/api/v1/chat/stream`
- 会话列表：`GET http://127.0.0.1:8000/api/v1/chat/conversations`
- 读取历史：`GET http://127.0.0.1:8000/api/v1/chat/history/{session_id}`
- 删除会话：`DELETE http://127.0.0.1:8000/api/v1/chat/history/{session_id}`
- 案例搜索：`POST http://127.0.0.1:8000/api/v1/cases/search`
- 案例详情：`GET http://127.0.0.1:8000/api/v1/cases/{case_id}`
- 文书模板：`GET http://127.0.0.1:8000/api/v1/documents/templates`
- 生成草稿：`POST http://127.0.0.1:8000/api/v1/documents/generate`
- 文书下载：`GET http://127.0.0.1:8000/api/v1/documents/{document_id}/download?format=md`
- 开发文档：`http://127.0.0.1:8000/docs`

健康检查、注册和登录为公开接口。`/auth/me`、聊天、会话、文书和案例接口必须携带登录取得的 `Authorization: Bearer <token>`。案例详情只返回 `indexed` 关系库来源；检索排序分数不表示法律结论置信度，所有演示详情固定提示“课程演示合成数据，不是真实判例或法律依据”。

生产环境会关闭 Swagger、ReDoc 和 OpenAPI 文档端点，并要求配置至少 32 字符的 JWT 密钥。

## 测试

修复前 RAG-v1 基线已本地提交为 `6fb2996`，保持默认运行库、冻结查询和 M3 标签不变。当前 RAG-v2 仅运行120条开发查询及36个开发场景（52轮），扩展209条法条与16条案例只导入 `tmp/` 下新建SQLite和Chroma；不需要改变 `.env`。默认库锁定 `demo-m3-60`，评估锁定 `eval-rag-v2-209`，响应会显示资料边界。详情见 [评估数据定义](data/evaluation/rag-v1/README.md) 和 [修复验收](../docs/acceptance/rag-v2.md)。

```powershell
.\.venv\Scripts\python.exe -m scripts.evaluate_rag --split development --corpus-profile eval-rag-v2-209 --output ../tmp/rag-retrieval-new-run.json
.\.venv\Scripts\python.exe -m scripts.evaluate_rag_answers --split development --corpus-profile eval-rag-v2-209 --output ../tmp/rag-answers-new-run.json
.\.venv\Scripts\python.exe -m scripts.review_rag_answers --input ../docs/acceptance/rag-v1-answers.json --annotations ../docs/acceptance/rag-v1-review-notes.json --output ../tmp/rag-review-new-run.json
```

前两条分别执行真实BGE检索和36场景真实模型HTTP联调；第二条需要Redis和现有DeepSeek配置，会消耗API额度。第三条仅离线复核既有合成结果。输出路径必须尚不存在；每次完整运行都保留失败，不能择优拼接。当前CLI只接受开发集；已看过的保留集不再用于调试。复现原40场景基线应在单独检出 `6fb2996` 的目录使用当时说明。新增资料见 [扩展解释](data/legal/expansion-v1/README.md) 与 [交通解释二](data/legal/traffic-ii-2026/README.md)，默认导入器仍指向M3的60条。

门槛检查绑定同一资料指纹，并要求为每条实际返回的法律回答记录逐条语义复核；缺少复核或报告哈希不符都会阻止通过。开发代理复核不等于法律专家认证：

```powershell
.\.venv\Scripts\python.exe -m scripts.evaluate_quality_gates --answers ../tmp/rag-answers-new-run.json --retrieval ../tmp/rag-retrieval-new-run.json --reviews ../tmp/semantic-review.json --output ../tmp/rag-gates-new-run.json
```

复核文件使用 `raw_report_sha256` 绑定答案报告，`reviewer` 记录复核身份，`turns` 以 `场景ID:轮次` 为键，每项包含 `faithfulness`、`applicability`（`pass/fail`）和具体 `notes`。不能仅根据引用真实或自动检查通过批量标记为通过。

```powershell
.\.venv\Scripts\python.exe -m pytest
```

测试覆盖意图回退、证据筛选、引用、模板与缺项、所有权、历史过期/裁剪、并发、补偿、真实本地 TCP 的首段到达和断开取消，以及 Schema 不变量、事务导入、确定性分块、向量元数据兼容、失败清理、BM25/RRF、过滤、Top-K、来源回查、案例 API 和错误/日志净化。

M2 复验写入临时报告，保留冻结评估文件；PostgreSQL 脚本报告实际迁移版本：

```powershell
.\.venv\Scripts\python.exe -m scripts.evaluate_week2_retrieval --output ..\tmp\week2-retrieval-recheck.json
.\.venv\Scripts\python.exe -m scripts.verify_postgres_week2
```

M1 最终验收实测结果：运行依赖全部可导入，PostgreSQL 17.11、Redis API 7.2.11 和 Chroma 持久化 smoke test 全部通过，94 项后端测试全部通过，`compileall` 通过，`pip check` 无依赖冲突；Alembic 已在全新隔离 SQLite 上完成升级、一致性检查、降级和重新升级。完整证据见 [第一周 M1 验收记录](../docs/acceptance/week1-m1.md)。

第二周最终结果见 [`docs/acceptance/week2-m2.md`](../docs/acceptance/week2-m2.md)。M3 后端已完成这些业务接入；第四周剩余完整界面和 Docker 部署。


## M3 复现与验收

先启动已配置的本地 Redis/PostgreSQL（Compose 命令见上文）。自动化测试使用临时库，不修改默认开发库；实库脚本只操作随机 PostgreSQL schema 和随机 Redis 命名空间，结束后精确清理。

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -m compileall -q app scripts
.\.venv\Scripts\python.exe -m scripts.verify_week3_storage --output ..\docs\acceptance\legal-multiturn-storage.json
```

当前真实模型联调仅发送脚本内的合成输入，使用本地 DeepSeek 配置，可能消耗模型额度。它在被忽略的 `tmp/legal-multiturn-*` 新建 SQLite，并只读使用现有冻结案例向量，不迁移或改写已有业务库；结束后精确清理合成用户 Redis 键。报告保存已校验的合成回答，临时目录中的诊断文件可能包含未通过校验的合成输出，不能作为产品回答。下列 offline 标记只关闭 BGE 权重联网下载，不关闭 DeepSeek 网络；首次需要先缓存固定模型。

```powershell
$env:HF_HUB_OFFLINE='1'
.\.venv\Scripts\python.exe -m scripts.smoke_legal_multiturn --output ..\docs\acceptance\legal-multiturn-real-model.json
```

SSE 到达顺序和断流不是用缓冲 ASGI 客户端推断：`tests/integration/test_live_stream.py` 启动真实 Uvicorn 回环端口，暂停假模型验证首段到达，再关闭客户端验证上游取消、历史不变和释放锁。真实模型脚本验证内容/完成事件，与此测试互补。

Redis 24 小时 TTL 仅在成功成对追加时刷新。关系记录保留过期会话；任务快照与消息同一键保存、一起过期；上下文最多 10 条/12000 字符；同会话并发为 409。文书需核对摘要后确认生成，过期或陈旧摘要为 TASK_CHANGED。修改模型超时时要同步核对前端 72 秒等待和代理设置。完整说明见架构和 API 合同。
