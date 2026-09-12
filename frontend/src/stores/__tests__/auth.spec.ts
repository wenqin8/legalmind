import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { ACCESS_TOKEN_STORAGE_KEY, ApiRequestError } from '@/api/client'

const authApi = vi.hoisted(() => ({
  getCurrentUser: vi.fn(),
  loginAccount: vi.fn(),
  registerAccount: vi.fn(),
}))

vi.mock('@/api/auth', () => authApi)

import { useAuthStore } from '@/stores/auth'

const user = {
  id: 'bbdf6db3-ff17-4b8a-afc8-ccbad7b9ad2e',
  username: 'demo_user',
  email: 'demo@example.com',
}

function loginResponse() {
  return {
    success: true as const,
    data: {
      access_token: 'test-jwt',
      token_type: 'bearer' as const,
      expires_in: 3600,
      user,
    },
    request_id: 'request-id',
  }
}

describe('auth store', () => {
  beforeEach(() => {
    window.sessionStorage.clear()
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('persists only the JWT and public user profile after login', async () => {
    authApi.loginAccount.mockResolvedValue(loginResponse())
    const store = useAuthStore()

    await expect(store.login({ login: 'demo_user', password: 'safe-password' })).resolves.toBe(true)

    expect(window.sessionStorage.getItem(ACCESS_TOKEN_STORAGE_KEY)).toBe('test-jwt')
    expect(window.sessionStorage.getItem('legalmind_auth_user')).toContain('demo_user')
    expect(JSON.stringify(window.sessionStorage)).not.toContain('safe-password')
    expect(store.user).toEqual(user)
  })

  it('registers and then logs in without persisting the password', async () => {
    authApi.registerAccount.mockResolvedValue({
      success: true,
      data: user,
      request_id: 'register-request-id',
    })
    authApi.loginAccount.mockResolvedValue(loginResponse())
    const store = useAuthStore()

    const payload = {
      username: 'demo_user',
      email: 'demo@example.com',
      password: 'safe-password',
    }
    await expect(store.registerAndLogin(payload)).resolves.toBe(true)

    expect(authApi.registerAccount).toHaveBeenCalledWith(payload)
    expect(authApi.loginAccount).toHaveBeenCalledWith({
      login: 'demo_user',
      password: 'safe-password',
    })
    expect(JSON.stringify(window.sessionStorage)).not.toContain('safe-password')
  })

  it('keeps a safe backend error and no partial session on failed login', async () => {
    authApi.loginAccount.mockRejectedValue(
      new ApiRequestError('用户名或密码不正确', {
        status: 401,
        code: 'INVALID_CREDENTIALS',
        requestId: 'failed-request-id',
      }),
    )
    const store = useAuthStore()

    await expect(store.login({ login: 'demo_user', password: 'wrong-password' })).resolves.toBe(false)

    expect(store.errorCode).toBe('INVALID_CREDENTIALS')
    expect(store.errorMessage).toBe('用户名或密码不正确')
    expect(store.errorRequestId).toBe('failed-request-id')
    expect(window.sessionStorage.getItem(ACCESS_TOKEN_STORAGE_KEY)).toBeNull()
  })

  it('removes the local session on logout', async () => {
    authApi.loginAccount.mockResolvedValue(loginResponse())
    const store = useAuthStore()
    await store.login({ login: 'demo_user', password: 'safe-password' })

    store.logout()

    expect(store.isAuthenticated).toBe(false)
    expect(store.user).toBeNull()
    expect(window.sessionStorage.length).toBe(0)
  })

  it('validates a cached token with auth/me before restoring the session', async () => {
    window.sessionStorage.setItem(ACCESS_TOKEN_STORAGE_KEY, 'cached-token')
    window.sessionStorage.setItem(
      'legalmind_auth_user',
      JSON.stringify({ ...user, username: 'stale-name' }),
    )
    authApi.getCurrentUser.mockResolvedValue({
      success: true,
      data: user,
      request_id: 'me-request-id',
    })
    const store = useAuthStore()

    await expect(store.restoreSession()).resolves.toBe(true)

    expect(authApi.getCurrentUser).toHaveBeenCalledOnce()
    expect(store.user?.username).toBe('demo_user')
    expect(store.hasRestored).toBe(true)
  })

  it('clears a cached session when auth/me cannot validate it', async () => {
    window.sessionStorage.setItem(ACCESS_TOKEN_STORAGE_KEY, 'expired-token')
    window.sessionStorage.setItem('legalmind_auth_user', JSON.stringify(user))
    authApi.getCurrentUser.mockRejectedValue(
      new ApiRequestError('登录状态已过期', { status: 401, code: 'AUTH_REQUIRED' }),
    )
    const store = useAuthStore()

    await expect(store.restoreSession()).resolves.toBe(false)

    expect(store.isAuthenticated).toBe(false)
    expect(store.user).toBeNull()
    expect(window.sessionStorage.getItem(ACCESS_TOKEN_STORAGE_KEY)).toBeNull()
  })
})
