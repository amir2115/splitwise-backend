import { mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import AppReleasesPage from './AppReleasesPage.vue'

const replace = vi.fn()
const apiRequest = vi.fn()

vi.mock('vue-router', () => ({
  useRouter: () => ({ replace }),
}))

vi.mock('@/shared/auth/store', () => ({
  adminAuthStore: {
    accessToken: 'admin-token',
    logout: vi.fn(),
  },
}))

vi.mock('@/shared/api/client', () => ({
  ApiError: class ApiError extends Error {
    constructor(
      message: string,
      public status: number,
      public payload: unknown,
    ) {
      super(message)
    }
  },
  apiRequest: (...args: unknown[]) => apiRequest(...args),
}))

function flushPromises() {
  return new Promise((resolve) => setTimeout(resolve, 0))
}

const releasesResponse = {
  items: [
    {
      id: 'release-1',
      version_name: '1.4.0',
      version_code: 42,
      title: 'دانلود اپلیکیشن',
      subtitle: 'آخرین نسخه دنگینو را از کافه بازار، مایکت یا لینک مستقیم نصب کن.',
      app_icon_url: 'https://splitwise.ir/android-chrome-512x512.png',
      release_date: '2026-05-30',
      file_size: '18.4 MB',
      bazaar_url: 'https://cafebazaar.ir/app/com.encer.splitwise',
      myket_url: 'https://myket.ir/app/com.encer.splitwise',
      release_notes: ['بهبود پایداری'],
      primary_badge_text: 'نسخه جدید',
      min_supported_version_code: 12,
      update_mode: 'soft',
      update_title: 'نسخه جدید آماده است',
      update_message: 'برای نصب نسخه جدید روی لینک دانلود بزن.',
      apk_object_key: 'app-releases/app-release_1.4.0.apk',
      apk_url: 'https://cdn.example.com/files/app-releases/app-release_1.4.0.apk',
      is_published: true,
      published_at: '2026-05-30T00:00:00Z',
      created_at: '2026-05-30T00:00:00Z',
      updated_at: '2026-05-30T00:00:00Z',
    },
  ],
}

describe('AppReleasesPage', () => {
  beforeEach(() => {
    apiRequest.mockReset()
    replace.mockReset()
    apiRequest.mockResolvedValue(releasesResponse)
  })

  it('renders release history and published version', async () => {
    const wrapper = mount(AppReleasesPage)
    await flushPromises()

    expect(apiRequest).toHaveBeenCalledWith('/admin/app-releases', { method: 'GET' }, 'admin-token')
    expect(wrapper.text()).toContain('نسخه منتشرشده: 1.4.0')
    expect(wrapper.text()).toContain('بهبود پایداری')
    expect(wrapper.find('a[href="https://cdn.example.com/files/app-releases/app-release_1.4.0.apk"]').exists()).toBe(true)
  })

  it('creates release with newline-separated release notes', async () => {
    apiRequest
      .mockResolvedValueOnce({ items: [] })
      .mockResolvedValueOnce({ id: 'release-2' })
      .mockResolvedValueOnce(releasesResponse)
    const wrapper = mount(AppReleasesPage)
    await flushPromises()

    await wrapper.find('input[placeholder="1.4.0"]').setValue('1.5.0')
    await wrapper.find('input[inputmode="numeric"]').setValue(43)
    await wrapper.find('textarea').setValue('تغییر اول\nتغییر دوم')
    await wrapper.find('form').trigger('submit.prevent')
    await flushPromises()

    const [, init] = apiRequest.mock.calls[1]
    const payload = JSON.parse(init.body)
    expect(payload.version_name).toBe('1.5.0')
    expect(payload.version_code).toBe(43)
    expect(payload.title).toBe('دانلود اپلیکیشن')
    expect(payload.app_icon_url).toBe('https://splitwise.ir/android-chrome-512x512.png')
    expect(payload.release_notes).toEqual(['تغییر اول', 'تغییر دوم'])
  })
})
