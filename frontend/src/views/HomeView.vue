<script setup lang="ts">
import { computed, ref } from 'vue'
import { RouterLink, useRouter } from 'vue-router'

import AppIcon from '@/components/AppIcon.vue'
import { useChatStore } from '@/stores/chat'
import { MAX_CHAT_MESSAGE_LENGTH } from '@/types/chat'

const router = useRouter()
const chatStore = useChatStore()
const question = ref('')

const domains = [
  {
    number: '01',
    icon: 'heart',
    title: '婚姻家庭',
    description: '婚姻关系、子女抚养与财产分割等常见问题。',
    prompt: '我想咨询婚姻家庭问题，事情经过是：',
  },
  {
    number: '02',
    icon: 'briefcase',
    title: '劳动争议',
    description: '劳动合同、薪酬、工伤与解除关系等事项。',
    prompt: '我想咨询劳动争议问题，事情经过是：',
  },
  {
    number: '03',
    icon: 'car',
    title: '交通事故',
    description: '责任认定、损害赔偿与证据准备等信息。',
    prompt: '我想咨询交通事故问题，事情经过是：',
  },
  {
    number: '04',
    icon: 'file',
    title: '合同纠纷',
    description: '合同履行、违约责任与争议解决等场景。',
    prompt: '我想咨询合同纠纷问题，事情经过是：',
  },
]

const principles = [
  ['01', '说明事实', '按时间顺序讲清人物、行为与已有材料。'],
  ['02', '核对依据', '重要结论要回到法规、合同或证据原文。'],
  ['03', '审慎行动', '涉及期限和重大权益时及时寻求专业帮助。'],
]

const featureEntries = [
  {
    icon: 'message',
    title: '法律咨询',
    description: '梳理事实、法律关系、所需材料和下一步。',
    available: true,
  },
  {
    icon: 'search',
    title: '案例检索',
    description: '按领域和关键事实查找可核验的参考资料。',
    available: false,
  },
  {
    icon: 'file',
    title: '文书生成',
    description: '根据结构化信息生成可复核的法律文书草稿。',
    available: false,
  },
]

const canStart = computed(() => {
  const length = question.value.trim().length
  return length > 0 && length <= MAX_CHAT_MESSAGE_LENGTH
})

function startConsultation(seed = question.value): void {
  const normalized = seed.trim()
  if (!normalized) return
  chatStore.useSuggestedQuestion(normalized)
  void router.push({ name: 'chat' })
}
</script>

