<script setup lang="ts">
defineProps<{
  label: string
  value: string
  tone?: 'default' | 'accent' | 'warning'
}>()
</script>

<template>
  <article class="summary-card" :data-tone="tone || 'default'">
    <span class="summary-card__label">{{ label }}</span>
    <strong class="summary-card__value">{{ value }}</strong>
  </article>
</template>
