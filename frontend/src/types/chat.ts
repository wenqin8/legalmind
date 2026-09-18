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
  hasDemoSources?: boolean
  missingFields?: string[]
  warnings?: string[]
  sources?: SourceReference[]
  task?: TaskState | null
  documentId?: string | null
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
  task_action?: TaskAction
  task_revision?: string
}

export interface ChatResponseData {
  response: string
  intent: string
  sources: SourceReference[]
  session_id: string
  missing_fields: string[]
  warnings: string[]
  document_id?: string | null
  task?: TaskState | null
}

export interface SourceReference {
  source_type: 'case' | 'legal_provision'
  source_id: string
  citation_id: string
  title: string
  reference_number: string
  publisher: string | null
  date: string | null
  sample_date: string | null
  source_url: string | null
  source_kind: 'demo' | 'official' | 'public_reference'
  is_demo: boolean
  is_synthetic: boolean
  version?: string | null
  effective_from?: string | null
  effective_until?: string | null
  verified_at?: string | null
  status_as_of?: string | null
  legal_status?: string | null
  original_text?: string | null
  applicability?: 'general_reference' | 'event_candidate' | null
}

export type TaskAction = 'confirm' | 'accept_changes' | 'reject_changes' | 'cancel' | 'restart'
export interface TaskState {
  task_id: string
  revision: string
  kind: 'qa' | 'document'
  phase: 'collecting' | 'conflict' | 'review' | 'completed' | 'cancelled'
  fields: Record<string, { value: string; quote: string; source_turn_id: string; source: 'message' | 'parameters' }>
  conflicts: TaskState['fields']
  missing_fields: string[]
  questions: string[]
  document_id: string | null
}

export interface DeletedConversationData {
  deleted_session_id: string
}
