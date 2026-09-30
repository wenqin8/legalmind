# RAG 开发集最终复验（2026-09-30）

当前已完成第一阶段基线冻结、第二阶段阻断修复，以及第三阶段的完整开发集真实运行和开发代理逐条复核。**Run21 冻结开发门槛通过；用户已确认人工复核完成，前三阶段可完成交接。** 仍有两轮服务失败和少量表达问题，第四周界面尚未实施，不代表整个项目全部交付或盲测通过。

人工复核确认（2026-09-30）：用户在本会话明确表示“我已人工复核完成，现在可以完成交接。”据此关闭人工复核待办；未另附逐条人工批注，本记录不推定复核者资质、不改写原始评估文件或哈希。交接范围见[文档索引](../handoff-index.md)。

## 阶段判断与本轮改动

接手时第一阶段已经完成：修复前基线单独提交为 `6fb2996`；QA 补充/更正/确认路由、口语漏检、未知领域检索、直接依据筛选、逐句结论支持校验及三种输出策略均已有实现。原始 64.29% 行为匹配、25/40 场景、42.29% 最终来源 Recall 是修复前全量基线，不能当作当前版本成绩。Run14 虽有较高自动指标，语义尚未通过，接手点实际处在第三阶段复验未完成、仍需第二阶段补修的状态。

本轮按真实失败证据补修：

- 返还社保补偿保留“有前款规定情形”的条件回指，防止缩写成只要补缴即可返还；不自行决定前款各情形的逻辑关系。
- 营养费“参照医疗机构意见”不能反推意见不是必要条件、无需意见也能获得赔偿。增加确定性已知错误保护及提示约束；原有两次语义审核继续执行。这些保护只覆盖已观察模式，不是通用法律逻辑证明。
- 字段提取的重复字段被丢弃时，先保留可识别法律领域，防止旧合同问题绕过法律任务误入演示问答。曾尝试过宽的领域回退导致 7 个既有测试失败，随后收窄至有效提取阶段，保留全部失败证据。
- 新增 15 个离线回归，包括真实错误回放、正常表达、来源隔离及重复字段路由。未改门槛、冻结标签、默认数据或模型；未使用保留集调试。

## 最终版本的同轮证据

[Run21 原始回答](rag-v2-development-answers-run21.json)、[结构评审](rag-v2-development-review21.md)、[逐条语义复核](rag-v2-development-semantic-run21.json)、[质量门槛](rag-v2-development-gates-run21.json)、[开发检索](rag-v2-development-retrieval-run21.json)、[完整离线报告](rag-v2-final-offline-run21.json)。语义记录绑定原始报告 SHA-256；离线与真实运行实现指纹一致，见[保全核对](rag-v2-preservation-run21.json)。未拼接不同轮次的最佳答案。

| 指标 | Run21 结果 | 口径 |
| --- | --- | --- |
| 完整运行 | 36 场景 / 52 轮 | 仅冻结开发集；252 次内部真实模型调用 |
| 行为匹配 | 50/52，96.15% | 两条 424 保留失败分母；门槛 ≥85% |
| 场景结构通过 | 34/36 | 不等于法律正确率 |
| 四组日期更正 | 4/4 | 四领域均先确认冲突、再采用更正值续接 QA |
| 依据不足安全输出 | 8/8，100% | 本轮均为 insufficient |
| 直接依据 Hit@5 | 44/44，100% | 120 条开发查询中的 44 条有三级直接金标准法条查询；完整运行 240 个检索路由 |
| 候选 / 筛选后来源 Recall | 91.96% / 88.39% | 28 个预期可回答轮次，宏平均 |
| 最终来源 Recall | 81.25% | 同一 28 轮，包含两条服务失败；并非完整召回 |
| 最终直接依据 Recall | 92.86% | 三级金标准宏平均；27/29 条直接来源返回 |
| 逐条开发代理语义复核 | 26/26 成功法律答复通过 | 已读最终正文和对应原文；非独立人工/法律专家认证 |
| 结构安全失败 | 0 | 来源完整性、引用、版本、字段来源及更正确认等 |
| 完整离线 | 425/425 | 零真实模型调用、零外部网络尝试，含本地向量检索 |

`quality_gate_passed=true` 只表示仓库已有开发门槛通过。最终 Recall 低于 Run14 的 84.82%，不宣称所有指标单调改善；Run14 语义未过，不能沿用其成绩覆盖本轮结果。pip check、compileall 和 diff 检查通过；前端未改，未重复前端测试。

## 失败、重跑与尚存问题

