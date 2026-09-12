<script setup lang="ts">
import { RouterView } from 'vue-router'

import AppHeader from '@/components/AppHeader.vue'
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

    <footer class="border-t border-ink-950/8 bg-white/35">
      <div
        class="mx-auto flex max-w-7xl flex-col gap-2 px-5 py-6 text-xs leading-5 text-ink-500 sm:px-8 md:flex-row md:items-center md:justify-between lg:px-10"
      >
        <p>LegalMind · 中国大陆法律信息场景 · 本地课程演示</p>
        <p>AI 输出不构成法律意见，请核对原始依据。</p>
      </div>
    </footer>
  </div>
</template>
