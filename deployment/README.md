# 完整本地部署

本部署使用独立 PostgreSQL、Redis、Chroma 和模型缓存卷，应用入口只绑定本机。日常 SQLite 与原有基础设施 Compose 不参与初始化。已在Windows 11 build 26100、WSL 3.0.1、Docker Desktop 4.93.0上完成干净卷启动与重启保留；Engine 29.8.1、Compose 5.5.1，见[M4证据](../docs/acceptance/m4-progress.md)。

## 首次启动

在仓库根目录执行：

```powershell
python deployment/init_env.py
```

该脚本仅使用Python标准库，新克隆环境需要Python 3.11+，无需先安装后端虚拟环境。它新建 `deployment/.env`并生成三项独立密钥；已有文件保持原样。请在本地配置 DeepSeek API Key，密钥不要写入前端或 Git。启动与下列部署烟测均不发起真实模型调用；实际法律咨询会使用所配置的模型。开发和交接入口见[开发者指南](../docs/developer-onboarding.md)。

```powershell
powershell -ExecutionPolicy Bypass -File deployment\start.ps1
```

访问 `http://127.0.0.1:8080`。首次构建安装现有后端依赖，初始化下载固定 revision 的 BGE 权重；需可访问对应包与模型源。初始化依次执行迁移、导入16条演示案例与60条默认法规、建立64块向量索引。后端在初始化成功、数据库和Redis健康后启动，前端在后端健康后启动。初始化失败时停止，不宣称部署完成。

Nginx 使用 SPA 路由回退，API 响应关闭缓冲和缓存；代理超时75秒，前端72秒，后端默认总预算65秒。应用使用单个 Uvicorn worker，限流为进程内固定窗口：认证20次/分钟、业务120次/分钟。经本地代理访问的用户共享后端客户端配额，适用于本地演示；不宣称分布式或面向公众的生产限流。

启动脚本支持Docker Desktop按用户安装位置，无需修改系统PATH。后端镜像以非root运行，使用CPU PyTorch，不安装未使用的CUDA依赖；`.env`、本地数据库和npm缓存不进入构建上下文。

## 干净环境验收

使用新的 Compose 项目名及未使用的端口，避免复用旧卷；不要删除已有卷：

```powershell
# 在 deployment/.env 设置一个未使用的 LEGALMIND_HTTP_PORT，例如18080
powershell -ExecutionPolicy Bypass -File deployment\start.ps1 -ProjectName legalmind-clean-001
cd backend
.\.venv\Scripts\python.exe -m scripts.verify_deployment --base-url http://127.0.0.1:18080 --output ../tmp/deployment-clean-001.json
```

烟测经过 Nginx，检查认证、真实案例索引、三类文书下载、SSE协议、真实Redis历史和跨用户拒绝访问；仅创建合成验收账户及文书，删除本轮咨询。生成文书和合成账户保留在这个专用验收项目中，便于重启检查。烟测不验证新模型法律回答。

随后重启服务，再次检查账户可登录、旧文书可下载和索引可检索，记录 Docker/Compose版本、镜像ID、操作系统、初始化计数和日志结果。另执行正常、空结果、超时、断流、非法令牌五类演示；模型及故障场景的检查方式见 M4 验收说明。

```powershell
docker compose --env-file deployment/.env -f compose.yml -p legalmind-clean-001 restart
docker compose --env-file deployment/.env -f compose.yml -p legalmind-clean-001 ps
docker compose --env-file deployment/.env -f compose.yml -p legalmind-clean-001 logs --tail 100
```

以上命令在仓库根目录执行。不要把 `docker compose config` 的完整输出或容器环境输出用于分享，因为插值后包含密钥；验证使用 `config --quiet`。

停止用 `docker compose ... down`，保留卷；不使用 `down -v` 作为普通排查步骤。更新已有真实运行库前先备份；本包不执行日常数据迁移。

## 当前本机验收部署

项目名为`legalmind-clean-20261001`，入口`http://127.0.0.1:8080`。MF04修复后仅重建并更新后端，无迁移或删卷；[烟测Run3](../docs/acceptance/m4-deployment-smoke-20261001-run3.json)14/14、[运行Run7](../docs/acceptance/m4-deployment-runtime-20261001-run7.json)9/9、[代码指纹](../docs/acceptance/m4-deployed-rag-files-20261001.json)9文件与宿主一致，零模型调用。存储仍是实际PostgreSQL和Redis，默认16案例/60法规/64分块。

课程收尾的[存储浏览器Run15](../docs/acceptance/m4-deployed-browser-20261001-run15.json)4/4，[重启后运行Run8](../docs/acceptance/m4-deployment-runtime-20261001-run8.json)9/9，均无模型调用。真实咨询浏览器Run12曾4/4通过，Run13在来源等待时超时，同期供应商HTTP 402；新提示效果及供应商可用性未重测。按用户确认先交付课程MVP，法律质量验收保留未完成，案例、文书、取消和历史等零模型路径可使用。交付包与校验见[收尾清单](../docs/acceptance/m4-course-mvp-closeout-20261001.md)。

已升级可修复的Python依赖，requirements自动载入constraints；Chroma上游公告仍未消除，当前仅使用嵌入模式且不开放其HTTP接口。依赖结果与部署边界见[安全复核](../docs/acceptance/m4-security-review-20261001.md)。

在仓库根目录采集非敏感运行证据：

```powershell
backend\.venv\Scripts\python.exe deployment\collect_evidence.py --project legalmind-clean-20261001 --docker "$env:LOCALAPPDATA\Programs\DockerDesktop\resources\bin\docker.exe" --output tmp\deployment-runtime-new.json
```

在frontend目录进行真实存储浏览器与专用项目重启检查，报告须使用新的项目内绝对路径：

```powershell
$env:LEGALMIND_DOCKER_CLI="$env:LOCALAPPDATA\Programs\DockerDesktop\resources\bin\docker.exe"
$env:PATH=(Split-Path $env:LEGALMIND_DOCKER_CLI)+';'+$env:PATH
$env:LEGALMIND_E2E_OUTPUT=(Join-Path (Resolve-Path ..).Path 'tmp\deployed-browser-new.json')
node scripts/deployed-e2e.mjs --storage-only
```

该脚本只重启`legalmind-clean-20261001`。`--storage-only`显式取消且零模型调用；恢复账户后可用`--allow-real-model`代替，进行一次真实咨询和来源/刷新检查，该命令使用API额度，不能把存储模式当作模型质量证明。

启动顺序依据 [Docker Compose官方说明](https://docs.docker.com/compose/how-tos/startup-order/)，关闭流缓冲依据 [Nginx官方代理说明](https://nginx.org/en/docs/http/ngx_http_proxy_module.html#proxy_buffering)。
