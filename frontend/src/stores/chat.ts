import { computed, ref } from 'vue'
import { defineStore } from 'pinia'

import { deleteChatSession, hasChatCredential, sendChatMessage } from '@/api/chat'
import { ApiRequestError, normalizeApiError } from '@/api/client'
import { useAuthStore } from '@/stores/auth'
import {
  MAX_CHAT_MESSAGE_LENGTH,
  type ChatMessage,
  type ChatStatus,
  type LocalConversationRecord,
  type TaskAction,
} from '@/types/chat'

function createMessage(
  role: ChatMessage['role'],
  content: string,
  metadata: Partial<Omit<ChatMessage, 'id' | 'role' | 'content'>> = {},
): ChatMessage {
  return {
    id: globalThis.crypto.randomUUID(),
    role,
    content,
    isDemo: false,
    ...metadata,
  }
}

function authMessage(): string {
  return '提交咨询需要登录。当前页面尚未取得登录会话，请先完成登录后再试。'
}

function copyMessages(messages: ChatMessage[]): ChatMessage[] {
  return messages.map((message) => ({
    ...message,
    warnings: message.warnings ? [...message.warnings] : undefined,
  }))
}

function conversationTitle(messages: ChatMessage[]): string {
  const firstQuestion = messages.find((message) => message.role === 'user')?.content
  if (!firstQuestion) return '未命名咨询'
  const normalized = firstQuestion.replace(/\s+/g, ' ').trim()
  return normalized.length > 24 ? `${normalized.slice(0, 24)}…` : normalized
}

