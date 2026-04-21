<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { ApiError, apiRequest } from '@/shared/api/client'
import { adminAuthStore } from '@/shared/auth/store'
import StatusBadge from '@/shared/components/StatusBadge.vue'
import SummaryCard from '@/shared/components/SummaryCard.vue'
import type { AdminUserListFilters, AdminUserListItem, AdminUserListResponse, AdminUserUpdateRequest } from '@/shared/types/api'
import { formatDate, formatNumber } from '@/shared/utils/format'

const route = useRoute()
const router = useRouter()

const loading = ref(false)
const isUpdating = ref(false)
const isDeleting = ref(false)
const errorMessage = ref('')
const updateErrorMessage = ref('')
const deleteErrorMessage = ref('')
const response = ref<AdminUserListResponse | null>(null)
const searchDraft = ref('')
const editingUser = ref<AdminUserListItem | null>(null)
const editForm = ref({
  name: '',
  phone_number: '',
})
const deleteConfirmStep = ref(false)

const filters = computed<AdminUserListFilters>(() => ({
  search: typeof route.query.search === 'string' ? route.query.search : '',
  must_change_password:
    route.query.must_change_password === 'true' || route.query.must_change_password === 'false'
      ? route.query.must_change_password
      : 'all',
  sort_by:
    typeof route.query.sort_by === 'string' &&
    ['created_at', 'updated_at', 'name', 'username', 'groups_count', 'active_refresh_tokens_count'].includes(route.query.sort_by)
      ? (route.query.sort_by as AdminUserListFilters['sort_by'])
      : 'created_at',
  sort_order: route.query.sort_order === 'asc' ? 'asc' : 'desc',
  page: Number(route.query.page || 1) > 0 ? Number(route.query.page || 1) : 1,
  page_size: Number(route.query.page_size || 20) > 0 ? Number(route.query.page_size || 20) : 20,
}))

const totalPages = computed(() => {
  if (!response.value) return 1
  return Math.max(1, Math.ceil(response.value.pagination.total / response.value.pagination.page_size))
})

const visibleCount = computed(() => response.value?.items.length ?? 0)

watch(
  filters,
  async (nextFilters) => {
    searchDraft.value = nextFilters.search
    await fetchUsers(nextFilters)
  },
  { immediate: true },
)

async function fetchUsers(currentFilters: AdminUserListFilters) {
  loading.value = true
  errorMessage.value = ''
  try {
    const params = new URLSearchParams()
    if (currentFilters.search) params.set('search', currentFilters.search)
    if (currentFilters.must_change_password !== 'all') params.set('must_change_password', currentFilters.must_change_password)
    params.set('sort_by', currentFilters.sort_by)
    params.set('sort_order', currentFilters.sort_order)
    params.set('page', String(currentFilters.page))
    params.set('page_size', String(currentFilters.page_size))

    response.value = await apiRequest<AdminUserListResponse>(
      `/admin/users?${params.toString()}`,
      { method: 'GET' },
      adminAuthStore.accessToken,
    )
  } catch (error) {
    if (error instanceof ApiError && error.status === 401) {
      adminAuthStore.logout()
      await router.replace('/login')
      return
    }
    errorMessage.value = error instanceof ApiError ? error.message : 'دریافت کاربران ناموفق بود.'
  } finally {
    loading.value = false
  }
}

async function updateFilters(patch: Partial<AdminUserListFilters>) {
  const next = { ...filters.value, ...patch }
  const query: Record<string, string> = {
    sort_by: next.sort_by,
    sort_order: next.sort_order,
    page: String(next.page),
    page_size: String(next.page_size),
  }
  if (next.search) query.search = next.search
  if (next.must_change_password !== 'all') query.must_change_password = next.must_change_password
  await router.replace({ path: '/users', query })
}

function submitSearch() {
  void updateFilters({ search: searchDraft.value, page: 1 })
}

function clearSearch() {
  searchDraft.value = ''
  void updateFilters({ search: '', page: 1 })
}

function logout() {
  adminAuthStore.logout()
  void router.replace('/login')
}

function displayPhoneNumber(phoneNumber: string | null) {
  return phoneNumber || 'ثبت نشده'
}

function displayPhoneVerificationStatus(isVerified: boolean) {
  return isVerified ? 'تایید شده' : 'تایید نشده'
}

