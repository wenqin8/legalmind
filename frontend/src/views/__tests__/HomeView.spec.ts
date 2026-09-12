import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'

import HomeView from '@/views/HomeView.vue'

describe('HomeView', () => {
  it('shows the scoped domains and full legal disclaimer', () => {
    const wrapper = mount(HomeView, {
      global: {
        stubs: {
          RouterLink: true,
        },
      },
    })

    for (const domain of ['婚姻家庭', '劳动争议', '交通事故', '合同纠纷']) {
      expect(wrapper.text()).toContain(domain)
    }
    expect(wrapper.text()).toContain('仅用于课程演示和一般法律信息参考')
    expect(wrapper.text()).toContain('不构成法律意见、律师服务或任何结果保证')
    expect(wrapper.text()).not.toContain('专业法律建议')
  })
})
