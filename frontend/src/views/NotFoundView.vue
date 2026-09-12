<script setup lang="ts">
import { RouterLink } from 'vue-router'

import AppIcon from '@/components/AppIcon.vue'
</script>

<template>
  <section class="mx-auto flex min-h-[70vh] max-w-2xl flex-col items-center justify-center px-5 py-20 text-center">
    <p class="font-mono text-xs tracking-[0.18em] text-jade-800">404 · NOT FOUND</p>
    <h1 class="mt-4 text-4xl font-semibold tracking-[-0.04em] text-ink-950">这个页面尚不存在</h1>
    <p class="mt-4 text-sm leading-7 text-ink-500">链接可能已经改变，或者对应功能尚未进入首月开发范围。</p>
    <RouterLink
      to="/"
      class="focus-ring mt-8 inline-flex min-h-11 items-center gap-2 rounded-xl bg-ink-950 px-5 text-sm font-semibold text-white"
    >
      返回首页
      <AppIcon name="arrow-right" :size="16" />
    </RouterLink>
  </section>
</template>
