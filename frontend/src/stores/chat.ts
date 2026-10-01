import { computed, ref, watch } from 'vue'
import { defineStore } from 'pinia'
import { deleteChatSession, hasChatCredential } from '@/api/chat'
import { listConversations, readHistory, type ConversationSummary } from '@/api/chat-session'
import { streamChat } from '@/api/chat-stream'
import { ApiRequestError, normalizeApiError } from '@/api/client'
import { useAuthStore } from '@/stores/auth'
import { MAX_CHAT_MESSAGE_LENGTH, type ChatMessage, type ChatStatus, type LocalConversationRecord, type TaskAction } from '@/types/chat'

export const useChatStore = defineStore('chat', () => {
  const auth = useAuthStore()
  const messages = ref<ChatMessage[]>([]), draft = ref(''), status = ref<ChatStatus>('idle')
  const sessionId = ref<string | null>(null), activeKey = ref(crypto.randomUUID() as string)
  const records = ref<ConversationSummary[]>([]), localRecords = ref<LocalConversationRecord[]>([])
  const deletingConversationKey = ref<string | null>(null), loadingHistory = ref(false), loadingRecords = ref(false)
  const recordTotal = ref(0), historyNotice = ref(''), recordError = ref('')
  const errorMessage = ref(''), errorCode = ref(''), errorRequestId = ref<string>()
  const lastFailedQuestion = ref(''), hasCredential = ref(hasChatCredential())
  let lastAction: { action: TaskAction; revision: string } | undefined
  let controller: AbortController | undefined, generation = 0
  let uncertain: { session: string; previousTail?: string; question: string } | undefined
  const isSending = computed(() => status.value === 'sending')
  const isBusy = computed(() => isSending.value || loadingHistory.value || !!deletingConversationKey.value)
  const canSend = computed(() => !!draft.value.trim() && draft.value.trim().length <= MAX_CHAT_MESSAGE_LENGTH && !isBusy.value)
  const conversationRecords = computed<LocalConversationRecord[]>(() => {
    const title = messages.value.find(m => m.role === 'user')?.content.slice(0,24) || '当前咨询'
    const active = messages.value.length || sessionId.value ? [{ key: activeKey.value, sessionId: sessionId.value, title, messages: messages.value, isActive: true }] : []
    const server = records.value.filter(r => r.session_id !== sessionId.value).map(r => ({
      key: r.session_id, sessionId: r.session_id, title: r.title, messages: [], isActive: false, historyExpired: r.history_expired, updatedAt: r.updated_at,
    }))
    return [...active, ...server, ...localRecords.value.filter(r => r.key !== activeKey.value && !records.value.some(s => s.session_id === r.sessionId))]
  })
  const hasMoreRecords = computed(() => records.value.length < recordTotal.value)
  function pointerKey() { return `legalmind_active_session:${auth.user?.id ?? 'current'}` }
  function rememberSession() { try { if (sessionId.value) sessionStorage.setItem(pointerKey(), sessionId.value); else sessionStorage.removeItem(pointerKey()) } catch { /* History remains on the server. */ } }
  function refreshCredentialState() { hasCredential.value = hasChatCredential() }
  function clearError() { errorMessage.value = ''; errorCode.value = ''; errorRequestId.value = undefined; if (!isSending.value) status.value = 'idle' }
  function setError(error: unknown) {
    const normalized = normalizeApiError(error)
    status.value = 'error'; errorMessage.value = normalized.message; errorCode.value = normalized.code; errorRequestId.value = normalized.requestId
    if (normalized.code === 'AUTH_REQUIRED') { const unsentDraft = draft.value; clearConversation(); auth.logout(); draft.value = unsentDraft; hasCredential.value = false; errorMessage.value = '提交咨询需要登录，请先完成登录后再试。'; errorCode.value = 'AUTH_REQUIRED'; status.value = 'error' }
  }
  async function refreshConversations(append = false) {
    if (loadingRecords.value || !hasChatCredential()) return
    const epoch = generation
    loadingRecords.value = true; recordError.value = ''
    try {
      const result = await listConversations(append ? records.value.length : 0)
      if (epoch !== generation) return
      records.value = append ? [...records.value, ...result.items.filter(r => !records.value.some(p => p.session_id === r.session_id))] : result.items
      recordTotal.value = result.total
    } catch (error) { if (epoch === generation) { recordError.value = normalizeApiError(error).message; if (normalizeApiError(error).code === 'AUTH_REQUIRED') setError(error) } }
    finally { if (epoch === generation) loadingRecords.value = false }
  }
  async function initialize() {
    const epoch = generation
    refreshCredentialState()
    if (!hasCredential.value) return
    await refreshConversations()
    if (epoch !== generation) return
    if (messages.value.length || sessionId.value) return
    let previous: string | null = null
    try { previous = sessionStorage.getItem(pointerKey()) } catch { /* Optional pointer. */ }
    if (previous) await switchConversation(previous)
  }
  async function switchConversation(key: string, force = false) {
    if (isBusy.value || (key === activeKey.value && !force)) return
    const local = localRecords.value.find(r => r.key === key)
    const targetSession = records.value.find(r => r.session_id === key)?.session_id ?? local?.sessionId ?? key
    if (local && !local.sessionId) { archiveLocal(); activeKey.value = key; messages.value = [...local.messages]; sessionId.value = null; return }
    const epoch = generation
    loadingHistory.value = true; clearError()
    try {
      const result = await readHistory(targetSession)
      if (epoch !== generation) return
      archiveLocal(); messages.value = result.messages; sessionId.value = targetSession; activeKey.value = targetSession
      historyNotice.value = result.warnings.join(' '); draft.value = ''; lastFailedQuestion.value = ''; uncertain = undefined; rememberSession()
    } catch (error) { if (epoch === generation) setError(error) }
    finally { if (epoch === generation) loadingHistory.value = false }
  }
  function archiveLocal() {
    if (!messages.value.length) return
    const record = { key: activeKey.value, sessionId: sessionId.value, title: messages.value.find(m => m.role === 'user')?.content.slice(0,24) ?? '咨询', messages: [...messages.value], isActive: false }
    localRecords.value = [record, ...localRecords.value.filter(r => r.key !== record.key)]
  }
  function resetActive() { messages.value = []; draft.value = ''; sessionId.value = null; activeKey.value = crypto.randomUUID(); lastFailedQuestion.value = ''; lastAction = undefined; uncertain = undefined; historyNotice.value = ''; clearError(); rememberSession() }
  function startNewConversation() { if (isBusy.value) return; archiveLocal(); resetActive() }
  // Resolve a possibly committed turn before resending; a busy/failed read blocks resubmission.
  async function reconcile(epoch: number): Promise<boolean> {
    if (!uncertain) return false
    const pending = uncertain
    try {
      const result = await readHistory(pending.session)
      if (epoch !== generation) return false
      const tail = result.messages.at(-1)
      const committed = tail?.role === 'assistant' && tail.id !== pending.previousTail && result.messages.at(-2)?.content === pending.question
      if (committed) { messages.value = result.messages; sessionId.value = pending.session; activeKey.value = pending.session; rememberSession(); lastFailedQuestion.value = ''; clearError() }
      uncertain = undefined
      return committed
    } catch (error) {
      if (epoch !== generation) return false
      if (normalizeApiError(error).code === 'RESOURCE_NOT_FOUND') { uncertain = undefined; return false }
      throw error
    }
  }
  async function requestAnswer(question: string, append: boolean, action?: { action: TaskAction; revision: string }): Promise<boolean> {
    if (isBusy.value) return false
    refreshCredentialState(); clearError()
    if (!hasCredential.value) { setError(new ApiRequestError('提交咨询需要登录，请先完成登录后再试。', { code: 'AUTH_REQUIRED' })); return false }
    const epoch = generation
    if (uncertain) {
      const pendingQuestion = uncertain.question
      loadingHistory.value = true
      try {
        const committed = await reconcile(epoch)
        if (epoch !== generation) return false
        if (committed && !append && question === pendingQuestion) return true
      } catch (error) { if (epoch === generation) setError(error); return false }
      finally { if (epoch === generation) loadingHistory.value = false }
    }
    let previousTail: string | undefined
    if (sessionId.value) {
      loadingHistory.value = true
      try { previousTail = (await readHistory(sessionId.value)).messages.at(-1)?.id }
      catch (error) { if (epoch === generation) setError(error); return false }
      finally { if (epoch === generation) loadingHistory.value = false }
      if (epoch !== generation) return false
    }
    messages.value = messages.value.filter(m => m.delivery !== 'interrupted')
    if (append) messages.value.push({ id: crypto.randomUUID(), role: 'user', content: question, isDemo: false })
    messages.value.push({ id: crypto.randomUUID(), role: 'assistant', content: '', isDemo: false, delivery: 'pending' })
    const pendingMessage = messages.value.at(-1)!
    status.value = 'sending'; controller = new AbortController()
    let streamSession: string | undefined
    try {
      const result = await streamChat({ message: question, session_id: sessionId.value, document_type: null, document_params: null,
        ...(action ? { task_action: action.action, task_revision: action.revision } : {}) }, controller.signal, {
        meta(id, intent) { if (epoch !== generation) return; streamSession = id; pendingMessage.intent = intent },
        content(delta) { if (epoch === generation) pendingMessage.content += delta },
      })
      if (epoch !== generation) return false
      sessionId.value = result.session_id; activeKey.value = result.session_id; rememberSession()
      Object.assign(pendingMessage, { content: result.response, intent: result.intent, sources: result.sources, sourceCount: result.sources.length,
        hasDemoSources: result.sources.some(s => s.is_demo), missingFields: result.missing_fields, warnings: result.warnings,
        task: result.task, documentId: result.document_id, delivery: 'completed' })
      status.value = 'idle'; lastFailedQuestion.value = ''; lastAction = undefined; uncertain = undefined
      void refreshConversations(); return true
    } catch (error) {
      if (epoch !== generation) return false
      pendingMessage.delivery = 'interrupted'
      lastFailedQuestion.value = question; lastAction = action
      const knownSession = streamSession ?? sessionId.value
      if (knownSession) uncertain = { session: knownSession, previousTail, question }
      setError(error); return false
    } finally { if (epoch === generation) controller = undefined }
  }
  async function submitQuestion(question = draft.value) {
    const value = question.trim()
    if (!value || isBusy.value) return false
    if (value.length > MAX_CHAT_MESSAGE_LENGTH) { setError(new ApiRequestError('问题不能超过 4000 个字符', { code: 'VALIDATION_ERROR' })); return false }
    if (hasChatCredential()) draft.value = ''
    return requestAnswer(value, true)
  }
  async function retryLastQuestion() { return lastFailedQuestion.value ? requestAnswer(lastFailedQuestion.value, false, lastAction) : false }
  async function submitTaskAction(action: TaskAction, revision: string) {
    const labels = { confirm: '确认生成', accept_changes: '确认修改', reject_changes: '保留原值', cancel: '取消任务', restart: '重新开始' }
    return requestAnswer(labels[action], true, { action, revision })
  }
  function stopGeneration() { controller?.abort() }
  async function restoreCurrentConversation() { if (sessionId.value) await switchConversation(sessionId.value, true); else await refreshConversations() }
  function useSuggestedQuestion(question: string) { if (isBusy.value) return; draft.value = question.slice(0,MAX_CHAT_MESSAGE_LENGTH); clearError() }
  async function deleteConversation(key: string) {
    if (isBusy.value) return false
    const target = conversationRecords.value.find(r => r.key === key)
    if (!target) return false
    const epoch = generation
    deletingConversationKey.value = key
    try {
      if (target.sessionId) await deleteChatSession(target.sessionId)
      if (epoch !== generation) return false
      records.value = records.value.filter(r => r.session_id !== target.sessionId); localRecords.value = localRecords.value.filter(r => r.key !== key)
      if (key === activeKey.value) resetActive()
      void refreshConversations(); return true
    } catch (error) { if (epoch === generation) setError(error); return false }
    finally { if (epoch === generation) deletingConversationKey.value = null }
  }
  function clearConversation() { generation++; controller?.abort(); controller = undefined; records.value = []; localRecords.value = []; recordTotal.value = 0; deletingConversationKey.value = null; loadingHistory.value = false; loadingRecords.value = false; recordError.value = ''; resetActive(); status.value = 'idle' }
  watch(() => auth.accessToken, (next, previous) => { const openingQuestion = !previous && next ? draft.value : ''; clearConversation(); draft.value = openingQuestion; refreshCredentialState() }, { flush: 'sync' })
  return { messages, draft, status, sessionId, conversationRecords, deletingConversationKey, loadingHistory, loadingRecords, historyNotice, recordError, hasMoreRecords,
    errorMessage, errorCode, errorRequestId, lastFailedQuestion, hasCredential, isSending, isBusy, canSend,
    initialize, refreshConversations, refreshCredentialState, submitQuestion, submitTaskAction, retryLastQuestion, stopGeneration, restoreCurrentConversation, useSuggestedQuestion, startNewConversation, switchConversation, deleteConversation, clearConversation }
})
