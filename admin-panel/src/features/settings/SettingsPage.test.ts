import { mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import SettingsPage from './SettingsPage.vue'

const replace = vi.fn()
const push = vi.fn()
const apiRequest = vi.fn()

vi.mock('vue-router', () => ({
  useRouter: () => ({ replace, push }),
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

const settingsResponse = {
  phone_verification_required: false,
  sms_ir_api_key_masked: null,
  sms_ir_api_key_configured: false,
  sms_ir_verify_template_id: null,
  sms_ir_verify_template_id_android: null,
  sms_ir_verify_parameter_name: 'OTP',
  sms_otp_bypass_enabled: false,
  sms_ir_invited_account_template_id: null,
  sms_ir_invited_account_link_parameter_name: 'TOKEN',
  sms_ir_invited_account_group_name_parameter_name: 'GROUP_NAME',
  web_app_base_url: 'https://pwa.splitwise.ir',
  support_email: 'support@splitwise.ir',
  support_url: 'mailto:support@splitwise.ir',
  twitter_url: 'https://x.com/dongino',
  instagram_url: null,
  telegram_url: null,
  linkedin_url: null,
  enamad_url: null,
  pwa_url: 'https://pwa.splitwise.ir',
  bazaar_url: 'https://cafebazaar.ir/app/com.encer.offlinesplitwise',
  myket_url: 'https://myket.ir/app/com.encer.offlinesplitwise',
  apk_url: 'https://splitwise.ir/files/app.apk',
  footer_short_text: 'مدیریت هزینه‌های گروهی، ساده و شفاف.',
  contact_body: 'از ایمیل پشتیبانی استفاده کنید.',
}

function flushPromises() {
  return new Promise((resolve) => setTimeout(resolve, 0))
}

describe('SettingsPage public site settings', () => {
  beforeEach(() => {
    apiRequest.mockReset()
    replace.mockReset()
    push.mockReset()
    apiRequest.mockResolvedValue(settingsResponse)
  })

  it('renders public site setting fields from the runtime response', async () => {
    const wrapper = mount(SettingsPage)
    await flushPromises()

    expect(wrapper.text()).toContain('تنظیمات عمومی سایت')
    expect((wrapper.find('input[type="email"]').element as HTMLInputElement).value).toBe('support@splitwise.ir')
    expect((wrapper.find('input[placeholder="https://x.com/..."]').element as HTMLInputElement).value).toBe('https://x.com/dongino')
  })

  it('sends empty public site fields as null', async () => {
    const wrapper = mount(SettingsPage)
    await flushPromises()

    await wrapper.find('input[placeholder="https://x.com/..."]').setValue('')
    await wrapper.find('form').trigger('submit.prevent')
    await flushPromises()

    const [, init] = apiRequest.mock.calls[1]
    const payload = JSON.parse(init.body)
    expect(payload.twitter_url).toBeNull()
    expect(payload.instagram_url).toBeNull()
    expect(payload.support_email).toBe('support@splitwise.ir')
  })
})
