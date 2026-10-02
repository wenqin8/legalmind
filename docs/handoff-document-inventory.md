# LegalMind 交接文档总清单

清点日期：2026-10-02（America/New_York）。本清单列出Git已跟踪及本次新增的全部Markdown文档；JSON、JSONL、TXT、XML、配置和交付件另按目录及关键文件列出。

Markdown合计 **84份**。开始阅读使用[上手指南](developer-onboarding.md)与[推荐阅读索引](handoff-index.md)；完整保留不代表必须逐篇阅读。本文不是自动生成的验收结论。

当前课程验收以2026-10-02项目方决定为准。历史文件中的未执行、未验收、未上传等措辞只描述其当时状态；原manifest、首次观察和复核身份保持不变。GitHub远端目前仅保留m4，最新使用说明位于master。

## 入口与运行说明（8份）

首次接手阅读；后端、前端和部署说明按选择的运行模式查阅。

| 文档 | 仓库路径 |
| --- | --- |
| [项目交接](../HANDOFF.md) | `HANDOFF.md` |
| [LegalMind](../README.md) | `README.md` |
| [LegalMind后端运行说明](../backend/README.md) | `backend/README.md` |
| [完整本地部署](../deployment/README.md) | `deployment/README.md` |
| [LegalMind 开发者上手与交接指南](developer-onboarding.md) | `docs/developer-onboarding.md` |
| [LegalMind 交接文档总清单](handoff-document-inventory.md) | `docs/handoff-document-inventory.md` |
| [交接文档索引](handoff-index.md) | `docs/handoff-index.md` |
| [LegalMind Frontend](../frontend/README.md) | `frontend/README.md` |

## 需求与设计（5份）

修改功能、字段、接口或状态流程前阅读。数据模型保留M3物理模型描述，Compose已使用PostgreSQL的部署状态见当前上手指南。

| 文档 | 仓库路径 |
| --- | --- |
| [API 合同设计](api-contract.md) | `docs/api-contract.md` |
| [系统架构与工作流](architecture.md) | `docs/architecture.md` |
| [数据模型设计](data-model.md) | `docs/data-model.md` |
| [官方法条与多轮任务扩展](legal-multiturn.md) | `docs/legal-multiturn.md` |
| [法律咨询 Agent MVP 需求与范围基线](mvp-requirements.md) | `docs/mvp-requirements.md` |

## 当前验收、验证与排查（6份）

最终决定说明现行课程口径；progress正文及安全/修复报告包含历史证据，不承诺未来零故障或生产可用。

| 文档 | 仓库路径 |
| --- | --- |
| [MF04 的424原因与离线修复](acceptance/m4-mf04-rag-fix-20261001.md) | `docs/acceptance/m4-mf04-rag-fix-20261001.md` |
| [M4 实施与验收边界](acceptance/m4-progress.md) | `docs/acceptance/m4-progress.md` |
| [M4项目方验收决定](acceptance/m4-project-acceptance-20261002.md) | `docs/acceptance/m4-project-acceptance-20261002.md` |
| [M4 安全复核](acceptance/m4-security-review-20261001.md) | `docs/acceptance/m4-security-review-20261001.md` |
| [M4作业提交前复验与交付](acceptance/m4-submission-closeout-20261002.md) | `docs/acceptance/m4-submission-closeout-20261002.md` |
| [RAG验证方法](acceptance/rag-v2-offline.md) | `docs/acceptance/rag-v2-offline.md` |

## 数据与回放定义（7份）

导入、扩库和离线检索时查阅；默认60法条与209评估法条不能混用成绩。

| 文档 | 仓库路径 |
| --- | --- |
| [第二周演示案例原始数据](../backend/data/demo/README.md) | `backend/data/demo/README.md` |
| [M4 已观察记录的离线回放](../backend/data/evaluation/offline-m4-v1/README.md) | `backend/data/evaluation/offline-m4-v1/README.md` |
| [离线回归记录](../backend/data/evaluation/offline-v1/README.md) | `backend/data/evaluation/offline-v1/README.md` |
| [RAG-v1 冻结评估集](../backend/data/evaluation/rag-v1/README.md) | `backend/data/evaluation/rag-v1/README.md` |
| [官方法条本地版本库](../backend/data/legal/README.md) | `backend/data/legal/README.md` |
| [RAG-v1 扩展资料](../backend/data/legal/expansion-v1/README.md) | `backend/data/legal/expansion-v1/README.md` |
| [道路交通事故解释（二）补充资料](../backend/data/legal/traffic-ii-2026/README.md) | `backend/data/legal/traffic-ii-2026/README.md` |

## 一次性评估包历史（17份）