export const useChatStore = defineStore('chat', () => {
  const messages = ref<ChatMessage[]>([])
  const draft = ref('')
  const status = ref<ChatStatus>('idle')
  const sessionId = ref<string | null>(null)
  const activeConversationKey = ref<string>(globalThis.crypto.randomUUID())
  const archivedConversations = ref<LocalConversationRecord[]>([])
  const deletingConversationKey = ref<string | null>(null)
  const errorMessage = ref('')
  const errorCode = ref('')
  const errorRequestId = ref<string | undefined>()
  const lastFailedQuestion = ref('')
  const lastFailedAction = ref<{ action: TaskAction; revision: string } | undefined>()
  const hasCredential = ref(hasChatCredential())

  const isSending = computed(() => status.value === 'sending')
  const canSend = computed(() => {
    const length = draft.value.trim().length
    return length > 0 && length <= MAX_CHAT_MESSAGE_LENGTH && !isSending.value
  })
  const conversationRecords = computed<LocalConversationRecord[]>(() => {
    const activeRecord = messages.value.length
      ? [
          {
            key: activeConversationKey.value,
            sessionId: sessionId.value,
            title: conversationTitle(messages.value),
            messages: messages.value,
            isActive: true,
          },
        ]
      : []
    return [
      ...activeRecord,
      ...archivedConversations.value.map((conversation) => ({
        ...conversation,
        isActive: false,
      })),
    ]
  })

  function refreshCredentialState(): void {
    hasCredential.value = hasChatCredential()
  }

  function clearError(): void {
    errorMessage.value = ''
    errorCode.value = ''
    errorRequestId.value = undefined
    if (status.value === 'error') status.value = 'idle'
  }

  function setError(error: ApiRequestError): void {
    status.value = 'error'
    errorCode.value = error.code
    errorRequestId.value = error.requestId
    errorMessage.value = error.code === 'AUTH_REQUIRED' ? authMessage() : error.message
    if (error.code === 'AUTH_REQUIRED') {
      hasCredential.value = false
      discardConversationRecords()
      useAuthStore().logout()
    }
  }

  function validateQuestion(question: string): string | null {
    if (!question) return null
    if (question.length > MAX_CHAT_MESSAGE_LENGTH) {
      setError(
        new ApiRequestError(`问题不能超过 ${MAX_CHAT_MESSAGE_LENGTH} 个字符`, {
          code: 'VALIDATION_ERROR',
        }),
      )
      return null
    }
    return question
  }

  async function requestAnswer(question: string, appendUserMessage: boolean, taskAction?: { action: TaskAction; revision: string }): Promise<boolean> {
    if (isSending.value) return false

    refreshCredentialState()
    clearError()
    if (!hasCredential.value) {
      lastFailedQuestion.value = question
      setError(new ApiRequestError(authMessage(), { status: 401, code: 'AUTH_REQUIRED' }))
      return false
    }

    status.value = 'sending'
    if (appendUserMessage) messages.value.push(createMessage('user', question))

    try {
      const result = taskAction ? await sendChatMessage(question, sessionId.value, taskAction) : await sendChatMessage(question, sessionId.value)
      sessionId.value = result.data.session_id
      messages.value.push(
        createMessage('assistant', result.data.response, {
          intent: result.data.intent,
          sourceCount: result.data.sources.length,
          hasDemoSources: result.data.sources.some((source) => source.is_demo),
          missingFields: result.data.missing_fields,
          warnings: result.data.warnings,
          sources: result.data.sources,
          task: result.data.task,
          documentId: result.data.document_id,
        }),
      )
      lastFailedQuestion.value = ''
      lastFailedAction.value = undefined
      status.value = 'idle'
      return true
    } catch (error: unknown) {
      lastFailedQuestion.value = question
      lastFailedAction.value = taskAction
      setError(normalizeApiError(error))
      return false
    }
  }

  async function submitQuestion(question = draft.value): Promise<boolean> {
    const normalized = validateQuestion(question.trim())
    if (!normalized || isSending.value) return false

    if (hasChatCredential()) draft.value = ''
    return requestAnswer(normalized, true)
  }

  async function retryLastQuestion(): Promise<boolean> {
    const question = validateQuestion(lastFailedQuestion.value.trim())
    if (!question) return false
    return requestAnswer(question, false, lastFailedAction.value)
  }

  async function submitTaskAction(action: TaskAction, revision: string): Promise<boolean> {
    const labels: Record<TaskAction, string> = { confirm: '确认生成', accept_changes: '确认修改', reject_changes: '保留原值', cancel: '取消任务', restart: '重新开始' }
    return requestAnswer(labels[action], true, { action, revision })
  }

  function useSuggestedQuestion(question: string): void {
    if (isSending.value) return
    draft.value = question.slice(0, MAX_CHAT_MESSAGE_LENGTH)
    clearError()
  }

  function resetActiveConversation(): void {
    messages.value = []
    draft.value = ''
    sessionId.value = null
    activeConversationKey.value = globalThis.crypto.randomUUID()
    lastFailedQuestion.value = ''
    clearError()
  }

  function discardConversationRecords(): void {
    messages.value = []
    sessionId.value = null
    activeConversationKey.value = globalThis.crypto.randomUUID()
    archivedConversations.value = []
  }

  function archiveActiveConversation(): void {
    if (!messages.value.length) return
    const record: LocalConversationRecord = {
      key: activeConversationKey.value,
      sessionId: sessionId.value,
      title: conversationTitle(messages.value),
      messages: copyMessages(messages.value),
      isActive: false,
    }
    archivedConversations.value = [
      record,
      ...archivedConversations.value.filter((item) => item.key !== record.key),
    ]
  }

  function startNewConversation(): void {
    if (isSending.value) return
    archiveActiveConversation()
    resetActiveConversation()
  }

  function switchConversation(key: string): void {
    if (isSending.value || deletingConversationKey.value || key === activeConversationKey.value) return
    const target = archivedConversations.value.find((item) => item.key === key)
    if (!target) return

    archiveActiveConversation()
    archivedConversations.value = archivedConversations.value.filter((item) => item.key !== key)
    activeConversationKey.value = target.key
    sessionId.value = target.sessionId
    messages.value = copyMessages(target.messages)
    draft.value = ''
    lastFailedQuestion.value = ''
    clearError()
  }

  function removeConversationLocally(key: string): void {
    if (key === activeConversationKey.value) {
      resetActiveConversation()
      return
    }
    archivedConversations.value = archivedConversations.value.filter((item) => item.key !== key)
  }

  async function deleteConversation(key: string): Promise<boolean> {
    if (isSending.value || deletingConversationKey.value) return false
    const target = conversationRecords.value.find((item) => item.key === key)
    if (!target) return false

    clearError()
    if (!target.sessionId) {
      removeConversationLocally(key)
      return true
    }

    deletingConversationKey.value = key
    try {
      await deleteChatSession(target.sessionId)
      removeConversationLocally(key)
      return true
    } catch (error: unknown) {
      setError(normalizeApiError(error))
      return false
    } finally {
      deletingConversationKey.value = null
    }
  }

  function clearConversation(): void {
    if (isSending.value) return
    discardConversationRecords()
    draft.value = ''
    lastFailedQuestion.value = ''
    clearError()
  }

  return {
    messages,
    draft,
    status,
    sessionId,
    conversationRecords,
    deletingConversationKey,
    errorMessage,
    errorCode,
    errorRequestId,
    lastFailedQuestion,
    hasCredential,
    isSending,
    canSend,
    refreshCredentialState,
    submitQuestion,
    submitTaskAction,
    retryLastQuestion,
    useSuggestedQuestion,
    startNewConversation,
    switchConversation,
    deleteConversation,
    clearConversation,
  }
})
