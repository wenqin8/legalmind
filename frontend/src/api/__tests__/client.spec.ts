import type { InternalAxiosRequestConfig } from 'axios'
import { beforeEach, describe, expect, it } from 'vitest'

import {
  ACCESS_TOKEN_STORAGE_KEY,
  ApiRequestError,
  apiClient,
  normalizeApiError,
} from '@/api/client'

describe('apiClient', () => {
  beforeEach(() => {
    window.sessionStorage.clear()
  })

  it('uses the frozen API v1 base path', () => {
    expect(apiClient.defaults.baseURL).toBe('/api/v1')
  })

  it('removes stale authorization from public endpoints and keeps it for protected ones', async () => {
    window.sessionStorage.setItem(ACCESS_TOKEN_STORAGE_KEY, 'test-token')
    const observed: Array<string | null | undefined> = []
    const adapter = async (config: InternalAxiosRequestConfig) => {
      observed.push(config.headers.get('Authorization') as string | null | undefined)
      return { data: {}, status: 200, statusText: 'OK', headers: {}, config }
    }

    await apiClient.get('/health', { adapter })
    await apiClient.get('/auth/me', { adapter })

    expect(observed).toEqual([undefined, 'Bearer test-token'])
  })
})

describe('normalizeApiError', () => {
  it('keeps the stable backend code and body request id', () => {
    const normalized = normalizeApiError({
      isAxiosError: true,
      response: {
        status: 422,
        headers: { 'x-request-id': 'header-request-id' },
        data: {
          success: false,
          error: {
            code: 'VALIDATION_ERROR',
            message: '请求参数不正确',
            details: { fields: [] },
          },
          request_id: 'body-request-id',
        },
      },
    })

    expect(normalized).toBeInstanceOf(ApiRequestError)
    expect(normalized.status).toBe(422)
    expect(normalized.code).toBe('VALIDATION_ERROR')
    expect(normalized.requestId).toBe('body-request-id')
    expect(normalized.message).toBe('请求参数不正确')
  })

  it('uses a safe message when the backend is unavailable', () => {
    const normalized = normalizeApiError({
      isAxiosError: true,
      message: 'connect ECONNREFUSED with internal details',
    })

    expect(normalized.code).toBe('NETWORK_ERROR')
    expect(normalized.message).toBe('无法连接后端服务')
    expect(normalized.message).not.toContain('ECONNREFUSED')
  })

  it('normalizes a model request timeout without changing the global timeout', () => {
    const normalized = normalizeApiError({
      isAxiosError: true,
      code: 'ECONNABORTED',
    })

    expect(normalized.code).toBe('REQUEST_TIMEOUT')
    expect(normalized.message).toBe('请求超时，请稍后重试')
    expect(apiClient.defaults.timeout).toBe(10_000)
  })
})
