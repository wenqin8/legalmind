<script setup lang="ts">
import AppIcon from '@/components/AppIcon.vue'

withDefaults(
  defineProps<{
    variant?: 'full' | 'compact'
  }>(),
  { variant: 'compact' },
)
</script>

<template>
  <aside
    role="note"
    class="rounded-2xl border border-ink-950/8 bg-white/55"
    :class="variant === 'full' ? 'p-5 sm:p-6' : 'px-4 py-3.5'"
  >
    <div class="flex items-start gap-3">
      <div
        class="mt-0.5 flex size-8 shrink-0 items-center justify-center rounded-full bg-jade-100 text-jade-800"
      >
        <AppIcon name="shield" :size="17" />
      </div>
      <div>
        <p
          v-if="variant === 'full'"
          class="mb-1.5 text-xs font-semibold tracking-[0.16em] text-jade-800 uppercase"
        >
          使用边界
        </p>
        <p
          v-if="variant === 'full'"
          class="text-sm leading-7 text-ink-700"
        >
          本系统由人工智能生成内容，仅用于课程演示和一般法律信息参考，不构成法律意见、律师服务或任何结果保证。人工智能可能产生错误、遗漏或过时信息，请核对展示的法规和案例原文。涉及诉讼时效、举证期限、重大财产、人身安全或其他重要权益时，请及时咨询执业律师或有关机关。请勿提交身份证号码、银行卡号、完整住址等非必要敏感信息。
        </p>
        <p v-else class="text-xs leading-5 text-ink-600 sm:text-sm">
          AI 内容仅供参考，不构成法律意见；重要事项请咨询执业律师并核对原始依据。
        </p>
      </div>
    </div>
  </aside>
</template>
