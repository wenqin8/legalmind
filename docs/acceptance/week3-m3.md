# 第三周 M3 开发验收记录

记录日期：2026-09-18（Asia/Shanghai）
基线：`37e8575` / `v0.1.0-m2`
结论：本记录保留 Day 1–5 初始验收的历史证据。第三周最终范围已增加官方法条引用与多轮补充；最终验收以 [扩展验收记录](legal-multiturn.md) 及本记录合并判断。Git 冻结状态以实际标签为准。

## 1. 范围与每日交付

| 开发日 | 完成内容 | 当日定向验证与证据 |
| --- | --- | --- |
| Day 1 | 可注入 Intent Agent，规则优先、结构化输出、qa 回退；三类意图和来源合同；前端必要兼容 | 初始 11 项节点测试通过；qa/search/document 各至少 2 个用例，显式文书优先、非法/低置信度输出回退 |
| Day 2 | 复用案例服务、最多 5 条候选、独立证据筛选；段落生成、编号引用和服务端参考列表 | 累计节点测试 19 项通过；空/无关结果、未知来源、法条、外链、司法事实校验；后续补历史引用和跨段校验测试 |
| Day 3 | 三套固定模板、字段及缺项、草稿表、MD/TXT 下载、用户所有权 | 文书及迁移定向 5 项通过；三类模板逐一缺项及生成/下载，跨用户 404 |
| Day 4 | LangGraph 三分支及统一完成节点，共用同步/流式逻辑，总预算，无重试环 | 节点/图累计 25 项通过；三意图各至少 2 个图级终点，空来源与缺项均可结束 |
| Day 5 | Redis 历史/过期/裁剪、互斥、会话列表/读取/删除、补偿及提交标记，实时 SSE | 完整后端 199 项通过；实库、真实模型和真实 TCP 证据见下文 |

初始阶段不改冻结数据或相关性标签，也未新增真实法条。来源独立保存样本日期和空裁判日期。合成案例只能作为演示参考，具体法律结论仍明确依据不足。初始文书只接受结构化参数；随后已按追加范围实现自然语言逐轮补字段、冲突处理和摘要确认，详见扩展验收记录。身份、金额、日期、请求和义务均不自动补造。

## 2. 最终自动化回归

| 检查 | 结果 |
| --- | --- |
| 后端 `python -m pytest -q` | **199 passed**，23.53 秒；11 条已有 Chroma `legacy embedding function config` 弃用警告，无失败 |
| `python -m pip check` | `No broken requirements found.` |
| `python -m compileall -q app scripts` | 通过 |
| 前端 `npm run test` | **40 passed**，11 个测试文件 |
| 前端 `npm run typecheck` | 通过 |
| 前端 `npm run build` | 通过（含 vue-tsc 与 Vite 生产构建） |
| `git diff --check` | 通过；仅 Git 的 LF/CRLF 提示 |
| SQLite Alembic | 隔离临时库 upgrade → metadata check → downgrade base → upgrade → metadata check 通过 |

自动化使用确定性假模型及可注入测试存储，不访问付费模型。运行依赖复用原有 LangChain/LangGraph/Redis/SQLAlchemy 等，本周未新增依赖。

覆盖要点：

- 用户/会话/文书隔离，非法参数，来源演示标记，检索空结果和无法确认相关性。
- 每类文书缺项及完整生成，参数必须为模板字符串字段，500/4000 字符和 20KB 边界，固定文件名和草稿提示。
- 历史最多 20 条，模型最近 10 条且不超过 12000 字符，按完整问答对裁剪；过期保留会话并从空上下文继续。
- 同会话生成/删除实际并发为 409，另一会话可独立成功；所有权在模型和 Redis 访问前验证。
- Redis 追加失败、关系库提交失败、文书保存失败、删除失败的补偿；补偿也失败时，恢复服务后剔除未提交消息尾部。
- SSE 协议、非法引用不发送、跨 chunk/段落编号检查、模型截断、总超时、流开始后的 Redis 故障，失败内容不进入后续历史。
- 既有 DeepSeek 适配器检查 `finish_reason` 和 `[DONE]`，不把 HTTP 200 或半段正文当完整成功。

## 3. 真实流式与断开验证

`backend/tests/integration/test_live_stream.py` 在随机回环端口启动真实 Uvicorn，使用 HTTPX TCP 连接。不是用缓冲式 ASGI 测试客户端推断流式时序：

