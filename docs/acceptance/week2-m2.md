# 第二周 M2 验收记录

验收日期：2026-09-13

当前结论：通过

用户验收确认：2026-09-13 已确认通过

冻结标识：`v0.1.0-m2`。用户确认验收后授权创建，不移动或覆盖既有 M1 标签。

## 验收基线

- 计划文件：`output/pdf/法律咨询Agent一个月开发计划.pdf`
- 计划页数：8
- 计划 SHA-256：`9A49723FEE1AD8BB1610A92BC5C088D5F73E12F622859681F2CC2669C61EBC1D`
- 第二周目标：建立可追溯、可重复导入、可量化评估的案例数据管线，并在本周末交付混合检索和案例 API。
- 用户确认：第二周只交付数据管线和后端案例 API；前端案例页面留到第四周。

## 已确认的第二周技术边界

- 原始数据使用 12-20 条课程演示合成案例，编号统一为 `DEMO-*`，不伪造法院、案号、裁判日期、法条或外部来源。
- 同时定义案例与法条 Schema 和通用导入框架，但第二周不填充未经核验的法条语料。
- Embedding 使用可注入接口；测试使用确定性假实现，本地模型的名称、版本、revision 和 512 维向量配置在接入前固定。
- 关系表与迁移兼容 SQLite/PostgreSQL；日常测试继续使用隔离 SQLite，并增加 PostgreSQL 集成验收。
- 冻结 20 条评估查询，每个领域 5 条；`Top-5 hit rate` 至少达到 16/20。

## Day 1：演示数据基线

### 交付物

- `backend/data/demo/cases.jsonl`
- `backend/data/demo/README.md`
- `backend/tests/data/test_demo_case_dataset.py`

### 数据清单

| 领域 | 数量 | 演示编号 |
| --- | ---: | --- |
| 婚姻家庭 | 4 | `DEMO-MARRIAGE_FAMILY-001` 至 `004` |
| 劳动争议 | 4 | `DEMO-LABOR_DISPUTE-001` 至 `004` |
| 交通事故 | 4 | `DEMO-TRAFFIC_ACCIDENT-001` 至 `004` |
| 合同纠纷 | 4 | `DEMO-CONTRACT_DISPUTE-001` 至 `004` |

数据文件 SHA-256：`752EFB9C679BDBB30521BEAF77CC04A38588C49276C10F1E05F0EE452861BB84`

### 当日完成标准

| 验收项 | 结果 | 证据 |
| --- | --- | --- |
| 每个领域 3-5 条、总计 12-20 条 | 通过 | 四个领域各 4 条，总计 16 条 |
| 演示数据可识别 | 通过 | 所有编号为 `DEMO-*`，并同时设置四个演示/合成标记字段 |
| 来源可追溯 | 通过 | 每条记录含数据集名称、来源说明、采集时间和授权说明 |
| 不伪造司法事实 | 通过 | `court`、`judgment_date`、`source_url` 和 `law_references` 全部为空 |
| 文本可供后续切分 | 通过 | 每条均含标题、摘要、事实、争议焦点和演示分析 |
| 离线基线校验 | 通过 | 2 项定向测试通过 |

### 回归结果

| 检查 | 结果 |
| --- | --- |
| Day 1 数据定向测试 | 2 passed |
| 后端完整测试 | 97 passed |
| 前端测试 | 11 files / 37 tests passed |
| TypeScript 类型检查 | 通过（包含在生产构建命令中） |
| Vite 生产构建 | 通过 |
| `git diff --check` | 通过；仅有 Git 的 LF/CRLF 工作区提示，无空白错误 |

## Day 2：Schema、数据库与可重复导入

- 严格案例/法条 Schema、五组枚举、NFKC 文本规范化、canonical JSON SHA-256 和固定 namespace UUID 已实现。
- 新增 SQLite/PostgreSQL 兼容的 `cases`、`legal_provisions`、`knowledge_chunks` 表及可逆迁移 `20260913_0002`；PostgreSQL 使用 JSONB 变体。
- 案例与法条共用 JSONL 校验、规范化、冲突检测和事务导入框架；演示案例入库状态固定为 `pending`，不写向量。
- SQLite 定向测试 19 项通过；真实 CLI 连续执行结果为首次新增 16、第二次新增 0/跳过 16，库内仍为 16 条 `pending`；完整升降级后业务表残留为 0。
- PostgreSQL 临时 schema 已在 Day 5 完成迁移、导入、幂等和清理实测。

## Day 3：分块、Embedding 与 Chroma

- 案例固定切为标题、摘要+事实、争议焦点、演示分析；超过 800 字时在 500-800 字间择语义边界切分并保留约 100 字重叠，短段落不填充。
- `chunk_id`、内容哈希、字符数和来源引用均确定性生成；16 个案例当前形成 64 个知识块。
- 固定 BGE 模型名、revision、512 维、CPU、L2 归一化及中文查询前缀；真实适配器延迟加载，测试使用中文字符二元组哈希假实现。
- Chroma 正式集合为 `legal_knowledge_v1`、cosine 空间、显式向量；集合元数据不兼容时拒绝打开。
- 37 项 Day 3 定向测试通过；隔离 CLI 索引结果为 16 个 `indexed` 案例、关系库 64 块、Chroma 64 向量、16 个来源引用，持久化重开可查询。
- 真实 BGE 权重下载与量化评估已在 Day 5 通过。

