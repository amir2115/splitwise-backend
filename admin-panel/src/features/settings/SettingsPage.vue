<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'

import { ApiError, apiRequest } from '@/shared/api/client'
import { adminAuthStore } from '@/shared/auth/store'
import type { AdminRuntimeSettingsResponse, AdminRuntimeSettingsUpdateRequest } from '@/shared/types/api'

const router = useRouter()

const loading = ref(false)
const saving = ref(false)
const errorMessage = ref('')
const successMessage = ref('')
const settings = ref<AdminRuntimeSettingsResponse | null>(null)
const form = ref<AdminRuntimeSettingsUpdateRequest>({
  phone_verification_required: false,
  sms_ir_api_key: '',
  sms_ir_verify_template_id: '',
  sms_ir_verify_template_id_android: '',
  sms_ir_verify_parameter_name: '',
  sms_otp_bypass_enabled: false,
  sms_ir_invited_account_template_id: '',
  sms_ir_invited_account_link_parameter_name: '',
  sms_ir_invited_account_group_name_parameter_name: '',
  web_app_base_url: '',
})

async function fetchSettings() {
  loading.value = true
  errorMessage.value = ''
  try {
    const response = await apiRequest<AdminRuntimeSettingsResponse>(
      '/admin/settings/runtime',
      { method: 'GET' },
      adminAuthStore.accessToken,
    )
    settings.value = response
    form.value = {
      phone_verification_required: response.phone_verification_required,
      sms_ir_api_key: '',
      sms_ir_verify_template_id: response.sms_ir_verify_template_id ?? '',
      sms_ir_verify_template_id_android: response.sms_ir_verify_template_id_android ?? '',
      sms_ir_verify_parameter_name: response.sms_ir_verify_parameter_name ?? '',
      sms_otp_bypass_enabled: response.sms_otp_bypass_enabled,
      sms_ir_invited_account_template_id: response.sms_ir_invited_account_template_id ?? '',
      sms_ir_invited_account_link_parameter_name: response.sms_ir_invited_account_link_parameter_name ?? '',
      sms_ir_invited_account_group_name_parameter_name: response.sms_ir_invited_account_group_name_parameter_name ?? '',
      web_app_base_url: response.web_app_base_url ?? '',
    }
  } catch (error) {
    if (error instanceof ApiError && error.status === 401) {
      adminAuthStore.logout()
      await router.replace('/login')
      return
    }
    errorMessage.value = error instanceof ApiError ? error.message : 'دریافت تنظیمات ناموفق بود.'
  } finally {
    loading.value = false
  }
}

async function saveSettings() {
  saving.value = true
  errorMessage.value = ''
  successMessage.value = ''
  try {
    const response = await apiRequest<AdminRuntimeSettingsResponse>(
      '/admin/settings/runtime',
      {
        method: 'PATCH',
        body: JSON.stringify(form.value),
      },
      adminAuthStore.accessToken,
    )
    settings.value = response
    form.value.sms_ir_api_key = ''
    successMessage.value = 'تنظیمات با موفقیت ذخیره شد.'
  } catch (error) {
    if (error instanceof ApiError && error.status === 401) {
      adminAuthStore.logout()
      await router.replace('/login')
      return
    }
    errorMessage.value = error instanceof ApiError ? error.message : 'ذخیره تنظیمات ناموفق بود.'
  } finally {
    saving.value = false
  }
}

onMounted(() => {
  void fetchSettings()
})

function logout() {
  adminAuthStore.logout()
  void router.replace('/login')
}
</script>

