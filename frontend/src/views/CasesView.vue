<script setup lang="ts">
import { ref } from 'vue'
import { RouterLink } from 'vue-router'
import { searchCases } from '@/api/resources'
import { normalizeApiError } from '@/api/client'
import { domains, type CaseItem } from '@/types/resources'
const query = ref(''), domain = ref(''), topK = ref(5), busy = ref(false), searched = ref(false), error = ref(''), scoreNote = ref('')
const items = ref<CaseItem[]>([])
async function search() {
  if (busy.value || !query.value.trim()) return
  busy.value = true; error.value = ''; items.value = []; searched.value = false
  try { const result = await searchCases(query.value.trim(), domain.value || null, topK.value); items.value = result.items; scoreNote.value = result.score_note; searched.value = true }
  catch (e) { error.value = normalizeApiError(e).message } finally { busy.value = false }
}
</script>
<template>
  <div class="mx-auto max-w-5xl px-5 py-10 sm:px-8">
    <p class="text-xs font-semibold text-jade-800">参考资料</p><h1 class="mt-2 text-3xl font-semibold text-ink-950">案例检索</h1>
    <p class="mt-3 text-sm text-ink-600">按领域和关键事实检索。合成演示案例不是真实判例或法律依据。</p>
    <form class="mt-7 grid gap-4 rounded-2xl border border-ink-950/10 bg-white p-5 sm:grid-cols-[1fr_10rem_6rem_auto]" @submit.prevent="search">
      <label class="text-xs">关键事实<input v-model="query" required maxlength="1000" class="mt-2 w-full rounded-lg border p-3 text-sm" placeholder="例如：拖欠工资、劳动报酬争议" /></label>
      <label class="text-xs">领域<select v-model="domain" aria-label="领域" class="mt-2 w-full rounded-lg border p-3 text-sm"><option value="">全部领域</option><option v-for="(label, value) in domains" :key="value" :value="value">{{ label }}</option></select></label>
      <label class="text-xs">结果数量<input v-model.number="topK" type="number" min="1" max="20" class="mt-2 w-full rounded-lg border p-3 text-sm" /></label>
      <button class="focus-ring self-end rounded-lg bg-ink-950 px-5 py-3 text-sm text-white disabled:opacity-40" :disabled="busy">{{ busy ? '检索中……' : '搜索案例' }}</button>
    </form>
    <p v-if="error" class="mt-5 text-red-800" role="alert">{{ error }}</p>
    <p v-if="searched && !items.length" class="mt-8 text-sm" role="status">没有匹配的案例，请调整关键词或领域。</p>
    <p v-if="items.length" class="mt-5 text-xs text-ink-600">{{ scoreNote }}</p>
    <div class="mt-4 grid gap-4">
      <article v-for="item in items" :key="item.id" class="rounded-2xl border border-ink-950/10 bg-white p-5">
        <span class="text-xs text-jade-800">{{ domains[item.domain] }} · {{ item.is_demo ? '演示数据，不是真实判例' : '可追溯案例' }}</span>
        <h2 class="mt-2 text-lg font-semibold"><RouterLink :to="`/cases/${item.id}`" class="focus-ring underline decoration-jade-800/30">{{ item.title }}</RouterLink></h2>
        <p class="mt-2 text-xs text-ink-600">{{ item.case_number }}{{ item.court ? ` · ${item.court}` : '' }}{{ item.judgment_date ? ` · ${item.judgment_date}` : '' }}</p>
        <p class="mt-3 whitespace-pre-wrap text-sm leading-7">{{ item.summary }}</p>
      </article>
    </div>
  </div>
</template>
