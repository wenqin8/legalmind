# LegalMind Frontend

第 1 周第 5 天的 Vue 3 前端，包含首页、注册/登录、受保护的咨询台、Pinia 状态、统一 API 客户端和 Tailwind 视觉系统。

咨询台通过 `POST /api/v1/chat/send` 调用当前后端模型。当前阶段使用同步回答，不包含 SSE、RAG 或来源详情；界面不会伪造法规和案例来源。

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

默认访问地址：`http://127.0.0.1:5173/`。首页和 `/auth` 公开；`/chat` 要求登录，游客会被送到登录页；未知地址会显示项目内的 404 页面。

Vite 会把 `/api` 代理到 `http://127.0.0.1:8000`。后端未启动时页面仍可打开，顶部状态显示“仅前端预览”；后端启动后会通过 `GET /api/v1/health` 显示 API 版本。

注册成功后前端会自动登录。JWT 和公开用户资料只保存在 `sessionStorage`，密码不落地；应用重载时通过 `GET /api/v1/auth/me` 校验已有会话，校验失败即清理本地登录态。

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

M1 冻结前实测结果：9 个测试文件、26 项测试全部通过，TypeScript 检查和生产构建通过，使用 npm 官方 registry 审计为 0 个已知漏洞。浏览器已验证注册/登录、真实问答、刷新恢复、退出保护与桌面/390px/320px 布局，控制台无错误。
