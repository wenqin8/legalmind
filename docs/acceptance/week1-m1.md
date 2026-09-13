# 第一周 M1 最终验收记录

验收日期：2026-09-13

结论：通过

冻结标识：`v0.1.0-m1.2`

## 验收基线

- 计划文件：`output/pdf/法律咨询Agent一个月开发计划.pdf`
- 页数：8
- 文件生成时间：2026-09-13 08:30:41
- SHA-256：`9A49723FEE1AD8BB1610A92BC5C088D5F73E12F622859681F2CC2669C61EBC1D`
- 冲突处理：以该 8 页计划为准；67 页方案仅作架构、功能和界面参考。

新版计划的第一周硬性范围包括两层：

1. Vue 3 → FastAPI → LLM 的可运行、受认证保护的业务切片。
2. LangChain/LangGraph/Chroma/Redis/psycopg 运行依赖，以及 PostgreSQL、Redis、Chroma 的真实连通 smoke test。

基础设施连通不等同于后续业务接入。M1 业务数据仍使用 SQLite；Redis 消息历史、Chroma RAG、PostgreSQL 业务迁移和 LangGraph 工作流仍按后续周次实现。

## 功能闭环

| 验收项 | 结果 | 证据 |
| --- | --- | --- |
| `GET /api/v1/health` | 通过 | 真实 Uvicorn 进程返回 HTTP 200；健康检查公开且不触发模型 |
| 注册、密码哈希、登录 JWT | 通过 | Argon2 哈希、JWT 必需声明、活跃用户回查和统一登录错误均有自动化测试 |
| 非法或缺失 Token | 通过 | `/auth/me` 与 `/chat/send` 返回统一 401；公开端点不附带旧 Token |
| 用户与会话隔离 | 通过 | 会话 UUID 与用户 UUID 在同一查询中过滤；他人会话与不存在会话统一 404，且不调用模型 |
| 浏览器真实模型闭环 | 通过 | 已完成“注册 → 登录签发 JWT → 前端调用受保护 API → DeepSeek 返回真实回答”，约 3.9 秒返回 |
| 密钥边界 | 通过 | DeepSeek、JWT、PostgreSQL、Redis 密钥仅存于被 Git 忽略的 `backend/.env`；测试使用独立配置和假模型 |

## 依赖与基础设施

`backend/requirements.txt` 已显式包含并安装：

- `langchain~=1.4.0`
- `langgraph~=1.2.11`
- `chromadb~=1.5.9`
- `redis~=8.1.0`
- `psycopg[binary]~=3.3.5`

运行依赖导入成功，`pip check` 返回 `No broken requirements found.`。

统一命令：

```powershell
cd backend
.\.venv\Scripts\python.exe -m scripts.smoke_infrastructure
```

最终实测结果：

```json
{
  "ok": true,
  "checked_at": "2026-09-13T06:43:56.308465+00:00",
  "checks": {
    "postgresql": {
      "ok": true,
      "server_version": "17.11"
    },
    "redis": {
      "ok": true,
      "server_version": "7.2.11"
    },
    "chroma": {
      "ok": true,
      "persist_directory": "backend/data/chroma"
    }
  }
}
```

具体探针行为：

- PostgreSQL：连接真实 PostgreSQL 17.11，执行 `SELECT 1` 并读取服务版本；启用 SCRAM，额外确认错误密码被拒绝。
- Redis：连接 Memurai Developer 4.1.7 提供的 Redis API 7.2.11，执行鉴权、`PING`、带 30 秒 TTL 的唯一临时键写入/读取，并在 `finally` 中删除该键；额外确认错误密码被拒绝。
- Chroma：使用 `PersistentClient` 在本地持久化目录创建唯一临时集合，写入显式向量并查询同一文档，最后删除该集合。
- 服务仅监听 `127.0.0.1`。验收未输出任何连接 URL 或密码。

本机 WSL 与 VirtualMachinePlatform 已启用，Windows 返回 `3010`，需重启后生效。由于不能擅自重启用户电脑，本次先使用 Windows 原生 PostgreSQL 与 Redis 兼容服务完成真实连通；仓库同时提供 `compose.infrastructure.yml`，第 4 周在 Docker Desktop 中复验。

## 自动化回归

| 检查 | 结果 |
| --- | --- |
| 后端测试 | 94 passed |
| Python `compileall` | 通过 |
| 运行依赖导入 | 通过 |
| `pip check` | 无冲突 |
| 前端测试 | 11 files / 34 tests passed |
| TypeScript 类型检查 | 通过 |
| Vite 生产构建 | 通过 |

新增 smoke 相关自动化测试覆盖：基础设施密钥配置脚本幂等性、连接 URL 序列化脱敏、相对 Chroma 路径解析，以及 Chroma 本地持久化往返和探针集合清理。

## 交付判定

第一周全部验收项均有实现或真实运行证据，没有剩余阻断项。`v0.1.0-m1.2` 是按新版计划形成的最终第一周冻结点；既有 `v0.1.0-m1` 与 `v0.1.0-m1.1` 保留作为历史快照，不移动、不覆盖。
