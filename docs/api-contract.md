# API 合同设计

文档状态：2026-09-13 已按第二周 M2 案例 API 实现校准
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
| POST | `/api/v1/chat/stream` | 是 | 首月计划 | SSE 流式 Agent 问答 |
| GET | `/api/v1/chat/history/{session_id}` | 是 | 首月计划 | 当前用户会话历史 |
| DELETE | `/api/v1/chat/history/{session_id}` | 是 | 已实现 | 删除当前用户会话 |
| POST | `/api/v1/cases/search` | 是 | M2 已实现 | 案例混合检索 |
| GET | `/api/v1/cases/{case_id}` | 是 | M2 已实现 | 案例详情 |
| GET | `/api/v1/documents/templates` | 是 | 首月计划 | 三类文书及字段定义 |
| POST | `/api/v1/documents/generate` | 是 | 首月计划 | 生成并保存文书草稿 |
| GET | `/api/v1/documents/{document_id}/download` | 是 | 首月计划 | 下载 Markdown/TXT |

“首月计划”表示合同已冻结但尚未挂载路由；M2 标记的两个案例接口已经可用。

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

请求：

```json
{
  "message": "公司拖欠工资，我可以怎样维权？",
  "session_id": null,
  "document_type": null,
  "document_params": null
}
```

- `message`：1-4000 字符。
- `session_id`：可选 UUID；为空时创建当前用户的新会话。
- `document_type` 和 `document_params`：仅在通过聊天发起文书请求时使用。

成功数据：

```json
{
  "response": "回答正文",
  "intent": "qa",
  "sources": [],
  "session_id": "uuid",
  "missing_fields": [],
  "warnings": [
    "AI 内容仅供参考，不构成法律意见；重要事项请咨询执业律师并核对原始依据。",
    "当前版本尚未接入法律资料检索，未提供可核验来源。",
    "当前版本仅保存会话归属，不保存消息正文或上下文。"
  ]
}
```

第 1 周最短链路只支持 `intent=qa`。它会保存新会话 UUID 与当前用户的所有权，但不保存问题、回答正文或多轮上下文；带入已有 `session_id` 时，必须先以同一条数据库查询同时过滤 `id` 和当前 `user_id`，不存在或不属于当前用户均返回 404，且不调用模型。`document_type` 或 `document_params` 在文书能力接入前不会被静默忽略，而是返回 400。

### POST `/api/v1/chat/stream`

请求体与普通问答相同。响应类型为 `text/event-stream`，不使用 JSON 成功外壳。

```text
event: meta
data: {"request_id":"uuid","session_id":"uuid","intent":"qa"}

event: content
data: {"delta":"回答片段"}

event: sources
data: {"items":[]}

event: done
data: {"success":true}
```

若流已经开始后发生错误：

```text
event: error
data: {"code":"MODEL_UNAVAILABLE","message":"模型服务暂时不可用","request_id":"uuid"}

event: done
data: {"success":false}
```

每个事件的 `data` 必须位于单行 JSON 中。代理层需关闭响应缓冲并设置适当的读取超时。

### GET `/api/v1/chat/history/{session_id}`

查询参数 `limit` 默认为 20，范围 1-50。只有会话所有者可以访问；不存在和不属于当前用户都返回 `404 RESOURCE_NOT_FOUND`，避免泄露资源存在性。

### DELETE `/api/v1/chat/history/{session_id}`

当前实现先以会话 UUID 和当前用户 UUID 同时过滤关系库记录；不存在或不属于当前用户均返回 `404 RESOURCE_NOT_FOUND`。操作成功后删除会话归属并返回 `deleted_session_id`。Redis 消息正文接入后，该接口还须精确删除对应消息键；当前没有 Redis 消息可删除。

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

`additional_instructions` 最长 4000 字符；参数对象序列化后最大 20KB。缺少字段时返回 HTTP 422 和 `DOCUMENT_FIELDS_MISSING`，`details.fields` 列出英文名和中文提示。

成功数据包含 `document_id`、`document_type`、`title`、`content`、`sources`、`warnings` 和 `created_at`。正文必须以“草稿，提交或签署前须人工审核”开头。

### GET `/api/v1/documents/{document_id}/download?format=md|txt`

- 只允许创建者下载。
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

## 10. CORS 与日志

- 开发环境仅允许明确配置的本地前端来源。
- 生产配置不允许在携带凭据时使用通配来源。
- 访问日志记录时间、方法、路径模板、状态码、耗时、用户 UUID 和 `request_id`。
- 不记录密码、JWT、API Key、完整聊天正文或完整文书参数。