function openEditModal(user: AdminUserListItem) {
  editingUser.value = user
  updateErrorMessage.value = ''
  deleteErrorMessage.value = ''
  deleteConfirmStep.value = false
  editForm.value = {
    name: user.name,
    phone_number: user.phone_number ? user.phone_number.replace(/^98/, '0') : '',
  }
}

function closeEditModal() {
  if (isUpdating.value || isDeleting.value) return
  editingUser.value = null
  updateErrorMessage.value = ''
  deleteErrorMessage.value = ''
  deleteConfirmStep.value = false
}

async function submitEdit() {
  if (!editingUser.value) return
  isUpdating.value = true
  updateErrorMessage.value = ''
  try {
    const payload: AdminUserUpdateRequest = {
      name: editForm.value.name.trim(),
      phone_number: editForm.value.phone_number.trim() || '',
    }
    const updatedUser = await apiRequest<AdminUserListItem>(
      `/admin/users/${editingUser.value.id}`,
      {
        method: 'PATCH',
        body: JSON.stringify(payload),
      },
      adminAuthStore.accessToken,
    )
    if (response.value) {
      response.value.items = response.value.items.map((item) => (item.id === updatedUser.id ? updatedUser : item))
    }
    closeEditModal()
  } catch (error) {
    if (error instanceof ApiError && error.status === 401) {
      adminAuthStore.logout()
      await router.replace('/login')
      return
    }
    updateErrorMessage.value = error instanceof ApiError ? error.message : 'بروزرسانی کاربر ناموفق بود.'
  } finally {
    isUpdating.value = false
  }
}

function requestDeleteConfirmation() {
  deleteErrorMessage.value = ''
  deleteConfirmStep.value = true
}

async function submitDelete() {
  if (!editingUser.value) return
  isDeleting.value = true
  deleteErrorMessage.value = ''
  try {
    await apiRequest<void>(
      `/admin/users/${editingUser.value.id}`,
      {
        method: 'DELETE',
      },
      adminAuthStore.accessToken,
    )
    if (response.value) {
      response.value.items = response.value.items.filter((item) => item.id !== editingUser.value?.id)
      response.value.pagination.total = Math.max(0, response.value.pagination.total - 1)
      response.value.summary.total_users = Math.max(0, response.value.summary.total_users - 1)
      response.value.summary.must_change_password_count = Math.max(
        0,
        response.value.summary.must_change_password_count - (editingUser.value.must_change_password ? 1 : 0),
      )
    }
    closeEditModal()
  } catch (error) {
    if (error instanceof ApiError && error.status === 401) {
      adminAuthStore.logout()
      await router.replace('/login')
      return
    }
    deleteErrorMessage.value = error instanceof ApiError ? error.message : 'حذف کاربر ناموفق بود.'
  } finally {
    isDeleting.value = false
  }
}
</script>

