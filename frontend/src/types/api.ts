export interface ApiSuccess<T> {
  success: true
  data: T
  request_id: string
}

export interface ApiFailure {
  success: false
  error: {
    code: string
    message: string
    details: unknown
  }
  request_id: string
}

export interface HealthData {
  status: 'healthy'
  version: string
}
