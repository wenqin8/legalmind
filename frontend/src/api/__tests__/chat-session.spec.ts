import { afterEach, describe, it, expect, vi } from 'vitest'
import { apiClient } from '@/api/client'
import { readHistory } from '@/api/chat-session'
const id='97c94b7f-2451-470e-a3e5-a278a9d04929'
describe('restored history contract',()=>{
 afterEach(()=>vi.restoreAllMocks())
 it('restores legacy nullable turn IDs with stable timestamps',async()=>{
  vi.spyOn(apiClient,'get').mockResolvedValue({data:{success:true,request_id:id,data:{session_id:id,history_expired:false,warnings:[],messages:[{role:'user',content:'问题',turn_id:null,created_at:'2026-10-01T00:00:00Z'},{role:'assistant',content:'答案',turn_id:null,created_at:'2026-10-01T00:00:00Z',intent:'qa',sources:[],warnings:[],missing_fields:[],task:null,document_id:null}]}}})
  expect((await readHistory(id)).messages).toHaveLength(2)
 })
 it('rejects assistant history without valid source/task metadata',async()=>{
  vi.spyOn(apiClient,'get').mockResolvedValue({data:{success:true,request_id:id,data:{session_id:id,history_expired:false,warnings:[],messages:[{role:'assistant',content:'答案',turn_id:id,intent:'qa',sources:[{source_type:'legal_provision'}],warnings:[],missing_fields:[]}]}}})
  await expect(readHistory(id)).rejects.toMatchObject({code:'INVALID_RESPONSE'})
 })
})
