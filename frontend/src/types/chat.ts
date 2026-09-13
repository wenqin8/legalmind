export type ChatRole = 'user' | 'assistant'
export type ChatStatus = 'idle' | 'sending' | 'error'

export const MAX_CHAT_MESSAGE_LENGTH = 4_000

export interface ChatMessage {
  id: string
  role: ChatRole
  content: string
  isDemo: boolean
  intent?: string
  sourceCount?: number
  warnings?: string[]
}

export interface LocalConversationRecord {
  key: string
  sessionId: string | null
  title: string
  messages: ChatMessage[]
  isActive: boolean
}

export interface ChatSendRequest {
  message: string
  session_id: string | null
  document_type: null
  document_params: null
}

export interface ChatResponseData {
  response: string
  intent: string
  sources: unknown[]
  session_id: string
  missing_fields: unknown[]
  warnings: string[]
}
