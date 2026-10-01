import { apiClient, ApiRequestError } from '@/api/client'
import { parseChatEnvelope, UUID_PATTERN } from '@/api/chat'
import type { ChatMessage } from '@/types/chat'

export interface ConversationSummary {
  session_id: string; title: string; updated_at: string; history_expired: boolean
}
export interface HistoryResult {
  messages: ChatMessage[]; history_expired: boolean; warnings: string[]
}
const uuid = UUID_PATTERN
function invalid(): never { throw new ApiRequestError('服务响应异常，请稍后重试', { code: 'INVALID_RESPONSE' }) }

export async function listConversations(offset = 0) {
  const { data: envelope } = await apiClient.get('/chat/conversations', { params: { offset, limit: 20 } })
  const data = envelope?.data
  if (envelope?.success !== true || !Array.isArray(data?.items) || !Number.isInteger(data.total) || data.total < 0 ||
    data.offset !== offset || data.limit !== 20 || !data.items.every((item: ConversationSummary) =>
      uuid.test(item.session_id) && typeof item.title === 'string' && typeof item.updated_at === 'string' && typeof item.history_expired === 'boolean')) invalid()
  return data as { items: ConversationSummary[]; total: number; offset: number; limit: number }
}

export async function readHistory(sessionId: string): Promise<HistoryResult> {
  const { data: envelope } = await apiClient.get(`/chat/history/${sessionId}`)
  const data = envelope?.data
  if (envelope?.success !== true || data?.session_id !== sessionId || !Array.isArray(data.messages) ||
    typeof data.history_expired !== 'boolean' || !Array.isArray(data.warnings) || !data.warnings.every((w: unknown) => typeof w === 'string')) invalid()
  const messages = data.messages.map((item: Record<string, unknown>, index: number): ChatMessage => {
    if (!['user', 'assistant'].includes(String(item.role)) || typeof item.content !== 'string' || !item.content.trim() || (item.turn_id != null && !uuid.test(String(item.turn_id)))) invalid()
    if (item.turn_id == null && typeof item.created_at !== 'string') invalid()
    const id = `${item.turn_id ?? item.created_at}-${index}`
    if (item.role === 'user') return { id, role: 'user', content: item.content, isDemo: false }
    const result = parseChatEnvelope({ ...envelope, data: { ...item, response: item.content, session_id: sessionId } }).data
    return { id, role: 'assistant', content: result.response, isDemo: false,
      intent: result.intent, sources: result.sources, sourceCount: result.sources.length,
      hasDemoSources: result.sources.some(s => s.is_demo), warnings: result.warnings, task: result.task,
      missingFields: result.missing_fields, documentId: result.document_id, delivery: 'completed' }
  })
  return { messages, history_expired: data.history_expired, warnings: data.warnings }
}
