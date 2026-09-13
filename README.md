# LegalMind - 法律咨询 Agent

面向课程演示和本地部署的中国大陆法律咨询 MVP。第一周 M1 已打通用户注册、JWT 登录、受保护的同步问答和 DeepSeek 真实调用；来源检索、多轮会话与文书生成将在后续里程碑接入。

> 本项目输出由人工智能生成，仅用于课程演示和一般信息参考，不构成法律意见，也不能替代律师或其他专业人士的判断。

## 当前进度

- 阶段：第 1 周 M1 及补充验收已完成；原冻结标识为 `v0.1.0-m1`，补充闭环标识为 `v0.1.0-m1.1`
- 状态：后端 89 项、前端 34 项自动化测试通过；类型检查、生产构建、依赖检查和 Alembic 迁移校验通过
- 闭环：已在浏览器实测“注册 → 登录签发 JWT → 前端调用受保护 API → DeepSeek 返回真实回答”
- 界面：已完成产品化信息架构优化；首页可直接发起咨询，移动端登录表单优先，咨询页使用独立应用壳，项目属性集中在关于页面
- 交接状态：[HANDOFF](HANDOFF.md)

## 工程入口

- [后端启动、配置与测试说明](backend/README.md)
- [前端启动、配置与测试说明](frontend/README.md)
- 健康检查：`GET /api/v1/health`
- 前端开发地址：`http://127.0.0.1:5173/`，咨询页：`http://127.0.0.1:5173/chat`；另有 `/guide`、`/privacy`、`/about` 三个公开说明页面
- 当前咨询台调用受 JWT 保护的 `POST /api/v1/chat/send`；运行时按后端 `.env` 选择 DeepSeek 或离线假模型
- 当前尚未接入 RAG、Redis 消息历史或 LangGraph 运行工作流；LangGraph 仅完成依赖准备。回答会明确告知无可核验来源，不伪造法条和案例

## 设计文档

- [MVP 需求与范围基线](docs/mvp-requirements.md)
- [系统架构与工作流](docs/architecture.md)
- [数据模型](docs/data-model.md)
- [API 合同](docs/api-contract.md)

## 首月最终交付范围（非第一周 M1）

“首月 MVP”指四周结束时的目标；“第一周 M1”指已经验收的可运行切片。M1 的实际链路是 Vue 3 → FastAPI → 可注入 LLM，并以本地 SQLite 保存用户与会话归属。PostgreSQL 仅完成驱动和可配置 URL 预留，未完成实库验收；Redis、Chroma 未接入；LangGraph 已列入运行依赖，但工作流仍按第三周计划实现。

- Vue 3 前端与 FastAPI 后端
- DeepSeek OpenAI 兼容接口
- LangGraph 三类意图工作流
- Chroma 本地持久化 RAG
- PostgreSQL 业务数据与 Redis 会话数据
- 注册、JWT 登录和用户会话隔离
- Docker Compose 本地部署

具体范围、验收规则和不做清单以需求基线为准。
