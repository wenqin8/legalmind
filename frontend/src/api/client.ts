import axios from 'axios'

import type { ApiFailure } from '@/types/api'

const configuredBaseUrl = import.meta.env.VITE_API_BASE_URL?.trim() || '/api/v1'

export const apiClient = axios.create({
  baseURL: configuredBaseUrl.replace(/\/+$/, ''),
  timeout: 10_000,
  headers: {
    Accept: 'application/json',
  },
})

export interface ApiRequestErrorOptions {
  status?: number
  code?: string
  requestId?: string
  details?: unknown
}

export class ApiRequestError extends Error {
  readonly status?: number
  readonly code: string
  readonly requestId?: string
  readonly details?: unknown

  constructor(message: string, options: ApiRequestErrorOptions = {}) {
    super(message)
    this.name = 'ApiRequestError'
    this.status = options.status
    this.code = options.code ?? 'NETWORK_ERROR'
    this.requestId = options.requestId
    this.details = options.details
  }
}

export const ACCESS_TOKEN_STORAGE_KEY = 'legalmind_access_token'

export function readAccessToken(): string | null {
  if (typeof window === 'undefined') return null
  try {
    const token = window.sessionStorage.getItem(ACCESS_TOKEN_STORAGE_KEY)?.trim()
    return token || null
  } catch {
    return null
  }
}

function isApiFailure(value: unknown): value is ApiFailure {
  if (!value || typeof value !== 'object') return false
  const candidate = value as Partial<ApiFailure>
  return candidate.success === false && typeof candidate.error?.message === 'string'
}

export function normalizeApiError(error: unknown): ApiRequestError {
  if (error instanceof ApiRequestError) return error

  if (axios.isAxiosError(error)) {
    const responseBody: unknown = error.response?.data
    const headerRequestId = error.response?.headers?.['x-request-id']
    if (isApiFailure(responseBody)) {
      return new ApiRequestError(responseBody.error.message, {
        status: error.response?.status,
        code: responseBody.error.code,
        requestId:
          responseBody.request_id ||
          (typeof headerRequestId === 'string' ? headerRequestId : undefined),
        details: responseBody.error.details,
      })
    }

    if (error.code === 'ECONNABORTED') {
      return new ApiRequestError('请求超时，请稍后重试', {
        code: 'REQUEST_TIMEOUT',
      })
    }

    return new ApiRequestError(
      error.response ? '请求暂时无法处理，请稍后重试' : '暂时无法连接服务，请稍后重试',
      {
        status: error.response?.status,
        code: error.response ? 'HTTP_ERROR' : 'NETWORK_ERROR',
        requestId: typeof headerRequestId === 'string' ? headerRequestId : undefined,
      },
    )
  }

  return new ApiRequestError('发生未知错误，请稍后重试')
}

const PUBLIC_API_PATHS = new Set(['/health', '/auth/register', '/auth/login'])

apiClient.interceptors.request.use((config) => {
  const token = readAccessToken()
  if (token && !PUBLIC_API_PATHS.has(config.url ?? '')) {
    config.headers.set('Authorization', `Bearer ${token}`)
  } else {
    config.headers.delete('Authorization')
  }
  return config
})

apiClient.interceptors.response.use(
  (response) => response,
  (error: unknown) => Promise.reject(normalizeApiError(error)),
)
