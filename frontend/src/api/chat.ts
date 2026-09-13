import { ApiRequestError, apiClient, readAccessToken } from '@/api/client'
import type { ApiSuccess } from '@/types/api'
import type { ChatResponseData, ChatSendRequest } from '@/types/chat'

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
    data.intent !== 'qa' ||
    typeof data.session_id !== 'string' ||
    !UUID_PATTERN.test(data.session_id) ||
    !Array.isArray(data.sources) ||
    !Array.isArray(data.missing_fields) ||
    !isStringArray(data.warnings)
  ) {
    throw invalidChatResponse()
  }
  return candidate as ApiSuccess<ChatResponseData>
}

export async function sendChatMessage(
  message: string,
  sessionId: string | null,
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
  }

  const response = await apiClient.post<unknown>('/chat/send', payload, {
    timeout: CHAT_REQUEST_TIMEOUT_MS,
  })
  return parseChatEnvelope(response.data)
}
