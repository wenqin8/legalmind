<script setup lang="ts">
import { ref, watch } from 'vue'
import { useRoute, RouterLink } from 'vue-router'
import { getCase } from '@/api/resources'
import { normalizeApiError } from '@/api/client'
import { domains, type CaseDetail } from '@/types/resources'
const route = useRoute(), data = ref<CaseDetail>(), busy = ref(false), error = ref('')
let request = 0
async function load() {
  const id = ++request; busy.value = true; error.value = ''; data.value = undefined
  try { const result = await getCase(String(route.params.id)); if (id === request) data.value = result }
  catch (e) { if (id === request) error.value = normalizeApiError(e).message }
  finally { if (id === request) busy.value = false }
}
watch(() => route.params.id, load, { immediate: true })
</script>
<template>
  <div class="mx-auto max-w-4xl px-5 py-10 sm:px-8">
    <RouterLink to="/cases" class="focus-ring text-sm underline">返回案例检索</RouterLink>
    <p v-if="busy" role="status" class="mt-8">正在加载案例……</p>
    <div v-if="error" role="alert" class="mt-8 text-red-800">{{ error }} <button class="underline" @click="load">重试</button></div>
    <article v-if="data" class="mt-6 rounded-2xl border border-ink-950/10 bg-white p-6 sm:p-8">
      <p class="text-xs text-jade-800">{{ domains[data.domain] }} · {{ data.case_number }}</p><h1 class="mt-3 text-2xl font-semibold">{{ data.title }}</h1>
      <p class="mt-3 text-sm text-amber-900">{{ data.warning }}</p>
      <p v-if="data.is_demo" class="mt-2 text-xs text-ink-600">样本日期：{{ data.sample_date }}；不是裁判日期。</p>
      <p v-else class="mt-2 text-xs">{{ data.court }} · {{ data.judgment_date }}</p>
      <section v-for="(text, title) in { '基本事实': data.facts, '争议焦点': data.dispute_focus, [data.is_demo ? '演示分析' : '裁判理由']: data.reasoning }" :key="title" class="mt-7">
        <h2 class="font-semibold">{{ title }}</h2><p class="mt-2 whitespace-pre-wrap text-sm leading-7">{{ text }}</p>
      </section>
      <section class="mt-7 border-t pt-5 text-xs leading-6"><h2 class="font-semibold">来源说明</h2><p>{{ data.source_title }} · {{ data.source_description }}</p><p>{{ data.authorization_note }}</p>
        <a v-if="data.source_url && /^https?:\/\//.test(data.source_url)" :href="data.source_url" target="_blank" rel="noopener noreferrer" class="underline">查看原始来源</a>
        <p v-for="law in data.law_references" :key="law">{{ law }}</p>
      </section>
    </article>
  </div>
</template>
