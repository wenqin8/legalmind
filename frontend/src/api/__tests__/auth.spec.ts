import { beforeEach, describe, expect, it, vi } from 'vitest'

import { loginAccount } from '@/api/auth'
import { apiClient } from '@/api/client'

describe('loginAccount', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  it('accepts a complete login envelope and uses the public contract endpoint', async () => {
    const envelope = {
      success: true as const,
      data: {
        access_token: 'test-jwt',
        token_type: 'bearer' as const,
        expires_in: 3600,
        user: {
          id: 'user-id',
          username: 'demo_user',
          email: 'demo@example.com',
        },
      },
      request_id: 'request-id',
    }
    const post = vi.spyOn(apiClient, 'post').mockResolvedValue({ data: envelope })

    await expect(
      loginAccount({ login: 'demo_user', password: 'safe-password' }),
    ).resolves.toEqual(envelope)
    expect(post).toHaveBeenCalledWith('/auth/login', {
      login: 'demo_user',
      password: 'safe-password',
    })
  })

  it('rejects a 200 response without a usable bearer token', async () => {
    vi.spyOn(apiClient, 'post').mockResolvedValue({
      data: {
        success: true,
        data: {
          access_token: '',
          token_type: 'bearer',
          expires_in: 3600,
          user: {
            id: 'user-id',
            username: 'demo_user',
            email: 'demo@example.com',
          },
        },
        request_id: 'request-id',
      },
    })

    await expect(
      loginAccount({ login: 'demo_user', password: 'safe-password' }),
    ).rejects.toMatchObject({ code: 'INVALID_RESPONSE' })
  })
})
