<script setup lang="ts">
import { RouterLink } from 'vue-router'

import AppIcon from '@/components/AppIcon.vue'

const storageFacts = [
  {
    title: '登录会话',
    description: '登录后的 JWT 仅写入当前标签页的 sessionStorage，不写入 localStorage。关闭标签页后，浏览器通常会清除该会话数据。',
  },
  {
    title: '账户密码',
    description: '应用不会主动把密码写入浏览器存储；后端只保存密码哈希，不保存可直接读取的明文密码。',
  },
  {
    title: '应用数据库',
    description: '关系数据库保存账户、会话归属和生成的文书草稿。咨询消息保存在短期会话存储中，最多保留最近 20 条，每次成功咨询后续期 24 小时。已收集的任务字段及其来源原句与消息一起保存和过期。',
  },
]

const sensitiveExamples = ['身份证号码', '银行卡号与验证码', '完整住址', '账户密码', '与问题无关的病历或未成年人信息']
</script>

<template>
  <div class="relative overflow-hidden">
    <div class="pointer-events-none absolute inset-x-0 top-0 -z-10 h-72 hero-grid opacity-55" aria-hidden="true" />

    <header class="mx-auto max-w-5xl px-5 pt-16 pb-12 sm:px-8 sm:pt-22 sm:pb-16 lg:px-10">
      <div class="flex items-start gap-4">
        <span class="mt-1 grid size-11 shrink-0 place-items-center rounded-2xl bg-jade-100 text-jade-800" aria-hidden="true">
          <AppIcon name="lock" :size="21" />
        </span>
        <div>
          <p class="section-kicker">隐私说明</p>
          <h1 class="mt-3 text-4xl font-semibold tracking-[-0.045em] text-ink-950 sm:text-5xl">了解信息如何流转</h1>
          <p class="mt-5 max-w-2xl text-base leading-8 text-ink-600">
            这里说明当前版本在登录、存储和生成回答时如何处理信息，帮助你在提交问题前作出判断。
          </p>
        </div>
      </div>
    </header>

    <div class="mx-auto max-w-5xl px-5 pb-20 sm:px-8 sm:pb-24 lg:px-10">
      <section aria-labelledby="stored-title">
        <div class="flex flex-col justify-between gap-3 sm:flex-row sm:items-end">
          <div>
            <p class="section-kicker">登录与存储</p>
            <h2 id="stored-title" class="section-title">当前保存哪些信息</h2>
          </div>
          <p class="max-w-md text-sm leading-6 text-ink-600">浏览器或密码管理器自身提供的“保存密码”功能，由你和浏览器设置决定。</p>
        </div>

        <dl class="mt-8 grid gap-3 md:grid-cols-3">
          <div
            v-for="(fact, index) in storageFacts"
            :key="fact.title"
            class="rounded-2xl border border-ink-950/8 bg-white/60 p-5 sm:p-6"
          >
            <div class="flex items-center justify-between">
              <dt class="text-base font-semibold text-ink-950">{{ fact.title }}</dt>
              <span class="font-mono text-[10px] tracking-[0.14em] text-ink-400" aria-hidden="true">0{{ index + 1 }}</span>
            </div>
            <dd class="mt-4 text-sm leading-7 text-ink-600">{{ fact.description }}</dd>
          </div>
        </dl>

        <p class="mt-4 text-xs leading-6 text-ink-600">
          继续同一咨询时，系统会读取有限的近期上下文及已收集的任务字段；原消息被裁剪后，任务字段的来源原句仍可能保留至任务过期。过期后从空上下文开始，请重新补充。删除咨询会清除其短期消息、任务状态及会话记录，已生成的文书草稿单独保留。第三方 AI 服务如何处理数据取决于其配置。
        </p>
      </section>

      <section class="mt-14 sm:mt-18" aria-labelledby="ai-processing-title">
        <div class="overflow-hidden rounded-2xl border border-ink-950/8 bg-ink-950 text-white">
          <div class="grid gap-8 p-6 sm:p-8 lg:grid-cols-[0.78fr_1.22fr] lg:p-10">
            <div>
              <p class="text-[11px] font-semibold tracking-[0.18em] text-jade-300">AI 处理</p>
              <h2 id="ai-processing-title" class="mt-3 text-2xl font-semibold tracking-[-0.03em]">问题会发送到哪里</h2>
            </div>
            <div class="space-y-4 text-sm leading-7 text-white/75">
              <p>
                为生成回答，你提交的问题以及生成回答所需的上下文，会发送给运行方当前配置的 AI 服务。
              </p>
              <p>
                本地部署是指应用在本地环境运行，并不等于 AI 推理一定在本机完成。外部 AI 服务如何留存和处理请求，取决于部署时选择的服务及其数据设置。
              </p>
            </div>
          </div>
        </div>
      </section>

      <section class="mt-14 grid gap-8 sm:mt-18 lg:grid-cols-[0.82fr_1.18fr] lg:gap-12" aria-labelledby="minimize-title">
        <div>
          <p class="section-kicker">信息最小化</p>
          <h2 id="minimize-title" class="section-title">只提供解决问题所必需的内容</h2>
          <p class="mt-4 text-sm leading-7 text-ink-600">
            提交前可以用“当事人 A”“某公司”等代称，并遮盖材料中的识别信息。隐去这些内容通常不会影响对法律关系的初步梳理。
          </p>
        </div>

        <div class="rounded-2xl border border-jade-800/15 bg-jade-50/70 p-6 sm:p-7">
          <h3 class="text-sm font-semibold text-ink-950">请勿填写非必要敏感信息</h3>
          <ul class="mt-5 grid gap-3 sm:grid-cols-2">
            <li v-for="item in sensitiveExamples" :key="item" class="flex items-start gap-2.5 text-sm leading-6 text-ink-700">
              <AppIcon name="check" :size="16" class="mt-1 shrink-0 text-jade-700" />
              <span>{{ item }}</span>
            </li>
          </ul>
        </div>
      </section>

      <section class="mt-14 border-t border-ink-950/8 pt-8" aria-labelledby="privacy-control-title">
        <h2 id="privacy-control-title" class="text-lg font-semibold text-ink-950">你可以做什么</h2>
        <p class="mt-3 max-w-3xl text-sm leading-7 text-ink-600">
          使用结束后退出登录，并关闭不再使用的标签页。若对某类信息是否必要存在疑问，请先不要提交；你也可以先阅读使用说明，了解怎样在减少个人信息的同时描述事实。
        </p>
        <RouterLink
          to="/guide"
          class="focus-ring mt-5 inline-flex min-h-10 items-center gap-2 rounded-lg text-sm font-semibold text-jade-900 hover:text-jade-700"
        >
          查看使用说明
          <AppIcon name="arrow-right" :size="15" />
        </RouterLink>
      </section>
    </div>
  </div>
</template>
