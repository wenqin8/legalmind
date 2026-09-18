# 官方法条与多轮补充验收

完成记录：2026-09-19。用户批准同时实现问答补事实、文书逐轮补字段，覆盖婚姻家庭、劳动争议、交通事故、合同纠纷，采用官方核验后的本地版本及人工更新。初始 M3 的历史证据见 [week3-m3.md](week3-m3.md)。本地冻结状态以 Git 标签为准；远端交付须在配置并验证仓库地址后完成。

## 实现结果

- 四部法律共 60 条完整条文：民法典 32 条、劳动合同法 14 条、劳动争议调解仲裁法 10 条、道路交通安全法 4 条。官方来源、快照、采集方式和哈希保存在 [资料目录](../../backend/data/legal/README.md)。独立关系库版本过滤及 BM25 检索不改变冻结案例向量和 M2 参数。
- 区分一般规则参考和具体事件候选依据；日期缺失、范围横跨未覆盖版本或适用条件不足时追问。标题、条号、版本、链接及原文由服务端提供，未知引用、伪造外链和与对应版本不一致的引文拒绝输出。
- 问答和文书都保存结构化任务及每个字段的消息 UUID、原句；冲突须确认。每轮最多询问三项。三类文书均先补齐、展示摘要、用户确认，再生成草稿；支持取消、更正、陈旧摘要拒绝及重复确认幂等。完成后更正并确认会生成新文书，不覆盖旧文书。
- 任务嵌入成功助手消息，与 Redis 历史共享 24 小时滑动 TTL、所有权、互斥、原子追加和跨存储补偿。原消息被裁剪后，当前任务仍保留来源原句。过期后重新补充，不从其他会话或数据库重建事实。
- 同步与 SSE 共用节点及校验；未闭合引文或引用跨段时暂存，校验通过后才发出。截断、超时、断开、引用或保存失败均不推进历史和任务状态。
- 前端增加官方来源原文/版本卡片和任务确认、冲突处理、取消按钮；按钮携带任务修订 UUID，仍采用同步交互。接口、运行、架构、数据模型和隐私说明已同步。

## 自动化验证

| 检查 | 结果 |
| --- | --- |
| 后端完整 pytest | 240 passed，31.14 秒 |
| 最后统一适用性函数空结果类型后的定向回归 | 18 passed |
| pip check / compileall | 通过，无依赖冲突 |
| 前端 Vitest | 11 个文件、42 项通过 |
| TypeScript / 生产构建 | 通过 |
| 独立法条候选检索评估 | 20/20，通过四领域、无关查询、未覆盖日期检查 |
| git diff --check | 通过，仅 Windows 换行提示 |

后端有 11 条既有 Chroma `legacy embedding function config` 弃用警告，无测试失败。未引入新的依赖。

新增和扩展用例覆盖字段来源、无依据提取拒绝、领域切换、一般咨询、三模板缺项/确认/修改、任务裁剪后保留、过期/旧修订、跨用户访问、失败补偿、引用逐字校验、非法裁判事实、跨段未闭合引用和真实本地 HTTP 断流。检索评估仅衡量候选召回和日期过滤，不代表法律解释准确率，见 [逐条报告](legal-retrieval-evaluation.json)。

## 真实服务及默认环境

[存储报告](legal-multiturn-storage.json)：真实 Redis 8 项通过，包括 20 条保留、24 小时 TTL、结构化状态、互斥、写入锁校验、补偿、过期和精确清理；PostgreSQL 隔离 schema 8 项通过，包括 JSONB 核验信息、60 条法条往返、文书所有权、提交标记、升级/降级/重升及 schema 清理。SQLite 迁移可逆性由自动化迁移测试覆盖。

[真实模型报告](legal-multiturn-real-model.json)：通过真实本地 HTTP 调用 DeepSeek、既有 BGE/向量索引和 Redis，14 项通过。四领域均验证官方来源，劳动争议验证补事实后继续问答，文书验证两轮补字段、摘要确认、生成和下载。仅使用合成输入；需要更多材料的具体事件允许明确追问，不要求强行产生法律结论。

