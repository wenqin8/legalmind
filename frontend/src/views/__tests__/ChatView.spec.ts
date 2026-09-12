import { createPinia, setActivePinia } from 'pinia'
import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const chatApi = vi.hoisted(() => ({
  hasCredential: vi.fn(),
  send: vi.fn(),
}))

vi.mock('@/api/chat', () => ({
  hasChatCredential: chatApi.hasCredential,
  sendChatMessage: chatApi.send,
}))

import { useChatStore } from '@/stores/chat'
import ChatView from '@/views/ChatView.vue'

function successfulResponse() {
  return {
    success: true as const,
    data: {
      response: '请先保存劳动合同、工资记录和催告沟通记录。',
      intent: 'qa',
      sources: [],
      session_id: '97c94b7f-2451-470e-a3e5-a278a9d04929',
      missing_fields: [],
      warnings: ['AI 内容仅供参考，不构成法律意见；重要事项请咨询执业律师并核对原始依据。'],
    },
    request_id: 'c4f8e06b-686b-440e-8635-f8656f395d42',
  }
}

describe('ChatView', () => {
  beforeEach(() => {
    window.sessionStorage.clear()
    setActivePinia(createPinia())
    chatApi.hasCredential.mockReset()
    chatApi.send.mockReset()
    chatApi.hasCredential.mockReturnValue(true)
    chatApi.send.mockResolvedValue(successfulResponse())
  })

  it('submits a real API question and renders only returned answer metadata', async () => {
    const wrapper = mount(ChatView)
    const textarea = wrapper.get('textarea')

    await textarea.setValue('公司拖欠工资，我应该准备什么材料？')
    await wrapper.get('form').trigger('submit')
    await flushPromises()

    expect(chatApi.send).toHaveBeenCalledWith('公司拖欠工资，我应该准备什么材料？', null)
    expect(useChatStore().messages).toHaveLength(2)
    expect(useChatStore().sessionId).toBe('97c94b7f-2451-470e-a3e5-a278a9d04929')
    expect(wrapper.text()).toContain('请先保存劳动合同、工资记录和催告沟通记录。')
    expect(wrapper.text()).toContain('AI 回答')
    expect(wrapper.text()).toContain('本次回答未附带可核验来源')
    expect(wrapper.text()).not.toContain('演示回复')
  })

  it('does not send a question without an authenticated session', async () => {
    chatApi.hasCredential.mockReturnValue(false)
    const wrapper = mount(ChatView)

    await wrapper.get('textarea').setValue('公司拖欠工资怎么办？')
    await wrapper.get('form').trigger('submit')
    await flushPromises()

    expect(chatApi.send).not.toHaveBeenCalled()
    expect(useChatStore().messages).toHaveLength(0)
    expect(useChatStore().draft).toBe('公司拖欠工资怎么办？')
    expect(wrapper.get('[data-testid="chat-error"]').text()).toContain('需要登录')
  })

  it('always displays the compact legal disclaimer and strict input limit', () => {
    const wrapper = mount(ChatView)

    expect(wrapper.get('textarea').attributes('maxlength')).toBe('4000')
    expect(wrapper.text()).toContain(
      'AI 内容仅供参考，不构成法律意见；重要事项请咨询执业律师并核对原始依据。',
    )
  })

  it('rejects questions beyond the API contract limit outside the DOM', async () => {
    mount(ChatView)

    await expect(useChatStore().submitQuestion('问'.repeat(4001))).resolves.toBe(false)
    expect(useChatStore().messages).toHaveLength(0)
    expect(chatApi.send).not.toHaveBeenCalled()
    expect(useChatStore().errorCode).toBe('VALIDATION_ERROR')
  })
})
