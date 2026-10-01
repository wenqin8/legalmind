<script setup lang="ts">
import type { SourceReference } from '@/types/chat'
defineProps<{ sources: SourceReference[] }>()
</script>
<template>
  <details v-for="source in sources" :key="source.source_id" class="mt-2 rounded-lg border border-ink-950/10 p-3">
    <summary class="cursor-pointer font-semibold">[{{ source.citation_id }}] {{ source.title }} · {{ source.reference_number }}{{ source.is_demo ? '（演示参考）' : source.source_type === 'legal_provision' ? '（官方条文）' : '（案例参考）' }}</summary>
    <template v-if="source.source_type === 'legal_provision'">
      <p class="mt-2">{{ source.version }} · 生效日期：{{ source.effective_from }}{{ source.effective_until ? `，失效边界：${source.effective_until}` : '' }}</p>
      <p>核验日期：{{ source.verified_at }}；有效状态资料截至：{{ source.status_as_of }}。本次未实时联网核验。</p>
      <p>{{ source.applicability === 'general_reference' ? '一般规则参考' : '事件时间候选依据，仍须审查具体适用条件' }}</p>
      <p v-if="source.temporal_rule === 'pending_after_effective'">适用时间还须核对生效后的案件审理状态。</p>
      <blockquote v-if="source.transition_text" class="my-2 whitespace-pre-wrap border-l-2 border-jade-700/30 pl-3">过渡规定：{{ source.transition_text }}</blockquote>
      <blockquote class="my-2 whitespace-pre-wrap border-l-2 border-jade-700/30 pl-3">{{ source.original_text }}</blockquote>
      <a v-if="source.source_url" :href="source.source_url" target="_blank" rel="noopener noreferrer" class="focus-ring underline">查看官方原文（{{ source.publisher }}）</a>
    </template>
    <p v-else-if="source.is_demo" class="mt-2">演示数据，不是真实判例或法律依据。样本日期 {{ source.sample_date }} 不是裁判日期。</p>
    <a v-else-if="source.source_url && /^https?:\/\//.test(source.source_url)" :href="source.source_url" target="_blank" rel="noopener noreferrer" class="underline">查看原始来源</a>
  </details>
</template>