全部为冻结创建快照。v6已观察，v12至v17同族已首次执行；原目录没有receipt不代表题目仍未见。旧版本失效/失败状态不重置。

| 文档 | 仓库路径 |
| --- | --- |
| [M4 新建一次性验收候选集](../backend/data/evaluation/m4-once-v1/README.md) | `backend/data/evaluation/m4-once-v1/README.md` |
| [M4 未执行储备集 v10](../backend/data/evaluation/m4-once-v10/README.md) | `backend/data/evaluation/m4-once-v10/README.md` |
| [M4 未执行储备集 v11](../backend/data/evaluation/m4-once-v11/README.md) | `backend/data/evaluation/m4-once-v11/README.md` |
| [M4 未执行储备集 v12](../backend/data/evaluation/m4-once-v12/README.md) | `backend/data/evaluation/m4-once-v12/README.md` |
| [M4未执行储备v13：首轮辅助复核修订稿](../backend/data/evaluation/m4-once-v13/README.md) | `backend/data/evaluation/m4-once-v13/README.md` |
| [M4未执行储备v14：劳动争议辅助复核修订稿](../backend/data/evaluation/m4-once-v14/README.md) | `backend/data/evaluation/m4-once-v14/README.md` |
| [M4未执行储备v15：交通事故辅助复核修订稿](../backend/data/evaluation/m4-once-v15/README.md) | `backend/data/evaluation/m4-once-v15/README.md` |
| [M4未执行储备v16：24题首轮辅助复核修订稿](../backend/data/evaluation/m4-once-v16/README.md) | `backend/data/evaluation/m4-once-v16/README.md` |
| [M4 v17：辅助复核后定稿输入](../backend/data/evaluation/m4-once-v17/README.md) | `backend/data/evaluation/m4-once-v17/README.md` |
| [M4 一次性验收候选集 v2](../backend/data/evaluation/m4-once-v2/README.md) | `backend/data/evaluation/m4-once-v2/README.md` |
| [M4 一次性验收候选集 v3](../backend/data/evaluation/m4-once-v3/README.md) | `backend/data/evaluation/m4-once-v3/README.md` |
| [M4 一次性验收候选集 v4](../backend/data/evaluation/m4-once-v4/README.md) | `backend/data/evaluation/m4-once-v4/README.md` |
| [一次性候选 v5：未执行的历史包](../backend/data/evaluation/m4-once-v5/README.md) | `backend/data/evaluation/m4-once-v5/README.md` |
| [一次性候选 v6：首次观察已完成，未通过](../backend/data/evaluation/m4-once-v6/README.md) | `backend/data/evaluation/m4-once-v6/README.md` |
| [M4 储备集 v7：未执行的历史冻结](../backend/data/evaluation/m4-once-v7/README.md) | `backend/data/evaluation/m4-once-v7/README.md` |
| [M4 储备集 v8：未执行的历史冻结](../backend/data/evaluation/m4-once-v8/README.md) | `backend/data/evaluation/m4-once-v8/README.md` |
| [M4 储备集 v9：未执行的历史冻结](../backend/data/evaluation/m4-once-v9/README.md) | `backend/data/evaluation/m4-once-v9/README.md` |

## 题目与答案复核资料（10份）

保留原始意见、六处修改和空白人工表；课程已接受开发AI复核，不伪填专家身份或人工签署。

| 文档 | 仓库路径 |
| --- | --- |
| [合同纠纷6题：首轮辅助复核记录](review/m4-contract-review-round1-20261001.md) | `docs/review/m4-contract-review-round1-20261001.md` |
| [24题首轮题目与依据辅助复核汇总](review/m4-first-round-review-summary-20261001.md) | `docs/review/m4-first-round-review-summary-20261001.md` |
| [劳动争议6题：首轮辅助复核记录](review/m4-labor-review-round1-20261001.md) | `docs/review/m4-labor-review-round1-20261001.md` |
| [M4独立法律复核资料](review/m4-legal-review.md) | `docs/review/m4-legal-review.md` |
| [婚姻家庭6题：首轮辅助复核记录](review/m4-marriage-family-review-round1-20261001.md) | `docs/review/m4-marriage-family-review-round1-20261001.md` |
| [M4复核后输入定稿](review/m4-reviewed-inputs-final-20261001.md) | `docs/review/m4-reviewed-inputs-final-20261001.md` |
| [交通事故6题：首轮辅助复核记录](review/m4-traffic-review-round1-20261001.md) | `docs/review/m4-traffic-review-round1-20261001.md` |
| [M4人工复核：资料与标准](review/m4-user-review-guide-20261001.md) | `docs/review/m4-user-review-guide-20261001.md` |
| [M4未执行24题：人工复核表](review/m4-v12-review-worksheet-20261001.md) | `docs/review/m4-v12-review-worksheet-20261001.md` |
| [v17首次实际答案：人工语义复核表](review/m4-v17-actual-answer-review-20261001.md) | `docs/review/m4-v17-actual-answer-review-20261001.md` |