1. 假模型发出首个完整段落后等待测试信号。客户端先收到 `content`，断言模型尚未完成，再允许模型继续；最终有 `sources`、`done(success=true)` 和完整保存消息对。
2. 已有会话开始后续生成，客户端收到首段即关闭连接。测试确认上游生成器关闭、Redis 锁释放、旧历史不变，没有保存失败轮次。
3. 另有并发测试在生成暂停期间检查同会话再次生成/删除冲突，以及不同会话能够独立完成。

最终保存是短暂屏蔽取消的提交阶段。若客户端恰好在提交完成后断开，可能收不到 done，但服务端已有成功记录；本周没有请求幂等重放保证。

## 4. 真实 Redis / PostgreSQL

报告：[week3-storage-verification.json](week3-storage-verification.json)。执行脚本：`backend/scripts/verify_week3_storage.py`。

本地原生 PostgreSQL 17.11、Memurai Developer 4.1.7（Redis API 7.2.11）用于实库验收。启动前的连通检查曾出现 Redis TimeoutError 与 PostgreSQL OperationalError；恢复原有回环服务后复验通过。没有用假存储代替实库验收；这一阶段仅操作隔离库，随后按用户授权升级默认库，见下方补充记录。

- Redis：真实 PING、NX 互斥、Lua 原子成对追加及 20 条保留、成功后约 86400 秒 TTL、错误 token 拒绝写入、旧快照与剩余 TTL 恢复、真实键过期、只删除本轮随机消息/锁键，全部通过。
- PostgreSQL：随机 `legalmind_m3_*` schema，迁移至 `20260917_0003`，`alembic check` 无差异，参数和来源为 JSONB，文书/所有权及 history_commit_id UUID 往返、降至 base 后重升 head，全部通过；结束精确删除随机 schema，无残留。
- 原有 M2 PostgreSQL 导入脚本同步修正为读取实际迁移版本；在 M3 head 下首次导入 16、重复跳过 16、JSONB 与精确清理复验通过。
- SQLite 日常配置保持不变。已有 M2 数据库运行 M3 前须执行 `alembic upgrade head`；早期验收只升级隔离临时库，本机默认库现已完成授权升级。

### 默认环境升级与冒烟补充（2026-09-18）

用户明确要求保留现有用户和案例数据，在默认 SQLite 执行迁移，并检查 Redis 与默认环境功能。执行前核实数据库为 `backend/data/legalmind.db`，原版本为 `20260913_0002`，没有文书表；使用 SQLite backup API 创建一致备份并通过 integrity_check。

- 备份：`tmp/backups/legalmind-pre-m3-20260917T192538Z-a395569b.db`，SHA-256 `1C0851F1C83258D2C233F18AEE8B292EC6D017D351541E01927E5F229DAE3546`。备份保留在 Git 忽略目录，不覆盖原始文件。
- 在 backend 目录执行 `python -m alembic upgrade head`，成功升级至 `20260917_0003`；`alembic current` 显示 head，`alembic check` 无差异。已创建 `generated_documents` 并新增 `conversations.history_commit_id`。
- 默认 Redis 配置 PING 返回 PONG，无需重建存储或清空数据。
- 使用默认业务配置、已有 Chroma 集合、真实 BGE/DeepSeek/Redis，在随机本地端口进行 HTTP 冒烟；注册/登录、案例检索/详情、QA、SSE、历史、会话列表/删除、三类文书生成/下载、聊天生成文书均通过。
- 只清理本轮合成账户 UUID 对应的会话、文书和 Redis 键；原有 1 个用户、4 个会话、16 条案例、64 个分块、空法条表及 64 个向量均保留。原表原有列内容哈希与升级前一致，向量、文档和元数据哈希一致；未重导入、重建或清空数据库。
- 独立报告：[week3-default-environment-smoke.json](week3-default-environment-smoke.json)，`passed=true`。本次仅执行迁移和环境验证，没有修改业务运行代码。

## 5. 真实模型联调

报告：[week3-real-model-smoke.json](week3-real-model-smoke.json)。执行脚本：`backend/scripts/smoke_week3_real_model.py`。

使用真实固定 BGE、本地 Chroma、DeepSeek `deepseek-v4-flash`、真实 Redis，以及临时 SQLite。只使用脚本内合成账户/输入及 16 条冻结演示案例；报告中的回答和 SSE 正文均为合成输入结果，不含真实用户数据。

