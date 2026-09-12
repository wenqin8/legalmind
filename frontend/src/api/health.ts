import { ApiRequestError, apiClient } from './client'

import type { ApiSuccess, HealthData } from '@/types/api'

export async function getHealth(): Promise<ApiSuccess<HealthData>> {
  const response = await apiClient.get<unknown>('/health')
  const body = response.data

  if (
    !body ||
    typeof body !== 'object' ||
    (body as Partial<ApiSuccess<HealthData>>).success !== true ||
    (body as Partial<ApiSuccess<HealthData>>).data?.status !== 'healthy' ||
    typeof (body as Partial<ApiSuccess<HealthData>>).data?.version !== 'string' ||
    !(body as Partial<ApiSuccess<HealthData>>).data?.version.trim() ||
    typeof (body as Partial<ApiSuccess<HealthData>>).request_id !== 'string'
  ) {
    throw new ApiRequestError('后端健康响应格式不正确', {
      code: 'INVALID_RESPONSE',
    })
  }

  return body as ApiSuccess<HealthData>
}
