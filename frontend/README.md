# LegalMind Frontend

LegalMind 的 Vue 3 前端，包含应用入口首页、注册与登录、受保护的法律咨询工作台、公开说明页面、Pinia 状态、统一 API 客户端和 Tailwind 视觉系统。

咨询页使用认证 POST SSE，支持增量显示、停止、重试、服务端会话分页与刷新恢复。正文在成功 done 前标为待确认；失败片段标为未完成。已取得会话标识的断流重试先核对服务端历史，避免重复已提交轮次。来源卡片显示官方原文、版本、时间状态及过渡规定；确认按钮发送 task_revision。案例搜索/详情与三类结构化文书页面已接入。

## 页面与交互

- `/`：公开首页。首屏可直接输入问题并进入咨询流程，也可从婚姻家庭、劳动争议、交通事故和合同纠纷四个领域开始；游客会先完成登录，再返回咨询页继续。
- `/auth`：公开的登录与注册页。桌面端保留左右分栏，移动端优先显示表单，品牌介绍位于表单下方；完整版使用边界仅在注册状态展示。
- `/guide`：公开的使用说明，区分合成演示案例与本地核验官方条文，并说明逐轮补齐和文书确认流程。
- `/privacy`：公开的隐私说明，解释浏览器会话、账户密码、应用数据库和配置的 AI 服务之间的数据流转。
- `/about`：公开的关于页面，集中说明项目属性、部署方式、首批支持领域和服务边界。
- `/chat`：受登录保护的流式咨询台。服务端记录分页、读取、删除；标签页只额外保存当前会话ID，刷新后从服务端恢复消息和任务。历史过期时提示重新补充事实；退出登录会停止本轮请求并清理页面状态。停止生成与取消业务任务是两个操作。
- `/cases`、`/cases/:id`：案例搜索、领域筛选、结果与详情，保留演示标识和来源说明。
- `/documents`：由模板API驱动的三类表单；填写后先核对摘要，确认才生成。修改内容会撤销未提交的摘要确认；草稿可复制并下载Markdown/TXT。
- 其他地址：显示应用内 404 页面。

公共页面使用统一页脚链接到使用说明、隐私说明和关于页面；咨询应用壳专注于当前任务，不显示公共页脚。顶部通过 `GET /api/v1/health` 检查后端，仅展示“正在连接服务”“服务正常”或“服务暂不可用”，不向用户暴露技术版本号。

## 环境要求

- Node.js `^22.22.2`、`^24.15.0` 或 `>=26.0.0`；当前验收环境为 Node.js 24.15.0
- npm 11 或兼容版本

## 安装和启动

首次安装：

```powershell
cd frontend
npm install
```

以后可根据锁文件复现安装：

```powershell
npm ci
```

启动开发服务器：

```powershell
npm run dev
```

默认访问地址：`http://127.0.0.1:5173/`。

Vite 会把 `/api` 代理到 `http://127.0.0.1:8000`。后端暂不可用时，公开页面仍可打开，顶部会显示对应的服务状态。

注册成功后前端会自动登录。JWT 和公开用户资料只保存在 `sessionStorage`，前端不会主动持久化密码；后端保存密码哈希而非明文。应用重载时通过 `GET /api/v1/auth/me` 校验已有会话，校验失败即清理本地登录态。咨询台通过 `POST /api/v1/chat/stream` 调用后端配置的 AI 服务，并通过 `DELETE /api/v1/chat/history/{session_id}` 删除已有会话归属和 Redis 消息，独立文书不随会话删除。

## 配置

默认 API 基址为 `/api/v1`。如需覆盖，可复制 `.env.example` 为 `.env` 并修改：

```dotenv
VITE_API_BASE_URL=/api/v1
```

所有 `VITE_` 变量都会进入浏览器构建产物，因此这里不得放入 DeepSeek Key、JWT 私钥或其他秘密。DeepSeek Key 只能保存在后端本地 `.env`。

## 验证

```powershell
npm run typecheck
npm run test
npm run build
```

当前15个单元/组件测试文件、58项测试通过，覆盖流协议分块、认证、会话恢复/过期、断流后的提交核对、退出时取消、来源校验与文书摘要确认。完整M4进度和证据见[阶段验收](../docs/acceptance/m4-progress.md)。

浏览器回归运行隔离SQLite/Chroma、确定性模型和测试会话存储，不使用日常库、真实模型或真实Redis：

```powershell
# 安装Playwright Chromium（或使用已安装的Edge）
npx playwright install chromium
npm run test:e2e
# Windows已有Edge时：
$env:LEGALMIND_E2E_BROWSER_CHANNEL='msedge'
npm run test:e2e
```

测试使用本机8011和5173端口，已有监听时拒绝接管。每次创建新tmp目录并保存报告；可用`LEGALMIND_E2E_OUTPUT`指定新的报告路径。`LEGALMIND_DEV_API_TARGET`仅用于开发服务器代理测试后端，默认日常地址仍为8000。Playwright仅是开发依赖。

完整Compose及Nginx部署见[部署说明](../deployment/README.md)。

已完成本机Nginx页面的真实PostgreSQL/Redis浏览器检查和重启保留，移动导航在320、390、640px无重叠。部署浏览器脚本显式区分零模型存储检查与真实咨询；真实模型质量仍待完成，不能以隔离浏览器通过替代。