## 历史验收及演示记录（31份）

复现历史问题或查证阶段成果时按需读取；M3 Run21和旧演示提纲不能替代当前M4验收决定。

| 文档 | 仓库路径 |
| --- | --- |
| [官方法条与多轮补充验收](acceptance/legal-multiturn.md) | `docs/acceptance/legal-multiturn.md` |
| [第四周课程MVP收尾](acceptance/m4-course-mvp-closeout-20261001.md) | `docs/acceptance/m4-course-mvp-closeout-20261001.md` |
| [RAG 检索评估](acceptance/m4-retrieval-20261001-run1.md) | `docs/acceptance/m4-retrieval-20261001-run1.md` |
| [RAG 检索评估](acceptance/m4-retrieval-20261001-run2.md) | `docs/acceptance/m4-retrieval-20261001-run2.md` |
| [RAG 检索评估](acceptance/m4-retrieval-20261001-run3.md) | `docs/acceptance/m4-retrieval-20261001-run3.md` |
| [RAG 检索评估](acceptance/m4-retrieval-20261001-run4.md) | `docs/acceptance/m4-retrieval-20261001-run4.md` |
| [RAG 检索评估](acceptance/m4-retrieval-20261001-run5.md) | `docs/acceptance/m4-retrieval-20261001-run5.md` |
| [M4复核后收尾与补充交付](acceptance/m4-reviewed-closeout-20261001.md) | `docs/acceptance/m4-reviewed-closeout-20261001.md` |
| [RAG-v1 端到端复核](acceptance/rag-v1-answer-review-v2.md) | `docs/acceptance/rag-v1-answer-review-v2.md` |
| [RAG-v1 端到端复核](acceptance/rag-v1-answer-review.md) | `docs/acceptance/rag-v1-answer-review.md` |
| [RAG-v1 检索基线](acceptance/rag-v1-retrieval.md) | `docs/acceptance/rag-v1-retrieval.md` |
| [RAG-v1 质量失败：原因与修复建议](acceptance/rag-v1-root-causes.md) | `docs/acceptance/rag-v1-root-causes.md` |
| [RAG-v1 评估体系及基线](acceptance/rag-v1.md) | `docs/acceptance/rag-v1.md` |
| [剩余校验拦截与来源召回修复](acceptance/rag-v2-delivery.md) | `docs/acceptance/rag-v2-delivery.md` |
| [RAG 检索评估](acceptance/rag-v2-development-retrieval-run9.md) | `docs/acceptance/rag-v2-development-retrieval-run9.md` |
| [RAG-v1 检索基线](acceptance/rag-v2-development-retrieval.md) | `docs/acceptance/rag-v2-development-retrieval.md` |
| [RAG 端到端复核](acceptance/rag-v2-development-review-run10.md) | `docs/acceptance/rag-v2-development-review-run10.md` |
| [RAG 端到端复核](acceptance/rag-v2-development-review-run8-graded.md) | `docs/acceptance/rag-v2-development-review-run8-graded.md` |
| [RAG 端到端复核](acceptance/rag-v2-development-review-run9.md) | `docs/acceptance/rag-v2-development-review-run9.md` |
| [RAG 端到端复核](acceptance/rag-v2-development-review13.md) | `docs/acceptance/rag-v2-development-review13.md` |
| [RAG 端到端复核](acceptance/rag-v2-development-review14.md) | `docs/acceptance/rag-v2-development-review14.md` |
| [RAG 端到端复核](acceptance/rag-v2-development-review15.md) | `docs/acceptance/rag-v2-development-review15.md` |
| [RAG 端到端复核](acceptance/rag-v2-development-review21.md) | `docs/acceptance/rag-v2-development-review21.md` |
| [RAG最终验收](acceptance/rag-v2-final-acceptance.md) | `docs/acceptance/rag-v2-final-acceptance.md` |
| [额度恢复后的修复与复验（2026-09-28）](acceptance/rag-v2-resumed.md) | `docs/acceptance/rag-v2-resumed.md` |
| [RAG 端到端复核](acceptance/rag-v2-targeted-review11.md) | `docs/acceptance/rag-v2-targeted-review11.md` |
| [RAG-v2 开发集修复验收](acceptance/rag-v2.md) | `docs/acceptance/rag-v2.md` |
| [第一周 M1 最终验收记录](acceptance/week1-m1.md) | `docs/acceptance/week1-m1.md` |
| [第二周 M2 验收记录](acceptance/week2-m2.md) | `docs/acceptance/week2-m2.md` |
| [第三周 M3 开发验收记录](acceptance/week3-m3.md) | `docs/acceptance/week3-m3.md` |
| [M4课程演示提纲](m4-demo.md) | `docs/m4-demo.md` |

