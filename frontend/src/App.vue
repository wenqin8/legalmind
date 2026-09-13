<script setup lang="ts">
import { RouterLink, RouterView, useRoute } from 'vue-router'

import AppHeader from '@/components/AppHeader.vue'

const route = useRoute()
</script>

<template>
  <div class="flex min-h-screen flex-col">
    <a class="skip-link" href="#main-content">跳到主要内容</a>
    <AppHeader />

    <main id="main-content" class="flex-1" tabindex="-1">
      <RouterView v-slot="{ Component }">
        <Transition name="route" mode="out-in">
          <component :is="Component" />
        </Transition>
      </RouterView>
    </main>

    <footer v-if="!route.meta.appShell" class="border-t border-ink-950/8 bg-white/35">
      <nav
        class="mx-auto flex max-w-7xl flex-wrap items-center justify-center gap-x-6 gap-y-2 px-5 py-6 text-xs text-ink-600 sm:px-8 lg:px-10"
        aria-label="页脚导航"
      >
        <RouterLink class="focus-ring rounded-md transition hover:text-ink-950" to="/guide">使用说明</RouterLink>
        <RouterLink class="focus-ring rounded-md transition hover:text-ink-950" to="/privacy">隐私说明</RouterLink>
        <RouterLink class="focus-ring rounded-md transition hover:text-ink-950" to="/about">关于我们</RouterLink>
      </nav>
    </footer>
  </div>
</template>
