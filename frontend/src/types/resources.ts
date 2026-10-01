import type { SourceReference } from '@/types/chat'
export const domains = { marriage_family: '婚姻家庭', labor_dispute: '劳动争议', traffic_accident: '交通事故', contract_dispute: '合同纠纷' }
export interface CaseItem {
  id: string; title: string; case_number: string; court: string | null; judgment_date: string | null
  domain: keyof typeof domains; summary: string; source_kind: string; source_url: string | null
  is_demo: boolean; is_synthetic: boolean; rrf_score: number
}
export interface CaseDetail extends CaseItem {
  sample_date: string | null; facts: string; dispute_focus: string; reasoning: string
  law_references: string[]; source_title: string; source_description: string; authorization_note: string; warning: string
}
export interface DocumentTemplate {
  document_type: string; name: string
  fields: { name: string; label: string; required: boolean; max_length: number }[]
}
export interface GeneratedDocument {
  document_id: string; document_type: string; title: string; content: string; sources: SourceReference[]; warnings: string[]; created_at: string
}
