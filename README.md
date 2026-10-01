# LegalMind — 法律咨询 Agent

面向课程演示和本地部署的中国大陆法律咨询MVP，覆盖婚姻家庭、劳动争议、交通事故、合同纠纷。提供法律问答与多轮补充、案例检索、民事起诉状/答辩状/通用合同草稿及Markdown/TXT下载。

> AI内容仅供参考，不构成法律意见。合成案例不是真实判例；法规使用本地核验快照，不在每次回答时实时更新。

## 当前状态

第四周课程MVP工程交付完成：SSE、停止/重试、历史恢复、来源卡片、案例和文书页面，以及本机Docker Compose/Nginx部署。后端686项离线、前端58项测试及类型/构建通过；隔离浏览器9组、实际部署浏览器4组与重启后运行9项通过。24题首次执行HTTP/行为24/24、硬性失败0，限额160内实际134次请求。2026-10-02项目方决定用AI法律内容复核替代外部专家复核，确认24题复核通过、24/24未发现阻断性问题，课程MVP按该口径验收通过；见[验收决定](docs/acceptance/m4-project-acceptance-20261002.md)。保留原报告与历史专家门槛，不登记为专家认证或独立盲测；Chroma依赖风险及MF04原题真实复验边界保留。本地版本标签为`m4`。工程证据见[M4收尾](docs/acceptance/m4-course-mvp-closeout-20261001.md)，交付包见[复核后补充交付](docs/acceptance/m4-reviewed-closeout-20261001.md)。

默认应用使用60条法规和16条合成案例；209条扩展法规仅用于隔离评估，两者明确显示资料版本，不共用验收成绩。

2026-10-02当前Docker环境再次验证：部署烟测14/14、运行检查9/9通过，模型调用0。包含最终验收决定的新完整包及当前交付边界见[作业提交前复验](docs/acceptance/m4-submission-closeout-20261002.md)。

## 启动

1. 按[后端说明](backend/README.md)配置本地密钥、启动Redis、执行迁移与数据准备，再启动FastAPI。
2. 按[前端说明](frontend/README.md)安装依赖并执行`npm run dev`。
3. 访问`http://127.0.0.1:5173/`；后端健康检查为`GET /api/v1/health`。

日常使用SQLite，数据库位于`backend/data/legalmind.db`；聊天历史与任务保存在Redis，成功写入后续期24小时。前端刷新时从服务端恢复当前会话，退出登录清理页面消息和会话指针；独立文书不随会话删除。

## 文档

- [交接文档索引](docs/handoff-index.md)：阅读顺序、运行配置和证据入口。
- [MVP需求](docs/mvp-requirements.md)、[架构](docs/architecture.md)、[数据模型](docs/data-model.md)、[API合同](docs/api-contract.md)、[多轮设计](docs/legal-multiturn.md)。
- [离线验证方法](docs/acceptance/rag-v2-offline.md)：日常测试不调用真实模型。

Git外开发计划PDF及校验值见[交付定位](HANDOFF.md#交付定位)，须随仓库单独交付。

完整本地部署入口见[部署说明](deployment/README.md)，使用独立PostgreSQL及数据卷。

本机部署入口为 `http://127.0.0.1:8080`；账户、文书、案例、取消、历史恢复及重启保留已验证。真实咨询曾通过部署检查，本轮未重新探测模型可用性。
