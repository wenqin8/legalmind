# 交接文档索引（2026-09-30）

前三阶段已完成：基线单独冻结、阻断修复、Run21开发集验收通过，用户已在会话中确认人工复核完成并允许交接。实现与验收提交为`2095704`；失败证据另存`9d68172`、`63d43b9`，修复前基线为`6fb2996`。第四周界面不在本次已完成范围。

## 首先阅读

| 文档 | 用途 |
| --- | --- |
| [HANDOFF](../HANDOFF.md) | 当前状态、完成范围、后续待办及历史 |
| [项目README](../README.md) | 项目定位、功能和启动入口 |
| [最终验收与人工复核确认](acceptance/rag-v2-final-acceptance.md) | Run21结果、前三阶段结论及遗留问题 |
| [离线验证说明](acceptance/rag-v2-offline.md) | 不调用模型的日常回归方法 |
| [质量根因记录](acceptance/rag-v1-root-causes.md) | 修复前问题与原因 |

## 需求与实现合同

- [MVP需求与范围](mvp-requirements.md)
- [系统架构](architecture.md)
- [数据模型](data-model.md)
- [API合同](api-contract.md)
- [法律引用与多轮补充设计](legal-multiturn.md)

## 当前验收证据

| 文件 | 用途 |
| --- | --- |
| [Run21原始回答](acceptance/rag-v2-development-answers-run21.json) | 全部36场景、52轮真实运行 |
| [Run21结构评审](acceptance/rag-v2-development-review21.md) | 行为、来源召回及失败指标；[JSON](acceptance/rag-v2-development-review21.json) |
| [Run21语义记录](acceptance/rag-v2-development-semantic-run21.json) | 26条开发代理逐条复核，绑定原始报告哈希；用户人工完成确认另记于最终验收文档 |
| [Run21质量门槛](acceptance/rag-v2-development-gates-run21.json) | 最终开发门槛通过 |
| [Run21检索结果](acceptance/rag-v2-development-retrieval-run21.json) | 120开发查询、240检索路由 |
| [Run21完整离线报告](acceptance/rag-v2-final-offline-run21.json) | 425项通过、零真实模型调用 |
| [Run21保全核对](acceptance/rag-v2-preservation-run21.json) | 默认计数、冻结文件、PDF、M3及实现指纹 |
| [质量门槛配置](../backend/data/evaluation/rag-v2/quality-gates.json) | 冻结阈值和评估范围 |
| [评估集说明](../backend/data/evaluation/rag-v1/README.md) | 查询、相关性标签与边界 |
| [离线回放说明](../backend/data/evaluation/offline-v1/README.md) | 回放样本和使用方法 |

## 历史和失败证据

整个[docs/acceptance目录](acceptance)一并交付，包含M1、M2及全部原始回答、失败报告和语义记录。不要仅保留最新通过结果。

- [M3验收](acceptance/week3-m3.md)、[法律引用与多轮补充验收](acceptance/legal-multiturn.md)。
- [RAG-v1基线](acceptance/rag-v1.md)、[RAG-v2早期验收](acceptance/rag-v2.md)、[前轮恢复记录](acceptance/rag-v2-resumed.md)。
- [Run14评审](acceptance/rag-v2-development-review14.md)、[语义记录](acceptance/rag-v2-development-semantic-run14.json)、[未通过门槛](acceptance/rag-v2-development-gates-run14.json)。
- [Run16未完成尝试](acceptance/rag-v2-targeted-run16.json)：`complete=false`、基础设施`TimeoutError`，已提交留存，不是通过证据。
- Run17、Run19、Run20的失败和后续定向复验均保留；逐项链接见[最终验收历史表](acceptance/rag-v2-final-acceptance.md)。

## 运行配置与资料

- [后端运行说明](../backend/README.md)、[前端运行说明](../frontend/README.md)。
- [后端环境模板](../backend/.env.example)、[前端环境模板](../frontend/.env.example)、[基础设施Compose](../compose.infrastructure.yml)。
- [合成案例说明](../backend/data/demo/README.md)、[基础法规资料](../backend/data/legal/README.md)、[扩展法规资料](../backend/data/legal/expansion-v1/README.md)。
- [交通事故解释二资料](../backend/data/legal/traffic-ii-2026/README.md)、[交通题金标准复查](../backend/data/evaluation/rag-v2/traffic-gold-review.json)。

上述数据目录及对应manifest随仓库交付；真实密钥通过独立安全渠道配置，不提交`.env`。默认应用锁定`demo-m3-60`（60条），扩展评估锁定`eval-rag-v2-209`（209条），不可把评估成绩套到默认应用。

## Git外文件及遗留事项

[法律咨询Agent一个月开发计划PDF](../output/pdf/法律咨询Agent一个月开发计划.pdf)必须单独保留和交付，SHA-256：

```text
9A49723FEE1AD8BB1610A92BC5C088D5F73E12F622859681F2CC2669C61EBC1D
```

Run21行为匹配96.15%，最终来源Recall81.25%；仍有`E-L-MF-02:1`、`E-L-CD-02:1`两条424，以及少量重复或不协调表述，作为后续可用性改进保留。已观察保留集不能称为盲测；第四周界面、服务端历史恢复等按后续计划继续。
