# M4复核后收尾与补充交付

2026-10-01。六处题目按用户提交建议逐字核对定稿，24题首次真实测量完成；实际答案的开发代理辅助检查及人工复核资料已整理。未修改运行实现、默认数据、冻结法规、历史报告、原PDF或原课程ZIP，未再做第二轮模型运行。

| 项目 | 结果及证据 |
| --- | --- |
| 输入修订 | 六处修订处理完成，首轮18通过/6需修改原判保留；[v17输入](../../backend/data/evaluation/m4-once-v17/README.md)、[修订核对](../review/m4-revision-resolution-20261001.json)。 |
| 新24题离线 | 24/24输入/来源一致；16正例直接依据Top-5命中16/16，模型0、联网0；[证据](m4-reviewed-final-input-offline-20261001-run1.json)。 |
| 相关代码离线 | 50/50通过，覆盖冻结、预算、供应商停止、MF04范围和资料边界；[JUnit](m4-reviewed-closeout-offline-tests-20261001.xml)、[联网拦截记录](m4-reviewed-closeout-offline-network-20261001.json)。 |
| 首次真实测量 | HTTP24/24、行为24/24、硬性失败0；134/160次供应商请求、无重跑、隔离Redis合成键已清理；[原报告](m4-reviewed-first-model-20261001-run1.json)、[工程门槛](m4-reviewed-first-model-gates-20261001-run1.json)。 |
| 实际答案辅助检查 | 24条检查完成，未发现明显实质问题；[代理记录](../review/m4-v17-actual-answer-assisted-review-20261001.json)。此项不替代人工签署或独立专家意见。 |
| 人工资料 | [实际答案24题复核表](../review/m4-v17-actual-answer-review-20261001.md)、[填写JSON](../review/m4-v17-actual-answer-review-template-20261001.json)、[当前进度](../review/m4-annotation-review-progress-20261001-round6.json)。尚未填写人工通过结论。 |

合同第02题的首稿被依据审核拒绝，既有一次受限修订后成功；轨迹未删除。交通第03/04题生效及过渡原文在参考材料中完整保留。追问题首轮两组通用问题符合分轮上限，后续完整清单覆盖没有在本次单轮包中测量；地方缺口答复较通用，未把资料缺失误称政策不存在。

## 保留的验收边界

用户回复没有法律专业背景或执业资质，不能据此登记为独立法律专家。独立法律标注和人对实际答案的语义签署均未完成；因此最终法律质量验收继续为未完成。24/24行为和结构通过不是法律正确率认证，冻结门槛未放宽。

原MF04共同财产赠与题不在新24题包里；其离线修复及部署证据仍成立，但该特定题在修复后的真实输出未另行重测，不用本轮替代。Chroma四条上游公告继续保留，Python依赖审计仍未通过，当前仅本机嵌入模式运行；见[安全复核](m4-security-review-20261001.md)。

v17已有首次观察记录，本族v12至v16也不能作为未见验收重新运行；原目录没有自己的receipt只代表原文件保留，不证明仍然未见。见[同族观察记录](m4-reserved-question-family-observed-20261001.json)。后续只做离线检查和明确标注的开发回归，不重置记录，不拼接最佳答案。

## 交付

原课程包`output/delivery/LegalMind-M4-course-MVP-20261001.zip`保留不变，SHA-256为`68afcbccd8a5b4fce84c070499522283d79212176853104e3cb8309bf505c892`。新增补充包`output/delivery/LegalMind-M4-reviewed-supplement-20261001.zip`及同名manifest，包含v13至v17、四批复核、实际原始答案、人工表、当前交接和可重复离线工具。它需与原课程包一起使用；按同名路径补充当前文档和评估资料，不包含密钥、运行库、依赖缓存或模型权重。

日常离线：在项目根目录运行`backend/.venv/Scripts/python.exe tools/verify_m4_reviewed_candidate.py --package backend/data/evaluation/m4-once-v17 --output tmp/reviewed-input-check-new.json`，指定未使用的新输出路径。工具只读取模型观察记录并保持指纹，不调用模型；使用本地已安装后端环境，不需新增依赖。

课程工程证据仍使用[原课程收尾](m4-course-mvp-closeout-20261001.md)，本轮未改前后端代码或重新部署；209条隔离评估不替代60条默认库。原证据清单表示当时快照，本轮新增证据另存，不覆盖。
