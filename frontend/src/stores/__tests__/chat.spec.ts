import { beforeEach, describe, it, expect, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { ApiRequestError, ACCESS_TOKEN_STORAGE_KEY } from '@/api/client'
const api = vi.hoisted(() => ({stream:vi.fn(),list:vi.fn(),history:vi.fn(),remove:vi.fn()}))
vi.mock('@/api/chat-stream',()=>({streamChat:api.stream}))
vi.mock('@/api/chat-session',()=>({listConversations:api.list,readHistory:api.history}))
vi.mock('@/api/chat',()=>({hasChatCredential:()=>true,deleteChatSession:api.remove}))
import { useChatStore } from '@/stores/chat'
import { useAuthStore } from '@/stores/auth'
const id='97c94b7f-2451-470e-a3e5-a278a9d04929'
const result={session_id:id,response:'完整答案',intent:'qa',sources:[],warnings:[],missing_fields:[]}
describe('server session lifecycle',()=>{
  beforeEach(()=>{ setActivePinia(createPinia()); sessionStorage.clear(); sessionStorage.setItem(ACCESS_TOKEN_STORAGE_KEY,'test'); vi.resetAllMocks(); api.list.mockResolvedValue({items:[{session_id:id,title:'旧咨询',history_expired:false,updated_at:'2026-10-01'}],total:1}); api.history.mockResolvedValue({messages:[],warnings:['历史已过期'],history_expired:true}) })
  it('restores metadata and handles expired history without inventing facts',async()=>{
    const store=useChatStore(); await store.initialize(); expect(store.conversationRecords[0]?.title).toBe('旧咨询')
    await store.switchConversation(id); expect(store.sessionId).toBe(id); expect(store.messages).toEqual([]); expect(store.historyNotice).toContain('过期')
  })
  it('checks a committed turn after disconnect and does not send it twice',async()=>{
    api.stream.mockImplementation(async(_payload,_signal,handlers)=>{handlers.meta(id,'qa');handlers.content('未完成片段');throw new ApiRequestError('断流',{code:'STREAM_INTERRUPTED'})})
    const store=useChatStore(); await store.submitQuestion('问题'); expect(store.messages.at(-1)?.delivery).toBe('interrupted')
    api.history.mockResolvedValue({messages:[{id:'new-user',role:'user',content:'问题',isDemo:false},{id:'new-assistant',role:'assistant',content:'完整答案',isDemo:false}],warnings:[],history_expired:false})
    await expect(store.retryLastQuestion()).resolves.toBe(true); expect(api.stream).toHaveBeenCalledTimes(1); expect(store.messages.at(-1)?.content).toBe('完整答案')
  })
  it('blocks retry while the uncertain session is busy',async()=>{
    api.stream.mockImplementation(async(_payload,_signal,handlers)=>{handlers.meta(id,'qa');throw new ApiRequestError('断流',{code:'STREAM_INTERRUPTED'})})
    const store=useChatStore(); await store.submitQuestion('问题'); api.history.mockRejectedValue(new ApiRequestError('正在处理',{code:'SESSION_BUSY'}))
    await expect(store.retryLastQuestion()).resolves.toBe(false); expect(api.stream).toHaveBeenCalledTimes(1)
  })
  it('checks an existing session even when disconnect happens before stream metadata',async()=>{
    const store=useChatStore(); api.stream.mockResolvedValueOnce(result); await store.submitQuestion('旧问题')
    api.history.mockResolvedValueOnce({messages:[{id:'old-answer',role:'assistant',content:'完整答案',isDemo:false}],warnings:[],history_expired:false})
    api.stream.mockRejectedValueOnce(new ApiRequestError('断流',{code:'STREAM_INTERRUPTED'}))
    await store.submitQuestion('新问题')
    api.history.mockResolvedValueOnce({messages:[{id:'new-user',role:'user',content:'新问题',isDemo:false},{id:'new-answer',role:'assistant',content:'已提交的回答',isDemo:false}],warnings:[],history_expired:false})
    await expect(store.retryLastQuestion()).resolves.toBe(true)
    expect(api.stream).toHaveBeenCalledTimes(2); expect(store.messages.at(-1)?.content).toBe('已提交的回答')
  })
  it('continues a new question after recovering the previous committed turn',async()=>{
    api.stream.mockImplementationOnce(async(_payload,_signal,handlers)=>{handlers.meta(id,'qa');throw new ApiRequestError('断流',{code:'STREAM_INTERRUPTED'})})
    const store=useChatStore();await store.submitQuestion('问题')
    api.history.mockResolvedValue({messages:[{id:'new-user',role:'user',content:'问题',isDemo:false},{id:'new-assistant',role:'assistant',content:'旧完整答案',isDemo:false}],warnings:[],history_expired:false})
    api.stream.mockResolvedValue(result)
    await expect(store.submitQuestion('新问题')).resolves.toBe(true)
    expect(api.stream).toHaveBeenCalledTimes(2)
    expect(api.stream.mock.calls[1]?.[0]).toMatchObject({message:'新问题',session_id:id})
  })
  it('aborts generation and ignores late callbacks when logging out',async()=>{
    let resolve!: (r:typeof result)=>void
    let handlers: any, signal!: AbortSignal
    api.stream.mockImplementation((_p,s,h)=>{signal=s;handlers=h;return new Promise(r=>{resolve=r})})
    const store=useChatStore(); const pending=store.submitQuestion('问题'); expect(store.isSending).toBe(true)
    useAuthStore().logout(); expect(signal.aborted).toBe(true); handlers.content('不应出现'); resolve(result); await pending
    expect(store.messages).toEqual([]); expect(store.sessionId).toBeNull()
  })
  it('does not restore a committed turn after logout during retry reconciliation',async()=>{
    api.stream.mockImplementationOnce(async(_payload,_signal,handlers)=>{handlers.meta(id,'qa');throw new ApiRequestError('断流',{code:'STREAM_INTERRUPTED'})})
    const store=useChatStore(); await store.submitQuestion('问题')
    let resolve!: (value:unknown)=>void
    api.history.mockImplementationOnce(()=>new Promise(r=>{resolve=r}))
    const retry=store.retryLastQuestion()
    useAuthStore().logout()
    resolve({messages:[{id:'user',role:'user',content:'问题',isDemo:false},{id:'answer',role:'assistant',content:'旧用户答案',isDemo:false}],warnings:[],history_expired:false})
    await expect(retry).resolves.toBe(false)
    expect(store.messages).toEqual([]); expect(store.sessionId).toBeNull()
    expect(api.stream).toHaveBeenCalledTimes(1)
  })
  it('clears pending deletion and ignores its late error after logout',async()=>{
    const store=useChatStore(); await store.initialize()
    let reject!: (error:Error)=>void
    api.remove.mockImplementationOnce(()=>new Promise((_resolve,r)=>{reject=r}))
    const deletion=store.deleteConversation(id)
    expect(store.isBusy).toBe(true)
    useAuthStore().logout()
    expect(store.isBusy).toBe(false)
    reject(new ApiRequestError('旧请求错误',{code:'SERVICE_UNAVAILABLE'}))
    await expect(deletion).resolves.toBe(false)
    expect(store.errorMessage).toBe(''); expect(store.conversationRecords).toEqual([])
  })
})
