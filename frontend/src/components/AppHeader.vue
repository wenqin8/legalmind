<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { storeToRefs } from 'pinia'
import { RouterLink, useRoute, useRouter } from 'vue-router'

import { getHealth } from '@/api/health'
import { useAuthStore } from '@/stores/auth'
import { useChatStore } from '@/stores/chat'

type BackendState = 'checking' | 'online' | 'offline'

const backendState = ref<BackendState>('checking')
const authStore = useAuthStore()
const chatStore = useChatStore()
const { user, isAuthenticated } = storeToRefs(authStore)
const route = useRoute()
const router = useRouter()
const accountMenu = ref<HTMLDetailsElement | null>(null)

const statusLabel = computed(() => {
  if (backendState.value === 'online') return '服务正常'
  if (backendState.value === 'offline') return '服务暂不可用'
  return '正在连接服务'
})

const statusDotClass = computed(() => ({
  'bg-amber-400': backendState.value === 'checking',
  'bg-jade-500': backendState.value === 'online',
  'bg-ink-400': backendState.value === 'offline',
}))

const userInitial = computed(() => user.value?.username.trim().slice(0, 1).toUpperCase() || '我')

async function checkBackend(): Promise<void> {
  try {
    await getHealth()
    backendState.value = 'online'
  } catch {
    backendState.value = 'offline'
  }
}

async function logout(): Promise<void> {
  closeAccountMenu()
  chatStore.clearConversation()
  authStore.logout()
  if (route.meta.requiresAuth) {
    await router.replace({ name: 'auth', query: { redirect: '/chat' } })
  }
}

function closeAccountMenu(): void {
  if (accountMenu.value) accountMenu.value.open = false
}

onMounted(() => {
  void checkBackend()
})
</script>

<template>
  <header class="sticky top-0 z-40 border-b border-ink-950/8 bg-paper/88 backdrop-blur-xl">
    <div class="mx-auto flex h-17 max-w-7xl items-center px-3 min-[360px]:px-5 sm:px-8 lg:px-10">
      <RouterLink
        to="/"
        class="focus-ring -ml-1 flex items-center gap-3 rounded-xl px-2 py-1.5 min-[360px]:-ml-2"
        aria-label="LegalMind 首页"
      >
        <span
          class="grid size-9 place-items-center rounded-[11px] bg-ink-950 font-serif text-lg font-semibold text-paper shadow-sm"
          aria-hidden="true"
        >衡</span>
        <span class="hidden leading-none min-[360px]:block">
          <span class="block text-[15px] font-semibold tracking-[0.01em] text-ink-950">LegalMind</span>
          <span class="mt-1 hidden text-[10px] tracking-[0.12em] text-ink-600 sm:block">
            法律信息助手
          </span>
        </span>
      </RouterLink>

      <nav class="ml-1 flex items-center gap-0.5 min-[360px]:ml-2 sm:ml-12 sm:gap-1" aria-label="主导航">
        <RouterLink
          to="/"
          class="nav-link"
          active-class="nav-link-active"
          exact-active-class="nav-link-active"
        >
          首页
        </RouterLink>
        <RouterLink to="/chat" class="nav-link" active-class="nav-link-active">
          咨询
        </RouterLink>
      </nav>

      <div class="ml-auto flex items-center gap-1.5 sm:gap-2">
        <span
          class="hidden size-9 items-center justify-center gap-2 rounded-full border border-ink-950/8 bg-white/60 text-[11px] font-medium text-ink-600 min-[360px]:flex sm:h-9 sm:w-auto sm:px-3 sm:text-xs"
          aria-live="polite"
          :aria-label="statusLabel"
          :title="statusLabel"
          data-testid="backend-status"
        >
          <span class="relative flex size-2" aria-hidden="true">
            <span
              v-if="backendState === 'checking'"
              class="absolute inline-flex size-full animate-ping rounded-full bg-amber-400 opacity-40"
            />
            <span class="relative inline-flex size-2 rounded-full" :class="statusDotClass" />
          </span>
          <span class="hidden sm:inline" aria-hidden="true">{{ statusLabel }}</span>
        </span>

        <details v-if="isAuthenticated" ref="accountMenu" class="group relative">
          <summary
            class="focus-ring flex h-9 list-none items-center gap-2 rounded-full border border-ink-950/8 bg-white/60 p-1 pr-1 text-ink-700 transition hover:bg-white [&::-webkit-details-marker]:hidden"
            aria-label="打开账户菜单"
          >
            <span class="grid size-7 place-items-center rounded-full bg-ink-950 text-xs font-semibold text-white" aria-hidden="true">
              {{ userInitial }}
            </span>
            <span class="hidden max-w-24 truncate pr-2 text-xs font-medium lg:block">
              {{ user?.username }}
            </span>
          </summary>
          <div
            class="absolute right-0 mt-2 w-52 overflow-hidden rounded-2xl border border-ink-950/10 bg-paper p-2 text-sm shadow-[0_18px_55px_rgba(18,33,29,0.16)]"
          >
            <p class="truncate border-b border-ink-950/8 px-3 py-2 text-xs font-semibold text-ink-700">
              {{ user?.username }}
            </p>
            <RouterLink class="focus-ring mt-1 flex rounded-xl px-3 py-2.5 text-ink-600 transition hover:bg-white hover:text-ink-950" to="/about" @click="closeAccountMenu">
              关于 LegalMind
            </RouterLink>
            <RouterLink class="focus-ring flex rounded-xl px-3 py-2.5 text-ink-600 transition hover:bg-white hover:text-ink-950" to="/privacy" @click="closeAccountMenu">
              隐私说明
            </RouterLink>
            <button
              type="button"
              class="focus-ring flex w-full rounded-xl px-3 py-2.5 text-left text-ink-600 transition hover:bg-white hover:text-ink-950"
              @click="logout"
            >
              退出登录
            </button>
          </div>
        </details>

        <RouterLink
          v-else
          to="/auth"
          class="focus-ring inline-flex h-9 items-center rounded-full border border-ink-950/8 bg-white/60 px-3 text-xs font-semibold text-ink-700 transition hover:bg-white hover:text-ink-950"
        >
          登录
        </RouterLink>
      </div>
    </div>
  </header>
</template>
