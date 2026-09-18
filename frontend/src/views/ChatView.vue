<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { storeToRefs } from 'pinia'
import { RouterLink } from 'vue-router'

import AppIcon from '@/components/AppIcon.vue'
import LegalDisclaimer from '@/components/LegalDisclaimer.vue'
import { useChatStore } from '@/stores/chat'
import {
  MAX_CHAT_MESSAGE_LENGTH,
  type ChatMessage,
  type LocalConversationRecord,
} from '@/types/chat'

const chatStore = useChatStore()
const {
  messages,
  draft,
  sessionId,
  conversationRecords,
  deletingConversationKey,
  errorMessage,
  errorCode,
  errorRequestId,
  lastFailedQuestion,
  isSending,
  canSend,
} = storeToRefs(chatStore)

const domainEntries = [
  {
    icon: 'heart',
    title: '婚姻家庭',
    question: '我想咨询婚姻家庭问题，事情经过是：',
  },
  {
    icon: 'briefcase',
    title: '劳动争议',
    question: '我想咨询劳动争议问题，事情经过是：',
  },
  {
    icon: 'car',
    title: '交通事故',
    question: '我想咨询交通事故问题，事情经过是：',
  },
  {
    icon: 'file',
    title: '合同纠纷',
    question: '我想咨询合同纠纷问题，事情经过是：',
  },
]

const intentLabels: Record<string, string> = {
  qa: '法律问答',
  search: '案例检索',
  document: '文书生成',
}

const mobileDomainMenu = ref<HTMLDetailsElement | null>(null)
const mobileHistoryMenu = ref<HTMLDetailsElement | null>(null)

const sessionLabel = computed(() => (sessionId.value ? '当前咨询' : '新咨询'))

function intentLabel(intent?: string): string | null {
  return intent ? (intentLabels[intent] ?? null) : null
}

function displayWarnings(message: ChatMessage): string[] {
  return message.warnings ?? []
}

function submit(): void {
  void chatStore.submitQuestion()
}

function retry(): void {
  void chatStore.retryLastQuestion()
}

function chooseMobileDomain(question: string): void {
  chatStore.useSuggestedQuestion(question)
  if (mobileDomainMenu.value) mobileDomainMenu.value.open = false
}

function chooseMobileConversation(key: string): void {
  chatStore.switchConversation(key)
  if (mobileHistoryMenu.value) mobileHistoryMenu.value.open = false
}

async function requestDeleteConversation(conversation: LocalConversationRecord): Promise<void> {
  const confirmed = window.confirm(`确定删除“${conversation.title}”吗？删除后无法恢复。`)
  if (!confirmed) return
  const deleted = await chatStore.deleteConversation(conversation.key)
  if (deleted && mobileHistoryMenu.value) mobileHistoryMenu.value.open = false
}

onMounted(chatStore.refreshCredentialState)
</script>

