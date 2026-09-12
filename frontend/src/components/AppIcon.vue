<script setup lang="ts">
withDefaults(
  defineProps<{
    name: string
    size?: number
  }>(),
  { size: 20 },
)
</script>

<template>
  <svg
    :width="size"
    :height="size"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    stroke-width="1.7"
    stroke-linecap="round"
    stroke-linejoin="round"
    aria-hidden="true"
  >
    <template v-if="name === 'arrow-right'">
      <path d="M5 12h14" />
      <path d="m13 6 6 6-6 6" />
    </template>
    <template v-else-if="name === 'shield'">
      <path d="M12 3 5 6v5c0 4.4 2.8 7.8 7 10 4.2-2.2 7-5.6 7-10V6l-7-3Z" />
      <path d="m8.8 12 2.1 2.1 4.5-4.7" />
    </template>
    <template v-else-if="name === 'heart'">
      <path d="M20.8 5.7c-1.5-2.4-4.8-3-6.9-1L12 6.5l-1.9-1.8c-2.1-2-5.4-1.4-6.9 1-1.2 2-.9 4.5.8 6.2l8 7.6 8-7.6c1.7-1.7 2-4.2.8-6.2Z" />
    </template>
    <template v-else-if="name === 'briefcase'">
      <path d="M4 8h16a1 1 0 0 1 1 1v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V9a1 1 0 0 1 1-1Z" />
      <path d="M9 8V5h6v3M3 13h18M10 13v2h4v-2" />
    </template>
    <template v-else-if="name === 'car'">
      <path d="m5 11 1.5-4h11l1.5 4" />
      <path d="M4 11h16a1 1 0 0 1 1 1v5H3v-5a1 1 0 0 1 1-1Z" />
      <path d="M5 17v2M19 17v2M6.5 14h.01M17.5 14h.01" />
    </template>
    <template v-else-if="name === 'file'">
      <path d="M6 3h8l4 4v14H6z" />
      <path d="M14 3v5h5M9 13h6M9 17h6" />
    </template>
    <template v-else-if="name === 'send'">
      <path d="m3 11 18-8-8 18-2-8-8-2Z" />
      <path d="m11 13 4-4" />
    </template>
    <template v-else-if="name === 'plus'">
      <path d="M12 5v14M5 12h14" />
    </template>
    <template v-else-if="name === 'reset'">
      <path d="M4 4v6h6" />
      <path d="M5.5 15a8 8 0 1 0 .7-7.8L4 10" />
    </template>
    <template v-else-if="name === 'message'">
      <path d="M5 5h14a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2H9l-5 3v-4.2A2 2 0 0 1 3 15V7a2 2 0 0 1 2-2Z" />
      <path d="M8 10h8M8 14h5" />
    </template>
    <template v-else-if="name === 'lock'">
      <rect x="5" y="10" width="14" height="10" rx="2" />
      <path d="M8 10V7a4 4 0 0 1 8 0v3" />
    </template>
    <template v-else-if="name === 'logout'">
      <path d="M10 5H5v14h5" />
      <path d="M14 8l4 4-4 4M8 12h10" />
    </template>
    <template v-else-if="name === 'check'">
      <path d="m5 12 4 4L19 6" />
    </template>
    <template v-else-if="name === 'spark'">
      <path d="m12 3 1.2 4.1L17 9l-3.8 1.9L12 15l-1.2-4.1L7 9l3.8-1.9L12 3Z" />
      <path d="m5 15 .7 2.3L8 18l-2.3.7L5 21l-.7-2.3L2 18l2.3-.7L5 15Z" />
    </template>
    <template v-else>
      <circle cx="12" cy="12" r="8" />
    </template>
  </svg>
</template>
