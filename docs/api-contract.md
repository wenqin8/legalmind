# API 合同设计

文档状态：2026-09-18 已按第三周 M3 实现校准
Base URL：`/api/v1`

## 1. 通用规则

- 请求与响应使用 UTF-8 JSON；文书下载接口除外。
- 认证使用 `Authorization: Bearer <token>`。
- 所有响应包含 `X-Request-ID`；JSON 响应体同时包含 `request_id`。
- 客户端可以传入合法的 `X-Request-ID` UUID，否则由后端生成。
- 日期时间使用 ISO 8601 UTC；资源 ID 使用 UUID 字符串。
- 未列为公开的接口均要求登录。
- 不在响应中返回堆栈、SQL、密钥、Token 或第三方原始错误正文。

统一外壳适用于项目业务 JSON 响应。SSE、文书文件下载、CORS 预检以及仅开发环境开放的 Swagger、ReDoc、OpenAPI 工具端点遵循各自协议，不强行包装成 JSON 外壳。

## 2. 响应外壳

成功：

```json
{
  "success": true,
  "data": {},
  "request_id": "06a6f195-d745-4c25-b80d-bf32978f7801"
}
```

失败：

```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "请求参数不正确",
    "details": {
      "fields": []
    }
  },
  "request_id": "06a6f195-d745-4c25-b80d-bf32978f7801"
}
```

## 3. 接口清单

| 方法 | 路径 | 认证 | 当前状态 | 用途 |
| --- | --- | --- | --- | --- |
| GET | `/api/v1/health` | 否 | 已实现 | 健康检查和版本 |
| POST | `/api/v1/auth/register` | 否 | 已实现 | 注册 |
| POST | `/api/v1/auth/login` | 否 | 已实现 | 登录并取得 JWT |
| GET | `/api/v1/auth/me` | 是 | 已实现 | 当前用户信息 |
| POST | `/api/v1/chat/send` | 是 | 已实现 | 普通 Agent 问答 |
| POST | `/api/v1/chat/stream` | 是 | M3 已实现 | SSE 流式 Agent 问答 |
| GET | `/api/v1/chat/history/{session_id}` | 是 | M3 已实现 | 当前用户会话历史 |
| GET | `/api/v1/chat/conversations` | 是 | M3 已实现 | 当前用户会话分页列表 |
| DELETE | `/api/v1/chat/history/{session_id}` | 是 | 已实现 | 删除当前用户会话 |
| POST | `/api/v1/cases/search` | 是 | M2 已实现 | 案例混合检索 |
| GET | `/api/v1/cases/{case_id}` | 是 | M2 已实现 | 案例详情 |
| GET | `/api/v1/documents/templates` | 是 | M3 已实现 | 三类文书及字段定义 |
| POST | `/api/v1/documents/generate` | 是 | M3 已实现 | 生成并保存文书草稿 |
| GET | `/api/v1/documents/{document_id}/download` | 是 | M3 已实现 | 下载 Markdown/TXT |

所有列出的路由已挂载；前端仍采用同步咨询，SSE、服务端记录恢复和独立案例/文书页将在第四周接入。

## 4. 健康检查

### GET `/api/v1/health`

基础健康检查只表示 API 进程可响应，不泄露配置值。

```json
{
  "success": true,
  "data": {
    "status": "healthy",
    "version": "0.1.0"
  },
  "request_id": "uuid"
}
```

## 5. 认证接口

### POST `/api/v1/auth/register`

请求：

```json
{
  "username": "demo_user",
  "email": "demo@example.com",
  "password": "user-supplied-password"
}
```

约束：用户名 3-50 字符；邮箱最长 254 字符；密码 8-128 字符。响应返回用户资料，不自动返回密码或密码哈希。
成功注册返回 HTTP 201。用户名经过 NFKC、去首尾空白和大小写折叠后的值唯一；邮箱以小写规范化值唯一。用户名不能包含 `@`，避免与“用户名或邮箱登录”产生歧义。

### POST `/api/v1/auth/login`

请求：

```json
{
  "login": "demo_user",
  "password": "user-supplied-password"
}
```

成功数据：

```json
{
  "access_token": "jwt",
  "token_type": "bearer",
  "expires_in": 3600,
  "user": {
    "id": "uuid",
    "username": "demo_user",
    "email": "demo@example.com",
    "created_at": "2026-09-12T00:00:00Z"
  }
}
```

首月仅提供有效期 60 分钟的访问令牌，不实现刷新令牌和服务端注销名单。前端退出登录时删除本地令牌。

### GET `/api/v1/auth/me`

返回当前用户的 `id`、`username`、`email` 和 `created_at`。

## 6. 聊天接口

