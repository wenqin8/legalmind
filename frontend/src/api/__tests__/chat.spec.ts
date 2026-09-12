import { beforeEach, describe, expect, it, vi } from 'vitest'

import { CHAT_REQUEST_TIMEOUT_MS, sendChatMessage } from '@/api/chat'
import { ACCESS_TOKEN_STORAGE_KEY, apiClient } from '@/api/client'

describe('sendChatMessage', () => {
  beforeEach(() => {
    window.sessionStorage.clear()
    vi.restoreAllMocks()
  })

  it('uses the frozen contract payload and a request-specific model timeout', async () => {
    window.sessionStorage.setItem(ACCESS_TOKEN_STORAGE_KEY, 'test-token')
    const envelope = {
      success: true as const,
      data: {
        response: '回答',
        intent: 'qa',
        sources: [],
        session_id: '97c94b7f-2451-470e-a3e5-a278a9d04929',
        missing_fields: [],
        warnings: [],
      },
      request_id: 'request-id',
    }
    const post = vi.spyOn(apiClient, 'post').mockResolvedValue({ data: envelope })

    await expect(sendChatMessage('问题', null)).resolves.toEqual(envelope)
    expect(post).toHaveBeenCalledWith(
      '/chat/send',
      {
        message: '问题',
        session_id: null,
        document_type: null,
        document_params: null,
      },
      { timeout: 72_000 },
    )
    expect(CHAT_REQUEST_TIMEOUT_MS).toBe(72_000)
    expect(apiClient.defaults.timeout).toBe(10_000)
  })

  it('rejects locally instead of making an anonymous business request', async () => {
    const post = vi.spyOn(apiClient, 'post')

    await expect(sendChatMessage('问题', null)).rejects.toMatchObject({
      code: 'AUTH_REQUIRED',
      status: 401,
    })
    expect(post).not.toHaveBeenCalled()
  })

  it('rejects a malformed successful response at runtime', async () => {
    window.sessionStorage.setItem(ACCESS_TOKEN_STORAGE_KEY, 'test-token')
    vi.spyOn(apiClient, 'post').mockResolvedValue({
      data: {
        success: true,
        data: {
          response: '',
          intent: 'qa',
          sources: [],
          session_id: 'session-id',
          missing_fields: [],
          warnings: [],
        },
        request_id: 'request-id',
      },
    })

    await expect(sendChatMessage('问题', null)).rejects.toMatchObject({
      code: 'INVALID_RESPONSE',
    })
  })
})
