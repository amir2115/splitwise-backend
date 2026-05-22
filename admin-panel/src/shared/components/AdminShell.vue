<script setup lang="ts">
import { computed } from 'vue'
import { RouterLink, useRouter } from 'vue-router'

import { adminAuthStore } from '@/shared/auth/store'

const router = useRouter()

const navItems = [
  { to: '/articles', label: 'مقاله‌ها', hint: 'انتشار و آپلود تصویر' },
  { to: '/users', label: 'کاربران', hint: 'مدیریت حساب‌ها' },
  { to: '/settings', label: 'تنظیمات', hint: 'سایت و پیامک' },
]

const adminName = computed(() => adminAuthStore.admin?.username || 'admin')

function logout() {
  adminAuthStore.logout()
  void router.replace('/login')
}
</script>

<template>
  <div class="admin-shell">
    <aside class="admin-sidebar">
      <div class="admin-sidebar__brand">
        <span>پنل مدیریت</span>
        <strong>دنگینو</strong>
      </div>

      <nav class="admin-sidebar__nav" aria-label="Admin navigation">
        <RouterLink
          v-for="item in navItems"
          :key="item.to"
          :to="item.to"
          class="admin-sidebar__link"
        >
          <strong>{{ item.label }}</strong>
          <span>{{ item.hint }}</span>
        </RouterLink>
      </nav>

      <div class="admin-sidebar__footer">
        <span>ادمین فعال</span>
        <strong>{{ adminName }}</strong>
        <button class="ghost-button" type="button" @click="logout">خروج</button>
      </div>
    </aside>

    <div class="admin-shell__content">
      <slot />
    </div>
  </div>
</template>
