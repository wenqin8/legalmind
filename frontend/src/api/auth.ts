import { ApiRequestError, apiClient } from '@/api/client'
import type { ApiSuccess } from '@/types/api'
import type { AuthUser, LoginData, LoginRequest, RegisterRequest } from '@/types/auth'

function isNonEmptyString(value: unknown): value is string {
  return typeof value === 'string' && value.trim().length > 0
}

function isAuthUser(value: unknown): value is AuthUser {
  if (!value || typeof value !== 'object') return false
  const candidate = value as Partial<AuthUser>
  return (
    isNonEmptyString(candidate.id) &&
    isNonEmptyString(candidate.username) &&
    isNonEmptyString(candidate.email) &&
    (candidate.created_at === undefined || typeof candidate.created_at === 'string')
  )
}

function invalidAuthResponse(): ApiRequestError {
  return new ApiRequestError('服务响应异常，请稍后重试', { code: 'INVALID_RESPONSE' })
}

function parseUserEnvelope(value: unknown): ApiSuccess<AuthUser> {
  if (!value || typeof value !== 'object') throw invalidAuthResponse()
  const candidate = value as Partial<ApiSuccess<AuthUser>>
  if (
    candidate.success !== true ||
    !isNonEmptyString(candidate.request_id) ||
    !isAuthUser(candidate.data)
  ) {
    throw invalidAuthResponse()
  }
  return candidate as ApiSuccess<AuthUser>
}

function parseLoginEnvelope(value: unknown): ApiSuccess<LoginData> {
  if (!value || typeof value !== 'object') throw invalidAuthResponse()
  const candidate = value as Partial<ApiSuccess<LoginData>>
  const data = candidate.data as Partial<LoginData> | undefined
  if (
    candidate.success !== true ||
    !isNonEmptyString(candidate.request_id) ||
    !data ||
    !isNonEmptyString(data.access_token) ||
    data.token_type !== 'bearer' ||
    typeof data.expires_in !== 'number' ||
    !Number.isFinite(data.expires_in) ||
    !Number.isInteger(data.expires_in) ||
    data.expires_in <= 0 ||
    !isAuthUser(data.user)
  ) {
    throw invalidAuthResponse()
  }
  return candidate as ApiSuccess<LoginData>
}

export async function registerAccount(payload: RegisterRequest): Promise<ApiSuccess<AuthUser>> {
  const response = await apiClient.post<unknown>('/auth/register', payload)
  return parseUserEnvelope(response.data)
}

export async function loginAccount(payload: LoginRequest): Promise<ApiSuccess<LoginData>> {
  const response = await apiClient.post<unknown>('/auth/login', payload)
  return parseLoginEnvelope(response.data)
}

export async function getCurrentUser(): Promise<ApiSuccess<AuthUser>> {
  const response = await apiClient.get<unknown>('/auth/me')
  return parseUserEnvelope(response.data)
}
