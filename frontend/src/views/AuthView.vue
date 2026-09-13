<script setup lang="ts">
import { computed, reactive, ref } from 'vue'
import { storeToRefs } from 'pinia'
import { RouterLink, useRoute, useRouter } from 'vue-router'

import AppIcon from '@/components/AppIcon.vue'
import LegalDisclaimer from '@/components/LegalDisclaimer.vue'
import { useAuthStore } from '@/stores/auth'

type AuthMode = 'login' | 'register'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()
const { isSubmitting, errorMessage, errorRequestId } = storeToRefs(authStore)

const mode = ref<AuthMode>(route.query.mode === 'register' ? 'register' : 'login')
const form = reactive({
  login: '',
  username: '',
  email: '',
  password: '',
})

const isRegister = computed(() => mode.value === 'register')
const canSubmit = computed(() => {
  if (form.password.length < 8 || form.password.length > 128) return false
  if (!isRegister.value) return form.login.trim().length > 0
  return (
    form.username.trim().length >= 3 &&
    form.username.trim().length <= 50 &&
    form.email.trim().length > 0 &&
    form.email.trim().length <= 254
  )
})

const redirectTarget = computed(() => {
  const candidate = route.query.redirect
  if (
    typeof candidate === 'string' &&
    candidate.startsWith('/') &&
    !candidate.startsWith('//')
  ) {
    return candidate
  }
  return '/chat'
})

function switchMode(nextMode: AuthMode): void {
  if (isSubmitting.value || mode.value === nextMode) return
  mode.value = nextMode
  form.password = ''
  authStore.clearError()
}

async function submit(): Promise<void> {
  if (!canSubmit.value || isSubmitting.value) return

  const succeeded = isRegister.value
    ? await authStore.registerAndLogin({
        username: form.username.trim(),
        email: form.email.trim(),
        password: form.password,
      })
    : await authStore.login({
        login: form.login.trim(),
        password: form.password,
      })

  if (succeeded) {
    form.password = ''
    await router.replace(redirectTarget.value)
  }
}
</script>

