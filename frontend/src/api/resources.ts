import { apiClient, ApiRequestError } from '@/api/client'
import { isSource, UUID_PATTERN } from '@/api/chat'
import { domains, type CaseItem, type CaseDetail, type DocumentTemplate, type GeneratedDocument } from '@/types/resources'
function invalid(): never { throw new ApiRequestError('服务响应异常，请稍后重试', { code: 'INVALID_RESPONSE' }) }
const uuid = UUID_PATTERN
function isCase(item: CaseItem) {
  return item && uuid.test(item.id) && typeof item.title === 'string' && typeof item.summary === 'string' && typeof item.case_number === 'string' && item.domain in domains &&
    typeof item.is_demo === 'boolean' && item.is_demo === item.is_synthetic && (item.source_kind === 'demo') === item.is_demo &&
    (!item.is_demo || (item.source_url === null && item.judgment_date === null && item.case_number.startsWith('DEMO-')))
}
export async function searchCases(query: string, domain: string | null, topK: number) {
  const { data: result } = await apiClient.post('/cases/search', { query, domain, source_kind: null, top_k: topK }, { timeout: 72000 })
  const data = result?.data
  if (result?.success !== true || !Array.isArray(data?.items) || !data.items.every((i: CaseItem) => isCase(i) && Number.isFinite(i.rrf_score)) || data.count !== data.items.length || typeof data.score_note !== 'string') invalid()
  return data as { items: CaseItem[]; count: number; score_note: string }
}
export async function getCase(id: string): Promise<CaseDetail> {
  const { data: result } = await apiClient.get(`/cases/${id}`)
  const data = result?.data
  if (result?.success !== true || !isCase(data) || data.id !== id || !['facts','reasoning','dispute_focus','warning','source_description','source_title','authorization_note'].every(k => typeof data[k] === 'string') || !Array.isArray(data.law_references)) invalid()
  return data
}
export async function getTemplates(): Promise<DocumentTemplate[]> {
  const { data: result } = await apiClient.get('/documents/templates')
  const items = result?.data?.items
  if (result?.success !== true || !Array.isArray(items) || items.length !== 3 || !items.every((i: DocumentTemplate) =>
    ['civil_complaint','civil_defense','general_contract'].includes(i.document_type) && typeof i.name === 'string' && Array.isArray(i.fields) && i.fields.every(f =>
      typeof f.name === 'string' && /^[a-z_]+$/.test(f.name) && typeof f.label === 'string' && typeof f.required === 'boolean' && Number.isInteger(f.max_length) && f.max_length > 0))) invalid()
  return items
}
export async function generateDocument(documentType: string, parameters: Record<string,string>, instructions: string, useReferences: boolean): Promise<GeneratedDocument> {
  const { data: result } = await apiClient.post('/documents/generate', {
    document_type: documentType, parameters, additional_instructions: instructions, use_references: useReferences,
  }, { timeout: 72000 })
  const data = result?.data
  if (result?.success !== true || !uuid.test(data?.document_id) || typeof data.content !== 'string' || !data.content.trim() ||
    !Array.isArray(data.sources) || !data.sources.every(isSource) || !Array.isArray(data.warnings) || !data.warnings.every((w: unknown) => typeof w === 'string')) invalid()
  return data
}
export async function downloadDocument(id: string, format: 'md' | 'txt') {
  let response
  try { response = await apiClient.get(`/documents/${id}/download`, { params: { format }, responseType: 'blob' }) }
  catch (error) {
    if (error instanceof ApiRequestError && error.code === 'HTTP_ERROR') {
      // Axios' Blob transport cannot parse the normal JSON error envelope.
      throw new ApiRequestError(error.status === 401 ? '登录已过期，请重新登录后下载' : '文书无法下载，请确认登录状态和文书归属', { status: error.status, code: error.status === 401 ? 'AUTH_REQUIRED' : error.code })
    }
    throw error
  }
  const url = URL.createObjectURL(response.data)
  const link = document.createElement('a')
  link.href = url; link.download = `legalmind-${id}.${format}`; link.click()
  setTimeout(() => URL.revokeObjectURL(url), 1000)
}
