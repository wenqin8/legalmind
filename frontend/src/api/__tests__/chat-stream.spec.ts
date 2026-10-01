import { beforeEach, afterEach, describe, it, expect, vi } from 'vitest'
import { ACCESS_TOKEN_STORAGE_KEY } from '@/api/client'
import { streamChat } from '@/api/chat-stream'
const id = '97c94b7f-2451-470e-a3e5-a278a9d04929'
const payload = { message: '问题', session_id: null, document_type: null, document_params: null }
function frames(events: [string, unknown][]) { return events.map(([name, data]) => `event: ${name}\r\ndata: ${JSON.stringify(data)}\r\n\r\n`).join('') }
const meta: [string,unknown] = ['meta', { request_id: id, session_id: id, intent:'qa' }]
function respond(text: string) {
  const bytes = new TextEncoder().encode(text)
  const body = new ReadableStream({ start(controller) { for (let i=0;i<bytes.length;i+=3) controller.enqueue(bytes.slice(i,i+3)); controller.close() } })
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(body, { headers: { 'content-type':'text/event-stream' } })))
}
describe('authenticated SSE protocol', () => {
  beforeEach(() => sessionStorage.setItem(ACCESS_TOKEN_STORAGE_KEY, 'test-token'))
  afterEach(() => { vi.unstubAllGlobals(); sessionStorage.clear() })
  it('decodes fragmented Chinese UTF-8 and CRLF and waits for sources and successful done', async () => {
    respond(frames([meta, ['content',{delta:'结论\n中文'}],['content',{delta:'答案。'}],['sources',{items:[]}],['done',{success:true, missing_fields:[], warnings:[], task:null, document_id:null}]]))
    const content = vi.fn(), onMeta = vi.fn()
    const result = await streamChat(payload, new AbortController().signal, { meta:onMeta, content })
    expect(result.response).toBe('结论\n中文答案。')
    expect(content.mock.calls.flat().join('')).toBe(result.response)
    expect(onMeta).toHaveBeenCalledWith(id,'qa')
    expect(fetch).toHaveBeenCalledWith(expect.stringContaining('/chat/stream'), expect.objectContaining({ method:'POST', headers:expect.objectContaining({Authorization:'Bearer test-token'}) }))
  })
  it('rejects a truncated stream and never confirms received content', async () => {
    respond(frames([meta,['content',{delta:'部分答案'}]]))
    await expect(streamChat(payload, new AbortController().signal, {meta:vi.fn(),content:vi.fn()})).rejects.toMatchObject({code:'STREAM_INTERRUPTED'})
  })
  it('propagates service failures after headers and rejects success without sources', async () => {
    respond(frames([meta,['error',{code:'MODEL_UNAVAILABLE',message:'生成失败',request_id:id}],['done',{success:false}]]))
    await expect(streamChat(payload, new AbortController().signal, {meta:vi.fn(),content:vi.fn()})).rejects.toMatchObject({code:'MODEL_UNAVAILABLE'})
    respond(frames([meta,['content',{delta:'答案'}],['done',{success:true}]]))
    await expect(streamChat(payload, new AbortController().signal, {meta:vi.fn(),content:vi.fn()})).rejects.toMatchObject({code:'STREAM_INTERRUPTED'})
  })
  it('preserves HTTP errors and handles stopping before the first byte', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(JSON.stringify({success:false,error:{code:'AUTH_REQUIRED',message:'请登录'}}), {status:401})))
    await expect(streamChat(payload,new AbortController().signal,{meta:vi.fn(),content:vi.fn()})).rejects.toMatchObject({code:'AUTH_REQUIRED',status:401})
    const controller = new AbortController()
    vi.stubGlobal('fetch', vi.fn((_url, options) => new Promise((_resolve,reject) => { options.signal.addEventListener('abort', () => reject(new DOMException('aborted','AbortError'))) })))
    const pending = streamChat(payload,controller.signal,{meta:vi.fn(),content:vi.fn()})
    controller.abort()
    await expect(pending).rejects.toMatchObject({code:'REQUEST_CANCELLED'})
  })
})
