# 系统架构与工作流设计

文档状态：第 1 周第 2 天形成首月设计基线；2026-09-13 按新版计划完成 M1 基础设施就绪验收
适用范围：首月四周目标架构与第一周 M1 实际运行边界

本文同时记录两种范围：“首月四周目标”是四周结束时计划形成的完整 MVP，“第一周 M1”是已经冻结并实际验收的可运行切片。目标架构中的组件不得据此视为已在 M1 接入。

第一周已交付的实际路径如下：

```mermaid
flowchart LR
    Browser[Vue 3 注册、登录与咨询台] -->|/api/v1 + Bearer JWT| API[FastAPI]
    API --> Auth[认证与会话所有权服务]
    Auth --> DB[(SQLAlchemy / 本地 SQLite)]
    API --> Chat[单次同步问答服务]
    Chat --> LLM[可注入 LLM 端口]
    LLM --> Adapter[Fake / DeepSeek 适配器]
```

M1 只存用户与会话归属，不存消息正文。可注入 LLM 与 DeepSeek 适配器已经运行并完成真实调用验收；LangChain/LangGraph 只完成依赖准备，尚无运行工作流。RAG、Redis 消息历史、SSE、案例和文书接口均未接入。新版计划要求的 PostgreSQL、Redis 和 Chroma 环境就绪项已通过独立 smoke test；M1 业务路径仍使用 SQLite，不能把连通验收误写为业务接入。

前端允许在当前页面生命周期内归档、切换和删除多次咨询，解决“新建咨询后旧内容立即消失”的交互问题。删除已有后端会话时，先由受保护接口校验用户归属并删除关系库记录，成功后再移除前端记录；删除失败则保留界面内容。消息副本只存在 Pinia 内存中，页面刷新或退出登录即清除，也不会作为模型的多轮上下文；这一界面能力不替代后续 Redis 消息历史。

### 里程碑状态表

| 组件或能力 | 首月四周目标 | 第一周 M1 实际状态 |
| --- | --- | --- |
| Vue 3 前端 | 承载认证、问答、案例、文书和会话界面 | 已运行注册、登录、受保护咨询台与同步问答 |
| FastAPI | 提供完整 `/api/v1` 业务 API | 已运行健康检查、认证、受保护的 `POST /chat/send` 和 `DELETE /chat/history/{session_id}` |
| 可注入 LLM | 通过统一端口服务 Agent 各生成节点 | `LLMClient`、Fake 与 DeepSeek 适配器已运行；真实 DeepSeek 调用已验收 |
| SQLite | 本地开发兼容与阶段性验收数据库 | M1 实际关系数据库；仅保存用户和会话归属，迁移升降级已验收 |
| PostgreSQL | 月末关系业务数据库与来源事实库 | `psycopg`、独立 URL 和 PostgreSQL 17.11 `SELECT 1` smoke test 已通过；尚未切换应用迁移与业务表 |
| LangChain / LangGraph | 编排 `qa`、`search`、`document` 工作流 | 已显式加入运行依赖并验证导入；运行时代码中尚无 `AgentState`、图构建或调用链 |
| Redis | 保存有 TTL 的短期会话消息 | Python 客户端、独立 URL 及 Redis API 7.2.11 临时键往返 smoke test 已通过；当前页面记录仅在前端内存，Redis 尚未保存消息正文 |
| Chroma | 提供本地持久化向量检索 | 本地持久化客户端的写入、向量查询和探针集合清理已通过；尚无正式集合、Embedding、RAG 或回答来源 |

本文后续主图、请求链路、Agent 工作流和故障策略均属于“首月四周目标”；M1 的完成状态只以本节实际路径和状态表为准。

## 1. 首月四周架构目标

- 核心链路可独立测试，模型、检索和存储故障有明确边界。
- 前后端统一使用 `/api/v1`，前端不直接访问数据库、Redis、Chroma 或模型服务。
- DeepSeek 通过 OpenAI 兼容客户端接入，但业务代码只依赖项目内的 LLM 接口。
- 目标状态下，Chroma 采用后端进程内的本地持久化模式，开发和 Docker 环境只改变持久化路径。
- 目标状态下，PostgreSQL 负责持久业务数据和所有权，Redis 只负责有过期时间的短期会话消息。
- 演示资料与真实资料在导入、检索、展示和回答中始终可区分。