联调中曾出现模型压缩事实导致原句校验失败、重复日期字段、一般咨询未返回领域，以及普通引号/法条中的通用法院程序被过宽规则误拦。已分别改为保留可定位原句、忽略重复提取项、显式一般咨询领域规则补充，以及按实际法条引文和已给来源校验；新增相应用例后最终联调全部通过。失败记录没有被当作验收通过。

[默认环境报告](legal-multiturn-default-environment.json)：34 项通过，使用默认 SQLite、真实 Redis 和默认 DeepSeek。包括认证、案例搜索/详情、官方法条问答、真实 HTTP SSE、历史/列表/删除、三类文书 MD/TXT、聊天摘要确认、数据库完整性、迁移状态和合成测试数据精确清理。

- 默认库 `backend/data/legalmind.db` 已从 `20260917_0003` 升至 `20260918_0004`，`alembic check` 无差异，已导入 60 条法条，Redis PING 成功。
- 扩展升级前备份：`tmp/backups/legalmind-pre-laws-20260918T154922Z-bfbd9c91.db`，SHA-256 `0193945C03EBB5BBB6417ECC3A536E76B54FDD86D13A6506CE28AE90C0910DAD`。
- 原有用户 1、会话 4、案例 16、分块 64、向量 64，数量及内容校验一致；原文书表保持不变，清理后文书 0。未重建或清空数据库。
- 备份和临时模型诊断文件位于被忽略的 `tmp/`，不会进入 Git；不要将本机数据库备份当作公开演示资料分发。

## 复现命令

以下命令在 backend 目录执行。既有运行库先保留备份；导入命令只激活已核验的本地清单，不会自动联网更新。实库命令要求 `.env` 中的 Redis/PostgreSQL 可用，模型联调要求现有 DeepSeek 配置和案例索引。避免覆盖需要保留的历史验收报告，可改用新的输出路径。

```powershell
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m alembic check
.\.venv\Scripts\python.exe -m scripts.import_verified_laws --check-only
.\.venv\Scripts\python.exe -m scripts.import_verified_laws
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -m compileall -q app scripts
.\.venv\Scripts\python.exe -m scripts.evaluate_legal_retrieval --output ../tmp/legal-retrieval-recheck.json
.\.venv\Scripts\python.exe -m scripts.verify_week3_storage --output ../tmp/legal-storage-recheck.json
.\.venv\Scripts\python.exe -m scripts.smoke_legal_multiturn --output ../tmp/legal-model-recheck.json
```

在 frontend 目录执行：

```powershell
npm run typecheck
npm test
npm run build
```

## 交付边界与冻结文件

正文核验日为 **2026-09-18**；所引用现行法律目录的资料截止日为 **2026-03-12**。二者分别记录、显示，不能把较新的正文核验日当作有效状态已实时确认到同一天。60 条资料仅覆盖四领域的部分常见问题，没有完整历史版本、司法解释或地方规则；未覆盖情况继续提示依据不足或追问。引用真实也不保证适用性判断正确，人工更新和法律审查仍有必要。

完整服务端历史恢复界面、SSE 界面、独立案例/文书页及 Docker 部署留第四周。直接 `/documents/generate` 是调用者提交完整参数后的显式生成接口；对话生成必须完成摘要确认。

2026-09-19 再次核对下列冻结文件，SHA-256 与原基线相同：

| 文件 | SHA-256 |
| --- | --- |
| `backend/data/demo/cases.jsonl` | `752EFB9C679BDBB30521BEAF77CC04A38588C49276C10F1E05F0EE452861BB84` |
| `backend/data/evaluation/week2_queries.jsonl` | `DAE562F49CDD93E8B3076B4464F7F4729114C55F5F68BD828AD6817BE4A2AB81` |
| `docs/acceptance/week2-retrieval-evaluation.json` | `A0EB70AD66E234323E6174E4DACABBA44D6C98A894E65746897828C076BCA410` |
| `output/pdf/法律咨询Agent一个月开发计划.pdf` | `9A49723FEE1AD8BB1610A92BC5C088D5F73E12F622859681F2CC2669C61EBC1D` |

原始 8 页 PDF 未修改且不在 Git 提交中，交接须单独复制或打包保留。交付还应保留法条 JSONL、manifest、官方正文快照、本验收记录和四份扩展 JSON 报告。当前交接入口为 [HANDOFF.md](../../HANDOFF.md)。
