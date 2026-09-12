import { beforeEach, describe, expect, it } from 'vitest'

import { ACCESS_TOKEN_STORAGE_KEY } from '@/api/client'
import router from '@/router'

describe('router', () => {
  beforeEach(async () => {
    window.sessionStorage.clear()
    await router.push('/')
  })

  it('resolves the public pages and a deliberate not-found page', () => {
    expect(router.resolve('/').name).toBe('home')
    expect(router.resolve('/auth').name).toBe('auth')
    expect(router.resolve('/chat').name).toBe('chat')
    expect(router.resolve('/missing-page').name).toBe('not-found')
  })

  it('redirects guests to auth and permits a session token', async () => {
    await router.push('/chat')
    expect(router.currentRoute.value.name).toBe('auth')
    expect(router.currentRoute.value.query.redirect).toBe('/chat')

    window.sessionStorage.setItem(ACCESS_TOKEN_STORAGE_KEY, 'test-token')
    await router.push('/chat')
    expect(router.currentRoute.value.name).toBe('chat')
  })
})
