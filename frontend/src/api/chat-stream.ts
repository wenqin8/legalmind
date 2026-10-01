import { apiClient, ApiRequestError, readAccessToken } from '@/api/client'
import { CHAT_REQUEST_TIMEOUT_MS, isSource, parseChatEnvelope, UUID_PATTERN } from '@/api/chat'
import type { ChatResponseData, ChatSendRequest } from '@/types/chat'

export interface StreamHandlers {
  meta: (sessionId: string, intent: string) => void
  content: (delta: string) => void
}

// Fetch supports authenticated POST streams; EventSource only supports GET.
export async function streamChat(payload: ChatSendRequest, signal: AbortSignal, handlers: StreamHandlers): Promise<ChatResponseData> {
  const token = readAccessToken()
  if (!token) throw new ApiRequestError('请先登录后再提交咨询', { code: 'AUTH_REQUIRED', status: 401 })
  const controller = new AbortController()
  const abort = () => controller.abort()
  signal.addEventListener('abort', abort, { once: true })
  if (signal.aborted) abort()
  let timedOut = false
  const timer = setTimeout(() => { timedOut = true; controller.abort() }, CHAT_REQUEST_TIMEOUT_MS)
  let reader: ReadableStreamDefaultReader<Uint8Array> | undefined
  try {
    const response = await fetch(`${apiClient.defaults.baseURL}/chat/stream`, {
      method: 'POST', headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json', Accept: 'text/event-stream' },
      body: JSON.stringify(payload), signal: controller.signal,
    })
    if (!response.ok) {
      const body = await response.json().catch(() => null)
      throw new ApiRequestError(body?.error?.message ?? '咨询请求暂时无法处理', {
        status: response.status, code: body?.error?.code ?? 'HTTP_ERROR', requestId: body?.request_id,
      })
    }
    if (!response.body || !response.headers.get('content-type')?.includes('text/event-stream')) throw new ApiRequestError('流式响应格式异常', { code: 'INVALID_RESPONSE' })
    reader = response.body.getReader()
    const decoder = new TextDecoder('utf-8', { fatal: true })
    let buffer = '', requestId = '', sessionId = '', intent = '', text = ''
    let sources: ChatResponseData['sources'] | undefined
    let streamError: ApiRequestError | undefined
    const event = (frame: string): ChatResponseData | undefined => {
      const lines = frame.split('\n')
      const name = lines.find(line => line.startsWith('event:'))?.slice(6).trim()
      const raw = lines.filter(line => line.startsWith('data:')).map(line => line.slice(5).trimStart()).join('\n')
      if (!raw) return
      const value = JSON.parse(raw)
      if (name === 'meta') {
        if (sessionId || typeof value.request_id !== 'string' || !UUID_PATTERN.test(value.session_id) || !['qa','search','document'].includes(value.intent)) throw new Error('Invalid meta')
        requestId = value.request_id; sessionId = value.session_id; intent = value.intent
        handlers.meta(sessionId, intent)
      } else if (name === 'content') {
        if (!sessionId || sources || typeof value.delta !== 'string' || text.length + value.delta.length > 32000) throw new Error('Invalid content')
        text += value.delta; handlers.content(value.delta)
      } else if (name === 'sources') {
        if (!sessionId || sources || !Array.isArray(value.items) || !value.items.every(isSource)) throw new Error('Invalid sources')
        sources = value.items
      } else if (name === 'error') {
        if (typeof value.code !== 'string' || typeof value.message !== 'string') throw new Error('Invalid error')
        streamError = new ApiRequestError(value.message, { code: value.code, requestId: value.request_id })
      } else if (name === 'done') {
        if (streamError) throw streamError
        if (value.success !== true) throw new ApiRequestError('本次生成未完成', { code: 'STREAM_FAILED', requestId })
        if (!sources) throw new Error('Missing sources')
        return parseChatEnvelope({ success: true, request_id: requestId, data: {
          ...value, response: text, session_id: sessionId, intent, sources,
        } }).data
      }
    }
    while (true) {
      const chunk = await reader.read()
      buffer += decoder.decode(chunk.value, { stream: !chunk.done })
      // CRLF can be split across network chunks.
      buffer = buffer.replace(/\r\n/g, '\n')
      let boundary: number
      while ((boundary = buffer.indexOf('\n\n')) !== -1) {
        const frame = buffer.slice(0, boundary); buffer = buffer.slice(boundary + 2)
        const result = event(frame)
        if (result) return result
      }
      if (buffer.length > 200000) throw new Error('Oversized frame')
      if (chunk.done) break
    }
    throw streamError ?? new ApiRequestError('连接已中断，请核对会话记录后重试', { code: 'STREAM_INTERRUPTED', requestId })
  } catch (error) {
    if (error instanceof ApiRequestError) throw error
    if (controller.signal.aborted) throw new ApiRequestError(timedOut ? '请求超时，请核对会话记录后重试' : '已停止生成，请核对会话记录后继续', { code: timedOut ? 'REQUEST_TIMEOUT' : 'REQUEST_CANCELLED' })
    throw new ApiRequestError('连接中断或响应异常，请核对会话记录后重试', { code: 'STREAM_INTERRUPTED' })
  } finally {
    clearTimeout(timer); signal.removeEventListener('abort', abort)
    await reader?.cancel().catch(() => undefined)
    reader?.releaseLock()
  }
}
