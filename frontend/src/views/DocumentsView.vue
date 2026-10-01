<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { getTemplates, generateDocument } from '@/api/resources'
import { normalizeApiError } from '@/api/client'
import { type DocumentTemplate, type GeneratedDocument } from '@/types/resources'
import SourceCards from '@/components/SourceCards.vue'
import DocumentActions from '@/components/DocumentActions.vue'
const templates = ref<DocumentTemplate[]>([]), selected = ref(''), parameters = ref<Record<string,string>>({}), instructions = ref(''), references = ref(false)
const busy = ref(false), loading = ref(false), error = ref(''), review = ref(false), result = ref<GeneratedDocument>()
const template = computed(() => templates.value.find(t => t.document_type === selected.value))
watch(selected, () => { parameters.value = {}; review.value = false; error.value = '' })
watch([parameters, instructions, references], () => { review.value = false }, { deep: true })
async function load() {
  loading.value = true; error.value = ''
  try { templates.value = await getTemplates(); selected.value = templates.value[0]?.document_type ?? '' }
  catch (e) { error.value = normalizeApiError(e).message } finally { loading.value = false }
}
function summarize() { error.value = ''; review.value = true }
async function generate() {
  if (!template.value || !review.value || busy.value) return
  busy.value = true; error.value = ''
  try { result.value = await generateDocument(selected.value, Object.fromEntries(Object.entries(parameters.value).map(([k,v]) => [k,v.trim()])), instructions.value.trim(), references.value); review.value = false }
  catch (e) { error.value = normalizeApiError(e).message } finally { busy.value = false }
}
onMounted(load)
</script>
<template>
  <div class="mx-auto max-w-6xl px-5 py-10 sm:px-8">
    <p class="text-xs font-semibold text-jade-800">从已知材料开始</p><h1 class="mt-2 text-3xl font-semibold">文书生成</h1>
    <p class="mt-3 text-sm text-ink-600">填写必要信息，核对摘要后生成草稿。提交或签署前须人工审核。</p>
    <p v-if="loading" class="mt-6" role="status">正在加载文书模板……</p>
    <p v-if="error" role="alert" class="mt-5 text-red-800">{{ error }} <button v-if="!templates.length" class="underline" @click="load">重试加载</button></p>
    <div v-if="template" class="mt-7 grid gap-6 lg:grid-cols-2">
      <form class="space-y-4 rounded-2xl border border-ink-950/10 bg-white p-5" @submit.prevent="summarize">
        <fieldset :disabled="busy" class="space-y-4">
          <label class="block text-sm">文书类型<select v-model="selected" class="mt-2 w-full rounded-lg border p-3"><option v-for="t in templates" :key="t.document_type" :value="t.document_type">{{ t.name }}</option></select></label>
          <label v-for="field in template.fields" :key="field.name" class="block text-sm">{{ field.label }}{{ field.required ? '（必填）' : '' }}
            <textarea v-model="parameters[field.name]" :required="field.required" :maxlength="field.max_length" :rows="field.max_length > 500 ? 4 : 2" class="mt-2 w-full rounded-lg border p-3 text-sm" />
          </label>
          <label class="block text-sm">补充说明（可选）<textarea v-model="instructions" maxlength="4000" rows="3" class="mt-2 w-full rounded-lg border p-3" /></label>
          <label class="flex gap-2 text-xs"><input v-model="references" type="checkbox" />附检索参考材料（当前案例是演示数据，不作为法律依据）</label>
          <button class="focus-ring rounded-lg bg-ink-950 px-5 py-3 text-sm text-white">核对摘要</button>
        </fieldset>
      </form>
      <div class="space-y-5">
        <section v-if="review" class="rounded-2xl border border-jade-800/20 bg-jade-50 p-5" aria-label="文书摘要">
          <h2 class="font-semibold">确认 {{ template.name }} 摘要</h2>
          <dl v-for="field in template.fields" :key="field.name" class="mt-3 text-sm"><dt class="font-semibold">{{ field.label }}</dt><dd class="whitespace-pre-wrap">{{ parameters[field.name] }}</dd></dl>
          <p v-if="instructions" class="mt-3 whitespace-pre-wrap text-sm">补充说明：{{ instructions }}</p>
          <p class="mt-3 text-xs">{{ references ? '附检索参考材料' : '仅按填写内容生成' }}</p>
          <button type="button" class="focus-ring mt-5 rounded-lg bg-jade-800 px-5 py-3 text-sm text-white disabled:opacity-40" :disabled="busy" @click="generate">{{ busy ? '正在生成……' : '确认摘要并生成草稿' }}</button>
        </section>
        <section v-if="result" class="rounded-2xl border border-ink-950/10 bg-white p-5" aria-label="文书草稿">
          <h2 class="font-semibold">{{ result.title }}</h2>
          <DocumentActions :document-id="result.document_id" :content="result.content" />
          <p class="whitespace-pre-wrap text-sm leading-7">{{ result.content }}</p>
          <SourceCards :sources="result.sources" /><p v-for="w in result.warnings" :key="w" class="mt-3 text-xs text-ink-600">{{ w }}</p>
        </section>
        <p v-if="!review && !result" class="rounded-2xl border border-dashed p-8 text-sm text-ink-600">完成左侧信息后，先核对摘要，再生成草稿。</p>
      </div>
    </div>
  </div>
</template>
