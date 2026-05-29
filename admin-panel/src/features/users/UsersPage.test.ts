import { mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import UsersPage from './UsersPage.vue'

const mocks = vi.hoisted(() => {
  class MockApiError extends Error {
    constructor(
      message: string,
      public status: number,
      public payload: unknown,
    ) {
      super(message)
    }
  }
  return {
    replace: vi.fn(),
    push: vi.fn(),
    apiRequest: vi.fn(),
    routeQuery: {} as Record<string, string>,
    MockApiError,
  }
})

vi.mock('vue-router', () => ({
  useRoute: () => ({ query: mocks.routeQuery }),
  useRouter: () => ({ replace: mocks.replace, push: mocks.push }),
}))

vi.mock('@/shared/auth/store', () => ({
  adminAuthStore: {
    accessToken: 'admin-token',
    admin: { username: 'panel_admin' },
    logout: vi.fn(),
  },
}))

vi.mock('@/shared/api/client', () => ({
  ApiError: mocks.MockApiError,
  apiRequest: (...args: unknown[]) => mocks.apiRequest(...args),
}))

const usersResponse = {
  items: [
    {
      id: 'user-id',
      name: 'Android User',
      username: 'android_user',
      phone_number: null,
      is_phone_verified: false,
      must_change_password: false,
      client_platform: 'android',
      android_variant: 'bazaar',
      last_client_seen_at: '2026-05-29T10:00:00Z',
      created_at: '2026-05-29T09:00:00Z',
      updated_at: '2026-05-29T09:00:00Z',
      groups_count: 0,
      active_refresh_tokens_count: 0,
    },
  ],
  pagination: { page: 1, page_size: 20, total: 1 },
  summary: {
    total_users: 1,
    must_change_password_count: 0,
    android_users_count: 1,
    frontend_users_count: 0,
    unknown_client_users_count: 0,
  },
}

function flushPromises() {
  return new Promise((resolve) => setTimeout(resolve, 0))
}

describe('UsersPage', () => {
  beforeEach(() => {
    mocks.apiRequest.mockReset()
    mocks.replace.mockReset()
    mocks.push.mockReset()
    mocks.routeQuery = {}
    mocks.apiRequest.mockResolvedValue(usersResponse)
  })

  it('serializes client platform and android variant filters', async () => {
    mocks.routeQuery = {
      client_platform: 'android',
      android_variant: 'bazaar',
      sort_by: 'last_client_seen_at',
      sort_order: 'desc',
    }

    mount(UsersPage)
    await flushPromises()

    expect(mocks.apiRequest).toHaveBeenCalledWith(
      '/admin/users?client_platform=android&android_variant=bazaar&sort_by=last_client_seen_at&sort_order=desc&page=1&page_size=20',
      { method: 'GET' },
      'admin-token',
    )
  })

  it('renders client platform and android variant labels', async () => {
    const wrapper = mount(UsersPage)
    await flushPromises()

    expect(wrapper.text()).toContain('اندروید')
    expect(wrapper.text()).toContain('بازار')
  })
})
