<script setup lang="ts">
import { ref } from 'vue'
import { downloadDocument } from '@/api/resources'
import { normalizeApiError } from '@/api/client'
const props = defineProps<{ documentId: string; content: string }>()
const feedback = ref(''), busy = ref(false)
async function action(format?: 'md' | 'txt') {
  if (busy.value) return
  busy.value = true; feedback.value = ''
  try {
    if (format) { await downloadDocument(props.documentId, format); feedback.value = '已开始下载' }
    else { await navigator.clipboard.writeText(props.content); feedback.value = '已复制草稿' }
  } catch (error) { feedback.value = format ? normalizeApiError(error).message : '无法自动复制，请选择正文后复制。' }
  finally { busy.value = false }
}
</script>
<template>
  <div class="my-4 flex flex-wrap items-center gap-2 text-xs" :data-document-id="documentId">
    <button type="button" class="focus-ring rounded-lg border px-3 py-2" :disabled="busy" @click="action()">复制草稿</button>
    <button type="button" class="focus-ring rounded-lg border px-3 py-2" :disabled="busy" @click="action('md')">下载 Markdown</button>
    <button type="button" class="focus-ring rounded-lg border px-3 py-2" :disabled="busy" @click="action('txt')">下载 TXT</button>
    <span role="status">{{ feedback }}</span>
  </div>
</template>
