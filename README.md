# LegalMind — 法律咨询 Agent

面向课程演示和本地部署的中国大陆法律咨询MVP，覆盖婚姻家庭、劳动争议、交通事故、合同纠纷。提供法律问答与多轮补充、案例检索、民事起诉状/答辩状/通用合同草稿及Markdown/TXT下载。

> AI内容仅供参考，不构成法律意见。合成案例不是真实判例；法规使用本地核验快照，不在每次回答时实时更新。

## 当前状态

M3业务能力及后续RAG修复已完成，开发验收通过，用户已确认人工复核完成。前端支持同步咨询、官方来源卡片及任务确认；服务端历史恢复、SSE界面、独立案例/文书页和完整Docker部署留第四周。当前待办见[项目交接](HANDOFF.md)，指标及原始依据见[最终验收](docs/acceptance/rag-v2-final-acceptance.md)。

默认应用使用60条法规和16条合成案例；209条扩展法规仅用于隔离评估，两者明确显示资料版本，不共用验收成绩。

## 启动

1. 按[后端说明](backend/README.md)配置本地密钥、启动Redis、执行迁移与数据准备，再启动FastAPI。
2. 按[前端说明](frontend/README.md)安装依赖并执行`npm run dev`。
3. 访问`http://127.0.0.1:5173/`；后端健康检查为`GET /api/v1/health`。

日常使用SQLite，数据库位于`backend/data/legalmind.db`；聊天历史与任务保存在Redis，成功写入后续期24小时。当前前端刷新或退出后清除本地消息，尚未接入服务端历史恢复；独立文书不随会话删除。

## 文档

- [交接文档索引](docs/handoff-index.md)：阅读顺序、运行配置和证据入口。
- [MVP需求](docs/mvp-requirements.md)、[架构](docs/architecture.md)、[数据模型](docs/data-model.md)、[API合同](docs/api-contract.md)、[多轮设计](docs/legal-multiturn.md)。
- [离线验证方法](docs/acceptance/rag-v2-offline.md)：日常测试不调用真实模型。

Git外开发计划PDF及校验值见[交付定位](HANDOFF.md#交付定位)，须随仓库单独交付。
