<script setup lang="ts">
import { RouterLink } from 'vue-router'

import AppIcon from '@/components/AppIcon.vue'

const domains = [
  { icon: 'heart', title: '婚姻家庭', description: '婚姻关系、子女抚养与财产分割等常见问题。' },
  { icon: 'briefcase', title: '劳动争议', description: '劳动合同、薪酬、工伤与解除关系等事项。' },
  { icon: 'car', title: '交通事故', description: '责任认定、损害赔偿与证据准备等信息。' },
  { icon: 'file', title: '合同纠纷', description: '合同履行、违约责任与争议解决等场景。' },
]
</script>

<template>
  <div class="relative overflow-hidden">
    <div class="pointer-events-none absolute inset-x-0 top-0 -z-10 h-96 hero-grid opacity-55" aria-hidden="true" />
    <div
      class="pointer-events-none absolute -top-36 left-1/2 -z-10 size-[30rem] -translate-x-1/2 rounded-full bg-jade-100/50 blur-3xl"
      aria-hidden="true"
    />

    <header class="mx-auto max-w-5xl px-5 pt-16 pb-14 text-center sm:px-8 sm:pt-22 sm:pb-18 lg:px-10">
      <span class="mx-auto grid size-14 place-items-center rounded-2xl bg-ink-950 font-serif text-2xl text-white shadow-[0_14px_35px_rgba(18,33,29,0.16)]" aria-hidden="true">衡</span>
      <p class="mt-7 section-kicker">关于 LegalMind</p>
      <h1 class="mt-3 text-4xl font-semibold tracking-[-0.045em] text-ink-950 sm:text-5xl">让法律问题先变得清晰</h1>
      <p class="mx-auto mt-5 max-w-2xl text-base leading-8 text-ink-600">
        LegalMind 是一个面向中国大陆常见法律信息场景的课程项目，尝试用清晰、克制的交互帮助用户整理事实和下一步。
      </p>
    </header>

    <div class="mx-auto max-w-5xl px-5 pb-20 sm:px-8 sm:pb-24 lg:px-10">
      <section class="grid overflow-hidden rounded-2xl border border-ink-950/8 bg-white/65 md:grid-cols-3" aria-label="项目信息">
        <article class="p-6 sm:p-7">
          <span class="font-mono text-[10px] tracking-[0.16em] text-jade-800">01</span>
          <h2 class="mt-6 text-lg font-semibold text-ink-950">项目目标</h2>
          <p class="mt-3 text-sm leading-7 text-ink-600">先整理事实，再辨认可能相关的规则、材料与行动方向。</p>
        </article>
        <article class="border-t border-ink-950/8 p-6 sm:p-7 md:border-t-0 md:border-l">
          <span class="font-mono text-[10px] tracking-[0.16em] text-jade-800">02</span>
          <h2 class="mt-6 text-lg font-semibold text-ink-950">部署方式</h2>
          <p class="mt-3 text-sm leading-7 text-ink-600">项目以本地部署为主；配置外部 AI 服务时，问题仍会发送至对应服务处理。</p>
        </article>
        <article class="border-t border-ink-950/8 p-6 sm:p-7 md:border-t-0 md:border-l">
          <span class="font-mono text-[10px] tracking-[0.16em] text-jade-800">03</span>
          <h2 class="mt-6 text-lg font-semibold text-ink-950">服务边界</h2>
          <p class="mt-3 text-sm leading-7 text-ink-600">它不是律师事务所、政府机关或正式法律服务平台，不代替专业判断与个案代理。</p>
        </article>
      </section>

      <section class="mt-16 sm:mt-20" aria-labelledby="about-domains-title">
        <div class="flex flex-col justify-between gap-4 sm:flex-row sm:items-end">
          <div>
            <p class="section-kicker">首批支持领域</p>
            <h2 id="about-domains-title" class="section-title">聚焦四类常见民事场景</h2>
          </div>
          <p class="max-w-md text-sm leading-6 text-ink-600">范围之外的问题可能无法得到充分回答，系统应当明确提示能力不足。</p>
        </div>

        <div class="mt-8 grid gap-3 sm:grid-cols-2">
          <article
            v-for="domain in domains"
            :key="domain.title"
            class="flex gap-4 rounded-2xl border border-ink-950/8 bg-white/55 p-5 sm:p-6"
          >
            <span class="grid size-10 shrink-0 place-items-center rounded-xl bg-moss-100 text-jade-800" aria-hidden="true">
              <AppIcon :name="domain.icon" :size="18" />
            </span>
            <div>
              <h3 class="text-base font-semibold text-ink-950">{{ domain.title }}</h3>
              <p class="mt-1.5 text-sm leading-6 text-ink-600">{{ domain.description }}</p>
            </div>
          </article>
        </div>
      </section>

      <section class="mt-16 rounded-2xl bg-ink-950 p-6 text-white sm:mt-20 sm:flex sm:items-center sm:justify-between sm:gap-8 sm:p-8" aria-labelledby="about-next-title">
        <div>
          <h2 id="about-next-title" class="text-xl font-semibold tracking-[-0.025em]">使用前，先了解信息如何处理</h2>
          <p class="mt-2 max-w-xl text-sm leading-7 text-white/70">本地部署不等于所有处理都发生在本机。隐私说明列出了当前版本的数据流转方式。</p>
        </div>
        <RouterLink
          to="/privacy"
          class="focus-ring mt-5 inline-flex min-h-11 shrink-0 items-center justify-center gap-2 rounded-xl bg-white px-5 text-sm font-semibold text-ink-950 transition hover:bg-jade-50 sm:mt-0"
        >
          查看隐私说明
          <AppIcon name="arrow-right" :size="16" />
        </RouterLink>
      </section>
    </div>
  </div>
</template>
