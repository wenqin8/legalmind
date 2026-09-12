<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { storeToRefs } from 'pinia'

import AppIcon from '@/components/AppIcon.vue'
import LegalDisclaimer from '@/components/LegalDisclaimer.vue'
import { useChatStore } from '@/stores/chat'
import { MAX_CHAT_MESSAGE_LENGTH } from '@/types/chat'

const chatStore = useChatStore()
const {
  messages,
  draft,
  sessionId,
  errorMessage,
  errorCode,
  errorRequestId,
  lastFailedQuestion,
  hasCredential,
  isSending,
  canSend,
} = storeToRefs(chatStore)

const prompts = [
  '公司拖欠工资，我应当先准备哪些材料？',
  '发生交通事故后，赔偿项目通常有哪些？',
  '合同约定不明确时，应当如何整理争议事实？',
]

const sessionLabel = computed(() =>
  sessionId.value ? `会话 ${sessionId.value.slice(0, 8)}` : '发送首个问题后创建会话',
)

function submit(): void {
  void chatStore.submitQuestion()
}

function retry(): void {
  void chatStore.retryLastQuestion()
}

onMounted(chatStore.refreshCredentialState)
</script>

<template>
  <div class="mx-auto grid min-h-[calc(100vh-8.5rem)] max-w-[94rem] lg:grid-cols-[19rem_minmax(0,1fr)]">
    <aside class="border-b border-ink-950/8 bg-white/30 p-5 sm:p-7 lg:border-r lg:border-b-0 lg:p-6">
      <div class="flex items-center justify-between">
        <div>
          <p class="text-[10px] font-semibold tracking-[0.16em] text-ink-400 uppercase">Workspace</p>
          <h1 class="mt-1 text-lg font-semibold tracking-[-0.02em] text-ink-950">咨询工作台</h1>
        </div>
        <button
          v-if="messages.length"
          type="button"
          class="focus-ring grid size-10 place-items-center rounded-xl border border-ink-950/8 bg-white/60 text-ink-500 transition hover:bg-white hover:text-ink-950 disabled:cursor-not-allowed disabled:opacity-40"
          aria-label="清空当前对话"
          title="清空对话"
          :disabled="isSending"
          @click="chatStore.clearConversation"
        >
          <AppIcon name="reset" :size="17" />
        </button>
      </div>

      <div
        class="mt-6 rounded-2xl border p-4"
        :class="
          hasCredential
            ? 'border-jade-800/12 bg-jade-50/70'
            : 'border-amber-700/12 bg-amber-50/70'
        "
      >
        <div
          class="flex items-center gap-2 text-xs font-semibold"
          :class="hasCredential ? 'text-jade-900' : 'text-amber-900'"
        >
          <span
            class="size-1.5 rounded-full"
            :class="hasCredential ? 'bg-jade-500' : 'bg-amber-500'"
          />
          {{ hasCredential ? '已登录，可提交咨询' : '等待登录会话' }}
        </div>
        <p class="mt-2 text-xs leading-5" :class="hasCredential ? 'text-jade-950/62' : 'text-amber-950/65'">
          {{
            hasCredential
              ? '问题将发送至本地后端，并由当前配置的模型生成回答。'
              : '业务接口要求登录。未取得访问令牌时，页面不会提交你的问题。'
          }}
        </p>
      </div>

      <div class="mt-8">
        <p class="text-[11px] font-semibold tracking-[0.12em] text-ink-400 uppercase">建议问题</p>
        <div class="mt-3 grid gap-2 sm:grid-cols-3 lg:grid-cols-1">
          <button
            v-for="prompt in prompts"
            :key="prompt"
            type="button"
            class="focus-ring min-h-11 rounded-xl border border-transparent px-3 py-2.5 text-left text-xs leading-5 text-ink-600 transition hover:border-ink-950/8 hover:bg-white/70 hover:text-ink-950 disabled:cursor-not-allowed disabled:opacity-45"
            :disabled="isSending"
            @click="chatStore.useSuggestedQuestion(prompt)"
          >
            {{ prompt }}
          </button>
        </div>
      </div>

      <div class="mt-8 hidden border-t border-ink-950/8 pt-5 lg:block">
        <div class="flex items-start gap-2.5 text-xs leading-5 text-ink-400">
          <AppIcon name="lock" :size="15" class="mt-0.5 shrink-0" />
          <p>请勿输入身份证号、银行卡号或完整住址等非必要敏感信息。</p>
        </div>
      </div>
    </aside>

    <section class="flex min-w-0 flex-col bg-paper" aria-labelledby="chat-title">
      <header class="flex items-center justify-between border-b border-ink-950/8 px-5 py-4 sm:px-8">
        <div>
          <h2 id="chat-title" class="text-sm font-semibold text-ink-950">法律咨询</h2>
          <p class="mt-0.5 text-[11px] text-ink-400" :title="sessionId ?? undefined">
            {{ sessionLabel }}
          </p>
        </div>
        <span
          class="inline-flex items-center gap-2 rounded-full border border-ink-950/8 bg-white/60 px-3 py-1.5 text-[10px] font-semibold tracking-[0.11em] text-ink-500 uppercase"
        >
          <span v-if="isSending" class="size-1.5 animate-pulse rounded-full bg-jade-500" />
          {{ isSending ? '模型生成中' : '同步问答' }}
        </span>
      </header>

      <div
        class="flex-1 overflow-y-auto px-5 py-8 sm:px-8 lg:px-12"
        aria-live="polite"
        :aria-busy="isSending"
      >
        <div
          v-if="messages.length === 0 && !isSending"
          class="mx-auto flex min-h-[25rem] max-w-xl flex-col items-center justify-center text-center"
        >
          <div class="grid size-14 place-items-center rounded-2xl border border-ink-950/8 bg-white text-jade-800 shadow-sm">
            <AppIcon name="message" :size="25" />
          </div>
          <p class="mt-6 text-[11px] font-semibold tracking-[0.16em] text-jade-800 uppercase">Start with context</p>
          <h3 class="mt-2 text-2xl font-semibold tracking-[-0.035em] text-ink-950">先把事情讲清楚</h3>
          <p class="mt-3 max-w-md text-sm leading-7 text-ink-500">
            可以从发生时间、相关人物、已有材料和希望解决的问题开始。回答由 AI 生成，请自行核对法律依据。
          </p>
        </div>

        <div v-else class="mx-auto max-w-3xl space-y-7">
          <article
            v-for="message in messages"
            :key="message.id"
            class="flex gap-3 sm:gap-4"
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
              class="max-w-[86%] rounded-2xl px-4 py-3.5 text-sm leading-7 sm:max-w-[78%] sm:px-5"
              :class="
                message.role === 'user'
                  ? 'rounded-tr-md bg-ink-950 text-white'
                  : 'rounded-tl-md border border-ink-950/8 bg-white text-ink-700 shadow-sm'
              "
            >
              <div v-if="message.role === 'assistant'" class="mb-2 flex items-center gap-2">
                <span class="rounded-md bg-jade-50 px-2 py-0.5 text-[10px] font-semibold tracking-[0.08em] text-jade-800">
                  AI 回答
                </span>
                <span class="text-[10px] text-ink-400">{{ message.intent ?? 'qa' }}</span>
              </div>
              <p class="whitespace-pre-wrap [overflow-wrap:anywhere]">{{ message.content }}</p>

              <div
                v-if="message.role === 'assistant'"
                class="mt-4 space-y-2 border-t border-ink-950/8 pt-3 text-[11px] leading-5 text-ink-400"
              >
                <p v-if="message.sourceCount === 0">
                  本次回答未附带可核验来源，请勿将其直接作为法律依据。
                </p>
                <p v-else-if="message.sourceCount">
                  后端返回 {{ message.sourceCount }} 条来源；来源详情将在检索模块接入后展示。
                </p>
                <p
                  v-for="warning in message.warnings ?? []"
                  :key="warning"
                  class="text-amber-800"
                >
                  {{ warning }}
                </p>
              </div>
            </div>
          </article>

          <article v-if="isSending" class="flex gap-3 sm:gap-4" data-testid="sending-indicator">
            <div class="grid size-8 shrink-0 place-items-center rounded-xl bg-ink-950 font-serif text-xs text-white" aria-hidden="true">
              衡
            </div>
            <div class="rounded-2xl rounded-tl-md border border-ink-950/8 bg-white px-4 py-3.5 shadow-sm sm:px-5">
              <div class="flex items-center gap-2 text-xs text-ink-500">
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
              <p class="font-semibold">本次请求未完成</p>
              <p class="mt-1.5 leading-6 text-red-950/70">{{ errorMessage }}</p>
              <p v-if="errorRequestId" class="mt-2 text-[10px] text-red-950/45">
                请求编号：{{ errorRequestId }}
              </p>
            </div>
            <a
              v-if="errorCode === 'AUTH_REQUIRED'"
              href="/auth?redirect=/chat"
              class="focus-ring shrink-0 rounded-lg border border-red-950/10 bg-white/70 px-3 py-2 text-xs font-semibold text-red-900 transition hover:bg-white"
            >
              重新登录
            </a>
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

      <div class="border-t border-ink-950/8 bg-white/38 px-4 py-4 sm:px-8 sm:py-5 lg:px-12">
        <div class="mx-auto max-w-3xl">
          <form
            class="rounded-2xl border border-ink-950/10 bg-white p-2 shadow-[0_14px_40px_rgba(18,33,29,0.08)] transition focus-within:border-jade-700/35 focus-within:shadow-[0_18px_45px_rgba(18,33,29,0.11)]"
            @submit.prevent="submit"
          >
            <label for="legal-question" class="sr-only">描述你的法律问题</label>
            <textarea
              id="legal-question"
              v-model="draft"
              rows="3"
              :maxlength="MAX_CHAT_MESSAGE_LENGTH"
              class="min-h-20 w-full resize-none bg-transparent px-3 py-2 text-sm leading-6 text-ink-900 outline-none placeholder:text-ink-500"
              placeholder="描述发生了什么，以及你希望解决的问题……"
              aria-describedby="composer-help composer-count"
              :aria-invalid="errorCode === 'VALIDATION_ERROR'"
              @keydown.ctrl.enter.prevent="submit"
              @keydown.meta.enter.prevent="submit"
            />
            <div class="flex items-center justify-between gap-3 px-2 pb-1">
              <p id="composer-help" class="sr-only text-[11px] text-ink-400 sm:not-sr-only">
                Ctrl / ⌘ + Enter 发送
              </p>
              <p
                id="composer-count"
                class="text-[10px] tabular-nums"
                :class="draft.length > 3800 ? 'text-amber-800' : 'text-ink-300'"
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
          <LegalDisclaimer class="mt-3" />
          <p class="mt-2 text-center text-[11px] leading-5 text-ink-600 lg:hidden">
            请勿提交身份证号、银行卡号或完整住址等非必要敏感信息。
          </p>
        </div>
      </div>
    </section>
  </div>
</template>
