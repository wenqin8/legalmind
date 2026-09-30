# LegalMind - 法律咨询 Agent

面向课程演示和本地部署的中国大陆法律咨询 MVP。第三周 M3 已实现意图识别、RAG、三类固定文书、LangGraph、Redis 多轮历史与 SSE，并扩展官方法条引用、问答补事实和文书逐轮补字段；已本地冻结为 `v0.1.0-m3`。后续 RAG-v1 基线单独提交，RAG-v2 修复与开发集回归见验收记录。

> AI 生成内容仅供参考，不构成法律意见。16 条合成案例不是真实判例；60 条官方条文使用本地核验快照，未在每次回答时实时联网更新，具体适用条件仍须核对。

## 当前进度

- M1–M3 已本地冻结，最新标签 `v0.1.0-m3`，提交 `c399d78`；按用户要求不配置或推送远端。
- [RAG-v1 评估基线](docs/acceptance/rag-v1.md)单独冻结于 `6fb2996`，保留修复前失败证据。当前 [RAG-v2 修复验收](docs/acceptance/rag-v2.md)只用120条开发查询和36个开发场景；修复QA更正路由、法条漏检、直接证据选择和逐句支持检查，增加交通解释二12条，隔离评估共209条。默认库明确锁定60条演示版，响应显示资料边界，不能沿用209条库的成绩。
- 日常开发默认运行 [离线回归](docs/acceptance/rag-v2-offline.md)：测试、冻结检索、记录回放及旧答案复算，真实模型调用为0。真实验收命令需显式开启，离线通过不等于新模型答案质量通过。
- 最新[完整开发集复验](docs/acceptance/rag-v2-final-acceptance.md)：425项离线通过；最终Run21真实行为50/52（96.15%）、四组更正4/4、资料不足安全输出8/8、直接Hit@5为44/44、最终来源Recall81.25%。26条成功法律答复已逐条开发代理复核，冻结开发门槛通过；仍有两条424，独立人工法律复核未完成，不宣称整个项目全部交付或盲测通过。Run16未完成尝试及Run17、Run19、Run20失败证据均保留。
- M3 后端提供 `qa/search/document` 三分支、受控引用、文书逐轮补齐和摘要确认、Markdown/TXT 下载、会话列表/历史/删除及逐段校验的 SSE。任务状态含字段原句和用户消息来源；冲突需确认，过期重新补充。
- 继续使用 SQLite；迁移兼容 PostgreSQL，已完成随机隔离 schema 实测。Redis 已接入业务历史，24 小时滑动 TTL，最多 20 条消息。
- M2 数据和排名参数未改：16 条合成案例、64 块、固定 BGE/Chroma + BM25/RRF；冻结评估为 20/20。本周真实 BGE、DeepSeek、Redis 联调通过。
- 前端继续同步交互，已提供官方条文来源卡片、缺项追问及确认/取消按钮。SSE 界面、服务端记录恢复、独立案例/文书页及完整 Docker 部署留第四周。
- [法条与多轮扩展](docs/legal-multiturn.md)、[官方数据范围和更新](backend/data/legal/README.md)、[扩展验收](docs/acceptance/legal-multiturn.md)。
- [交接与下一步](HANDOFF.md)、[M3 验收记录](docs/acceptance/week3-m3.md)、[M2 验收记录](docs/acceptance/week2-m2.md)、[M1 验收记录](docs/acceptance/week1-m1.md)。

## 启动入口

1. 按[后端说明](backend/README.md)配置本地密钥，启动 Redis，执行迁移、导入及索引，再启动 FastAPI。
2. 按[前端说明](frontend/README.md)安装依赖并运行 `npm run dev`。
3. 打开 `http://127.0.0.1:5173/`，注册、登录并进入咨询页；健康检查为 `GET /api/v1/health`。

日常数据库仍为 `backend/data/legalmind.db`。当前迁移头为 `20260918_0004`，在文书表和会话提交标记基础上增加法条核验元数据；升级后执行 `python -m scripts.import_verified_laws`。聊天要求真实 Redis；Redis 故障会明确返回错误，不回退进程内历史。离线假模型仅用于开发，无法确认相关证据时返回依据不足提示。

咨询页“新建咨询”归档当前页面内的消息，可切换和删除。页面刷新或退出登录会清除浏览器临时记录；后端 Redis 消息仍按 TTL 保留，恢复这些记录的页面将在第四周接入。删除会话会清理该会话归属和 Redis 消息；独立保存的文书不会随会话删除。

## 文档与基线

- [MVP 需求与范围](docs/mvp-requirements.md)
- [当前架构](docs/architecture.md)
- [数据模型](docs/data-model.md)
- [API 合同](docs/api-contract.md)
- [演示数据边界](backend/data/demo/README.md)
- [冻结 M2 检索报告](docs/acceptance/week2-retrieval-evaluation.json)

原始 8 页开发计划 PDF 必须单独交付：`output/pdf/法律咨询Agent一个月开发计划.pdf`，SHA-256 为 `9A49723FEE1AD8BB1610A92BC5C088D5F73E12F622859681F2CC2669C61EBC1D`。该文件不在 Git 提交中，本周未修改。