### POST `/api/v1/chat/send`

```json
{
  "message": "公司拖欠工资，我应该整理什么材料？",
  "session_id": null,
  "document_type": null,
  "document_params": null
}
```

- `message`：去首尾空白后 1–4000 字符，必填。
- `session_id`：可选 UUID；为空时分配新会话，仅成功完成后保存关系记录。
- `document_type`：可选三类文书枚举，显式指定时优先进入文书分支。
- `document_params`：可选结构化字符串对象，字段/长度规则见文书接口。类型不明确时先返回 `document_type` 缺项。当前支持从本轮自然语言提取并合并已提交任务状态；冲突必须确认。
- `task_action`：可选 `confirm/accept_changes/reject_changes/cancel/restart`；`task_revision` 为用户所见摘要版本 UUID。陈旧或已过期的版本在流开始前返回 `409 TASK_CHANGED`。确认操作不同时接受字段修改。也支持约定的中文确认、纠正和取消指令。
- 未声明的顶层字段、错误参数类型、非法 UUID/枚举返回 422。

成功外壳的 `data`：

```json
{
  "response": "结论……风险……下一步……参考材料……",
  "intent": "qa",
  "sources": [],
  "session_id": "uuid",
  "missing_fields": [],
  "warnings": ["AI 生成内容仅供参考，不构成法律意见。重要事项请核对原始依据或咨询专业人士。"],
  "document_id": null
}
```

`intent` 为 `qa/search/document`；正文上限 32000 字符（QA 模型正文另限 16000）。无相关证据是成功的保守回答。文书缺项返回 HTTP 200、中文补充提示和英文 `missing_fields`，不生成文书；完整文书返回草稿和 `document_id`。搜索直接返回服务端列表及演示提示，不调用生成模型编造司法事实。

`sources` 的每项包含：`citation_id`（S1–S5）、`source_type`、`source_id`、`title`、`reference_number`、可空 `publisher/date/sample_date/source_url`、`source_kind`、`is_demo`、`is_synthetic`。字段全部由服务端关系来源构造，模型只引用 `[S1]` 等编号。演示来源 `date/source_url=null`，`sample_date` 为样本日期，两个标记为 true；不得把样本日期写成裁判日期。

`legal_provision` 来源另外包含 `version/effective_from/effective_until/verified_at/status_as_of/legal_status/original_text/applicability`，版本和官方原文必填，`effective_until` 为排他失效边界。此时 `date` 为该版本公布日期，`sample_date=null`，双演示标记为 false；`applicability=general_reference|event_candidate` 区分一般参考和事件时间候选依据。核验日期不等于本次实时联网时间；状态资料截止日单独显示。

同步结果、SSE 成功 `done` 和成功历史助手消息新增可空 `task`。其中 `task_id/revision/kind/phase/document_type/domain/mode/fields/conflicts/missing_fields/questions/document_id` 表示当前结构化任务，`phase=collecting|conflict|review|completed|cancelled`。字段值包含 `value/quote/source_turn_id/source`，source 区分自然语言 message 和 parameters。每次最多问三项，收齐文书后返回 review 且 document_id 为空；确认后才生成。重新修订已完成草稿会再次确认并生成新 ID，旧文书保留。任务与历史共用 24 小时 TTL、所有权、互斥和失败补偿。

携带已有会话时，所有权在 Redis 或模型访问前通过 `id + user_id` 过滤；不存在和非本人均返回 404。会话历史过期会附中文警告并使用空上下文。只有成功的完整问答对进入历史；模型截断、引用错误、超时和存储失败均不追加后续上下文。

### POST `/api/v1/chat/stream`

请求同 `/chat/send`。响应为 `text/event-stream`，不使用 JSON 成功外壳；`Cache-Control: no-store`、`X-Accel-Buffering: no`。

```text
event: meta
data: {"request_id":"uuid","session_id":"uuid","intent":"qa"}

event: content
data: {"delta":"通过引用检查的完整段落\n\n"}

event: sources
data: {"items":[]}

event: done
data: {"success":true,"warnings":[],"missing_fields":[],"document_id":null}
```

`content` 可以多次出现。完整段落通过累计引用校验后立即发送，服务端不等待全文；最后还校验完整性及最终输出。`sources` 位于成功正文之后，`done(success=true)` 只在历史和关系记录保存成功后发送。客户端应把完成前的片段视作待确认内容。警告、缺项与文书 ID 在成功 done 中提供，与同步响应一致。

认证、参数、所有权、互斥和初始存储错误在流开始前用普通 HTTP JSON 错误返回。开始后的故障：

```text
event: error
data: {"code":"MODEL_UNAVAILABLE","message":"模型服务暂时不可用，请稍后重试","request_id":"uuid"}

event: done
data: {"success":false}
```