| 运行 | 证据与结论 |
| --- | --- |
| Run16 | [定向报告](rag-v2-targeted-run16.json)：`complete=false`、基础设施 `TimeoutError`，0 场景和 0 模型调用；未完成尝试，不作为通过证据。 |
| Run17 | [定向回答](rag-v2-targeted-run17.json)、[语义](rag-v2-targeted-semantic-run17.json)：行为 4/4，但社保返还条件回指遗漏。与 Run16 单独保留于 `9d68172`。 |
| Run18 | [定向回答](rag-v2-targeted-run18.json)、[语义](rag-v2-targeted-semantic-run18.json)：4/4 行为，3 条法律答复复核通过；[离线](rag-v2-final-offline-run18.json)417 项。仅定向，不替代全量。 |
| Run19 | [全量回答](rag-v2-development-answers-run19.json)、[语义](rag-v2-development-semantic-run19.json)、[门槛](rag-v2-development-gates-run19.json)：49/52 行为；营养费负向推断、CD14 错路由、两条其他拦截，门槛未过。四份原始/检索/语义/门槛报告单独保留于 `63d43b9`。 |
| Run20 | [定向回答](rag-v2-targeted-run20.json)、[语义](rag-v2-targeted-semantic-run20.json)：7/7 行为，4 条法律答复通过；[离线失败](rag-v2-final-offline-run20.json)保留 7 个回归失败。领域回退随后收窄，此轮不能作为最终实现验收。离线子进程启动后发生修正，末尾采集的实现指纹不能用来重建失败时已加载的代码。 |
| Run21 | 最终收窄实现，425 项离线和完整真实开发门槛通过；以上报告均保留，不覆盖旧失败。 |

Run21 `E-L-MF-02:1` 与 `E-L-CD-02:1` 返回 424 `MODEL_UNAVAILABLE`，未发出未经校验的法律回答，仍为可用性失败。`CD01` 有重复句；`CD06` 首轮开头“依据不足”与后续能回答的一般规则表达不协调。后续应以这些保留输出改进校验可靠性和表达，不能通过降低忠实性要求换取成功率。

旧 `TA16` 属于已观察保留集，不再次用于调优或冒称盲测。本次在开发集逐条检查所有成功主要结论及直接原文，未发现同类无支持主要结论；这不能替代对未见问题的验证。人工复核已由用户确认完成，后续可组织新的未见验收集。

## 资料版本与保全

默认应用继续锁定 `demo-m3-60`（60 条）；隔离评估锁定 `eval-rag-v2-209`（209 条），响应显示资料版本，默认应用不得引用扩展评估成绩。交通事故解释（二）12 条已在扩展清单中；本轮再次核对[最高法官方正文](https://www.court.gov.cn/fabu/xiangqing/499051.html)的 2026 年 6 月 30 日施行及第十二条过渡规定，未重复导入。开发交通金标准复查见 [traffic-gold-review.json](../../backend/data/evaluation/rag-v2/traffic-gold-review.json)。不能据此宣称涵盖全部当前现行依据。

[最终保全](rag-v2-preservation-run21.json)只读核对默认表计数、迁移版本、冻结文件、M3 指向及实现指纹；未重新做默认全行或向量审计，历史完整保全见 [前轮保全](rag-v2-preservation-resumed-final.json)。默认仍为 1 用户、4 会话、16 案例、64 分块、60 法条、0 文书；评估合成 Redis 键已清理。

Git 外 PDF 继续单独交付：`output/pdf/法律咨询Agent一个月开发计划.pdf`，SHA-256 `9A49723FEE1AD8BB1610A92BC5C088D5F73E12F622859681F2CC2669C61EBC1D`。未迁移默认库、未改 M3 标签、未推送远端、未提交密钥。交接应保留整个 `docs/acceptance` 和对应数据及 manifest。

## 复现入口

在 `backend` 目录执行，输出必须使用不存在的新路径。日常优先离线，真实运行必须有调用授权；当前请求已授权本轮复验，不表示后续自动持续付费运行。

```powershell
.\.venv\Scripts\python.exe -m scripts.evaluate_offline --suite full --include-vectors --output ../tmp/rag-new-offline.json
.\.venv\Scripts\python.exe -m scripts.evaluate_rag_answers --allow-real-model --output ../tmp/rag-new-answers.json
.\.venv\Scripts\python.exe -m scripts.review_rag_answers --input ../tmp/rag-new-answers.json --output ../tmp/rag-new-review.json
```

新真实回答必须重新逐条复核并记录原始文件哈希，再用 `scripts.evaluate_quality_gates` 合并同版本开发检索和语义记录；不得复用 Run21 的语义结论给新答案盖章。
