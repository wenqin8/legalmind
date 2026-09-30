# 交接文档索引

按下列顺序阅读；当前状态以总交接和最终验收为准。

## 核心入口

| 文档 | 回答的问题 |
| --- | --- |
| [项目README](../README.md) | 项目做什么、如何启动 |
| [HANDOFF](../HANDOFF.md) | 做到哪里、还有什么待办、交付边界是什么 |
| [最终验收](acceptance/rag-v2-final-acceptance.md) | 验收结论、指标和证据在哪里 |
| [验证方法](acceptance/rag-v2-offline.md) | 如何跑离线回归和真实复验 |
| [后端说明](../backend/README.md)、[前端说明](../frontend/README.md) | 如何安装、配置和运行 |

## 开发时按需查阅

| 文档 | 用途 |
| --- | --- |
| [MVP需求](mvp-requirements.md) | 功能范围、产品约束和不做清单 |
| [系统架构](architecture.md) | 工作流、检索、存储和故障处理 |
| [数据模型](data-model.md) | 字段、关系和存储约束 |
| [API合同](api-contract.md) | 请求响应、SSE及错误码 |
| [多轮设计](legal-multiturn.md) | 事实来源、冲突确认、文书生成和任务一致性 |

## 随仓库交付

- 配置：[后端环境模板](../backend/.env.example)、[前端环境模板](../frontend/.env.example)、[基础设施Compose](../compose.infrastructure.yml)。真实密钥独立安全交付，不提交`.env`。
- 数据及manifest：[合成案例](../backend/data/demo/README.md)、[基础法规](../backend/data/legal/README.md)、[扩展法规](../backend/data/legal/expansion-v1/README.md)、[交通解释二](../backend/data/legal/traffic-ii-2026/README.md)。
- 评估定义：[查询与标签](../backend/data/evaluation/rag-v1/README.md)、[离线回放](../backend/data/evaluation/offline-v1/README.md)、[门槛配置](../backend/data/evaluation/rag-v2/quality-gates.json)、[交通金标准复查](../backend/data/evaluation/rag-v2/traffic-gold-review.json)。
- 原始证据：整个[acceptance目录](acceptance)，含M1–M3、修复前基线、历次失败及最终Run21报告；最新证据链接集中在[最终验收](acceptance/rag-v2-final-acceptance.md)，历史材料无需逐篇预读。
- Git外文件：[一个月开发计划PDF](../output/pdf/法律咨询Agent一个月开发计划.pdf)，校验值见[HANDOFF](../HANDOFF.md#交付定位)。