每个 `data` 为单行 JSON，正文中的换行经过转义。断开连接会取消生成并释放资源；断开后无法保证送达错误事件。若最终短事务已提交，断开可能发生在客户端收到 done 之前，不能据此推断服务端从未保存。无请求幂等重放接口。

默认工作流总超时约 65 秒（模型配置 60 秒加协议余量），前端同步超时 72 秒；修改后端预算时也应协调客户端/代理超时。代理需关闭 SSE 缓冲。

### GET `/api/v1/chat/history/{session_id}`

`limit` 默认 20，范围 1–50；Redis 实际最多保留 20 条。按时间顺序返回最近消息，读取不延长 TTL。

```json
{
  "session_id": "uuid",
  "messages": [],
  "history_expired": true,
  "warnings": ["历史内容已过期或尚未保存，本次咨询将从空上下文开始。"]
}
```

消息字段为 `role/content/created_at/turn_id`，助手消息还含 `intent/sources/warnings/missing_fields/document_id`。`turn_id` 只标识成对提交，不是新的会话 ID。缺少消息键返回空列表及过期提示，保留会话元数据；不从日志或浏览器补历史。不存在和非本人均为 `404 RESOURCE_NOT_FOUND`；处理中为 `409 SESSION_BUSY`。

### GET `/api/v1/chat/conversations`

查询参数 `offset=0`（非负）、`limit=20`（1–50）。成功 data 含 `items/total/offset/limit`。items 每项为 `session_id/title/created_at/updated_at/history_expired`；按 `updated_at` 降序，再按 UUID 降序稳定排序。只返回当前用户会话，过期记录仍保留；历史状态是 Redis 键存在性的瞬时快照。Redis 不可用返回 503。

### DELETE `/api/v1/chat/history/{session_id}`

持会话锁精确删除该用户该会话 Redis 消息及关系记录，返回 `deleted_session_id`。关系删除失败执行消息补偿；非本人或不存在为 404，同时生成/删除冲突为 409。该操作不删除独立生成文书。

## 7. 案例接口

### POST `/api/v1/cases/search`

请求：

```json
{
  "query": "劳动报酬争议",
  "domain": "labor_dispute",
  "source_kind": null,
  "top_k": 5
}
```

- `query`：1-1000 字符。
- `domain`：可选 `LegalDomain`。
- `source_kind`：可选；界面必须能显示是否为演示数据。
- `top_k`：1-20，默认 5。

成功数据包含 `items`、实际 `count` 和固定 `score_note`。每项包含案例 UUID、标题、`DEMO-*` 编号、可空法院/日期/链接、领域、摘要、来源类别、双演示标记，以及 `rrf_score`、可空 `vector_rank`、可空 `bm25_rank`。排名信息仅是检索排序依据，不表示法律结论置信度。

搜索先在向量与 BM25 两路应用 `domain`/`source_kind`；最终字段根据 `source_id` 回查关系库，且只返回 `import_status=indexed` 的案例。一路为空时保留另一路，两路为空时返回 `items=[]`。空白/超长查询、非法枚举或 `top_k` 返回统一 422；Embedding、Chroma 或集合不兼容返回净化后的 `424 RETRIEVAL_UNAVAILABLE`。

### GET `/api/v1/cases/{case_id}`

只返回 `indexed` 案例的完整事实、争议焦点、演示分析、来源元数据和引用法条；未知、未索引或非法 UUID 分别按 404/422 处理。演示案例包含 `is_demo=true`、`is_synthetic=true`，并固定警告“课程演示合成数据，不是真实判例或法律依据”。当前演示案例的法院、裁判日期、外链和法条引用均为空。

## 8. 文书接口

### GET `/api/v1/documents/templates`

返回三种 `DocumentType`、中文名称、字段定义、必填状态和长度限制。前端表单由此接口驱动，不自行维护另一套文书枚举。

### POST `/api/v1/documents/generate`

请求：

```json
{
  "document_type": "civil_complaint",
  "parameters": {
    "plaintiff": "用户填写内容",
    "defendant": "用户填写内容",
    "claims": "用户填写内容",
    "facts_and_reasons": "用户填写内容",
    "court": "用户填写内容"
  },
  "additional_instructions": "",
  "use_references": true
}
```

`parameters` 只接受模板声明的字符串字段，拒绝未知字段。身份、法院、案件标识、标的、生效条件等短字段最多 500 字符；事实、请求、意见和条款最多 4000 字符。`additional_instructions` 最长 4000 字符，作为独立用户补充说明原样保留；参数对象按 UTF-8 JSON 序列化后最大 20480 字节。缺少字段时返回 HTTP 422 和 `DOCUMENT_FIELDS_MISSING`，`details.fields` 列出英文名和中文提示。

