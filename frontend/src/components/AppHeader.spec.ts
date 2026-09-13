import { createPinia } from 'pinia'
import { flushPromises, mount } from '@vue/test-utils'
import { createMemoryHistory, createRouter } from 'vue-router'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const healthApi = vi.hoisted(() => ({
  getHealth: vi.fn(),
}))

vi.mock('@/api/health', () => ({
  getHealth: healthApi.getHealth,
}))

import { ACCESS_TOKEN_STORAGE_KEY } from '@/api/client'
import AppHeader from '@/components/AppHeader.vue'

async function mountHeader() {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/', component: { template: '<div>home</div>' } },
      { path: '/auth', component: { template: '<div>auth</div>' } },
      { path: '/chat', component: { template: '<div>chat</div>' } },
      { path: '/privacy', component: { template: '<div>privacy</div>' } },
      { path: '/about', component: { template: '<div>about</div>' } },
    ],
  })
  await router.push('/')
  await router.isReady()
  const wrapper = mount(AppHeader, {
    global: { plugins: [createPinia(), router] },
  })
  await flushPromises()
  return wrapper
}

describe('AppHeader', () => {
  beforeEach(() => {
    window.sessionStorage.clear()
    healthApi.getHealth.mockReset()
  })

  it('shows a user-facing online state without exposing an API version', async () => {
    healthApi.getHealth.mockResolvedValue({
      success: true,
      data: { status: 'healthy', version: '0.1.0' },
      request_id: '705c6bc8-419f-4c45-bc3a-253263096ea4',
    })

    const wrapper = await mountHeader()

    expect(wrapper.get('[data-testid="backend-status"]').attributes('aria-label')).toBe('服务正常')
    expect(wrapper.text()).toContain('服务正常')
    expect(wrapper.text()).not.toContain('API v0.1.0')
  })

  it('uses a clear unavailable state when the health request fails', async () => {
    healthApi.getHealth.mockRejectedValue(new Error('offline'))

    const wrapper = await mountHeader()

    expect(wrapper.get('[data-testid="backend-status"]').attributes('aria-label')).toBe('服务暂不可用')
    expect(wrapper.text()).not.toContain('仅前端预览')
  })

  it('closes the account menu after choosing a destination', async () => {
    healthApi.getHealth.mockResolvedValue({
      success: true,
      data: { status: 'healthy', version: '0.1.0' },
      request_id: '705c6bc8-419f-4c45-bc3a-253263096ea4',
    })
    window.sessionStorage.setItem(ACCESS_TOKEN_STORAGE_KEY, 'test-token')
    const wrapper = await mountHeader()
    const menu = wrapper.get('details')
    ;(menu.element as HTMLDetailsElement).open = true

    await wrapper.get('a[href="/privacy"]').trigger('click')

    expect((menu.element as HTMLDetailsElement).open).toBe(false)
  })
})
