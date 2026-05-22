<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'

import AdminShell from '@/shared/components/AdminShell.vue'

const route = useRoute()
const usesAdminShell = computed(() => Boolean(route.meta.requiresAuth))
</script>

<template>
  <AdminShell v-if="usesAdminShell">
    <router-view />
  </AdminShell>
  <router-view v-else />
</template>