## 非Markdown资料与交付文件

| 类别 | 必须保留的内容与入口 |
| --- | --- |
| 源码与依赖 | `backend/app`、`backend/scripts`、`backend/tests`、`frontend/src`、`frontend/scripts`、requirements/constraints、package.json及锁文件、迁移；源码导航见上手指南 |
| 配置与部署 | [后端模板](../backend/.env.example)、[前端模板](../frontend/.env.example)、[部署模板](../deployment/.env.example)、[完整Compose](../compose.yml)、[基础设施Compose](../compose.infrastructure.yml)、[Nginx](../deployment/nginx.conf)、[配置生成](../deployment/init_env.py)、[启动脚本](../deployment/start.ps1) |
| 法律与案例快照 | `backend/data/demo`、`backend/data/legal`下JSONL/manifest/核验资料；冻结来源及SHA-256不覆盖，默认运行数据库不随Git交付 |
| 评估输入与门槛 | `backend/data/evaluation`全部JSON/JSONL/manifest/rubric/执行计划；[历史开发门槛](../backend/data/evaluation/rag-v2/quality-gates.json)与[同族观察记录](acceptance/m4-reserved-question-family-observed-20261001.json) |
| 模型与工程证据 | [acceptance目录](acceptance)下原始JSON、XML、TXT，含完整/部分执行、失败、预算、指纹和部署报告；不得只交成功报告 |
| 人工及AI复核 | [review目录](review)下JSON记录与未填写模板；[AI实际答案复核](review/m4-v17-actual-answer-assisted-review-20261001.json)及[最终决定机器记录](acceptance/m4-project-acceptance-20261002.json) |
| 交付工具 | [完整打包工具](../tools/create_course_delivery.py)、[复核包离线核验](../tools/verify_m4_reviewed_candidate.py)；使用新输出路径，固定包不自动包含后来改动 |

下列三份ZIP与原PDF在Git之外，需随交接单独提供。对应manifest在仓库中；现有ZIP保持原内容和校验值，不因新增本指南而覆盖。

| 文件 | Git分发状态 | 校验与范围 |
| --- | --- |
| `output/delivery/LegalMind-M4-final-20261002.zip` | ZIP不在Git，manifest在Git | [清单](../output/delivery/LegalMind-M4-final-20261002.manifest.json)；SHA-256：`c18c958cd56bb261f06885ebd208a926df91ac8d5b1b9d47b65ab43ce38ab46a` |
| `output/delivery/LegalMind-M4-course-MVP-20261001.zip` | ZIP不在Git，manifest在Git | [清单](../output/delivery/LegalMind-M4-course-MVP-20261001.manifest.json)；SHA-256：`68afcbccd8a5b4fce84c070499522283d79212176853104e3cb8309bf505c892` |
| `output/delivery/LegalMind-M4-reviewed-supplement-20261001.zip` | ZIP不在Git，manifest在Git | [清单](../output/delivery/LegalMind-M4-reviewed-supplement-20261001.manifest.json)；SHA-256：`538ae79f1442ffc7fcc84cedad70cdfe24337a4e29398c9d40f05aad1f8ca34e` |
| [法律咨询Agent一个月开发计划PDF](../output/pdf/法律咨询Agent一个月开发计划.pdf) | 原PDF不在Git，另行交付 | SHA-256：`9a49723fee1ad8bb1610a92bc5c088d5f73e12f622859681f2cc2669c61ebc1d` |

最新完整包包含2026-10-02验收决定与部署复验；原课程包和补充包属于较早快照。master后续新增README/交接文档不回写m4，也不自动进入任何旧ZIP。

## 本地规划稿与个人配置

`docs/plans/legalmind-enterprise-pilot-plan-v1-20261002.md`在此次清点前已存在，当前为未纳入Git的实施建议稿，因此不计入上述84份Git交付文档。若需要随附，应另行登记版本；其中MCP、Skill、多Agent和企业排期是未来计划，不是当前功能。

真实.env、API Key、个人账号、日常数据库、模型权重、依赖缓存、临时日志和仓库备份不纳入Git/课程源码交付。密钥由接手方独立配置；已有运行数据如需迁移，单独备份和确认范围。
