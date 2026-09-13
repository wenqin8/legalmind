import { createPinia } from 'pinia'
import { mount } from '@vue/test-utils'
import { createMemoryHistory, createRouter } from 'vue-router'
import { beforeEach, describe, expect, it } from 'vitest'

import AuthView from '@/views/AuthView.vue'

describe('AuthView', () => {
  beforeEach(() => {
    window.sessionStorage.clear()
  })

  it('prioritizes the form on mobile and shows the full notice only for registration', async () => {
    const router = createRouter({
      history: createMemoryHistory(),
      routes: [
        { path: '/auth', component: AuthView },
        { path: '/chat', component: { template: '<div>chat</div>' } },
        { path: '/guide', component: { template: '<div>guide</div>' } },
        { path: '/privacy', component: { template: '<div>privacy</div>' } },
      ],
    })
    await router.push('/auth')
    await router.isReady()
    const wrapper = mount(AuthView, {
      global: { plugins: [createPinia(), router] },
    })

    expect(wrapper.get('[data-testid="auth-form-panel"]').classes()).toContain('order-1')
    expect(wrapper.get('[data-testid="auth-brand-panel"]').classes()).toContain('order-2')
    expect(wrapper.get('#login').attributes('autocomplete')).toBe('username')
    expect(wrapper.get('#login').attributes('autofocus')).toBeUndefined()
    expect(wrapper.get('#password').attributes('maxlength')).toBe('128')
    expect(wrapper.text()).toContain('继续即表示你已阅读')
    expect(wrapper.text()).not.toContain('不构成法律意见、律师服务或任何结果保证')
    expect(wrapper.text()).not.toContain('课程演示')

    await wrapper.get('button[aria-pressed="false"]').trigger('click')

    expect(wrapper.get('#username').attributes('minlength')).toBe('3')
    expect(wrapper.get('#username').attributes('maxlength')).toBe('50')
    expect(wrapper.get('#email').attributes('maxlength')).toBe('254')
    expect(wrapper.get('#password').attributes('autocomplete')).toBe('new-password')
    expect(wrapper.text()).toContain('注册成功后将自动进入咨询空间')
    expect(wrapper.text()).toContain('不构成法律意见、律师服务或任何结果保证')
  })
})
