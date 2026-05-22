import { createRouter, createWebHistory } from 'vue-router'

import ArticlesPage from '@/features/articles/ArticlesPage.vue'
import LoginPage from '@/features/auth/LoginPage.vue'
import SettingsPage from '@/features/settings/SettingsPage.vue'
import UsersPage from '@/features/users/UsersPage.vue'
import { adminAuthStore } from '@/shared/auth/store'

export const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', redirect: '/articles' },
    { path: '/login', component: LoginPage, meta: { guestOnly: true } },
    { path: '/articles', component: ArticlesPage, meta: { requiresAuth: true } },
    { path: '/users', component: UsersPage, meta: { requiresAuth: true } },
    { path: '/settings', component: SettingsPage, meta: { requiresAuth: true } },
  ],
})

router.beforeEach(async (to) => {
  if (!adminAuthStore.bootstrapped) {
    await adminAuthStore.bootstrap()
  }

  if (to.meta.requiresAuth && !adminAuthStore.isAuthenticated) {
    return '/login'
  }

  if (to.meta.guestOnly && adminAuthStore.isAuthenticated) {
    return '/articles'
  }

  return true
})
