import { createPinia } from 'pinia'
import { flushPromises, mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'

import { ACCESS_TOKEN_STORAGE_KEY } from '@/api/client'
import router from '@/router'
import { useChatStore } from '@/stores/chat'
import HomeView from '@/views/HomeView.vue'

async function mountHome() {
  const pinia = createPinia()
  window.sessionStorage.clear()
  await router.push('/')
  await router.isReady()

  const wrapper = mount(HomeView, {
    global: { plugins: [pinia, router] },
  })
  return { wrapper, router, chatStore: useChatStore(pinia) }
}

describe('HomeView', () => {
  it('acts as a concise application entry without project or unsupported-source copy', async () => {
    const { wrapper } = await mountHome()

    for (const domain of ['婚姻家庭', '劳动争议', '交通事故', '合同纠纷']) {
      expect(wrapper.text()).toContain(domain)
    }
    for (const entry of ['法律咨询', '案例检索', '文书生成']) {
      expect(wrapper.text()).toContain(entry)
    }
    expect(wrapper.text()).toContain('中国大陆法律信息助手')
    expect(wrapper.text()).not.toContain('课程演示')
    expect(wrapper.text()).not.toContain('答案保留来源线索')
    expect(wrapper.text()).not.toContain('不构成法律意见')
  })

  it('carries the opening question into the protected consultation flow', async () => {
    const { wrapper, router, chatStore } = await mountHome()
    const question = '公司拖欠两个月工资，我应该先准备哪些材料？'

    await wrapper.get('#home-question').setValue(question)
    await wrapper.get('form').trigger('submit')
    await flushPromises()

    expect(chatStore.draft).toBe(question)
    expect(router.currentRoute.value.name).toBe('auth')
    expect(router.currentRoute.value.query.redirect).toBe('/chat')

    window.sessionStorage.setItem(ACCESS_TOKEN_STORAGE_KEY, 'test-token')
    await router.push('/chat')
    expect(router.currentRoute.value.name).toBe('chat')
    expect(chatStore.draft).toBe(question)
  })
})
