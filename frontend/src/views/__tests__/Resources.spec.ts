import { mount, flushPromises } from '@vue/test-utils'
import { beforeEach, describe, it, expect, vi } from 'vitest'
const api=vi.hoisted(()=>({templates:vi.fn(),generate:vi.fn(),search:vi.fn()}))
vi.mock('@/api/resources',()=>({getTemplates:api.templates,generateDocument:api.generate,searchCases:api.search}))
import DocumentsView from '@/views/DocumentsView.vue'
import CasesView from '@/views/CasesView.vue'
describe('resource pages',()=>{
 beforeEach(()=>{vi.resetAllMocks();api.templates.mockResolvedValue([{document_type:'general_contract',name:'通用合同',fields:[{name:'party_a',label:'甲方',required:true,max_length:500}]}]);api.generate.mockResolvedValue({document_id:'id',title:'合同草稿',content:'草稿，提交前须人工审核',sources:[],warnings:[]});api.search.mockResolvedValue({items:[],count:0,score_note:''})})
 it('requires review and clears confirmation after any field edit',async()=>{
  const w=mount(DocumentsView);await flushPromises();await w.get('textarea').setValue('甲方');await w.get('form').trigger('submit');expect(api.generate).not.toHaveBeenCalled();expect(w.get('[aria-label="文书摘要"]').text()).toContain('甲方')
  await w.get('textarea').setValue('新甲方');expect(w.find('[aria-label="文书摘要"]').exists()).toBe(false)
  await w.get('form').trigger('submit');await w.get('[aria-label="文书摘要"] button').trigger('click');await flushPromises();expect(api.generate).toHaveBeenCalledWith('general_contract',{party_a:'新甲方'},'',false);expect(w.get('[aria-label="文书草稿"]').text()).toContain('草稿')
 })
 it('sends filters and displays empty results',async()=>{
  const w=mount(CasesView,{global:{stubs:{RouterLink:true}}});await w.get('input').setValue('劳动报酬');await w.get('select').setValue('labor_dispute');await w.get('form').trigger('submit');await flushPromises();expect(api.search).toHaveBeenCalledWith('劳动报酬','labor_dispute',5);expect(w.text()).toContain('没有匹配')
 })
})