最终结果：**7/7 项通过**。首轮 QA 4.50 秒、追问 3.53 秒，均返回 1 个可追溯演示来源；历史恢复 4 条消息；SSE 以成功 done 完成；三类文书分别生成并下载 MD/TXT；测试用户 Redis 键清理通过。真实模型脚本使用 ASGI 验证功能与完成事件，实时到达/断流由上一节的真实 TCP 测试单独证明。

保留失败过程：第一次联调 QA/追问成功，但流式末尾校验失败；第二次追问因 `qa_external_identifier` 被拒绝，均未作为成功记录。诊断发现历史参考附录/编号会混入下一轮，且对所有书名号内容的拒绝过宽。修正为移除历史参考附录和旧引用标签、只允许当前提供的 DEMO 编号、区分法规名称与普通材料清单标题；新增对应回归后再次实测全部通过。中间一次复验因账户额度耗尽被自动审批拒绝，命令未执行；2026-09-18 恢复后完成上述复验。

这些检查证明本组合输入的链路可运行，不是法律准确性评估。语法引用校验无法证明所有自然语言结论正确；系统仍需演示边界、依据不足提示和人工复核。

最后补充了非 HTTP 外链和全角引用编号的校验与回归，并按各轮实际参考列表离线复核保存的真实模型正文，均通过最终引用校验。文档的 9 份本地链接检查通过。

## 6. 复现命令

先根据 `backend/README.md` 配置本地密钥并启动 Redis/PostgreSQL。以下在 backend 目录执行：

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -m compileall -q app scripts
.\.venv\Scripts\python.exe -m scripts.verify_week3_storage --output ..\docs\acceptance\week3-storage-verification.json

# Requires cached BGE weights and the local DeepSeek configuration; synthetic inputs only.
$env:HF_HUB_OFFLINE='1'
.\.venv\Scripts\python.exe -m scripts.smoke_week3_real_model --output ..\docs\acceptance\week3-real-model-smoke.json
```

在 frontend 目录执行：

```powershell
npm run test
npm run typecheck
npm run build
```

真实模型脚本会使用模型额度；临时 SQLite/Chroma 保留在 Git 忽略的 `tmp/week3-model-*` 以便检查，不覆盖日常库。密钥只在忽略的本地配置，报告和日志不输出密钥或连接凭证。

## 7. 冻结文件与独立交付

2026-09-18 核对以下 SHA-256，全部与 M2 / 原始 PDF 一致：

| 文件 | SHA-256 |
| --- | --- |
| `backend/data/demo/cases.jsonl` | `752EFB9C679BDBB30521BEAF77CC04A38588C49276C10F1E05F0EE452861BB84` |
| `backend/data/evaluation/week2_queries.jsonl` | `DAE562F49CDD93E8B3076B4464F7F4729114C55F5F68BD828AD6817BE4A2AB81` |
| `docs/acceptance/week2-retrieval-evaluation.json` | `A0EB70AD66E234323E6174E4DACABBA44D6C98A894E65746897828C076BCA410` |
| `output/pdf/法律咨询Agent一个月开发计划.pdf` | `9A49723FEE1AD8BB1610A92BC5C088D5F73E12F622859681F2CC2669C61EBC1D` |

交付清单包括代码/测试/迁移、更新后的 README/HANDOFF/API/架构/数据模型/运行文档、本 M3 验收记录及三份 JSON 报告。原始 8 页 PDF 仍在上述路径，内容未改；它未在 Git 提交中，交接时必须单独复制或打包，不能只交付仓库提交。

## 8. 第四周与当前限制

- 当前前端为同步咨询，兼容三类意图、缺项与演示来源提示；SSE 界面、完整来源卡片、服务端历史列表恢复、独立案例/文书页、完整 Docker 部署留第四周。
- Redis 过期后不从其他存储补消息。跨存储使用提交标记和补偿，不是分布式事务；极端故障可能丢失已裁剪旧消息，但不会把未提交尾部作为后续上下文。
- 初始验收时只有合成资料、法条表为空；最终已导入 60 条带来源和版本信息的官方法条选编。仍不能据此提供未经场景、版本和人工复核的确定性法律结论；详见扩展验收记录。
- 本地服务连通已恢复，无阻塞本次 M3 验证的事项；第四周前需重新检查 Docker Desktop/WSL 状态，不能把原生服务证据当完整容器部署验收。
