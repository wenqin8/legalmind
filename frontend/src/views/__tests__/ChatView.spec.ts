import { createPinia, setActivePinia } from 'pinia'
import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const chatApi = vi.hoisted(() => ({
  hasCredential: vi.fn(),
  send: vi.fn(),
  deleteSession: vi.fn(),
}))

vi.mock('@/api/chat', async (importOriginal) => ({
  ...await importOriginal<typeof import('@/api/chat')>(),
  hasChatCredential: chatApi.hasCredential,
  sendChatMessage: chatApi.send,
  deleteChatSession: chatApi.deleteSession,
}))

vi.mock('@/api/chat-stream', () => ({
  streamChat: async (payload: any, _signal: AbortSignal, handlers: any) => {
    const action = payload.task_action ? { action: payload.task_action, revision: payload.task_revision } : undefined
    const result = action ? await chatApi.send(payload.message, payload.session_id, action) : await chatApi.send(payload.message, payload.session_id)
    handlers.meta(result.data.session_id, result.data.intent)
    handlers.content(result.data.response)
    return result.data
  },
}))
vi.mock('@/api/chat-session', () => ({
  listConversations: async () => ({ items: [], total: 0 }),
  readHistory: async () => ({ messages: [
    { id: 'user-history', role: 'user', content: '公司拖欠工资，我应该准备什么材料？', isDemo: false },
    { id: 'assistant-history', role: 'assistant', content: '请先保存劳动合同、工资记录和催告沟通记录。', isDemo: false },
  ], warnings: [], history_expired: false }),
}))

import { useChatStore } from '@/stores/chat'
import ChatView from '@/views/ChatView.vue'

const compactDisclaimer =
  'AI 生成内容仅供参考，不构成法律意见。重要事项请核对原始依据或咨询专业人士。'

function successfulResponse() {
  return {
    success: true as const,
    data: {
      response: '请先保存劳动合同、工资记录和催告沟通记录。',
      intent: 'qa',
      sources: [],
      session_id: '97c94b7f-2451-470e-a3e5-a278a9d04929',
      missing_fields: [],
      warnings: [
        compactDisclaimer,
        '没有可确认相关的资料，当前回答不提供具体法律结论。',
      ],
    },
    request_id: 'c4f8e06b-686b-440e-8635-f8656f395d42',
  }
}

function mountChat() {
  return mount(ChatView, {
    global: {
      stubs: { RouterLink: true },
    },
  })
}

