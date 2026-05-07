<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'

import { ApiError } from '@/shared/api/client'
import { adminAuthStore } from '@/shared/auth/store'

const router = useRouter()
const username = ref('')
const password = ref('')
const errorMessage = ref('')

async function submit() {
  errorMessage.value = ''
  try {
    await adminAuthStore.login(username.value, password.value)
    await router.replace('/users')
  } catch (error) {
    if (error instanceof ApiError) {
      const payload = error.payload as { error?: { code?: string } }
      errorMessage.value = payload?.error?.code === 'invalid_credentials' ? 'نام کاربری یا رمز عبور درست نیست.' : error.message
      return
    }
    errorMessage.value = 'ورود به پنل انجام نشد.'
  }
}
</script>

<template>
  <main class="auth-layout">
    <section class="auth-card-wrap">
      <form class="auth-card" @submit.prevent="submit">
        <div class="auth-card__header">
          <span class="auth-card__kicker">ورود ادمین</span>
          <h1>ورود به پنل مدیریت</h1>
          <p>نام کاربری و رمز عبور خود را وارد کنید.</p>
        </div>

        <label class="field">
          <span>نام کاربری</span>
          <input v-model.trim="username" type="text" autocomplete="username" placeholder="admin" />
        </label>

        <label class="field">
          <span>رمز عبور</span>
          <input v-model="password" type="password" autocomplete="current-password" placeholder="••••••••" />
        </label>

        <p v-if="errorMessage" class="inline-error">{{ errorMessage }}</p>

        <button class="primary-button" type="submit" :disabled="adminAuthStore.pending">
          {{ adminAuthStore.pending ? 'در حال بررسی...' : 'ورود به پنل' }}
        </button>
      </form>
    </section>
  </main>
</template>
