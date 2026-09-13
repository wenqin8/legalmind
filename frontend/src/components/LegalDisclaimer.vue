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
    v-if="variant === 'full'"
    role="note"
    class="rounded-2xl border border-ink-950/8 bg-white/55 p-5 sm:p-6"
  >
    <div class="flex items-start gap-3">
      <div
        class="mt-0.5 flex size-8 shrink-0 items-center justify-center rounded-full bg-jade-100 text-jade-800"
      >
        <AppIcon name="shield" :size="17" />
      </div>
      <div>
        <p class="mb-1.5 text-xs font-semibold tracking-[0.08em] text-jade-800">
          重要使用提示
        </p>
        <p class="text-sm leading-7 text-ink-700">
          本系统由人工智能生成内容，仅提供一般法律信息，不构成法律意见、律师服务或任何结果保证。AI 可能产生错误、遗漏或过时信息；在采取行动前，请核对法规、案例等原始依据。涉及诉讼时效、举证期限、重大财产、人身安全或其他重要权益时，请及时咨询执业律师或有关机关。请勿提交身份证号码、银行卡号、完整住址等非必要敏感信息。
        </p>
      </div>
    </div>
  </aside>
  <p v-else role="note" class="text-center text-[11px] leading-5 text-ink-600 sm:text-xs">
    AI 生成内容仅供参考，不构成法律意见。重要事项请核对原始依据或咨询专业人士。
  </p>
</template>
