<script setup lang="ts">
import { RouterLink } from 'vue-router'

import AppIcon from '@/components/AppIcon.vue'

const steps = [
  {
    number: '01',
    title: '说明事实',
    description: '按时间顺序写明人物、行为、结果和已有材料，先把事实与判断分开。',
  },
  {
    number: '02',
    title: '核对依据',
    description: '把回答当作检索线索，回到法规、司法解释或官方文件原文核对。',
  },
  {
    number: '03',
    title: '审慎行动',
    description: '结合期限、证据和风险决定下一步，重要事项及时寻求专业帮助。',
  },
]

const factChecklist = [
  ['时间', '事情何时开始，关键节点先后如何。'],
  ['人物', '各方是什么关系，分别做了什么。'],
  ['材料', '是否有合同、聊天记录、票据或通知。'],
  ['目标', '你希望了解什么，或准备解决什么问题。'],
]
</script>

<template>
  <div class="relative overflow-hidden">
    <div class="pointer-events-none absolute inset-x-0 top-0 -z-10 h-80 hero-grid opacity-55" aria-hidden="true" />
    <div
      class="pointer-events-none absolute -top-32 right-[-10rem] -z-10 size-96 rounded-full bg-jade-100/55 blur-3xl"
      aria-hidden="true"
    />

    <header class="mx-auto max-w-5xl px-5 pt-16 pb-12 sm:px-8 sm:pt-22 sm:pb-16 lg:px-10">
      <p class="section-kicker">使用说明</p>
      <h1 class="mt-3 max-w-3xl text-4xl leading-tight font-semibold tracking-[-0.045em] text-ink-950 sm:text-5xl">
        从事实开始，得到更清晰的下一步
      </h1>
      <p class="mt-5 max-w-2xl text-base leading-8 text-ink-600">
        LegalMind 帮你整理问题、识别可能相关的法律关系，并提示需要继续核对的材料。描述越具体，回答通常越有针对性。
      </p>
    </header>

    <div class="mx-auto max-w-5xl px-5 pb-20 sm:px-8 sm:pb-24 lg:px-10">
      <section aria-labelledby="guide-steps-title">
        <h2 id="guide-steps-title" class="sr-only">使用流程</h2>
        <ol class="grid overflow-hidden rounded-2xl border border-ink-950/8 bg-ink-950 text-white md:grid-cols-3">
          <li
            v-for="(step, index) in steps"
            :key="step.number"
            class="p-6 sm:p-7"
            :class="index > 0 ? 'border-t border-white/10 md:border-t-0 md:border-l' : ''"
          >
            <span class="font-mono text-[11px] tracking-[0.16em] text-jade-300">{{ step.number }}</span>
            <h3 class="mt-7 text-lg font-semibold">{{ step.title }}</h3>
            <p class="mt-2 text-sm leading-7 text-white/70">{{ step.description }}</p>
          </li>
        </ol>
      </section>

      <section class="mt-14 sm:mt-18" aria-labelledby="describe-title">
        <div class="grid gap-8 lg:grid-cols-[0.78fr_1.22fr] lg:gap-12">
          <div>
            <p class="section-kicker">说明事实</p>
            <h2 id="describe-title" class="section-title">怎样描述一个问题</h2>
            <p class="mt-4 text-sm leading-7 text-ink-600">
              不必先判断谁对谁错，也不必堆砌法律术语。先写清楚可以确认的事实，再补充你的疑问和目标。
            </p>
          </div>

          <div class="rounded-2xl border border-ink-950/8 bg-white/60 p-5 sm:p-7">
            <dl class="grid gap-x-8 gap-y-6 sm:grid-cols-2">
              <div v-for="item in factChecklist" :key="item[0]">
                <dt class="text-sm font-semibold text-ink-950">{{ item[0] }}</dt>
                <dd class="mt-1.5 text-sm leading-6 text-ink-600">{{ item[1] }}</dd>
              </div>
            </dl>
            <div class="mt-7 rounded-xl bg-moss-100 px-4 py-3.5">
              <p class="text-xs font-semibold text-jade-900">可以这样开始</p>
              <p class="mt-1.5 text-sm leading-6 text-ink-700">
                “事情发生在……，对方随后……，我目前有……材料，希望了解……”
              </p>
            </div>
          </div>
        </div>
      </section>

      <section class="mt-14 grid gap-4 sm:mt-18 lg:grid-cols-2" aria-label="核对与行动提示">
        <article class="rounded-2xl border border-jade-800/15 bg-jade-50/70 p-6 sm:p-7">
          <div class="flex items-center gap-3">
            <span class="grid size-10 place-items-center rounded-xl bg-jade-100 text-jade-800" aria-hidden="true">
              <AppIcon name="file" :size="19" />
            </span>
            <h2 class="text-lg font-semibold text-ink-950">当前如何核对依据</h2>
          </div>
          <p class="mt-4 text-sm leading-7 text-ink-600">
            当前版本可检索演示案例，并引用四个领域的部分官方条文。来源卡片显示版本、生效和核验日期；本次回答不会实时联网更新，仍须核对具体适用条件。演示数据不是真实判例或法律依据。
            缺少关键事实时会先追问；起草文书需补齐字段、核对摘要并确认后生成。信息不一致时可选择采用修改或保留原值，也可随时取消。
          </p>
        </article>

        <article class="rounded-2xl border border-ink-950/8 bg-white/60 p-6 sm:p-7">
          <div class="flex items-center gap-3">
            <span class="grid size-10 place-items-center rounded-xl bg-moss-100 text-jade-800" aria-hidden="true">
              <AppIcon name="shield" :size="19" />
            </span>
            <h2 class="text-lg font-semibold text-ink-950">何时需要及时行动</h2>
          </div>
          <p class="mt-4 text-sm leading-7 text-ink-600">
            涉及诉讼时效、举证期限、人身安全或重大财产处置时，不要只等待在线回答。请尽快联系执业律师、有关机关或其他适当的专业人员。
          </p>
        </article>
      </section>

      <section class="mt-14 flex flex-col gap-5 rounded-2xl border border-ink-950/8 bg-white/60 p-6 sm:flex-row sm:items-center sm:justify-between sm:p-8" aria-labelledby="guide-next-title">
        <div>
          <h2 id="guide-next-title" class="text-xl font-semibold tracking-[-0.025em] text-ink-950">准备好后，从一段事实开始</h2>
          <p class="mt-2 text-sm leading-6 text-ink-600">提交前请隐去身份证号、银行卡号、完整住址等非必要敏感信息。</p>
        </div>
        <RouterLink
          to="/chat"
          class="focus-ring inline-flex min-h-11 shrink-0 items-center justify-center gap-2 rounded-xl bg-ink-950 px-5 text-sm font-semibold text-white transition hover:bg-jade-950"
        >
          开始咨询
          <AppIcon name="arrow-right" :size="16" />
        </RouterLink>
      </section>
    </div>
  </div>
</template>