<template>
  <div class="mx-auto grid h-[calc(100dvh-4.25rem)] min-h-[34rem] max-w-[94rem] overflow-hidden lg:grid-cols-[19rem_minmax(0,1fr)]">
    <aside class="hidden border-r border-ink-950/8 bg-white/30 p-6 lg:flex lg:min-h-0 lg:flex-col" aria-labelledby="history-title">
      <div>
        <p class="text-xs font-semibold tracking-[0.08em] text-jade-800">个人空间</p>
        <h2 id="history-title" class="mt-1 text-lg font-semibold tracking-[-0.02em] text-ink-950">咨询记录</h2>
      </div>

      <button
        type="button"
        class="focus-ring mt-5 inline-flex min-h-11 w-full items-center justify-center gap-2 rounded-xl bg-ink-950 px-4 text-sm font-semibold text-white transition enabled:hover:bg-jade-900 disabled:cursor-not-allowed disabled:opacity-40"
        :disabled="isSending"
        @click="chatStore.startNewConversation"
      >
        <AppIcon name="plus" :size="17" />
        新建咨询
      </button>

      <div
        v-if="conversationRecords.length"
        class="mt-5 min-h-0 space-y-2 overflow-y-auto"
        data-testid="conversation-history"
      >
        <div
          v-for="conversation in conversationRecords"
          :key="conversation.key"
          class="flex items-center rounded-xl border transition"
          :class="
            conversation.isActive
              ? 'border-jade-800/20 bg-jade-50/70'
              : 'border-ink-950/8 bg-white/55 hover:border-ink-950/15 hover:bg-white/80'
          "
        >
          <button
            type="button"
            class="focus-ring min-w-0 flex-1 rounded-l-xl px-3.5 py-3 text-left"
            :aria-current="conversation.isActive ? 'page' : undefined"
            :disabled="isSending || Boolean(deletingConversationKey)"
            @click="chatStore.switchConversation(conversation.key)"
          >
            <span class="block truncate text-xs font-semibold text-ink-900">
              {{ conversation.title }}
            </span>
            <span class="mt-1 block text-[10px] text-ink-600">
              {{ conversation.isActive ? '当前咨询' : `${conversation.messages.length} 条消息` }}
            </span>
          </button>
          <button
            type="button"
            class="focus-ring mr-2 grid size-8 shrink-0 place-items-center rounded-lg text-ink-500 transition hover:bg-red-50 hover:text-red-800 disabled:cursor-not-allowed disabled:opacity-35"
            :aria-label="`删除咨询：${conversation.title}`"
            :title="`删除咨询：${conversation.title}`"
            :disabled="isSending || Boolean(deletingConversationKey)"
            @click="requestDeleteConversation(conversation)"
          >
            <AppIcon name="trash" :size="15" />
          </button>
        </div>
      </div>

      <div v-else class="mt-5 rounded-xl border border-ink-950/8 bg-white/55 p-3.5">
        <p class="text-xs font-semibold text-ink-900">暂无咨询记录</p>
        <p class="mt-1.5 text-xs leading-5 text-ink-600">选择一个问题类型，开始新的咨询。</p>
      </div>

      <p class="mt-3 text-[10px] leading-4 text-ink-500">记录仅保留在当前页面，刷新后会清空。</p>

      <div class="mt-7">
        <p class="text-xs font-semibold tracking-[0.08em] text-ink-600">常见问题类型</p>
        <div class="mt-3 grid gap-2">
          <button
            v-for="entry in domainEntries"
            :key="entry.title"
            type="button"
            class="focus-ring flex min-h-11 items-center gap-3 rounded-xl border border-transparent px-3 py-2.5 text-left text-xs font-medium text-ink-600 transition hover:border-ink-950/8 hover:bg-white/70 hover:text-ink-950 disabled:cursor-not-allowed disabled:opacity-45"
            :disabled="isSending"
            @click="chatStore.useSuggestedQuestion(entry.question)"
          >
            <span class="grid size-8 shrink-0 place-items-center rounded-lg bg-moss-100 text-jade-800">
              <AppIcon :name="entry.icon" :size="15" />
            </span>
            {{ entry.title }}
          </button>
        </div>
      </div>

      <div class="mt-auto border-t border-ink-950/8 pt-5">
        <div class="flex items-start gap-2.5 text-xs leading-5 text-ink-600">
          <AppIcon name="lock" :size="15" class="mt-0.5 shrink-0" />
          <p>请勿输入身份证号、银行卡号或完整住址等非必要敏感信息。</p>
        </div>
      </div>
    </aside>

    <section class="flex min-h-0 min-w-0 flex-col bg-paper" aria-labelledby="chat-title">
      <header class="flex shrink-0 items-center justify-between border-b border-ink-950/8 px-5 py-3.5 sm:px-8">
        <div>
          <h1 id="chat-title" class="text-sm font-semibold text-ink-950">法律咨询</h1>
          <p class="mt-0.5 text-[11px] text-ink-600">{{ sessionLabel }}</p>
        </div>
        <span
          class="inline-flex items-center gap-2 rounded-full border border-ink-950/8 bg-white/60 px-3 py-1.5 text-[10px] font-semibold text-ink-600"
        >
          <span :class="isSending ? 'animate-pulse bg-jade-500' : 'bg-jade-500'" class="size-1.5 rounded-full" />
          {{ isSending ? '正在生成' : '在线' }}
        </span>
      </header>

      <div class="flex shrink-0 items-center gap-2 border-b border-ink-950/8 bg-white/28 px-4 py-2.5 lg:hidden">
        <button
          type="button"
          class="focus-ring inline-flex min-h-10 items-center gap-2 rounded-xl bg-ink-950 px-3.5 text-xs font-semibold text-white disabled:opacity-40"
          :disabled="isSending"
          @click="chatStore.startNewConversation"
        >
          <AppIcon name="plus" :size="15" />
          新建咨询
        </button>
        <details v-if="conversationRecords.length" ref="mobileHistoryMenu" class="relative">
          <summary class="focus-ring flex min-h-10 list-none items-center rounded-xl border border-ink-950/8 bg-white/65 px-3 text-xs font-semibold text-ink-700 [&::-webkit-details-marker]:hidden">
            记录
          </summary>
          <div class="absolute left-0 z-20 mt-2 grid w-72 gap-1.5 rounded-2xl border border-ink-950/10 bg-paper p-2 shadow-[0_16px_45px_rgba(18,33,29,0.16)]">
            <div
              v-for="conversation in conversationRecords"
              :key="conversation.key"
              class="flex items-center rounded-xl text-xs transition"
              :class="conversation.isActive ? 'bg-jade-50 text-ink-950' : 'bg-white/65 text-ink-700'"
            >
              <button
                type="button"
                class="focus-ring min-w-0 flex-1 rounded-l-xl px-3 py-2.5 text-left"
                :disabled="isSending || Boolean(deletingConversationKey)"
                @click="chooseMobileConversation(conversation.key)"
              >
                <span class="block truncate font-medium">{{ conversation.title }}</span>
                <span class="mt-1 block text-[10px] text-ink-500">
                  {{ conversation.isActive ? '当前咨询' : `${conversation.messages.length} 条消息` }}
                </span>
              </button>
              <button
                type="button"
                class="focus-ring mr-1 grid size-8 shrink-0 place-items-center rounded-lg text-ink-500 hover:bg-red-50 hover:text-red-800 disabled:opacity-35"
                :aria-label="`删除咨询：${conversation.title}`"
                :disabled="isSending || Boolean(deletingConversationKey)"
                @click="requestDeleteConversation(conversation)"
              >
                <AppIcon name="trash" :size="14" />
              </button>
            </div>
          </div>
        </details>
        <details ref="mobileDomainMenu" class="relative ml-auto">
          <summary class="focus-ring flex min-h-10 list-none items-center rounded-xl border border-ink-950/8 bg-white/65 px-3.5 text-xs font-semibold text-ink-700 [&::-webkit-details-marker]:hidden">
            问题类型
          </summary>
          <div class="absolute right-0 z-20 mt-2 grid w-64 grid-cols-2 gap-2 rounded-2xl border border-ink-950/10 bg-paper p-2 shadow-[0_16px_45px_rgba(18,33,29,0.16)]">
            <button
              v-for="entry in domainEntries"
              :key="entry.title"
              type="button"
              class="focus-ring flex min-h-11 items-center gap-2 rounded-xl bg-white/65 px-3 text-left text-xs font-medium text-ink-700 disabled:opacity-40"
              :disabled="isSending"
              @click="chooseMobileDomain(entry.question)"
            >
              <AppIcon :name="entry.icon" :size="14" class="shrink-0 text-jade-800" />
              {{ entry.title }}
            </button>
          </div>
        </details>
      </div>

      <div class="min-h-0 flex-1 overflow-y-auto px-5 py-6 sm:px-8 lg:px-12">
        <div
          v-if="messages.length === 0 && !isSending"
          class="mx-auto flex min-h-full max-w-xl flex-col items-center justify-center py-8 text-center"
        >
          <div class="grid size-14 place-items-center rounded-2xl border border-ink-950/8 bg-white text-jade-800 shadow-sm">
            <AppIcon name="message" :size="25" />
          </div>
          <p class="mt-6 text-xs font-semibold tracking-[0.08em] text-jade-800">从事实开始</p>
          <h2 class="mt-2 text-2xl font-semibold tracking-[-0.035em] text-ink-950">先把事情讲清楚</h2>
          <p class="mt-3 max-w-md text-sm leading-7 text-ink-600">
            可以从发生时间、相关人物、已有材料和希望解决的问题开始。
          </p>
        </div>

        <div v-else class="mx-auto max-w-3xl space-y-7" role="log" aria-live="polite" aria-relevant="additions text">
          <article
            v-for="message in messages"
            :key="message.id"
            class="flex min-w-0 gap-3 sm:gap-4"
            :class="message.role === 'user' ? 'justify-end' : 'justify-start'"
          >
            <div
              v-if="message.role === 'assistant'"
              class="grid size-8 shrink-0 place-items-center rounded-xl bg-ink-950 font-serif text-xs text-white"
              aria-hidden="true"
            >
              衡
            </div>
            <div
              class="min-w-0 max-w-[88%] rounded-2xl px-4 py-3.5 text-sm leading-7 sm:max-w-[78%] sm:px-5"
              :class="
                message.role === 'user'
                  ? 'rounded-tr-md bg-ink-950 text-white'
                  : 'rounded-tl-md border border-ink-950/8 bg-white text-ink-700 shadow-sm'
              "
            >
              <div v-if="message.role === 'assistant'" class="mb-2 flex items-center gap-2">
                <span class="rounded-md bg-jade-50 px-2 py-0.5 text-[10px] font-semibold tracking-[0.06em] text-jade-800">
                  AI 回答
                </span>
                <span v-if="intentLabel(message.intent)" class="text-[10px] text-ink-600">
                  {{ intentLabel(message.intent) }}
                </span>
              </div>
              <p class="whitespace-pre-wrap [overflow-wrap:anywhere]">{{ message.content }}</p>

              <div v-if="message.task && message === messages[messages.length - 1] && !['completed', 'cancelled'].includes(message.task.phase)" class="mt-3 flex flex-wrap gap-2" aria-label="任务操作">
                <button v-if="message.task.phase === 'review'" type="button" class="focus-ring rounded-lg bg-jade-800 px-3 py-2 text-xs text-white" :disabled="isSending" @click="chatStore.submitTaskAction('confirm', message.task.revision)">确认摘要并生成草稿</button>
                <template v-if="message.task.phase === 'conflict'">
                  <button type="button" class="focus-ring rounded-lg border px-3 py-2 text-xs" :disabled="isSending" @click="chatStore.submitTaskAction('accept_changes', message.task.revision)">采用本次修改</button>
                  <button type="button" class="focus-ring rounded-lg border px-3 py-2 text-xs" :disabled="isSending" @click="chatStore.submitTaskAction('reject_changes', message.task.revision)">保留原值</button>
                </template>
                <button type="button" class="focus-ring rounded-lg border px-3 py-2 text-xs" :disabled="isSending" @click="chatStore.submitTaskAction('cancel', message.task.revision)">取消当前任务</button>
              </div>

              <section
                v-if="message.role === 'assistant'"
                class="mt-4 border-t border-ink-950/8 pt-3 text-[11px] leading-5 text-ink-600"
                aria-label="依据与提示"
              >
                <p class="font-semibold text-ink-700">依据与提示</p>
                <p v-if="message.sourceCount === 0" class="mt-1.5">
                  暂未附可核验的参考依据，请先自行核对原始材料。
                </p>
                <p v-else-if="message.sourceCount" class="mt-1.5">
                  已附 {{ message.sourceCount }} 条{{ message.hasDemoSources ? '参考材料，包含演示数据，不是真实判例或法律依据' : '参考材料，请核对原始来源' }}。
                </p>
                <details v-for="source in message.sources" :key="source.source_id" class="mt-2 rounded-lg border border-ink-950/10 p-3">
                  <summary class="cursor-pointer font-semibold">[{{ source.citation_id }}] {{ source.title }} · {{ source.reference_number }}{{ source.is_demo ? '（演示参考）' : '（官方条文）' }}</summary>
                  <template v-if="source.source_type === 'legal_provision'">
                    <p class="mt-2">{{ source.version }} · 生效日期：{{ source.effective_from }}{{ source.effective_until ? `，失效边界：${source.effective_until}` : '' }}</p>
                    <p>核验日期：{{ source.verified_at }}；有效状态资料截至：{{ source.status_as_of }}。本次未实时联网核验。</p>
                    <p>{{ source.applicability === 'general_reference' ? '一般规则参考' : '事件时间候选依据，仍须审查具体适用条件' }}</p>
                    <blockquote class="my-2 whitespace-pre-wrap border-l-2 border-jade-700/30 pl-3">{{ source.original_text }}</blockquote>
                    <a v-if="source.source_url" :href="source.source_url" target="_blank" rel="noopener noreferrer" class="focus-ring underline">查看官方原文（{{ source.publisher }}）</a>
                  </template>
                  <p v-else class="mt-2">合成场景仅用于演示，样本日期 {{ source.sample_date }} 不是裁判日期。</p>
                </details>
                <ul v-if="displayWarnings(message).length" class="mt-1.5 space-y-1.5">
                  <li v-for="warning in displayWarnings(message)" :key="warning">
                    {{ warning }}
                  </li>
                </ul>
              </section>
            </div>
          </article>

          <article v-if="isSending" class="flex gap-3 sm:gap-4" data-testid="sending-indicator">
            <div class="grid size-8 shrink-0 place-items-center rounded-xl bg-ink-950 font-serif text-xs text-white" aria-hidden="true">
              衡
            </div>
            <div class="rounded-2xl rounded-tl-md border border-ink-950/8 bg-white px-4 py-3.5 shadow-sm sm:px-5">
              <div class="flex items-center gap-2 text-xs text-ink-600">
                <span class="size-1.5 animate-pulse rounded-full bg-jade-500" />
                正在生成回答，通常需要几秒钟……
              </div>
            </div>
          </article>
        </div>

        <div
          v-if="errorMessage"
          class="mx-auto mt-6 max-w-3xl rounded-2xl border border-red-900/10 bg-red-50/75 p-4 text-sm text-red-950"
          role="alert"
          data-testid="chat-error"
        >
          <div class="flex items-start justify-between gap-4">
            <div>
              <p class="font-semibold">本次操作未完成</p>
              <p class="mt-1.5 leading-6 text-red-950/75">{{ errorMessage }}</p>
              <p v-if="errorRequestId" class="mt-2 text-[10px] text-red-950/60">
                请求编号：{{ errorRequestId }}
              </p>
            </div>
            <RouterLink
              v-if="errorCode === 'AUTH_REQUIRED'"
              to="/auth?redirect=/chat"
              class="focus-ring shrink-0 rounded-lg border border-red-950/10 bg-white/70 px-3 py-2 text-xs font-semibold text-red-900 transition hover:bg-white"
            >
              重新登录
            </RouterLink>
            <button
              v-else-if="lastFailedQuestion"
              type="button"
              class="focus-ring shrink-0 rounded-lg border border-red-950/10 bg-white/70 px-3 py-2 text-xs font-semibold text-red-900 transition hover:bg-white disabled:cursor-not-allowed disabled:opacity-40"
              :disabled="isSending"
              @click="retry"
            >
              重试
            </button>
          </div>
        </div>
      </div>

      <div
        class="shrink-0 border-t border-ink-950/8 bg-white/42 px-4 pt-3 sm:px-8 sm:pt-4 lg:px-12"
        style="padding-bottom: max(0.75rem, env(safe-area-inset-bottom))"
      >
        <div class="mx-auto max-w-3xl">
          <form
            class="rounded-2xl border border-ink-950/10 bg-white p-2 shadow-[0_14px_40px_rgba(18,33,29,0.08)] transition focus-within:border-jade-700/35 focus-within:shadow-[0_18px_45px_rgba(18,33,29,0.11)]"
            @submit.prevent="submit"
          >
            <label for="legal-question" class="sr-only">描述你的法律问题</label>
            <textarea
              id="legal-question"
              v-model="draft"
              rows="2"
              :maxlength="MAX_CHAT_MESSAGE_LENGTH"
              class="min-h-18 w-full resize-none bg-transparent px-3 py-2 text-sm leading-6 text-ink-900 outline-none placeholder:text-ink-500"
              placeholder="描述发生了什么，以及你希望解决的问题……"
              aria-describedby="composer-help composer-count composer-disclaimer"
              :aria-invalid="errorCode === 'VALIDATION_ERROR'"
              @keydown.ctrl.enter.prevent="submit"
              @keydown.meta.enter.prevent="submit"
            />
            <div class="flex items-center justify-between gap-3 px-2 pb-1">
              <p id="composer-help" class="sr-only text-[11px] text-ink-600 sm:not-sr-only">
                Ctrl / ⌘ + Enter 发送
              </p>
              <p
                id="composer-count"
                class="text-[10px] tabular-nums"
                :class="draft.length > 3800 ? 'text-amber-800' : 'text-ink-400'"
              >
                {{ draft.length }} / {{ MAX_CHAT_MESSAGE_LENGTH }}
              </p>
              <button
                type="submit"
                class="focus-ring ml-auto inline-flex min-h-10 items-center gap-2 rounded-xl bg-ink-950 px-4 text-xs font-semibold text-white transition enabled:hover:bg-jade-900 disabled:cursor-not-allowed disabled:opacity-35"
                :disabled="!canSend"
              >
                {{ isSending ? '生成中' : '发送咨询' }}
                <AppIcon name="send" :size="15" />
              </button>
            </div>
          </form>
          <LegalDisclaimer id="composer-disclaimer" class="mt-2.5" />
          <p class="mt-1.5 text-center text-[11px] leading-5 text-ink-600 lg:hidden">
            请勿提交身份证号、银行卡号或完整住址等非必要敏感信息。
          </p>
        </div>
      </div>
    </section>
  </div>
</template>
