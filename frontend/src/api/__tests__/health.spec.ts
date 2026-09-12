import { afterEach, describe, expect, it, vi } from 'vitest'

import { apiClient } from '@/api/client'
import { getHealth } from '@/api/health'

describe('getHealth', () => {
  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('requests the health endpoint and accepts the canonical response', async () => {
    const get = vi.spyOn(apiClient, 'get').mockResolvedValue({
      data: {
        success: true,
        data: { status: 'healthy', version: '0.1.0' },
        request_id: '705c6bc8-419f-4c45-bc3a-253263096ea4',
      },
    })

    await expect(getHealth()).resolves.toMatchObject({
      success: true,
      data: { status: 'healthy', version: '0.1.0' },
    })
    expect(get).toHaveBeenCalledOnce()
    expect(get).toHaveBeenCalledWith('/health')
  })

  it('rejects a malformed successful response', async () => {
    vi.spyOn(apiClient, 'get').mockResolvedValue({
      data: {
        success: true,
        data: { status: 'healthy' },
        request_id: '705c6bc8-419f-4c45-bc3a-253263096ea4',
      },
    })

    await expect(getHealth()).rejects.toMatchObject({
      code: 'INVALID_RESPONSE',
      message: '后端健康响应格式不正确',
    })
  })
})
