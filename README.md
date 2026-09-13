# LegalMind - 法律咨询 Agent

面向课程演示和本地部署的中国大陆法律咨询 MVP。第一周 M1 已打通认证和真实模型问答；第二周 M2 已交付可追溯演示数据管线、持久化混合检索与受保护的案例 API。聊天 RAG、多轮会话与文书生成仍属后续里程碑。

> 本项目输出由人工智能生成，仅用于课程演示和一般信息参考，不构成法律意见，也不能替代律师或其他专业人士的判断。

## 当前进度

- 阶段：第 2 周 M2 已实现并经用户确认验收；冻结标识为 `v0.1.0-m2`
- 状态：16 条 `DEMO-*` 课程演示合成案例已完成严格导入、64 块持久化索引和 BM25/RRF 混合检索；固定真实 BGE 的 20 条评估查询 Top-5 命中 `20/20`
- 闭环：已在浏览器实测“注册 → 登录签发 JWT → 前端调用受保护 API → DeepSeek 返回真实回答”
- 界面：已完成产品化信息架构优化；首页可直接发起咨询，移动端登录表单优先，咨询页使用独立应用壳，项目属性集中在关于页面
- 交接状态：[HANDOFF](HANDOFF.md)

## 工程入口

- [后端启动、配置与测试说明](backend/README.md)
- [前端启动、配置与测试说明](frontend/README.md)
- 健康检查：`GET /api/v1/health`
- 前端开发地址：`http://127.0.0.1:5173/`，咨询页：`http://127.0.0.1:5173/chat`；另有 `/guide`、`/privacy`、`/about` 三个公开说明页面
- 当前咨询台调用受 JWT 保护的 `POST /api/v1/chat/send`；运行时按后端 `.env` 选择 DeepSeek 或离线假模型
- “新建咨询”会在当前页面内归档已有消息，并可从桌面侧栏或移动端“记录”菜单切换回来；每条记录支持确认后删除，已有后端会话同时通过受保护的 `DELETE /api/v1/chat/history/{session_id}` 删除
- 页面刷新或退出登录仍会清除前端临时记录；后端尚未保存消息正文，也不会把此前问答作为模型上下文
- 聊天问答尚未接入 RAG、Redis 消息历史或 LangGraph；案例检索已通过 `POST /api/v1/cases/search` 和 `GET /api/v1/cases/{case_id}` 独立交付，两个接口均要求 JWT
- 原始演示案例及边界见 [`backend/data/demo`](backend/data/demo/README.md)，冻结评估集及真实模型逐条排名见 [`week2-retrieval-evaluation.json`](docs/acceptance/week2-retrieval-evaluation.json)

## 设计文档

- [MVP 需求与范围基线](docs/mvp-requirements.md)
- [系统架构与工作流](docs/architecture.md)
- [数据模型](docs/data-model.md)
- [API 合同](docs/api-contract.md)

## 首月最终交付范围（非第一周 M1）

“首月 MVP”指四周结束时的目标；“第一周 M1”指已经验收的可运行切片。M1 的业务链路是 Vue 3 → FastAPI → 可注入 LLM，并以本地 SQLite 保存用户与会话归属。PostgreSQL、Redis 和 Chroma 已完成独立的真实连通与持久化 smoke test，但尚未替代 SQLite 或接入问答、消息历史和 RAG 业务链路；LangChain/LangGraph 已列入运行依赖，工作流仍按第三周实现。

第一周证据见 [M1 验收记录](docs/acceptance/week1-m1.md)，第二周证据见 [M2 验收记录](docs/acceptance/week2-m2.md)。

- Vue 3 前端与 FastAPI 后端
- DeepSeek OpenAI 兼容接口
- LangGraph 三类意图工作流
- Chroma 本地持久化 RAG
- PostgreSQL 业务数据与 Redis 会话数据
- 注册、JWT 登录和用户会话隔离
- Docker Compose 本地部署

具体范围、验收规则和不做清单以需求基线为准。
