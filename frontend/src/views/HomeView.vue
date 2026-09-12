<script setup lang="ts">
import { RouterLink } from 'vue-router'

import AppIcon from '@/components/AppIcon.vue'
import LegalDisclaimer from '@/components/LegalDisclaimer.vue'

const domains = [
  {
    number: '01',
    icon: 'heart',
    title: '婚姻家庭',
    description: '婚姻关系、子女抚养与财产分割等常见问题。',
  },
  {
    number: '02',
    icon: 'briefcase',
    title: '劳动争议',
    description: '劳动合同、薪酬、工伤与解除关系等事项。',
  },
  {
    number: '03',
    icon: 'car',
    title: '交通事故',
    description: '责任认定、损害赔偿与证据准备等信息。',
  },
  {
    number: '04',
    icon: 'file',
    title: '合同纠纷',
    description: '合同履行、违约责任与争议解决等场景。',
  },
]

const principles = [
  ['01', '说明事实', '用时间顺序讲清人物、行为与已有材料。'],
  ['02', '核对依据', '查看回答引用的法规或案例原始来源。'],
  ['03', '审慎行动', '重要权益和期限问题及时咨询专业人士。'],
]
</script>

<template>
  <div class="overflow-hidden">
    <section class="hero-grid relative border-b border-ink-950/8">
      <div
        class="pointer-events-none absolute -top-40 right-[-12rem] size-[34rem] rounded-full bg-jade-300/18 blur-3xl"
        aria-hidden="true"
      />
      <div
        class="relative mx-auto grid max-w-7xl gap-14 px-5 py-18 sm:px-8 sm:py-24 lg:grid-cols-[1.25fr_0.75fr] lg:items-center lg:px-10 lg:py-28"
      >
        <div class="reveal-up max-w-3xl">
          <div
            class="mb-7 inline-flex items-center gap-2 rounded-full border border-jade-800/14 bg-jade-50/80 px-3.5 py-2 text-[11px] font-semibold tracking-[0.14em] text-jade-900 uppercase"
          >
            <span class="size-1.5 rounded-full bg-jade-500" />
            中国大陆法律信息 · 课程演示
          </div>
          <h1
            class="max-w-3xl text-[2.65rem] leading-[1.12] font-semibold tracking-[-0.045em] text-balance text-ink-950 sm:text-6xl lg:text-[4.4rem]"
          >
            让复杂的法律问题，<br class="hidden sm:block" />先变得清晰。
          </h1>
          <p class="mt-7 max-w-2xl text-base leading-8 text-ink-600 sm:text-lg sm:leading-9">
            从事实整理开始，逐步理解可能涉及的规则、材料与下一步。答案保留来源线索，也明确能力边界。
          </p>
          <div class="mt-9 flex flex-col gap-3 sm:flex-row sm:items-center">
            <RouterLink
              to="/chat"
              class="focus-ring group inline-flex min-h-12 items-center justify-center gap-3 rounded-xl bg-ink-950 px-6 text-sm font-semibold text-white shadow-[0_12px_30px_rgba(18,33,29,0.18)] transition hover:-translate-y-0.5 hover:bg-jade-950"
            >
              进入咨询台
              <AppIcon
                name="arrow-right"
                :size="17"
                class="transition-transform group-hover:translate-x-0.5"
              />
            </RouterLink>
            <a
              href="#service-boundary"
              class="focus-ring inline-flex min-h-12 items-center justify-center rounded-xl px-5 text-sm font-medium text-ink-600 transition hover:bg-white/65 hover:text-ink-950"
            >
              先了解使用边界
            </a>
          </div>
        </div>

        <div class="reveal-up relative lg:justify-self-end" style="animation-delay: 90ms">
          <div
            class="absolute -inset-3 translate-x-3 translate-y-3 rounded-[1.7rem] border border-ink-950/8"
            aria-hidden="true"
          />
          <div
            class="relative max-w-md rounded-[1.55rem] border border-ink-950/10 bg-white/80 p-6 shadow-[0_28px_70px_rgba(18,33,29,0.10)] backdrop-blur sm:p-8"
          >
            <div class="flex items-center justify-between border-b border-ink-950/8 pb-5">
              <div>
                <p class="text-xs font-semibold tracking-[0.15em] text-ink-400 uppercase">Before you ask</p>
                <h2 class="mt-1.5 text-xl font-semibold tracking-[-0.02em] text-ink-950">咨询前，准备三件事</h2>
              </div>
              <div class="grid size-11 place-items-center rounded-2xl bg-jade-100 text-jade-800">
                <AppIcon name="spark" :size="21" />
              </div>
            </div>
            <ol class="mt-2 divide-y divide-ink-950/8">
              <li class="flex gap-4 py-5">
                <span class="step-number">1</span>
                <div>
                  <p class="text-sm font-semibold text-ink-900">关键时间线</p>
                  <p class="mt-1 text-sm leading-6 text-ink-500">事情何时发生，先后顺序如何。</p>
                </div>
              </li>
              <li class="flex gap-4 py-5">
                <span class="step-number">2</span>
                <div>
                  <p class="text-sm font-semibold text-ink-900">已有材料</p>
                  <p class="mt-1 text-sm leading-6 text-ink-500">合同、沟通记录或其他证据线索。</p>
                </div>
              </li>
              <li class="flex gap-4 pt-5">
                <span class="step-number">3</span>
                <div>
                  <p class="text-sm font-semibold text-ink-900">希望解决什么</p>
                  <p class="mt-1 text-sm leading-6 text-ink-500">明确目标，系统才能更好地整理问题。</p>
                </div>
              </li>
            </ol>
          </div>
        </div>
      </div>
    </section>

    <section class="mx-auto max-w-7xl px-5 py-18 sm:px-8 sm:py-24 lg:px-10" aria-labelledby="domain-title">
      <div class="flex flex-col justify-between gap-5 md:flex-row md:items-end">
        <div>
          <p class="section-kicker">首月范围</p>
          <h2 id="domain-title" class="section-title">聚焦四类常见民事场景</h2>
        </div>
        <p class="max-w-lg text-sm leading-7 text-ink-500">
          范围之外的问题会明确提示知识覆盖不足，不把未经核验的内容包装成确定结论。
        </p>
      </div>

      <div class="mt-10 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <article
          v-for="domain in domains"
          :key="domain.title"
          class="group rounded-2xl border border-ink-950/8 bg-white/52 p-5 transition duration-300 hover:-translate-y-1 hover:border-jade-800/18 hover:bg-white hover:shadow-[0_18px_45px_rgba(18,33,29,0.08)]"
        >
          <div class="flex items-center justify-between">
            <div
              class="grid size-10 place-items-center rounded-xl bg-moss-100 text-jade-800 transition group-hover:bg-jade-800 group-hover:text-white"
            >
              <AppIcon :name="domain.icon" :size="19" />
            </div>
            <span class="font-mono text-[10px] tracking-[0.15em] text-ink-300">{{ domain.number }}</span>
          </div>
          <h3 class="mt-7 text-lg font-semibold tracking-[-0.02em] text-ink-950">{{ domain.title }}</h3>
          <p class="mt-2 text-sm leading-6 text-ink-500">{{ domain.description }}</p>
        </article>
      </div>
    </section>

    <section class="border-y border-ink-950/8 bg-ink-950 text-white" aria-labelledby="principle-title">
      <div class="mx-auto max-w-7xl px-5 py-18 sm:px-8 sm:py-22 lg:px-10">
        <p class="text-xs font-semibold tracking-[0.18em] text-jade-300 uppercase">A clear path</p>
        <h2 id="principle-title" class="mt-3 text-3xl font-semibold tracking-[-0.035em] sm:text-4xl">
          从问题，到可核验的下一步
        </h2>
        <div class="mt-10 grid gap-px overflow-hidden rounded-2xl border border-white/10 bg-white/10 md:grid-cols-3">
          <article
            v-for="principle in principles"
            :key="principle[0]"
            class="bg-ink-950 p-6 sm:p-7"
          >
            <span class="font-mono text-[11px] tracking-[0.16em] text-jade-300">{{ principle[0] }}</span>
            <h3 class="mt-8 text-lg font-semibold">{{ principle[1] }}</h3>
            <p class="mt-2 text-sm leading-7 text-white/55">{{ principle[2] }}</p>
          </article>
        </div>
      </div>
    </section>

    <section id="service-boundary" class="mx-auto max-w-4xl scroll-mt-24 px-5 py-18 sm:px-8 sm:py-24">
      <div class="mb-7 text-center">
        <p class="section-kicker">请在使用前阅读</p>
        <h2 class="section-title">清楚能力，也清楚边界</h2>
      </div>
      <LegalDisclaimer variant="full" />
    </section>
  </div>
</template>
