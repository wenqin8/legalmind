import { computed, ref } from 'vue'
import { defineStore } from 'pinia'

import { hasChatCredential, sendChatMessage } from '@/api/chat'
import { ApiRequestError, normalizeApiError } from '@/api/client'
import { useAuthStore } from '@/stores/auth'
import { MAX_CHAT_MESSAGE_LENGTH, type ChatMessage, type ChatStatus } from '@/types/chat'

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

export const useChatStore = defineStore('chat', () => {
  const messages = ref<ChatMessage[]>([])
  const draft = ref('')
  const status = ref<ChatStatus>('idle')
  const sessionId = ref<string | null>(null)
  const errorMessage = ref('')
  const errorCode = ref('')
  const errorRequestId = ref<string | undefined>()
  const lastFailedQuestion = ref('')
  const hasCredential = ref(hasChatCredential())

  const isSending = computed(() => status.value === 'sending')
  const canSend = computed(() => {
    const length = draft.value.trim().length
    return length > 0 && length <= MAX_CHAT_MESSAGE_LENGTH && !isSending.value
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

  async function requestAnswer(question: string, appendUserMessage: boolean): Promise<boolean> {
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
      const result = await sendChatMessage(question, sessionId.value)
      sessionId.value = result.data.session_id
      messages.value.push(
        createMessage('assistant', result.data.response, {
          intent: result.data.intent,
          sourceCount: result.data.sources.length,
          warnings: result.data.warnings,
        }),
      )
      lastFailedQuestion.value = ''
      status.value = 'idle'
      return true
    } catch (error: unknown) {
      lastFailedQuestion.value = question
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
    return requestAnswer(question, false)
  }

  function useSuggestedQuestion(question: string): void {
    if (isSending.value) return
    draft.value = question.slice(0, MAX_CHAT_MESSAGE_LENGTH)
    clearError()
  }

  function clearConversation(): void {
    if (isSending.value) return
    messages.value = []
    draft.value = ''
    sessionId.value = null
    lastFailedQuestion.value = ''
    clearError()
  }

  return {
    messages,
    draft,
    status,
    sessionId,
    errorMessage,
    errorCode,
    errorRequestId,
    lastFailedQuestion,
    hasCredential,
    isSending,
    canSend,
    refreshCredentialState,
    submitQuestion,
    retryLastQuestion,
    useSuggestedQuestion,
    clearConversation,
  }
})
