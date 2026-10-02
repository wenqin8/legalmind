# LegalMind后端运行说明

FastAPI + LangGraph，提供问答、检索、文书及会话API。日常使用SQLite，Redis保存短期消息和任务，Chroma本地持久化案例向量。接手先读[开发者指南](../docs/developer-onboarding.md)；工作流见[架构](../docs/architecture.md)，接口见[API合同](../docs/api-contract.md)，当前课程验收见[M4项目方决定](../docs/acceptance/m4-project-acceptance-20261002.md)，[Run21](../docs/acceptance/rag-v2-final-acceptance.md)仅为M3历史结果。

以下Python命令在`backend`目录执行，除非另有说明。

## 安装与密钥

需要Python 3.11+，验收环境为3.12.12。

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
.\.venv\Scripts\python.exe scripts\ensure_local_jwt_secret.py
```

JWT使用独立、至少32字符的密钥。配置从源码定位的`backend/.env`加载，密钥不写入模板、日志或Git。真实模型还需在本地配置：

```dotenv
LEGALMIND_LLM_BACKEND=deepseek
LEGALMIND_DEEPSEEK_API_KEY=your-local-key
```

默认Fake模型只用于开发，不能证明真实回答质量；未配置模型密钥不影响健康检查。前端`VITE_`变量不可存放后端密钥。

## Redis与可选PostgreSQL

聊天、历史和会话列表要求可用Redis，故障返回`SESSION_STORE_UNAVAILABLE`，不降级到内存历史。可连接已有服务，或生成本地连接配置后使用Compose：

```powershell
.\.venv\Scripts\python.exe scripts\ensure_local_infrastructure_secrets.py
```

在仓库根目录执行：

```powershell
docker compose --env-file backend\.env -f compose.infrastructure.yml up -d --wait
```

回到`backend`目录验证：

```powershell
.\.venv\Scripts\python.exe -m scripts.smoke_infrastructure
```

该脚本检查PostgreSQL、Redis及本地Chroma，使用临时键和探针集合并清理。Compose仅含基础设施，不能据此认定完整应用部署完成；使用前检查本机Docker/WSL可用状态。PostgreSQL已做隔离兼容验收，默认业务库仍是SQLite。

## 数据准备

默认库为`backend/data/legalmind.db`，当前迁移头`20260918_0004`。新环境先迁移；已有库先备份，不重建、清空或降级已有数据。

```powershell
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m scripts.import_legal_data
.\.venv\Scripts\python.exe -m scripts.import_verified_laws --check-only
.\.venv\Scripts\python.exe -m scripts.import_verified_laws
.\.venv\Scripts\python.exe -m scripts.index_legal_data
```

案例和法规分别导入。默认法规为60条，版本标识`demo-m3-60`；209条扩展法规`eval-rag-v2-209`用于隔离评估，不自动替换默认库。法条不混入案例向量，没有核验元数据的条文不用于回答；更新前须人工核对官方来源，见[法规资料说明](data/legal/README.md)。已有索引不必为普通启动重复建立。

案例使用16条冻结合成数据、64个分块。向量模型为`BAAI/bge-small-zh-v1.5`，固定revision `7999e1d3359715c523056ef9478215996d62a620`，512维、CPU、L2归一化；查询加“为这个句子生成表示以用于检索相关文章：”，文档不加前缀。首次索引会下载权重至`data/models`；API启动和健康检查不加载模型。测试的`LEGALMIND_EMBEDDING_BACKEND=fake`不能替代真实检索验收。

本机升级前备份留在`tmp/backups/`，已记录的M3及法条升级备份分别为`legalmind-pre-m3-20260917T192538Z-a395569b.db`和`legalmind-pre-laws-20260918T154922Z-bfbd9c91.db`。备份不随Git分发，迁移其他运行库时须另行备份。

## 启动与接口

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

健康检查：`GET http://127.0.0.1:8000/api/v1/health`。开发API文档：`http://127.0.0.1:8000/docs`；生产环境关闭Swagger、ReDoc和OpenAPI端点。

健康检查、注册和登录公开，其他业务接口需`Authorization: Bearer <token>`。接口前缀统一`/api/v1`，完整请求、响应、SSE和错误码见[API合同](../docs/api-contract.md)。

## 验证与故障排查

日常优先离线，不需模型额度或真实Redis：

```powershell
.\.venv\Scripts\python.exe -m scripts.evaluate_offline --suite quick --output ../tmp/offline-quick-new.json
.\.venv\Scripts\python.exe -m scripts.evaluate_offline --suite full --include-vectors --output ../tmp/offline-full-new.json
```

输出须使用新路径。向量模式要求已缓存模型；测试和检索使用隔离数据。真实开发集复验、逐条语义复核及质量门槛命令统一见[验证方法](../docs/acceptance/rag-v2-offline.md)，真实模型调用需明确授权。

按改动需要执行依赖、编译及实库检查：

```powershell
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -m compileall -q app scripts
.\.venv\Scripts\python.exe -m scripts.verify_week3_storage --output ../tmp/storage-new.json
```

实库检查需Redis/PostgreSQL，只操作随机schema和命名空间并清理。来源损失排查入口见[验证方法](../docs/acceptance/rag-v2-offline.md#排查入口)。

Redis消息和任务仅在成功成对写入后续期24小时；最多保存20条，上下文最多10条/12000字符。同会话并发返回409，陈旧摘要返回`TASK_CHANGED`。调整模型超时时须同步核对前端72秒等待和代理设置。SSE流开始后的错误通过`error`/`done`事件报告；失败不保存本轮内容，状态恢复与取消语义见[架构](../docs/architecture.md)。