## Day 4：BM25、RRF 与案例 API

- 实现无新增依赖的 Okapi BM25：中文字符二元组、单个中文字符一元组和 ASCII 词元，固定 `k1=1.5`、`b=0.75`。
- 向量与 BM25 分别折叠为最多 10 个来源案例，采用等权 `RRF k=60`；结果稳定去重并支持 `top_k=1..20`。
- `domain`、`source_kind` 在两路召回前应用；向量元数据只参与候选检索，返回字段按 UUID 回查关系库且只接受 `indexed` 来源。
- 新增 JWT 保护的 `POST /api/v1/cases/search` 与 `GET /api/v1/cases/{case_id}`，统一覆盖 401、404、422、424；演示详情固定返回课程合成数据警告。
- 33 项 Day 4 相关定向测试通过，覆盖 BM25、RRF、过滤、Top-K、空结果、来源事实回查、认证、详情和错误/日志净化。

## Day 5：冻结评估与最终审核

- 评估集：`backend/data/evaluation/week2_queries.jsonl`
- 评估集 SHA-256：`DAE562F49CDD93E8B3076B4464F7F4729114C55F5F68BD828AD6817BE4A2AB81`
- 原始案例集 SHA-256：`752EFB9C679BDBB30521BEAF77CC04A38588C49276C10F1E05F0EE452861BB84`
- 逐条报告：`docs/acceptance/week2-retrieval-evaluation.json`
- 报告 SHA-256：`A0EB70AD66E234323E6174E4DACABBA44D6C98A894E65746897828C076BCA410`
- 真实模型：`sentence-transformers 6.0.1` + `BAAI/bge-small-zh-v1.5` revision `7999e1d3359715c523056ef9478215996d62a620`，512 维、CPU、L2 归一化。
- 量化结果：主评估不传领域过滤，Top-5 命中 `20/20`（100%），最低门槛为 `16/20`；两次运行排序稳定，结果无重复案例。评估集冻结后未修改查询、相关性标签或检索参数。
- PostgreSQL 17.11：随机临时 schema 执行 `20260913_0002` head 迁移，五张表齐全，`law_references` 确认为 JSONB；首次导入 16、第二次跳过 16，最终 `schema_removed=true`。

## 最终验收矩阵

| 验收域 | 结果 | 核心证据 |
| --- | --- | --- |
| Schema 与演示数据边界 | 通过 | 未知字段、非法日期/枚举、缺失来源、错误演示组合均失败；16 条均为空法院/裁判日期/外链/法条 |
| 导入与事务 | 通过 | 首次 16、重复 0 新增；编号冲突、内容换号、批内重复及先写后冲突均整批回滚 |
| SQLite 迁移 | 通过 | 完整升级/模型一致性/降级通过，降级后五张业务表残留为 0 |
| PostgreSQL 迁移 | 通过 | 随机 schema 迁移、JSONB、导入与幂等通过，精确清理后无残留 |
| 分块与索引 | 通过 | 确定性分块/ID、512 维、元数据不兼容拒绝、部分写入失败按来源清理、持久化重开通过 |
| 混合检索 | 通过 | BM25、向量、RRF、去重、过滤、Top-K、单路为空保留另一路、双路为空通过 |
| 案例 API | 通过 | JWT、成功结构、详情警告、404/422/424、`indexed` 门槛、关系库事实回查和日志脱敏通过 |
| 真实模型量化 | 通过 | 20/20 Top-5 命中；重复排名稳定、无重复案例 |
| 范围控制 | 通过 | 法条 0 条；未接入聊天 RAG、Redis、LangGraph、SSE、文书或前端案例页 |

## 最终回归

| 检查 | 结果 |
| --- | --- |
| 后端完整 pytest | 149 passed；11 条 Chroma 上游 legacy embedding config 弃用警告，不影响显式向量或结果 |
| Python `compileall` | 通过 |
| 关键依赖导入 | `sentence-transformers 6.0.1`、`torch 2.14.0+cpu`、`transformers 5.17.0`、`chromadb 1.5.9`、`SQLAlchemy 2.0.52`、`psycopg 3.3.5` |
| `pip check` | `No broken requirements found` |
| 前端测试 | 11 files / 37 tests passed |
| TypeScript 类型检查 | 通过 |
| Vite 生产构建 | 通过，106 modules transformed |
| `git diff --check` | 通过；仅有 Git 的 LF/CRLF 工作区提示，无空白错误 |

## 结论与未实现边界

M2 所有硬性项均有真实证据，验收结论为“通过”。本结论只覆盖数据管线、案例索引、混合检索和后端案例 API，不代表以下能力已完成：聊天 RAG、LangGraph Agent、Redis 多轮历史、SSE、文书生成/下载、PostgreSQL 默认切换、Docker 正式部署或前端案例检索页面。

## 完成状态

- [x] Day 2：案例/法条 Schema、清洗、去重、确定性 ID、关系表迁移和可重复导入（SQLite/PostgreSQL 均通过）。
- [x] Day 3：固定中文本地 Embedding、分块和 Chroma 持久化索引（假 Embedding 自动化与真实 BGE 均通过）。
- [x] Day 4：向量 + BM25 + RRF、领域过滤、Top-K、案例搜索与详情 API。
- [x] Day 5：冻结 20 条查询、评估报告、错误与来源检查、M2 完整验收。