<template>
  <main class="dashboard-shell">
    <header class="dashboard-hero">
      <div>
        <span class="eyebrow">پنل مدیریت کاربران</span>
        <h1>لیست کاربران Splitwise</h1>
        <p>
          مانیتورینگ کاربران ثبت‌شده، بررسی وضعیت تغییر رمز، و مرور سریع آمار هر کاربر در یک نمای واحد.
        </p>
      </div>

      <div class="dashboard-hero__actions">
        <div class="profile-pill">
          <span>ادمین فعال</span>
          <strong>{{ adminAuthStore.admin?.username }}</strong>
        </div>
        <button class="ghost-button" type="button" @click="router.push('/settings')">تنظیمات پیامک</button>
        <button class="ghost-button" type="button" @click="logout">خروج</button>
      </div>
    </header>

    <section class="summary-grid">
      <SummaryCard
        label="کل کاربران"
        :value="formatNumber(response?.summary.total_users ?? 0)"
        tone="accent"
      />
      <SummaryCard
        label="نیازمند تغییر رمز"
        :value="formatNumber(response?.summary.must_change_password_count ?? 0)"
        tone="warning"
      />
      <SummaryCard
        label="نمایش در این صفحه"
        :value="formatNumber(visibleCount)"
      />
    </section>

    <section class="filters-card">
      <form class="filters-grid" @submit.prevent="submitSearch">
        <label class="field field--search">
          <span>جست‌وجو</span>
          <input
            v-model.trim="searchDraft"
            type="search"
            placeholder="جست‌وجو با نام یا نام کاربری"
          />
        </label>

        <label class="field">
          <span>وضعیت رمز</span>
          <select
            :value="filters.must_change_password"
            @change="updateFilters({ must_change_password: ($event.target as HTMLSelectElement).value as AdminUserListFilters['must_change_password'], page: 1 })"
          >
            <option value="all">همه</option>
            <option value="true">نیازمند تغییر رمز</option>
            <option value="false">عادی</option>
          </select>
        </label>

        <label class="field">
          <span>مرتب‌سازی</span>
          <select
            :value="filters.sort_by"
            @change="updateFilters({ sort_by: ($event.target as HTMLSelectElement).value as AdminUserListFilters['sort_by'] })"
          >
            <option value="created_at">تاریخ ساخت</option>
            <option value="updated_at">آخرین بروزرسانی</option>
            <option value="name">نام</option>
            <option value="username">نام کاربری</option>
            <option value="groups_count">تعداد گروه‌ها</option>
            <option value="active_refresh_tokens_count">توکن فعال</option>
          </select>
        </label>

        <label class="field">
          <span>جهت مرتب‌سازی</span>
          <select
            :value="filters.sort_order"
            @change="updateFilters({ sort_order: ($event.target as HTMLSelectElement).value as AdminUserListFilters['sort_order'] })"
          >
            <option value="desc">نزولی</option>
            <option value="asc">صعودی</option>
          </select>
        </label>

        <div class="filters-actions">
          <button class="primary-button" type="submit">اعمال جست‌وجو</button>
          <button class="ghost-button" type="button" @click="clearSearch">حذف جست‌وجو</button>
        </div>
      </form>
    </section>

    <section v-if="errorMessage" class="state-card state-card--error">
      <strong>خطا در دریافت داده</strong>
      <p>{{ errorMessage }}</p>
    </section>

    <section v-else-if="loading" class="state-card">
      <strong>در حال بارگذاری کاربران...</strong>
      <p>داده‌های API در حال دریافت هستند.</p>
    </section>

    <section v-else-if="response && response.items.length === 0" class="state-card">
      <strong>کاربری پیدا نشد</strong>
      <p>فیلترها یا عبارت جست‌وجو را تغییر بده.</p>
    </section>

    <section v-else-if="response" class="users-section">
      <div class="users-table-wrap">
        <table class="users-table">
          <thead>
            <tr>
              <th>کاربر</th>
              <th>شماره تلفن</th>
              <th>وضعیت</th>
              <th>گروه‌ها</th>
              <th>توکن فعال</th>
              <th>تاریخ ساخت</th>
              <th>آخرین بروزرسانی</th>
              <th>عملیات</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="user in response.items" :key="user.id">
              <td>
                <div class="user-cell">
                  <strong>{{ user.name }}</strong>
                  <span>@{{ user.username }}</span>
                  <small>{{ user.id }}</small>
                </div>
              </td>
              <td>
                <span class="user-phone">{{ displayPhoneNumber(user.phone_number) }}</span>
                <small class="user-phone-verified">{{ displayPhoneVerificationStatus(user.is_phone_verified) }}</small>
              </td>
              <td><StatusBadge :active="user.must_change_password" /></td>
              <td>{{ formatNumber(user.groups_count) }}</td>
              <td>{{ formatNumber(user.active_refresh_tokens_count) }}</td>
              <td>{{ formatDate(user.created_at) }}</td>
              <td>{{ formatDate(user.updated_at) }}</td>
              <td>
                <div class="users-actions-cell">
                  <button class="ghost-button users-edit-button" type="button" @click="openEditModal(user)">ویرایش</button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <div class="user-cards">
        <article v-for="user in response.items" :key="user.id" class="user-card">
          <div class="user-card__header">
            <div>
              <h2>{{ user.name }}</h2>
              <p>@{{ user.username }}</p>
              <small class="user-card__phone">{{ displayPhoneNumber(user.phone_number) }}</small>
              <small class="user-card__phone user-card__phone--status">{{ displayPhoneVerificationStatus(user.is_phone_verified) }}</small>
            </div>
            <StatusBadge :active="user.must_change_password" />
          </div>

          <dl class="user-card__stats">
            <div>
              <dt>شناسه</dt>
              <dd>{{ user.id }}</dd>
            </div>
            <div>
              <dt>گروه‌ها</dt>
              <dd>{{ formatNumber(user.groups_count) }}</dd>
            </div>
            <div>
              <dt>توکن فعال</dt>
              <dd>{{ formatNumber(user.active_refresh_tokens_count) }}</dd>
            </div>
            <div>
              <dt>تاریخ ساخت</dt>
              <dd>{{ formatDate(user.created_at) }}</dd>
            </div>
            <div>
              <dt>آخرین بروزرسانی</dt>
              <dd>{{ formatDate(user.updated_at) }}</dd>
            </div>
          </dl>
          <button class="ghost-button users-edit-button users-edit-button--card" type="button" @click="openEditModal(user)">ویرایش کاربر</button>
        </article>
      </div>

      <footer class="pagination-bar">
        <span>صفحه {{ formatNumber(filters.page) }} از {{ formatNumber(totalPages) }}</span>
        <div class="pagination-bar__actions">
          <button
            class="ghost-button"
            type="button"
            :disabled="filters.page <= 1"
            @click="updateFilters({ page: filters.page - 1 })"
          >
            صفحه قبل
          </button>
          <button
            class="ghost-button"
            type="button"
            :disabled="filters.page >= totalPages"
            @click="updateFilters({ page: filters.page + 1 })"
          >
            صفحه بعد
          </button>
        </div>
      </footer>
    </section>

    <div v-if="editingUser" class="modal-backdrop" @click.self="closeEditModal">
      <div class="modal-card" role="dialog" aria-modal="true">
        <div class="modal-card__header">
          <div></div>
          <strong>ویرایش کاربر</strong>
          <button class="ghost-button users-modal-close" type="button" :disabled="isUpdating || isDeleting" @click="closeEditModal">بستن</button>
        </div>
        <div class="modal-card__body">
          <div class="field">
            <span>نام</span>
            <input v-model.trim="editForm.name" type="text" :disabled="isUpdating" />
          </div>
          <div class="field">
            <span>شماره تلفن</span>
            <input v-model.trim="editForm.phone_number" type="text" inputmode="numeric" placeholder="09120000000" :disabled="isUpdating" />
          </div>
          <p class="user-edit-help">برای حذف شماره تلفن، فیلد را خالی بگذار.</p>
          <p v-if="updateErrorMessage" class="inline-error">{{ updateErrorMessage }}</p>
          <div class="user-delete-card">
            <div class="user-delete-card__copy">
              <strong>حذف کاربر</strong>
              <p>این عملیات برگشت‌پذیر نیست و اطلاعات کاربر از سیستم حذف می‌شود.</p>
            </div>
            <button
              v-if="!deleteConfirmStep"
              class="danger-button"
              type="button"
              :disabled="isUpdating || isDeleting"
              @click="requestDeleteConfirmation"
            >
              حذف کاربر
            </button>
            <div v-else class="user-delete-card__confirm">
              <p>از حذف این کاربر مطمئنی؟</p>
              <div class="user-delete-card__actions">
                <button class="ghost-button" type="button" :disabled="isDeleting" @click="deleteConfirmStep = false">لغو حذف</button>
                <button class="danger-button" type="button" :disabled="isDeleting" @click="submitDelete">
                  {{ isDeleting ? 'در حال حذف...' : 'تایید حذف' }}
                </button>
              </div>
            </div>
          </div>
          <p v-if="deleteErrorMessage" class="inline-error">{{ deleteErrorMessage }}</p>
          <div class="users-modal-actions">
            <button class="ghost-button" type="button" :disabled="isUpdating || isDeleting" @click="closeEditModal">انصراف</button>
            <button class="primary-button" type="button" :disabled="isUpdating || isDeleting" @click="submitEdit">
              {{ isUpdating ? 'در حال ذخیره...' : 'ذخیره تغییرات' }}
            </button>
          </div>
        </div>
      </div>
    </div>
  </main>
</template>

<style scoped>
.users-actions-cell {
  display: flex;
  justify-content: flex-start;
}

.user-delete-card {
  display: grid;
  gap: 12px;
  padding: 16px;
  border: 1px solid rgba(239, 68, 68, 0.24);
  border-radius: 18px;
  background: rgba(239, 68, 68, 0.08);
}

.user-delete-card__copy {
  display: grid;
  gap: 6px;
}

.user-delete-card__copy p,
.user-delete-card__confirm p {
  margin: 0;
  color: rgba(255, 255, 255, 0.74);
}

.user-delete-card__confirm {
  display: grid;
  gap: 10px;
}

.user-delete-card__actions {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}

.danger-button {
  border: 0;
  border-radius: 14px;
  min-height: 44px;
  padding: 0 16px;
  background: linear-gradient(135deg, #ef4444, #dc2626);
  color: #fff;
  font: inherit;
  cursor: pointer;
}

.danger-button:disabled {
  opacity: 0.65;
  cursor: default;
}
</style>
