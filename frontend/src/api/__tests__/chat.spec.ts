import { beforeEach, describe, expect, it, vi } from 'vitest'

import { CHAT_REQUEST_TIMEOUT_MS, deleteChatSession, sendChatMessage } from '@/api/chat'
import { ACCESS_TOKEN_STORAGE_KEY, apiClient } from '@/api/client'

describe('sendChatMessage', () => {
  beforeEach(() => {
    window.sessionStorage.clear()
    vi.restoreAllMocks()
  })

  it('validates official versions and sends confirmation for the reviewed revision', async () => {
    window.sessionStorage.setItem(ACCESS_TOKEN_STORAGE_KEY, 'test-token')
    const id = '97c94b7f-2451-470e-a3e5-a278a9d04929'
    const source = { source_type: 'legal_provision', source_id: id, citation_id: 'S1', title: '法律', reference_number: '第一条', publisher: '官方', date: '2020-01-01', sample_date: null, source_url: 'https://www.court.gov.cn/example', source_kind: 'official', is_demo: false, is_synthetic: false, version: '核验版本', effective_from: '2021-01-01', verified_at: '2026-09-18', status_as_of: '2026-03-12', original_text: '原文', applicability: 'general_reference' }
    const envelope = { success: true, request_id: 'request-id', data: { response: '参考', intent: 'qa', sources: [source], session_id: id, warnings: [], missing_fields: [], task: null } }
    const post = vi.spyOn(apiClient, 'post').mockResolvedValue({ data: envelope })
    await expect(sendChatMessage('确认生成', id, { action: 'confirm', revision: id })).resolves.toEqual(envelope)
    expect(post).toHaveBeenCalledWith('/chat/send', expect.objectContaining({ task_action: 'confirm', task_revision: id }), expect.anything())
    source.source_url = 'javascript:alert(1)'
    await expect(sendChatMessage('问题', id)).rejects.toMatchObject({ code: 'INVALID_RESPONSE' })
    source.source_url = 'https://www.court.gov.cn/example'
    source.original_text = ''
    await expect(sendChatMessage('问题', id)).rejects.toMatchObject({ code: 'INVALID_RESPONSE' })
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
      message: '服务响应异常，请稍后重试',
    })
  })

  it('deletes an authenticated chat session through the protected endpoint', async () => {
    window.sessionStorage.setItem(ACCESS_TOKEN_STORAGE_KEY, 'test-token')
    const sessionId = '97c94b7f-2451-470e-a3e5-a278a9d04929'
    const envelope = {
      success: true as const,
      data: { deleted_session_id: sessionId },
      request_id: 'delete-request-id',
    }
    const remove = vi.spyOn(apiClient, 'delete').mockResolvedValue({ data: envelope })

    await expect(deleteChatSession(sessionId)).resolves.toEqual(envelope)
    expect(remove).toHaveBeenCalledWith(`/chat/history/${sessionId}`)
  })

  it.each(['qa', 'search', 'document'])('accepts the %s branch with nullable demo dates', async (intent) => {
    window.sessionStorage.setItem(ACCESS_TOKEN_STORAGE_KEY, 'test-token')
    const source = {
      source_type: 'case', source_id: '97c94b7f-2451-470e-a3e5-a278a9d04929',
      citation_id: 'S1', title: '演示案例', reference_number: 'DEMO-LABOR_DISPUTE-001',
      publisher: null, date: null, sample_date: '2026-09-13', source_url: null,
      source_kind: 'demo', is_demo: true, is_synthetic: true,
    }
    const envelope = { success: true, request_id: 'request-id', data: {
      response: '请补充信息', intent, sources: [source], missing_fields: ['court'],
      warnings: ['演示数据不是真实判例'], session_id: source.source_id, document_id: null,
    } }
    vi.spyOn(apiClient, 'post').mockResolvedValue({ data: envelope })
    await expect(sendChatMessage('问题', null)).resolves.toEqual(envelope)
    vi.spyOn(apiClient, 'post').mockResolvedValue({ data: {
      ...envelope, data: { ...envelope.data, sources: [{ ...source, date: '2026-09-13' }] },
    } })
    await expect(sendChatMessage('问题', null)).rejects.toMatchObject({ code: 'INVALID_RESPONSE' })
  })
})
