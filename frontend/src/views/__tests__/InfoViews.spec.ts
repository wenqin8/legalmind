import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'

import AboutView from '@/views/AboutView.vue'
import GuideView from '@/views/GuideView.vue'
import PrivacyView from '@/views/PrivacyView.vue'

const mountInfoView = (component: typeof GuideView) =>
  mount(component, {
    global: { stubs: { RouterLink: true } },
  })

describe('public information views', () => {
  it('explains how to use the assistant without claiming source retrieval is available', () => {
    const wrapper = mountInfoView(GuideView)

    expect(wrapper.get('h1').text()).toBe('从事实开始，得到更清晰的下一步')
    expect(wrapper.text()).toContain('当前版本尚未接入法规与案例来源检索')
  })

  it('explains browser, database, and AI-service data handling', () => {
    const wrapper = mountInfoView(PrivacyView)

    expect(wrapper.get('h1').text()).toBe('了解信息如何流转')
    expect(wrapper.text()).toContain('sessionStorage')
    expect(wrapper.text()).toContain('问题会发送到哪里')
  })

  it('keeps project context and supported domains on the about page', () => {
    const wrapper = mountInfoView(AboutView)

    expect(wrapper.get('h1').text()).toBe('让法律问题先变得清晰')
    expect(wrapper.text()).toContain('课程项目')
    for (const domain of ['婚姻家庭', '劳动争议', '交通事故', '合同纠纷']) {
      expect(wrapper.text()).toContain(domain)
    }
  })
})
