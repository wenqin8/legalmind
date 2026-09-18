import { ApiRequestError, apiClient, readAccessToken } from '@/api/client'
import type { ApiSuccess } from '@/types/api'
import type { ChatResponseData, ChatSendRequest, DeletedConversationData, SourceReference, TaskState, TaskAction } from '@/types/chat'

export const CHAT_REQUEST_TIMEOUT_MS = 72_000
const UUID_PATTERN = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i

export function hasChatCredential(): boolean {
  return readAccessToken() !== null
}

function invalidChatResponse(): ApiRequestError {
  return new ApiRequestError('服务响应异常，请稍后重试', { code: 'INVALID_RESPONSE' })
}

function isStringArray(value: unknown): value is string[] {
  return Array.isArray(value) && value.every((item) => typeof item === 'string')
}

function isSource(value: unknown): value is SourceReference {
  if (!value || typeof value !== 'object') return false
  const source = value as Partial<SourceReference>
  const optionalText = (item: unknown) => item === null || typeof item === 'string'
  return (
    ['case', 'legal_provision'].includes(source.source_type ?? '') &&
    typeof source.source_id === 'string' && UUID_PATTERN.test(source.source_id) &&
    typeof source.citation_id === 'string' && /^S[1-5]$/.test(source.citation_id) &&
    typeof source.title === 'string' && !!source.title.trim() &&
    typeof source.reference_number === 'string' && !!source.reference_number.trim() &&
    optionalText(source.publisher) && optionalText(source.date) && optionalText(source.sample_date) &&
    optionalText(source.source_url) &&
    ['demo', 'official', 'public_reference'].includes(source.source_kind ?? '') &&
    typeof source.is_demo === 'boolean' && typeof source.is_synthetic === 'boolean' &&
    (source.source_type !== 'legal_provision' || (
      source.source_kind === 'official' && !source.is_demo &&
      typeof source.version === 'string' && !!source.version &&
      typeof source.original_text === 'string' && !!source.original_text &&
      typeof source.verified_at === 'string' && typeof source.status_as_of === 'string' &&
      typeof source.effective_from === 'string' &&
      typeof source.source_url === 'string' && /^https:\/\/[^/]+\.gov\.cn\//.test(source.source_url) &&
      ['general_reference', 'event_candidate'].includes(source.applicability ?? '')
    )) &&
    (source.is_demo
      ? source.source_kind === 'demo' && source.is_synthetic === true && source.date === null && source.source_url === null
      : source.source_kind !== 'demo' && source.is_synthetic === false)
  )
}

function isTask(value: unknown): value is TaskState {
  if (!value || typeof value !== 'object') return false
  const task = value as Partial<TaskState>
  const fieldsValid = (fields: unknown) => !!fields && typeof fields === 'object' && !Array.isArray(fields) &&
    Object.values(fields).every((field) => field && typeof field.value === 'string' && typeof field.quote === 'string' &&
      typeof field.source_turn_id === 'string' && UUID_PATTERN.test(field.source_turn_id) && ['message', 'parameters'].includes(field.source))
  return typeof task.task_id === 'string' && UUID_PATTERN.test(task.task_id) &&
    typeof task.revision === 'string' && UUID_PATTERN.test(task.revision) &&
    ['qa', 'document'].includes(task.kind ?? '') &&
    ['collecting', 'conflict', 'review', 'completed', 'cancelled'].includes(task.phase ?? '') &&
    fieldsValid(task.fields) && fieldsValid(task.conflicts) && isStringArray(task.questions) &&
    task.questions.length <= 3 && isStringArray(task.missing_fields) &&
    (task.document_id === null || (typeof task.document_id === 'string' && UUID_PATTERN.test(task.document_id)))
}

function parseChatEnvelope(value: unknown): ApiSuccess<ChatResponseData> {
  if (!value || typeof value !== 'object') throw invalidChatResponse()
  const candidate = value as Partial<ApiSuccess<ChatResponseData>>
  const data = candidate.data as Partial<ChatResponseData> | undefined
  if (
    candidate.success !== true ||
    typeof candidate.request_id !== 'string' ||
    !candidate.request_id.trim() ||
    !data ||
    typeof data.response !== 'string' ||
    !data.response.trim() ||
    !['qa', 'search', 'document'].includes(data.intent ?? '') ||
    typeof data.session_id !== 'string' ||
    !UUID_PATTERN.test(data.session_id) ||
    !Array.isArray(data.sources) ||
    !data.sources.every(isSource) ||
    !isStringArray(data.missing_fields) ||
    (data.document_id != null && (typeof data.document_id !== 'string' || !UUID_PATTERN.test(data.document_id))) ||
    (data.task != null && !isTask(data.task)) ||
    !isStringArray(data.warnings)
  ) {
    throw invalidChatResponse()
  }
  return candidate as ApiSuccess<ChatResponseData>
}

function parseDeleteEnvelope(value: unknown): ApiSuccess<DeletedConversationData> {
  if (!value || typeof value !== 'object') throw invalidChatResponse()
  const candidate = value as Partial<ApiSuccess<DeletedConversationData>>
  const sessionId = candidate.data?.deleted_session_id
  if (
    candidate.success !== true ||
    typeof candidate.request_id !== 'string' ||
    !candidate.request_id.trim() ||
    typeof sessionId !== 'string' ||
    !UUID_PATTERN.test(sessionId)
  ) {
    throw invalidChatResponse()
  }
  return candidate as ApiSuccess<DeletedConversationData>
}

export async function sendChatMessage(
  message: string,
  sessionId: string | null,
  taskAction?: { action: TaskAction; revision: string },
): Promise<ApiSuccess<ChatResponseData>> {
  if (!hasChatCredential()) {
    throw new ApiRequestError('请先登录后再提交咨询', {
      status: 401,
      code: 'AUTH_REQUIRED',
    })
  }

  const payload: ChatSendRequest = {
    message,
    session_id: sessionId,
    document_type: null,
    document_params: null,
    ...(taskAction ? { task_action: taskAction.action, task_revision: taskAction.revision } : {}),
  }

  const response = await apiClient.post<unknown>('/chat/send', payload, {
    timeout: CHAT_REQUEST_TIMEOUT_MS,
  })
  return parseChatEnvelope(response.data)
}

export async function deleteChatSession(
  sessionId: string,
): Promise<ApiSuccess<DeletedConversationData>> {
  if (!hasChatCredential()) {
    throw new ApiRequestError('请先登录后再删除咨询', {
      status: 401,
      code: 'AUTH_REQUIRED',
    })
  }
  if (!UUID_PATTERN.test(sessionId)) throw invalidChatResponse()

  const response = await apiClient.delete<unknown>(`/chat/history/${sessionId}`)
  return parseDeleteEnvelope(response.data)
}