## 2. 首月四周目标系统组件

下图是四周结束时的目标拓扑，不是 M1 运行拓扑。

```mermaid
flowchart TB
    User[访客或注册用户] --> Web[Vue 3 Web 应用]
    Web -->|HTTPS / JSON / SSE| API[FastAPI /api/v1]

    subgraph Backend[后端应用]
        API --> MW[请求 ID、认证、异常处理]
        MW --> Routes[Auth / Chat / Cases / Documents]
        Routes --> Services[应用服务层]
        Services --> Graph[LangGraph 工作流]
        Graph --> LLM[LLM 端口]
        Graph --> Retrieval[混合检索服务]
        Services --> Repositories[仓储层]
        Retrieval --> VectorAdapter[Chroma 适配器]
        Retrieval --> Keyword[BM25 关键词检索器]
    end

    LLM -->|OpenAI 兼容协议| DeepSeek[DeepSeek API]
    Repositories --> PostgreSQL[(PostgreSQL)]
    Services --> Redis[(Redis 会话缓存)]
    VectorAdapter --> Chroma[(本地 Chroma)]
    Keyword --> Corpus[(受控检索语料)]
    PostgreSQL --> Corpus
```

### 2.1 边界规则

- 路由层只负责协议转换、身份提取和输入校验，不直接拼 Prompt 或访问数据库。
- 服务层组织用例和事务，不包含 HTTP 细节。
- Agent 节点输入输出统一通过 `AgentState`，不得依赖全局可变状态。
- LLM 和 Embedding 均通过接口注入；测试环境使用确定性假实现。
- 仓储层执行用户所有权过滤，不能只在前端或路由层判断。
- 检索层只能把带来源元数据的资料交给生成层。

## 3. 首月四周目标请求处理链路

下列时序包含尚未接入的 LangGraph、RAG、Redis 和 PostgreSQL 实库。

```mermaid
sequenceDiagram
    actor U as 用户
    participant F as Vue 前端
    participant A as FastAPI
    participant S as 应用服务
    participant G as LangGraph
    participant R as RAG
    participant L as DeepSeek
    participant D as PostgreSQL/Redis

    U->>F: 提交问题
    F->>A: Bearer Token + 请求体
    A->>A: 生成 request_id 并校验 JWT
    A->>S: 用户 ID、请求 DTO
    S->>D: 校验会话所有权并加载上下文
    S->>G: 初始化 AgentState
    G->>R: 按意图检索资料
    R-->>G: 带来源的候选资料
    G->>L: 受控 Prompt + 证据
    L-->>G: 回答或文书草稿
    G-->>S: 标准化结果
    S->>D: 保存当前用户会话
    S-->>A: 领域结果
    A-->>F: 统一 JSON 或 SSE 事件
    F-->>U: 内容、来源和免责声明
```

## 4. 首月四周目标 Agent 工作流

M1 仅准备了 LangGraph Python 依赖；本节的状态结构、节点和条件边仍是后续实现合同，尚未进入当前问答运行链路。

### 4.1 AgentState

| 字段 | 类型 | 必需 | 说明 |
| --- | --- | --- | --- |
| `request_id` | UUID | 是 | 单次请求追踪 ID |
| `user_id` | UUID | 是 | 已认证用户 ID |
| `session_id` | UUID | 是 | 会话 ID；缺省时由服务层创建 |
| `query` | string | 是 | 清洗后的用户输入 |
| `intent` | `qa/search/document` | 路由后 | 严格枚举 |
| `conversation_messages` | list | 是 | 当前用户当前会话的有限历史 |
| `document_type` | enum/null | 文书时 | 三种英文标识之一 |
| `document_params` | object | 文书时 | 已校验的结构化参数 |
| `retrieved_sources` | list | 检索后 | 带来源元数据的证据 |
| `missing_fields` | list[string] | 否 | 文书缺失字段 |
| `response` | string/null | 完成时 | 回答、搜索摘要或文书草稿 |
| `warnings` | list[string] | 是 | 免责声明、演示数据等提示 |
| `error_code` | string/null | 否 | 可映射到稳定 API 错误码 |

状态对象不保存 API Key、JWT、密码或完整请求日志。

### 4.2 工作流图

