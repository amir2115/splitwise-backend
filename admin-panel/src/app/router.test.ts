import { beforeEach, describe, expect, it, vi } from 'vitest'

const bootstrap = vi.fn()
let authenticated = false

vi.mock('@/shared/auth/store', () => ({
  adminAuthStore: {
    get bootstrapped() {
      return true
    },
    get isAuthenticated() {
      return authenticated
    },
    bootstrap,
  },
}))

describe('admin router guards', () => {
  beforeEach(() => {
    authenticated = false
  })

  it('redirects guests away from protected users page', async () => {
    const { router } = await import('@/app/router')
    await router.push('/users')
    expect(router.currentRoute.value.fullPath).toBe('/login')
  }, 15000)

  it('redirects authenticated admins away from login', async () => {
    authenticated = true
    const { router } = await import('@/app/router')
    await router.replace('/')
    await router.push('/login')
    expect(router.currentRoute.value.fullPath).toBe('/users')
  }, 15000)
})
