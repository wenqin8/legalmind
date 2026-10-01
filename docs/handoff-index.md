# 交接文档索引

按下列顺序阅读；当前结论以2026-10-02项目方验收决定为准：接受AI法律内容复核替代外部专家，课程MVP验收通过。2026-10-01材料保留其历史状态和原门槛。

## 核心入口

| 文档 | 回答的问题 |
| --- | --- |
| [项目README](../README.md) | 项目做什么、如何启动 |
| [HANDOFF](../HANDOFF.md) | 做到哪里、还有什么待办、交付边界是什么 |
| [M4项目方验收决定](acceptance/m4-project-acceptance-20261002.md)、[机器记录](acceptance/m4-project-acceptance-20261002.json) | AI复核24/24通过、新验收口径、原证据绑定和本地m4标签范围 |
| [作业提交前复验](acceptance/m4-submission-closeout-20261002.md) | 当前Docker烟测14/14、运行9/9，新完整包与远端refs核对要求 |
| [M4课程收尾](acceptance/m4-course-mvp-closeout-20261001.md)、[详细证据](acceptance/m4-progress.md) | 工程交付、部署回归与未完成的法律质量验收 |
| [复核后收尾](acceptance/m4-reviewed-closeout-20261001.md)、[实际答案人工表](review/m4-v17-actual-answer-review-20261001.md) | 修订定稿、首次24/24测量、人工与独立专家未完成项及补充交付 |
| [M4安全复核](acceptance/m4-security-review-20261001.md) | 依赖修复、Chroma剩余公告与当前部署边界 |
| [Run21历史验收](acceptance/rag-v2-final-acceptance.md) | M3/RAG历史验收结论与证据，不代表最终M4代码 |
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

- 配置：[后端环境模板](../backend/.env.example)、[前端环境模板](../frontend/.env.example)、[基础设施Compose](../compose.infrastructure.yml)、[完整Compose](../compose.yml)及[部署说明](../deployment/README.md)。真实密钥独立安全交付，不提交`.env`。
- 数据及manifest：[合成案例](../backend/data/demo/README.md)、[基础法规](../backend/data/legal/README.md)、[扩展法规](../backend/data/legal/expansion-v1/README.md)、[交通解释二](../backend/data/legal/traffic-ii-2026/README.md)。
- 评估定义：[查询与标签](../backend/data/evaluation/rag-v1/README.md)、[离线回放](../backend/data/evaluation/offline-v1/README.md)、[门槛配置](../backend/data/evaluation/rag-v2/quality-gates.json)、[交通金标准复查](../backend/data/evaluation/rag-v2/traffic-gold-review.json)。
- 新验收：[v17](../backend/data/evaluation/m4-once-v17/README.md)已首次测量24/24，原报告及同族观察状态保留；v12至v16不得重新称未见。项目方已接受24题AI内容复核，外部专家改为非本次课程验收必需；原人工表未伪填，历史门槛仍原样保留。日常使用[复核后离线工具说明](acceptance/m4-reviewed-closeout-20261001.md)，不调用真实模型。原[M4证据快照](acceptance/m4-evidence-final-manifest-20261001-run5.json)和失败历史保留。
- 原始证据：整个[acceptance目录](acceptance)，含M1–M3、修复前基线、历次失败及Run21历史报告；当前证据链接集中在[M4阶段验收](acceptance/m4-progress.md)，历史材料无需逐篇预读。
- 课程包：`output/delivery/LegalMind-M4-course-MVP-20261001.zip`及同名manifest，含源码、模板、数据、证据、文档和PDF；无密钥、运行库及依赖缓存。新补充包为`output/delivery/LegalMind-M4-reviewed-supplement-20261001.zip`及同名manifest，配合原课程包使用；法律复核资料见[当前收尾](acceptance/m4-reviewed-closeout-20261001.md)。
- Git外文件：[一个月开发计划PDF](../output/pdf/法律咨询Agent一个月开发计划.pdf)，校验值见[HANDOFF](../HANDOFF.md#交付定位)。
