export interface AuthUser {
  id: string
  username: string
  email: string
  created_at?: string
}

export interface LoginRequest {
  login: string
  password: string
}

export interface RegisterRequest {
  username: string
  email: string
  password: string
}

export interface LoginData {
  access_token: string
  token_type: 'bearer'
  expires_in: number
  user: AuthUser
}