<template>
  <div class="overflow-hidden">
    <section class="hero-grid relative border-b border-ink-950/8">
      <div
        class="pointer-events-none absolute -top-40 right-[-12rem] size-[34rem] rounded-full bg-jade-300/18 blur-3xl"
        aria-hidden="true"
      />
      <div
        class="relative mx-auto grid max-w-7xl gap-10 px-5 py-14 sm:px-8 sm:py-18 lg:grid-cols-[1.2fr_0.8fr] lg:items-center lg:px-10 lg:py-20"
      >
        <div class="reveal-up max-w-3xl">
          <div
            class="mb-6 inline-flex items-center gap-2 rounded-full border border-jade-800/14 bg-jade-50/80 px-3.5 py-2 text-[11px] font-semibold tracking-[0.08em] text-jade-900"
          >
            <span class="size-1.5 rounded-full bg-jade-500" />
            中国大陆法律信息助手
          </div>
          <h1
            class="max-w-3xl text-[2.65rem] leading-[1.12] font-semibold tracking-[-0.045em] text-balance text-ink-950 sm:text-6xl lg:text-[4.2rem]"
          >
            让复杂的法律问题，<br class="hidden sm:block" />先变得清晰。
          </h1>
          <p class="mt-6 max-w-2xl text-base leading-8 text-ink-600 sm:text-lg sm:leading-9">
            描述事情经过，我会帮你梳理法律关系、所需材料和下一步。
          </p>

          <form class="mt-8 max-w-2xl" @submit.prevent="startConsultation()">
            <div
              class="rounded-2xl border border-ink-950/10 bg-white/90 p-2 shadow-[0_18px_55px_rgba(18,33,29,0.10)] transition focus-within:border-jade-700/35 focus-within:shadow-[0_22px_60px_rgba(18,33,29,0.13)]"
            >
              <label class="sr-only" for="home-question">描述你的法律问题</label>
              <textarea
                id="home-question"
                v-model="question"
                rows="2"
                :maxlength="MAX_CHAT_MESSAGE_LENGTH"
                class="min-h-24 w-full resize-none bg-transparent px-3 py-3 text-sm leading-7 text-ink-950 outline-none placeholder:text-ink-500 sm:text-base"
                placeholder="例如：公司拖欠两个月工资，我已经多次沟通但没有结果……"
                aria-describedby="home-question-help"
              />
              <div class="flex flex-col gap-3 border-t border-ink-950/8 px-2 pt-2 pb-1 sm:flex-row sm:items-center">
                <p id="home-question-help" class="text-xs leading-5 text-ink-600">
                  进入咨询后仍可补充和修改，请勿填写无关敏感信息。
                </p>
                <button
                  type="submit"
                  class="focus-ring inline-flex min-h-11 shrink-0 items-center justify-center gap-2 rounded-xl bg-ink-950 px-5 text-sm font-semibold text-white transition enabled:hover:bg-jade-900 disabled:cursor-not-allowed disabled:opacity-40 sm:ml-auto"
                  :disabled="!canStart"
                >
                  开始梳理
                  <AppIcon name="arrow-right" :size="16" />
                </button>
              </div>
            </div>
          </form>

          <RouterLink
            to="/guide"
            class="focus-ring mt-4 inline-flex rounded-lg text-xs font-medium text-ink-600 underline decoration-ink-300 underline-offset-4 transition hover:text-ink-950"
          >
            查看使用说明
          </RouterLink>
        </div>

        <aside class="reveal-up relative lg:justify-self-end" style="animation-delay: 90ms" aria-labelledby="clarity-title">
          <div
            class="absolute -inset-3 translate-x-3 translate-y-3 rounded-[1.7rem] border border-ink-950/8"
            aria-hidden="true"
          />
          <div
            class="relative max-w-md rounded-[1.55rem] border border-ink-950/10 bg-white/82 p-5 shadow-[0_28px_70px_rgba(18,33,29,0.10)] backdrop-blur sm:p-7"
          >
            <p class="text-xs font-semibold tracking-[0.08em] text-jade-800">获得清晰回答</p>
            <h2 id="clarity-title" class="mt-2 text-xl font-semibold tracking-[-0.02em] text-ink-950">
              从事实开始，逐步判断
            </h2>
            <ol class="mt-4 grid grid-cols-3 gap-2 sm:block sm:divide-y sm:divide-ink-950/8">
              <li
                v-for="principle in principles"
                :key="principle[0]"
                class="rounded-xl bg-moss-100/65 p-3 sm:flex sm:gap-4 sm:rounded-none sm:bg-transparent sm:px-0 sm:py-4 sm:first:pt-2 sm:last:pb-0"
              >
                <span class="step-number">{{ principle[0] }}</span>
                <div class="mt-3 sm:mt-0">
                  <p class="text-xs font-semibold text-ink-900 sm:text-sm">{{ principle[1] }}</p>
                  <p class="mt-1 hidden text-sm leading-6 text-ink-600 sm:block">{{ principle[2] }}</p>
                </div>
              </li>
            </ol>
          </div>
        </aside>
      </div>
    </section>

    <section id="functions" class="mx-auto max-w-7xl px-5 py-14 sm:px-8 sm:py-16 lg:px-10" aria-labelledby="function-title">
      <div>
        <p class="section-kicker">功能入口</p>
        <h2 id="function-title" class="section-title">从你要完成的事情开始</h2>
      </div>

      <div class="mt-8 grid grid-cols-2 gap-3 md:grid-cols-3">
        <template v-for="entry in featureEntries" :key="entry.title">
          <RouterLink
            v-if="entry.available"
            to="/chat"
            class="focus-ring group col-span-2 rounded-2xl border border-ink-950/8 bg-white/62 p-5 transition hover:-translate-y-1 hover:border-jade-800/18 hover:bg-white hover:shadow-[0_18px_45px_rgba(18,33,29,0.08)] md:col-span-1"
          >
            <div class="flex items-start justify-between gap-4">
              <span class="grid size-11 place-items-center rounded-xl bg-jade-100 text-jade-800">
                <AppIcon :name="entry.icon" :size="20" />
              </span>
              <AppIcon name="arrow-right" :size="17" class="mt-2 text-ink-400 transition group-hover:translate-x-0.5 group-hover:text-jade-800" />
            </div>
            <h3 class="mt-6 text-lg font-semibold text-ink-950">{{ entry.title }}</h3>
            <p class="mt-2 text-sm leading-6 text-ink-600">{{ entry.description }}</p>
          </RouterLink>

          <article v-else class="rounded-2xl border border-ink-950/8 bg-white/42 p-4 sm:p-5">
            <div class="flex items-start justify-between gap-4">
              <span class="grid size-11 place-items-center rounded-xl bg-moss-100 text-ink-600">
                <AppIcon :name="entry.icon" :size="20" />
              </span>
              <span class="rounded-full bg-ink-950/5 px-2.5 py-1 text-[10px] font-semibold text-ink-600">即将开放</span>
            </div>
            <h3 class="mt-6 text-lg font-semibold text-ink-950">{{ entry.title }}</h3>
            <p class="mt-2 text-sm leading-6 text-ink-600">{{ entry.description }}</p>
          </article>
        </template>
      </div>
    </section>

    <section class="border-t border-ink-950/8 bg-white/30" aria-labelledby="domain-title">
      <div class="mx-auto max-w-7xl px-5 py-14 sm:px-8 sm:py-16 lg:px-10">
        <div class="flex flex-col justify-between gap-4 md:flex-row md:items-end">
          <div>
            <p class="section-kicker">支持领域</p>
            <h2 id="domain-title" class="section-title">四类常见民事问题</h2>
          </div>
          <p class="max-w-lg text-sm leading-7 text-ink-600">
            选择问题类型后补充事实；范围之外的问题会提示当前能力边界。
          </p>
        </div>

        <div class="mt-8 grid grid-cols-2 gap-3 lg:grid-cols-4">
          <button
            v-for="domain in domains"
            :key="domain.title"
            type="button"
            class="focus-ring group rounded-2xl border border-ink-950/8 bg-white/62 p-4 text-left transition hover:-translate-y-1 hover:border-jade-800/18 hover:bg-white hover:shadow-[0_18px_45px_rgba(18,33,29,0.08)] sm:p-5"
            :aria-label="`咨询${domain.title}问题`"
            @click="startConsultation(domain.prompt)"
          >
            <div class="flex items-center justify-between">
              <span class="grid size-10 place-items-center rounded-xl bg-moss-100 text-jade-800 transition group-hover:bg-jade-800 group-hover:text-white">
                <AppIcon :name="domain.icon" :size="19" />
              </span>
              <span class="font-mono text-[10px] tracking-[0.15em] text-ink-400">{{ domain.number }}</span>
            </div>
            <h3 class="mt-6 text-lg font-semibold tracking-[-0.02em] text-ink-950">{{ domain.title }}</h3>
            <p class="mt-2 text-xs leading-5 text-ink-600 sm:text-sm sm:leading-6">{{ domain.description }}</p>
          </button>
        </div>
      </div>
    </section>
  </div>
</template>