```mermaid
flowchart TD
    Start([开始]) --> Validate[校验并规范化输入]
    Validate --> Context[加载当前用户会话上下文]
    Context --> Intent[意图识别]
    Intent --> Route{intent}

    Route -->|qa| QRetrieve[检索案例和法条]
    QRetrieve --> Evidence{证据是否足够}
    Evidence -->|是| QGenerate[基于证据生成回答]
    Evidence -->|否| Refuse[生成依据不足提示]

    Route -->|search| Search[执行混合检索]
    Search --> SearchOutput[整理案例列表]

    Route -->|document| DocValidate[校验文书类型和参数]
    DocValidate --> Missing{是否缺少必要字段}
    Missing -->|是| NeedInfo[返回缺失字段]
    Missing -->|否| DocRetrieve[可选检索参考依据]
    DocRetrieve --> DocGenerate[按固定模板生成草稿]

    QGenerate --> Finalize[来源校验与统一输出]
    Refuse --> Finalize
    SearchOutput --> Finalize
    NeedInfo --> Finalize
    DocGenerate --> Finalize
    Finalize --> Save[保存会话消息]
    Save --> End([结束])
```

### 4.3 路由规则

- `document`：包含明确的生成、起草、修改文书意图，或请求体已提供 `document_type`。
- `search`：明确要求查找、列出、比较案例，输出重点是案例列表。
- `qa`：其他合法问题默认进入问答，作为意图模型异常时的安全回退。
- 专用案例和文书 API 直接进入对应服务，不重复调用意图识别；聊天 API 才运行完整路由图。
- 意图模型输出不在枚举中时记录可观测事件并回退为 `qa`，不把原始模型输出暴露给用户。

## 5. 首月四周目标 RAG 数据流

本节是后续目标。M1 尚未加入 Chroma、Embedding、BM25、导入器或检索运行链路。

### 5.1 导入流程

```mermaid
flowchart LR
    Raw[演示或公开资料] --> Validate[字段与来源校验]
    Validate --> Normalize[文本规范化]
    Normalize --> Hash[计算 source/content hash]
    Hash --> Dedup{是否已导入}
    Dedup -->|是| Skip[跳过或更新元数据]
    Dedup -->|否| Persist[保存来源元数据到 PostgreSQL]
    Persist --> Chunk[按语义边界分块]
    Chunk --> Embed[生成 Embedding]
    Embed --> Upsert[按确定性 chunk_id 写入 Chroma]
    Chunk --> Keyword[重建 BM25 语料索引]
```

导入失败不得留下“数据库已保存但向量缺失”的成功状态。实现阶段使用显式导入状态，并提供可重复执行的重建命令。

### 5.2 查询流程

```mermaid
flowchart LR
    Query[用户查询] --> Clean[清洗与长度校验]
    Clean --> Filters[构造领域和来源过滤条件]
    Filters --> Vector[Chroma 向量召回]
    Filters --> BM25[BM25 关键词召回]
    Vector --> Merge[RRF 合并去重]
    BM25 --> Merge
    Merge --> Gate[来源完整性与最低质量门槛]
    Gate --> Top[选择最终 Top 3-5]
    Top --> Context[构造带编号上下文]
    Context --> Generate[问答或文书生成]
    Generate --> Verify[核对引用仅来自输入证据]
```

### 5.3 检索参数基线

- 分块目标：500-800 个中文字符，重叠约 80-120 个字符。
- 向量和 BM25 各召回最多 10 条候选。
- 使用 Reciprocal Rank Fusion 合并排名，避免直接混合不可比较的原始分数。
- 去重后向 Agent 提供 3-5 条证据。
- 首月不增加正式 Reranker；质量不足通过来源门槛和拒答处理。
- 所有数字做成配置项，第二周根据测试集结果调整。

## 6. 计划目录结构

