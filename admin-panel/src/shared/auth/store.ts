import { reactive } from 'vue'

import { apiRequest } from '@/shared/api/client'
import { clearAdminAccessToken, readAdminAccessToken, writeAdminAccessToken } from '@/shared/auth/storage'
import type { AdminAuthResponse, AdminIdentity } from '@/shared/types/api'

const state = reactive({
  accessToken: readAdminAccessToken() as string | null,
  admin: null as AdminIdentity | null,
  bootstrapped: false,
  pending: false,
})

export const adminAuthStore = {
  get accessToken() {
    return state.accessToken
  },
  get admin() {
    return state.admin
  },
  get bootstrapped() {
    return state.bootstrapped
  },
  get pending() {
    return state.pending
  },
  get isAuthenticated() {
    return Boolean(state.accessToken && state.admin)
  },
  async bootstrap() {
    if (state.bootstrapped) return
    if (!state.accessToken) {
      state.bootstrapped = true
      return
    }
    try {
      state.admin = await apiRequest<AdminIdentity>('/admin/auth/me', { method: 'GET' }, state.accessToken)
    } catch {
      this.logout()
    } finally {
      state.bootstrapped = true
    }
  },
  async login(username: string, password: string) {
    state.pending = true
    try {
      const payload = await apiRequest<AdminAuthResponse>('/admin/auth/login', {
        method: 'POST',
        body: JSON.stringify({ username, password }),
      })
      state.accessToken = payload.access_token
      state.admin = payload.admin
      state.bootstrapped = true
      writeAdminAccessToken(payload.access_token)
      return payload
    } finally {
      state.pending = false
    }
  },
  logout() {
    state.accessToken = null
    state.admin = null
    state.bootstrapped = true
    clearAdminAccessToken()
  },
}