<template>
  <main class="dashboard-shell">
    <header class="dashboard-hero">
      <div>
        <span class="eyebrow">تنظیمات پیامک، دعوت و تایید شماره</span>
        <h1>تنظیمات runtime</h1>
        <p>کلید API، template idها، فلگ نیاز به تایید شماره، bypass کد OTP و آدرس وب‌اپ را از اینجا مدیریت کن.</p>
      </div>

      <div class="dashboard-hero__actions">
        <button class="ghost-button" type="button" @click="router.push('/users')">کاربران</button>
        <button class="ghost-button" type="button" @click="logout">خروج</button>
      </div>
    </header>

    <section v-if="errorMessage" class="state-card state-card--error">
      <strong>خطا</strong>
      <p>{{ errorMessage }}</p>
    </section>

    <section v-else-if="loading" class="state-card">
      <strong>در حال بارگذاری...</strong>
      <p>تنظیمات پنل در حال دریافت است.</p>
    </section>

    <section v-else class="filters-card">
      <form class="page-form-stack" @submit.prevent="saveSettings">
        <label class="field field--checkbox">
          <span>PHONE_VERIFICATION_REQUIRED</span>
          <input v-model="form.phone_verification_required" type="checkbox" />
          <small class="field-hint">
            اگر روشن باشد، کاربر لاگین‌شده‌ای که شماره تلفن ندارد یا شماره‌اش تایید نشده، بعد از ورود به اپ باید مودال
            تایید شماره تلفن را ببیند.
          </small>
        </label>

        <div class="field">
          <span>SMS_IR_API_KEY</span>
          <input v-model.trim="form.sms_ir_api_key" type="text" placeholder="برای حفظ مقدار فعلی خالی بگذار" />
          <small class="field-hint">مقدار فعلی: {{ settings?.sms_ir_api_key_masked || 'تنظیم نشده' }}</small>
        </div>

        <div class="field">
          <span>SMS_IR_VERIFY_TEMPLATE_ID</span>
          <input v-model.trim="form.sms_ir_verify_template_id" type="text" />
        </div>

        <div class="field">
          <span>SMS_IR_VERIFY_TEMPLATE_ID_ANDROID</span>
          <input v-model.trim="form.sms_ir_verify_template_id_android" type="text" />
        </div>

        <div class="field">
          <span>SMS_IR_VERIFY_PARAMETER_NAME</span>
          <input v-model.trim="form.sms_ir_verify_parameter_name" type="text" placeholder="OTP" />
        </div>

        <label class="field field--checkbox">
          <span>SMS_OTP_BYPASS_ENABLED</span>
          <input v-model="form.sms_otp_bypass_enabled" type="checkbox" />
          <small class="field-hint">
            اگر روشن باشد، برای ثبت‌نام، تایید شماره و فراموشی رمز هیچ درخواستی به sms.ir ارسال نمی‌شود و فقط کد ثابت
            <strong>12345</strong>
            معتبر خواهد بود.
          </small>
        </label>

        <div class="field">
          <span>SMS_IR_INVITED_ACCOUNT_TEMPLATE_ID</span>
          <input v-model.trim="form.sms_ir_invited_account_template_id" type="text" />
        </div>

        <div class="field">
          <span>SMS_IR_INVITED_ACCOUNT_LINK_PARAMETER_NAME</span>
          <input v-model.trim="form.sms_ir_invited_account_link_parameter_name" type="text" placeholder="LINK" />
        </div>

        <div class="field">
          <span>SMS_IR_INVITED_ACCOUNT_GROUP_NAME_PARAMETER_NAME</span>
          <input v-model.trim="form.sms_ir_invited_account_group_name_parameter_name" type="text" placeholder="GROUP_NAME" />
        </div>

        <div class="field">
          <span>WEB_APP_BASE_URL</span>
          <input v-model.trim="form.web_app_base_url" type="text" placeholder="https://pwa.splitwise.ir" />
        </div>

        <p v-if="successMessage" class="field-success">{{ successMessage }}</p>
        <button class="primary-button" type="submit" :disabled="saving">
          {{ saving ? 'در حال ذخیره...' : 'ذخیره تنظیمات' }}
        </button>
      </form>
    </section>
  </main>
</template>