```text
legal-mind/
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── api/
│   │   │   └── v1/
│   │   │       ├── router.py
│   │   │       └── endpoints/
│   │   │           ├── auth.py
│   │   │           ├── health.py
│   │   │           ├── chat.py
│   │   │           ├── cases.py
│   │   │           └── documents.py
│   │   ├── agents/
│   │   │   ├── state.py
│   │   │   ├── workflow.py
│   │   │   └── nodes/
│   │   ├── core/
│   │   │   ├── config.py
│   │   │   ├── errors.py
│   │   │   ├── logging.py
│   │   │   └── security.py
│   │   ├── db/
│   │   │   ├── base.py
│   │   │   ├── models.py
│   │   │   └── session.py
│   │   ├── llm/
│   │   │   ├── base.py
│   │   │   ├── deepseek.py
│   │   │   ├── fake.py
│   │   │   └── prompts.py
│   │   ├── rag/
│   │   │   ├── chunking.py
│   │   │   ├── embeddings.py
│   │   │   ├── importer.py
│   │   │   ├── retriever.py
│   │   │   └── vector_store.py
│   │   ├── repositories/
│   │   ├── schemas/
│   │   └── services/
│   ├── migrations/
│   ├── data/demo/
│   ├── scripts/
│   ├── tests/
│   │   ├── unit/
│   │   ├── integration/
│   │   └── fixtures/
│   ├── .env.example
│   ├── requirements.txt
│   └── requirements-dev.txt
├── frontend/
│   ├── src/
│   │   ├── api/
│   │   ├── components/
│   │   ├── router/
│   │   ├── stores/
│   │   ├── types/
│   │   ├── views/
│   │   ├── tests/
│   │   ├── App.vue
│   │   └── main.ts
│   ├── .env.example
│   ├── package.json
│   └── vite.config.ts
├── docs/
├── output/
├── .gitignore
├── docker-compose.yml
├── HANDOFF.md
└── README.md
```

测试目录按行为分层；不为每个源文件机械创建一一对应的测试文件。运行时生成的数据不进入 Git。

上述仍是月末目标目录；`agents`、`rag`、`repositories`、案例/文书路由和部分数据目录在 M1 中尚未创建。`migrations` 是已落地的 Alembic 脚本目录；LangGraph 当前仅在依赖清单中准备，不能因依赖存在而把 `agents` 目录或运行工作流标为已实现。

## 7. 首月四周目标关键架构决策

| 决策 | 选择 | 原因 |
| --- | --- | --- |
| API 版本 | 全部使用 `/api/v1` | 消除前后端和代理路径冲突 |
| 标识符 | UUID v4 | 统一数据库、API 与会话 ID，降低顺序 ID 泄露风险 |
| LLM | 单一 DeepSeek 适配器 | 满足首月范围，同时保留可替换接口 |
| Chroma | 本地持久化 | 减少独立服务和部署复杂度 |
| 混合检索 | Chroma + BM25 + RRF | 满足语义与关键词召回，不引入正式重排模型 |
| 会话 | PostgreSQL 记所有权，Redis 存消息 | 实现隔离并保持短期记忆简单 |
| 流式协议 | SSE 具名事件 | 前端能区分正文、来源、错误和完成状态 |
| 文书输出 | Markdown/TXT | 满足首月下载，避免引入 DOCX/PDF 生成链路 |
| 测试模型 | 依赖注入的假模型 | 测试不依赖网络、余额或模型输出波动 |

## 8. 首月四周目标故障与降级原则

PostgreSQL、Redis、Chroma、Embedding、BM25 和 SSE 的条目是对应组件接入后的验收合同。M1 已实现并验证的是关系数据库抽象及 DeepSeek 调用的错误边界，不代表尚未接入的服务已有运行时降级代码。

- PostgreSQL 不可用：认证和所有业务请求失败，返回数据库不可用错误。
- Redis 不可用：不静默退化为跨用户内存缓存；会话相关请求返回明确错误。
- Chroma 或 Embedding 不可用：案例检索失败；法律问答不得绕过来源要求直接编造回答。
- DeepSeek 不可用：保留已检索来源，但返回模型服务不可用错误，不生成伪答案。
- BM25 单路为空：保留向量结果；向量单路为空：保留 BM25 结果；两路均为空时触发依据不足。
- SSE 已开始后出错：发送 `error` 事件和 `done` 事件并正常关闭连接。

## 9. 第二天设计完成定义

- [x] 系统组件和访问边界明确。
- [x] AgentState、节点、条件边和回退规则明确。
- [x] RAG 导入、检索、合并和来源门槛明确。
- [x] 计划目录结构明确。
- [x] 数据模型和 API 合同分别形成文档。
- [x] 冲突项已形成统一架构决策。