成功数据包含 `document_id`、`document_type`、`title`、`content`、`sources`、`warnings` 和 `created_at`。正文以“草稿，提交或签署前须人工审核”开头。固定模板只填入已提供内容，不自动补造身份、金额、日期、诉讼请求或合同义务。`use_references=true` 时最多附可追溯演示参考说明；false 时不调用模型或检索即可生成，不将参考写成法律依据。

### GET `/api/v1/documents/{document_id}/download?format=md|txt`

- 以文书 UUID 和当前用户 UUID 同时过滤，只允许创建者下载；不存在和非本人均为 404。
- `format` 默认为 `md`。
- 使用安全、固定规则生成文件名，不把用户原始输入直接作为路径。
- 设置正确的 `Content-Type` 和 `Content-Disposition`。

## 9. 稳定错误码

| HTTP | 错误码 | 使用场景 |
| --- | --- | --- |
| 400 | `BAD_REQUEST` | 请求语义不成立 |
| 401 | `AUTH_REQUIRED` | 缺少、无效或过期 Token |
| 401 | `INVALID_CREDENTIALS` | 登录失败 |
| 409 | `ACCOUNT_ALREADY_EXISTS` | 用户名或邮箱冲突 |
| 409 | `SESSION_BUSY` | 同会话已有生成、历史读取或删除操作 |
| 409 | `TASK_CHANGED` | 任务摘要已更新、取消或过期，不能确认旧版本 |
| 404 | `RESOURCE_NOT_FOUND` | 资源不存在或不属于当前用户 |
| 422 | `VALIDATION_ERROR` | 常规字段校验失败 |
| 422 | `DOCUMENT_FIELDS_MISSING` | 文书必要字段缺失 |
| 424 | `RETRIEVAL_UNAVAILABLE` | 检索依赖不可用 |
| 424 | `MODEL_UNAVAILABLE` | 模型服务不可用 |
| 503 | `DATABASE_UNAVAILABLE` | 当前配置的业务数据库不可用 |
| 503 | `SESSION_STORE_UNAVAILABLE` | Redis 不可用 |
| 503 | `AUTH_UNAVAILABLE` | JWT 登录配置缺失或不安全 |
| 500 | `INTERNAL_ERROR` | 未分类内部错误 |

“没有检索到足够依据”是可预期业务结果，普通问答返回保守回答和空来源，不作为 500 错误。

RAG-v2 保持上述接口与错误外壳。活动 QA 的更正、确认继续原会话任务；`task.fields.case_status` 可保存终审/再审事实及消息出处，`requires_local_material` 表示所问地方资料不在当前冻结资料集中。官方 `sources` 增加 `temporal_rule`（默认 `event_date`，或 `pending_after_effective`）和可空 `transition_text`；服务器参考附录展示过渡原文。`warnings` 包含实际资料版本和演示/评估边界，不把209条评估成绩用于默认60条库。

法律回答每段需通过逐句证据审查才能成为 `content`。一次修订后仍无法支持、审核结构非法或超时均为 `MODEL_UNAVAILABLE`，不当作成功拒答，也不进入后续历史；同步返回424，流开始后使用既有失败事件。业务上的“依据不足”和“必须补充”仍为200，并分别返回空来源或具体 `missing_fields`。

审核可读取本次回答中已经校验并发送的前文来理解条件和指代，最多12000字符，超限移除最早完整段落；前文不充当新增法律证据。引用格式错误与语义错误共用每段一次修订机会，修订后重新检查来源、原文支持和条件，再发送；非法原始段落不会作为成功内容或历史保存。不同请求的来源编号仍独立。

任务字段提取的服务故障、超时或结构非法同样返回 `MODEL_UNAVAILABLE`，不能以空提取结果冒充“资料不足”或“需要补充”；本轮消息和任务变化不保存。意图分类按原合同回退为 `qa`，但后续提取仍必须实际成功。

正文可能在参考材料前增加一段“补充说明”，用于解释筛选阶段认定必要但正文遗漏的依据。该段同样先完成引用与双重语义校验才成为 `content`，之后才返回 `sources`；没有实际支持已验证句子的来源不会仅为提高召回率而附加。补充失败或超时仍使用原错误合同，本轮不写入历史；不新增公共字段。

## 10. CORS 与日志

- 开发环境仅允许明确配置的本地前端来源。
- 生产配置不允许在携带凭据时使用通配来源。
- 访问日志记录时间、方法、路径模板、状态码、耗时、用户 UUID 和 `request_id`。
- 不记录密码、JWT、API Key、完整聊天正文或完整文书参数。