<template>
  <section class="relative isolate overflow-hidden px-5 py-8 sm:px-8 sm:py-14 lg:px-10 lg:py-20">
    <div class="pointer-events-none absolute inset-0 -z-10 hero-grid opacity-55" />
    <div class="pointer-events-none absolute top-0 left-1/2 -z-10 h-96 w-96 -translate-x-1/2 rounded-full bg-jade-100/45 blur-3xl" />

    <div class="mx-auto grid max-w-5xl overflow-hidden rounded-[2rem] border border-ink-950/8 bg-white/74 shadow-[0_28px_90px_rgba(19,33,29,0.12)] backdrop-blur md:grid-cols-[0.9fr_1.1fr]">
      <div class="order-1 p-6 sm:p-10 md:order-2 md:p-12" data-testid="auth-form-panel">
        <div class="flex rounded-xl bg-ink-950/5 p-1" aria-label="选择登录或注册">
          <button
            type="button"
            class="focus-ring flex-1 rounded-lg px-4 py-2.5 text-xs font-semibold transition"
            :class="!isRegister ? 'bg-white text-ink-950 shadow-sm' : 'text-ink-600 hover:text-ink-950'"
            :aria-pressed="!isRegister"
            @click="switchMode('login')"
          >
            登录
          </button>
          <button
            type="button"
            class="focus-ring flex-1 rounded-lg px-4 py-2.5 text-xs font-semibold transition"
            :class="isRegister ? 'bg-white text-ink-950 shadow-sm' : 'text-ink-600 hover:text-ink-950'"
            :aria-pressed="isRegister"
            @click="switchMode('register')"
          >
            注册
          </button>
        </div>

        <div class="mt-8">
          <p class="text-xs font-semibold tracking-[0.08em] text-jade-800">
            {{ isRegister ? '创建账户' : '账户登录' }}
          </p>
          <h1 class="mt-2 text-2xl font-semibold tracking-[-0.035em] text-ink-950">
            {{ isRegister ? '开始使用 LegalMind' : '欢迎回来' }}
          </h1>
          <p class="mt-2 text-xs leading-5 text-ink-600">
            {{ isRegister ? '注册成功后将自动进入咨询空间。' : '可使用用户名或邮箱登录。' }}
          </p>
        </div>

        <form class="mt-7 space-y-5" @submit.prevent="submit">
          <template v-if="isRegister">
            <div>
              <label for="username" class="text-xs font-semibold text-ink-700">用户名</label>
              <input
                id="username"
                v-model="form.username"
                name="username"
                type="text"
                minlength="3"
                maxlength="50"
                autocomplete="username"
                required
                class="focus-ring mt-2 h-12 w-full rounded-xl border border-ink-950/10 bg-white/80 px-4 text-sm text-ink-950 outline-none transition placeholder:text-ink-400 focus:border-jade-700/40"
                placeholder="3–50 个字符"
              />
            </div>
            <div>
              <label for="email" class="text-xs font-semibold text-ink-700">邮箱</label>
              <input
                id="email"
                v-model="form.email"
                name="email"
                type="email"
                maxlength="254"
                autocomplete="email"
                required
                class="focus-ring mt-2 h-12 w-full rounded-xl border border-ink-950/10 bg-white/80 px-4 text-sm text-ink-950 outline-none transition placeholder:text-ink-400 focus:border-jade-700/40"
                placeholder="name@example.com"
              />
            </div>
          </template>

          <div v-else>
            <label for="login" class="text-xs font-semibold text-ink-700">用户名或邮箱</label>
            <input
              id="login"
              v-model="form.login"
              name="login"
              type="text"
              maxlength="254"
              autocomplete="username"
              required
              class="focus-ring mt-2 h-12 w-full rounded-xl border border-ink-950/10 bg-white/80 px-4 text-sm text-ink-950 outline-none transition placeholder:text-ink-400 focus:border-jade-700/40"
              placeholder="输入用户名或邮箱"
            />
          </div>

          <div>
            <label for="password" class="text-xs font-semibold text-ink-700">密码</label>
            <input
              id="password"
              v-model="form.password"
              name="password"
              type="password"
              minlength="8"
              maxlength="128"
              :autocomplete="isRegister ? 'new-password' : 'current-password'"
              required
              class="focus-ring mt-2 h-12 w-full rounded-xl border border-ink-950/10 bg-white/80 px-4 text-sm text-ink-950 outline-none transition placeholder:text-ink-400 focus:border-jade-700/40"
              placeholder="8–128 个字符"
            />
          </div>

          <div
            v-if="errorMessage"
            class="rounded-xl border border-red-900/10 bg-red-50/75 px-4 py-3 text-xs leading-5 text-red-950"
            role="alert"
            data-testid="auth-error"
          >
            <p>{{ errorMessage }}</p>
            <p v-if="errorRequestId" class="mt-1 text-[10px] text-red-950/60">请求编号：{{ errorRequestId }}</p>
          </div>

          <button
            type="submit"
            class="focus-ring inline-flex h-12 w-full items-center justify-center gap-2 rounded-xl bg-ink-950 px-5 text-sm font-semibold text-white transition enabled:hover:bg-jade-900 disabled:cursor-not-allowed disabled:opacity-40"
            :disabled="!canSubmit || isSubmitting"
          >
            {{ isSubmitting ? '正在处理…' : isRegister ? '注册并登录' : '登录' }}
            <AppIcon v-if="!isSubmitting" name="arrow-right" :size="16" />
          </button>
        </form>

        <p class="mt-6 text-center text-[11px] leading-5 text-ink-600">
          继续即表示你已阅读
          <RouterLink class="focus-ring rounded underline decoration-ink-300 underline-offset-3 hover:text-ink-950" to="/guide">使用说明</RouterLink>
          和
          <RouterLink class="focus-ring rounded underline decoration-ink-300 underline-offset-3 hover:text-ink-950" to="/privacy">隐私说明</RouterLink>。
        </p>

        <LegalDisclaimer v-if="isRegister" variant="full" class="mt-5" />
      </div>

      <div
        class="relative order-2 overflow-hidden bg-ink-950 p-7 text-white sm:p-9 md:order-1 md:p-12"
        data-testid="auth-brand-panel"
      >
        <div class="absolute -right-20 -bottom-24 size-72 rounded-full border border-white/10" />
        <div class="absolute -right-8 -bottom-14 size-52 rounded-full border border-white/8" />

        <div class="relative flex h-full flex-col">
          <span class="grid size-11 place-items-center rounded-2xl bg-white/10 font-serif text-xl" aria-hidden="true">衡</span>
          <p class="mt-6 text-xs font-semibold tracking-[0.08em] text-jade-300 md:mt-10">个人咨询空间</p>
          <h2 class="mt-3 max-w-sm text-2xl font-semibold leading-tight tracking-[-0.04em] sm:text-3xl md:text-4xl">
            把复杂事实，整理成清晰问题。
          </h2>
          <p class="mt-4 max-w-sm text-sm leading-7 text-white/72">
            登录用于识别并隔离你的咨询会话，让每次交流保持独立、有序。
          </p>

          <div class="mt-10 hidden space-y-4 md:block md:mt-auto md:pt-14">
            <div class="flex items-center gap-3 text-xs text-white/75">
              <AppIcon name="lock" :size="16" class="text-jade-300" />
              咨询会话按账户隔离
            </div>
            <div class="flex items-center gap-3 text-xs text-white/75">
              <AppIcon name="shield" :size="16" class="text-jade-300" />
              密码以安全哈希保存
            </div>
          </div>
        </div>
      </div>
    </div>
  </section>
</template>