describe('ChatView', () => {
  beforeEach(() => {
    window.sessionStorage.clear()
    setActivePinia(createPinia())
    chatApi.hasCredential.mockReset()
    chatApi.send.mockReset()
    chatApi.deleteSession.mockReset()
    chatApi.hasCredential.mockReturnValue(true)
    chatApi.send.mockResolvedValue(successfulResponse())
    chatApi.deleteSession.mockResolvedValue({
      success: true,
      data: { deleted_session_id: '97c94b7f-2451-470e-a3e5-a278a9d04929' },
      request_id: 'delete-request-id',
    })
  })

  it('offers confirmation only for the latest reviewed task and displays official source provenance', async () => {
    const id = '97c94b7f-2451-470e-a3e5-a278a9d04929'
    const task = { task_id: id, revision: id, kind: 'document' as const, phase: 'review' as const, fields: {}, conflicts: {}, missing_fields: [], questions: [], document_id: null }
    const store = useChatStore()
    store.sessionId = id
    store.messages.push({ id: 'review', role: 'assistant', content: '请核对摘要', isDemo: false, task, sources: [{ source_type: 'legal_provision', source_id: id, citation_id: 'S1', title: '官方法律', reference_number: '第一条', publisher: '官方', date: '2020-01-01', sample_date: null, source_url: 'https://www.court.gov.cn/example', source_kind: 'official', is_demo: false, is_synthetic: false, version: '核验版本', effective_from: '2021-01-01', verified_at: '2026-09-18', status_as_of: '2026-03-12', original_text: '逐字保留的官方原文', applicability: 'event_candidate' }] })
    const wrapper = mountChat()
    expect(wrapper.text()).toContain('逐字保留的官方原文')
    expect(wrapper.text()).toContain('本次未实时联网核验')
    expect(wrapper.get('a[href="https://www.court.gov.cn/example"]').attributes('rel')).toBe('noopener noreferrer')
    const button = wrapper.findAll('button').find(b => b.text() === '确认摘要并生成草稿')!
    await button.trigger('click')
    await flushPromises()
    expect(chatApi.send).toHaveBeenCalledWith('确认生成', id, { action: 'confirm', revision: id })
    expect(wrapper.text()).not.toContain('确认摘要并生成草稿')
  })

  it('submits a real API question and presents user-facing answer metadata', async () => {
    const wrapper = mountChat()
    const textarea = wrapper.get('textarea')

    await textarea.setValue('公司拖欠工资，我应该准备什么材料？')
    await wrapper.get('form').trigger('submit')
    await flushPromises()

    expect(chatApi.send).toHaveBeenCalledWith('公司拖欠工资，我应该准备什么材料？', null)
    expect(useChatStore().messages).toHaveLength(2)
    expect(useChatStore().sessionId).toBe('97c94b7f-2451-470e-a3e5-a278a9d04929')
    expect(wrapper.text()).toContain('请先保存劳动合同、工资记录和催告沟通记录。')
    expect(wrapper.text()).toContain('AI 回答')
    expect(wrapper.text()).toContain('法律问答')
    expect(wrapper.text()).toContain('依据与提示')
    expect(wrapper.get('section[aria-label="依据与提示"]').text()).toContain(compactDisclaimer)
    expect(wrapper.text()).toContain('暂未附可核验的参考依据')
    expect(wrapper.text()).toContain('不提供具体法律结论')
    expect(wrapper.text()).not.toContain('当前版本尚未接入')
    expect(wrapper.text()).not.toContain('演示回复')
    expect(wrapper.text()).not.toMatch(/\bqa\b/)
  })

  it('does not send a question without an authenticated session', async () => {
    chatApi.hasCredential.mockReturnValue(false)
    const wrapper = mountChat()

    await wrapper.get('textarea').setValue('公司拖欠工资怎么办？')
    await wrapper.get('form').trigger('submit')
    await flushPromises()

    expect(chatApi.send).not.toHaveBeenCalled()
    expect(useChatStore().messages).toHaveLength(0)
    expect(useChatStore().draft).toBe('公司拖欠工资怎么办？')
    expect(wrapper.get('[data-testid="chat-error"]').text()).toContain('需要登录')
  })

  it('shows four legal-domain entries, a new consultation action, and one composer notice', () => {
    const wrapper = mountChat()

    for (const domain of ['婚姻家庭', '劳动争议', '交通事故', '合同纠纷']) {
      expect(wrapper.text()).toContain(domain)
    }
    expect(wrapper.text()).toContain('新建咨询')
    expect(wrapper.get('textarea').attributes('maxlength')).toBe('4000')
    expect(wrapper.text()).toContain(compactDisclaimer)
    expect(wrapper.findAll('[role="note"]')).toHaveLength(1)
  })

  it('fills the draft and closes the mobile domain menu after selection', async () => {
    const wrapper = mountChat()
    const menu = wrapper.get('details')
    ;(menu.element as HTMLDetailsElement).open = true

    await menu.findAll('button')[1]!.trigger('click')

    expect(useChatStore().draft).toBe('我想咨询劳动争议问题，事情经过是：')
    expect((menu.element as HTMLDetailsElement).open).toBe(false)
  })

  it('archives the current consultation when starting a new one and can restore it', async () => {
    const wrapper = mountChat()
    await wrapper.get('textarea').setValue('公司拖欠工资，我应该准备什么材料？')
    await wrapper.get('form').trigger('submit')
    await flushPromises()

    const store = useChatStore()
    expect(store.messages).toHaveLength(2)

    await wrapper.get('aside button').trigger('click')

    expect(store.messages).toHaveLength(0)
    expect(store.conversationRecords).toHaveLength(1)
    expect(wrapper.get('[data-testid="conversation-history"]').text()).toContain('公司拖欠工资')

    await wrapper.get('[data-testid="conversation-history"] button').trigger('click')

    expect(store.messages).toHaveLength(2)
    expect(wrapper.text()).toContain('请先保存劳动合同、工资记录和催告沟通记录。')

    store.startNewConversation()
    expect(store.conversationRecords).toHaveLength(1)
    store.clearConversation()
    expect(store.conversationRecords).toHaveLength(0)
  })

  it('confirms and deletes an archived consultation from the server and local history', async () => {
    const confirm = vi.spyOn(window, 'confirm').mockReturnValue(true)
    const wrapper = mountChat()
    await wrapper.get('textarea').setValue('公司拖欠工资，我应该准备什么材料？')
    await wrapper.get('form').trigger('submit')
    await flushPromises()

    const store = useChatStore()
    store.startNewConversation()
    await wrapper.vm.$nextTick()
    const deleteButton = wrapper.findAll('button[aria-label^="删除咨询"]')[0]
    expect(deleteButton).toBeDefined()
    await deleteButton!.trigger('click')
    await flushPromises()

    expect(confirm).toHaveBeenCalledWith(expect.stringContaining('删除后无法恢复'))
    expect(chatApi.deleteSession).toHaveBeenCalledWith(
      '97c94b7f-2451-470e-a3e5-a278a9d04929',
    )
    expect(store.conversationRecords).toHaveLength(0)
    expect(wrapper.find('[data-testid="conversation-history"]').exists()).toBe(false)
  })

  it('rejects questions beyond the API contract limit outside the DOM', async () => {
    mountChat()

    await expect(useChatStore().submitQuestion('问'.repeat(4001))).resolves.toBe(false)
    expect(useChatStore().messages).toHaveLength(0)
    expect(chatApi.send).not.toHaveBeenCalled()
    expect(useChatStore().errorCode).toBe('VALIDATION_ERROR')
  })
})
