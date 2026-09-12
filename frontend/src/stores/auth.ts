import { computed, ref } from 'vue'
import { defineStore } from 'pinia'

import { getCurrentUser, loginAccount, registerAccount } from '@/api/auth'
import {
  ACCESS_TOKEN_STORAGE_KEY,
  ApiRequestError,
  normalizeApiError,
  readAccessToken,
} from '@/api/client'
import type { AuthUser, LoginRequest, RegisterRequest } from '@/types/auth'

const USER_STORAGE_KEY = 'legalmind_auth_user'

function readStoredUser(): AuthUser | null {
  if (typeof window === 'undefined') return null
  try {
    const serialized = window.sessionStorage.getItem(USER_STORAGE_KEY)
    if (!serialized) return null
    const candidate = JSON.parse(serialized) as Partial<AuthUser>
    if (
      typeof candidate.id !== 'string' ||
      typeof candidate.username !== 'string' ||
      typeof candidate.email !== 'string'
    ) {
      return null
    }
    return candidate as AuthUser
  } catch {
    return null
  }
}

function persistSession(token: string, user: AuthUser): void {
  try {
    window.sessionStorage.setItem(ACCESS_TOKEN_STORAGE_KEY, token)
    window.sessionStorage.setItem(USER_STORAGE_KEY, JSON.stringify(user))
  } catch (error: unknown) {
    clearPersistedSession()
    throw new ApiRequestError('浏览器无法保存登录会话', {
      code: 'SESSION_STORAGE_UNAVAILABLE',
      details: error,
    })
  }
}

function clearPersistedSession(): void {
  if (typeof window === 'undefined') return
  try {
    window.sessionStorage.removeItem(ACCESS_TOKEN_STORAGE_KEY)
    window.sessionStorage.removeItem(USER_STORAGE_KEY)
  } catch {
    // In-memory state is still cleared if browser storage is unavailable.
  }
}

export const useAuthStore = defineStore('auth', () => {
  const accessToken = ref(readAccessToken())
  const user = ref<AuthUser | null>(readStoredUser())
  const isSubmitting = ref(false)
  const isRestoring = ref(false)
  const hasRestored = ref(false)
  const errorMessage = ref('')
  const errorCode = ref('')
  const errorRequestId = ref<string | undefined>()

  const isAuthenticated = computed(() => accessToken.value !== null)

  function clearError(): void {
    errorMessage.value = ''
    errorCode.value = ''
    errorRequestId.value = undefined
  }

  function setError(error: ApiRequestError): void {
    errorMessage.value = error.message
    errorCode.value = error.code
    errorRequestId.value = error.requestId
  }

  async function login(payload: LoginRequest): Promise<boolean> {
    if (isSubmitting.value) return false
    clearError()
    isSubmitting.value = true
    try {
      const result = await loginAccount(payload)
      persistSession(result.data.access_token, result.data.user)
      accessToken.value = result.data.access_token
      user.value = result.data.user
      hasRestored.value = true
      return true
    } catch (error: unknown) {
      setError(normalizeApiError(error))
      return false
    } finally {
      isSubmitting.value = false
    }
  }

  async function registerAndLogin(payload: RegisterRequest): Promise<boolean> {
    if (isSubmitting.value) return false
    clearError()
    isSubmitting.value = true
    try {
      await registerAccount(payload)
      const result = await loginAccount({ login: payload.username, password: payload.password })
      persistSession(result.data.access_token, result.data.user)
      accessToken.value = result.data.access_token
      user.value = result.data.user
      hasRestored.value = true
      return true
    } catch (error: unknown) {
      setError(normalizeApiError(error))
      return false
    } finally {
      isSubmitting.value = false
    }
  }

  async function restoreSession(): Promise<boolean> {
    if (hasRestored.value) return isAuthenticated.value

    accessToken.value = readAccessToken()
    if (!accessToken.value) {
      user.value = null
      hasRestored.value = true
      return false
    }

    isRestoring.value = true
    try {
      const result = await getCurrentUser()
      user.value = result.data
      window.sessionStorage.setItem(USER_STORAGE_KEY, JSON.stringify(result.data))
      return true
    } catch {
      logout()
      return false
    } finally {
      isRestoring.value = false
      hasRestored.value = true
    }
  }

  function logout(): void {
    clearPersistedSession()
    accessToken.value = null
    user.value = null
    hasRestored.value = true
    clearError()
  }

  return {
    accessToken,
    user,
    isSubmitting,
    isRestoring,
    hasRestored,
    errorMessage,
    errorCode,
    errorRequestId,
    isAuthenticated,
    clearError,
    login,
    registerAndLogin,
    restoreSession,
    logout,
  }
})
