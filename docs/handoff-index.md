# 交接文档索引

更新日期：2026-10-02。新开发者先读[上手指南](developer-onboarding.md)；[完整文档清单](handoff-document-inventory.md)逐项列出仓库Markdown文档、机器证据和Git外交付件。当前结论以项目方最终决定为准；2026-10-01及更早材料保留其历史状态，不能把创建时的“未执行/未验收”当作当前结论。

## 核心入口

| 文档 | 回答的问题 |
| --- | --- |
| [项目README](../README.md) | 项目做什么、如何启动 |
| [开发者上手指南](developer-onboarding.md) | 功能、架构、存储、代码地图、接口、启动、测试、排查及第一项改动怎么做 |
| [HANDOFF](../HANDOFF.md) | 做到哪里、还有什么待办、交付边界是什么 |
| [后端说明](../backend/README.md)、[前端说明](../frontend/README.md)、[完整部署](../deployment/README.md) | 如何安装、配置、初始化和启动 |
| [M4项目方验收决定](acceptance/m4-project-acceptance-20261002.md)、[机器记录](acceptance/m4-project-acceptance-20261002.json) | AI复核24/24通过、新验收口径及原证据绑定；不是独立专家认证 |
| [作业提交前复验](acceptance/m4-submission-closeout-20261002.md) | 最近Docker烟测14/14、运行9/9，新完整包及固定快照范围 |

## 开发时按需查阅

| 文档 | 用途 |
| --- | --- |
| [MVP需求](mvp-requirements.md) | 功能范围、产品约束和不做清单 |
| [系统架构](architecture.md) | 工作流、检索、存储和故障处理 |
| [数据模型](data-model.md) | 字段、关系和存储约束 |
| [API合同](api-contract.md) | 请求响应、SSE及错误码 |
| [多轮设计](legal-multiturn.md) | 事实来源、冲突确认、文书生成和任务一致性 |
| [离线验证方法](acceptance/rag-v2-offline.md) | 日常回归、旧录制回放、真实调用预算及门槛 |
| [M4安全复核](acceptance/m4-security-review-20261001.md) | JWT、所有权、依赖修复、Chroma公告与本机部署边界 |
| [MF04诊断与修复](acceptance/m4-mf04-rag-fix-20261001.md) | 检索、片段用途、引用身份与审查424的原因；真实复验范围 |
| [M4详细证据](acceptance/m4-progress.md) | 首次观察、失败和开发回归；顶部最新状态优先，正文历史逐项保留 |
| [实际答案复核表](review/m4-v17-actual-answer-review-20261001.md)、[AI复核记录](review/m4-v17-actual-answer-assisted-review-20261001.json) | 原始24题答案、判定依据、逐题意见和身份边界；空白人工项不伪填 |

## 数据与评估资料

- 数据说明：[合成案例](../backend/data/demo/README.md)、[默认法规](../backend/data/legal/README.md)、[扩展法规](../backend/data/legal/expansion-v1/README.md)、[交通解释二](../backend/data/legal/traffic-ii-2026/README.md)。默认60条与评估209条分开；16案例为合成数据。
- 评估定义：[查询与标签](../backend/data/evaluation/rag-v1/README.md)、[旧回放](../backend/data/evaluation/offline-v1/README.md)、[M4回放](../backend/data/evaluation/offline-m4-v1/README.md)、[历史开发门槛](../backend/data/evaluation/rag-v2/quality-gates.json)。
- 首次记录：[v17输入](../backend/data/evaluation/m4-once-v17/README.md)、[原始答案](acceptance/m4-reviewed-first-model-20261001-run1.json)、[原门槛](acceptance/m4-reviewed-first-model-gates-20261001-run1.json)、[同族观察记录](acceptance/m4-reserved-question-family-observed-20261001.json)。v12至v17同族已观察，不能再次称未见或独立盲测。
- 历史材料：[M4工程收尾](acceptance/m4-course-mvp-closeout-20261001.md)、[复核后收尾](acceptance/m4-reviewed-closeout-20261001.md)、[Run21历史验收](acceptance/rag-v2-final-acceptance.md)以及完整[acceptance目录](acceptance)和[review目录](review)。无需逐篇预读，诊断对应问题时保留原文件和分母。

## 随仓库交付

- 配置：[后端环境模板](../backend/.env.example)、[前端环境模板](../frontend/.env.example)、[部署环境模板](../deployment/.env.example)、[基础设施Compose](../compose.infrastructure.yml)、[完整Compose](../compose.yml)及[Nginx](../deployment/nginx.conf)。真实密钥独立配置，不提交`.env`。
- Git：源码、文档、锁文件、迁移、冻结数据与证据随master交付；远端只保留`m4`。后续说明不回写m4或旧报告，禁止用`git push --tags`恢复已移除的远端历史标签。
- 最新完整包：`output/delivery/LegalMind-M4-final-20261002.zip`与[同名manifest](../output/delivery/LegalMind-M4-final-20261002.manifest.json)，含源码、配置模板、数据、证据、最终验收决定及原PDF；无密钥、运行库、模型权重和依赖缓存。包是固定提交快照，不自动包含后来README和本次上手文档；后续开发应使用master。
- 历史包：原课程ZIP与复核后补充ZIP保持原文件及校验值，见[交付总清单](handoff-document-inventory.md)。它们不能替代最新完整包中的最终决定。
- Git外文件：[一个月开发计划PDF](../output/pdf/法律咨询Agent一个月开发计划.pdf)，校验值见[HANDOFF](../HANDOFF.md#交付定位)。
