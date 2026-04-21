<script setup lang="ts">
defineProps<{
  active: boolean
}>()
</script>

<template>
  <span class="status-badge" :data-active="active">
    {{ active ? 'نیازمند تغییر رمز' : 'عادی' }}
  </span>
</template>
