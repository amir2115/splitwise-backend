<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'

import { ApiError, apiRequest } from '@/shared/api/client'
import { adminAuthStore } from '@/shared/auth/store'
import type {
  AppReleaseApkUploadResponse,
  AppReleaseCreateRequest,
  AppReleaseItem,
  AppReleaseListResponse,
} from '@/shared/types/api'
import { formatDate, formatNumber } from '@/shared/utils/format'

const router = useRouter()

const loading = ref(false)
const saving = ref(false)
const uploadingId = ref('')
const publishingId = ref('')
const errorMessage = ref('')
const successMessage = ref('')
const releases = ref<AppReleaseItem[]>([])
const selectedFiles = ref<Record<string, File | null>>({})
const createSelectedFile = ref<File | null>(null)
const createApkDragDepth = ref(0)
const isDraggingCreateApk = ref(false)
const form = ref({
  title: 'دانلود اپلیکیشن',
  subtitle: 'آخرین نسخه دنگینو را از کافه بازار، مایکت یا لینک مستقیم نصب کن.',
  app_icon_url: 'https://splitwise.ir/android-chrome-512x512.png',
  version_name: '',
  version_code: null as number | null,
  release_date: '',
  file_size: '',
  bazaar_url: 'https://cafebazaar.ir/app/com.encer.splitwise',
  myket_url: 'https://myket.ir/app/com.encer.splitwise',
  release_notes: '',
  primary_badge_text: 'نسخه جدید',
  min_supported_version_code: null as number | null,
  update_mode: 'soft' as 'none' | 'soft' | 'hard',
  update_title: '',
  update_message: '',
})

const publishedRelease = computed(() => releases.value.find((release) => release.is_published) ?? null)

onMounted(() => {
  void fetchReleases()
})

function handleAuthError(error: unknown) {
  if (error instanceof ApiError && error.status === 401) {
    adminAuthStore.logout()
    void router.replace('/login')
    return true
  }
  return false
}

async function fetchReleases() {
  loading.value = true
  errorMessage.value = ''
  try {
    const response = await apiRequest<AppReleaseListResponse>(
      '/admin/app-releases',
      { method: 'GET' },
      adminAuthStore.accessToken,
    )
    releases.value = response.items
  } catch (error) {
    if (handleAuthError(error)) return
    errorMessage.value = error instanceof ApiError ? error.message : 'دریافت نسخه‌ها ناموفق بود.'
  } finally {
    loading.value = false
  }
}

function buildCreatePayload(): AppReleaseCreateRequest {
  const notes = form.value.release_notes
    .split('\n')
    .map((item) => item.trim())
    .filter(Boolean)
  return {
    title: form.value.title.trim(),
    subtitle: form.value.subtitle.trim(),
    app_icon_url: form.value.app_icon_url.trim() || null,
    version_name: form.value.version_name.trim(),
    version_code: Number(form.value.version_code),
    release_date: form.value.release_date || null,
    file_size: form.value.file_size.trim() || null,
    bazaar_url: form.value.bazaar_url.trim() || null,
    myket_url: form.value.myket_url.trim() || null,
    release_notes: notes,
    primary_badge_text: form.value.primary_badge_text.trim() || null,
    min_supported_version_code: form.value.min_supported_version_code,
    update_mode: form.value.update_mode,
    update_title: form.value.update_title.trim() || null,
    update_message: form.value.update_message.trim() || null,
  }
}

async function createRelease() {
  if (!createSelectedFile.value) {
    errorMessage.value = 'ابتدا فایل APK نسخه جدید را انتخاب کن.'
    return
  }

  saving.value = true
  errorMessage.value = ''
  successMessage.value = ''
  let createdRelease: AppReleaseItem | null = null
  try {
    createdRelease = await apiRequest<AppReleaseItem>(
      '/admin/app-releases',
      { method: 'POST', body: JSON.stringify(buildCreatePayload()) },
      adminAuthStore.accessToken,
    )

    const data = new FormData()
    data.set('file', createSelectedFile.value)
    const response = await apiRequest<AppReleaseApkUploadResponse>(
      `/admin/app-releases/${createdRelease.id}/apk`,
      { method: 'POST', body: data },
      adminAuthStore.accessToken,
    )

    successMessage.value = `نسخه جدید ساخته شد و APK در ${response.apk_object_key} آپلود شد.`
    form.value = {
      title: 'دانلود اپلیکیشن',
      subtitle: 'آخرین نسخه دنگینو را از کافه بازار، مایکت یا لینک مستقیم نصب کن.',
      app_icon_url: 'https://splitwise.ir/android-chrome-512x512.png',
      version_name: '',
      version_code: null,
      release_date: '',
      file_size: '',
      bazaar_url: 'https://cafebazaar.ir/app/com.encer.splitwise',
      myket_url: 'https://myket.ir/app/com.encer.splitwise',
      release_notes: '',
      primary_badge_text: 'نسخه جدید',
      min_supported_version_code: null,
      update_mode: 'soft',
      update_title: '',
      update_message: '',
    }
    createSelectedFile.value = null
    await fetchReleases()
  } catch (error) {
    if (handleAuthError(error)) return
    const fallback = createdRelease ? 'نسخه ساخته شد، اما آپلود APK ناموفق بود.' : 'ساخت نسخه ناموفق بود.'
    errorMessage.value = error instanceof ApiError ? error.message : fallback
    if (createdRelease) {
      await fetchReleases()
    }
  } finally {
    saving.value = false
  }
}

function selectCreateApk(file: File | null) {
  if (!file) return
  if (!file.name.toLowerCase().endsWith('.apk')) {
    errorMessage.value = 'فرمت فایل باید APK باشد.'
    return
  }
  createSelectedFile.value = file
  errorMessage.value = ''
}

function onCreateApkInput(event: Event) {
  const input = event.target as HTMLInputElement
  selectCreateApk(input.files?.[0] ?? null)
}

function onCreateApkDragEnter() {
  createApkDragDepth.value += 1
  isDraggingCreateApk.value = true
}

function onCreateApkDragLeave() {
  createApkDragDepth.value = Math.max(0, createApkDragDepth.value - 1)
  isDraggingCreateApk.value = createApkDragDepth.value > 0
}

function onCreateApkDrop(event: DragEvent) {
  createApkDragDepth.value = 0
  isDraggingCreateApk.value = false
  selectCreateApk(event.dataTransfer?.files?.[0] ?? null)
}

function clearCreateApk() {
  createSelectedFile.value = null
}

function onFileInput(releaseId: string, event: Event) {
  const input = event.target as HTMLInputElement
  selectedFiles.value = { ...selectedFiles.value, [releaseId]: input.files?.[0] ?? null }
}

async function uploadApk(release: AppReleaseItem) {
  const file = selectedFiles.value[release.id]
  if (!file) {
    errorMessage.value = 'ابتدا فایل APK را انتخاب کن.'
    return
  }
  uploadingId.value = release.id
  errorMessage.value = ''
  successMessage.value = ''
  try {
    const data = new FormData()
    data.set('file', file)
    const response = await apiRequest<AppReleaseApkUploadResponse>(
      `/admin/app-releases/${release.id}/apk`,
      { method: 'POST', body: data },
      adminAuthStore.accessToken,
    )
    successMessage.value = `APK در ${response.apk_object_key} آپلود شد.`
    selectedFiles.value = { ...selectedFiles.value, [release.id]: null }
    await fetchReleases()
  } catch (error) {
    if (handleAuthError(error)) return
    errorMessage.value = error instanceof ApiError ? error.message : 'آپلود APK ناموفق بود.'
  } finally {
    uploadingId.value = ''
  }
}

async function publishRelease(release: AppReleaseItem) {
  publishingId.value = release.id
  errorMessage.value = ''
  successMessage.value = ''
  try {
    await apiRequest<AppReleaseItem>(
      `/admin/app-releases/${release.id}/publish`,
      { method: 'POST' },
      adminAuthStore.accessToken,
    )
    successMessage.value = `نسخه ${release.version_name} منتشر شد و لینک سایت به‌روزرسانی شد.`
    await fetchReleases()
  } catch (error) {
    if (handleAuthError(error)) return
    errorMessage.value = error instanceof ApiError ? error.message : 'انتشار نسخه ناموفق بود.'
  } finally {
    publishingId.value = ''
  }
}
</script>

<template>
  <main class="dashboard-shell app-releases-page">
    <header class="dashboard-hero">
      <div>
        <span class="eyebrow">تاریخچه نسخه‌های اپ</span>
        <h1>نسخه‌های اپ</h1>
        <p>نسخه جدید بساز، APK مستقیم را آپلود کن، و نسخه منتشرشده سایت را از همین‌جا تغییر بده.</p>
      </div>
    </header>

    <section v-if="errorMessage" class="state-card state-card--error">
      <strong>خطا</strong>
      <p>{{ errorMessage }}</p>
    </section>
    <section v-if="successMessage" class="state-card state-card--success">
      <strong>انجام شد</strong>
      <p>{{ successMessage }}</p>
    </section>

    <section class="release-grid">
      <form class="filters-card release-form" @submit.prevent="createRelease">
        <div class="panel-heading">
          <div>
            <strong>نسخه جدید</strong>
            <span>metadata نسخه و فایل APK را ثبت کن تا با ساخت نسخه روی آروان آپلود شود.</span>
          </div>
        </div>

        <label class="field">
          <span>TITLE</span>
          <input v-model.trim="form.title" type="text" required />
        </label>
        <label class="field">
          <span>SUBTITLE</span>
          <input v-model.trim="form.subtitle" type="text" required />
        </label>
        <label class="field">
          <span>APP_ICON_URL</span>
          <input v-model.trim="form.app_icon_url" type="url" placeholder="https://splitwise.ir/android-chrome-512x512.png" />
        </label>

        <label class="field">
          <span>VERSION_NAME</span>
          <input v-model.trim="form.version_name" type="text" placeholder="1.4.0" required />
        </label>
        <label class="field">
          <span>VERSION_CODE</span>
          <input v-model.number="form.version_code" type="number" min="0" inputmode="numeric" required />
        </label>
        <label class="field">
          <span>RELEASE_DATE</span>
          <input v-model="form.release_date" type="date" />
        </label>
        <label class="field">
          <span>FILE_SIZE</span>
          <input v-model.trim="form.file_size" type="text" placeholder="18.4 MB" />
        </label>
        <label class="field">
          <span>BAZAAR_URL</span>
          <input v-model.trim="form.bazaar_url" type="url" placeholder="https://cafebazaar.ir/app/..." />
        </label>
        <label class="field">
          <span>MYKET_URL</span>
          <input v-model.trim="form.myket_url" type="url" placeholder="https://myket.ir/app/..." />
        </label>
        <label class="field">
          <span>PRIMARY_BADGE_TEXT</span>
          <input v-model.trim="form.primary_badge_text" type="text" placeholder="نسخه جدید" />
        </label>
        <label class="field">
          <span>MIN_SUPPORTED_VERSION_CODE</span>
          <input v-model.number="form.min_supported_version_code" type="number" min="0" inputmode="numeric" />
        </label>
        <label class="field">
          <span>UPDATE_MODE</span>
          <select v-model="form.update_mode">
            <option value="none">none</option>
            <option value="soft">soft</option>
            <option value="hard">hard</option>
          </select>
        </label>
        <label class="field">
          <span>UPDATE_TITLE</span>
          <input v-model.trim="form.update_title" type="text" placeholder="نسخه جدید آماده است" />
        </label>
        <label class="field">
          <span>UPDATE_MESSAGE</span>
          <input v-model.trim="form.update_message" type="text" placeholder="برای نصب نسخه جدید روی لینک دانلود بزن." />
        </label>
        <label class="field">
          <span>RELEASE_NOTES</span>
          <textarea v-model="form.release_notes" rows="6" placeholder="هر خط یک تغییر" required></textarea>
        </label>
        <div
          :class="['apk-dropzone', isDraggingCreateApk && 'apk-dropzone--active']"
          @dragenter.prevent.stop="onCreateApkDragEnter"
          @dragover.prevent.stop="isDraggingCreateApk = true"
          @dragleave.prevent.stop="onCreateApkDragLeave"
          @drop.prevent.stop="onCreateApkDrop"
        >
          <div class="apk-dropzone__copy">
            <strong>APK نسخه جدید</strong>
            <span>{{ createSelectedFile?.name || 'فایل APK را اینجا بکش یا انتخاب کن.' }}</span>
          </div>
          <input id="create-release-apk" type="file" accept=".apk,application/vnd.android.package-archive" @change="onCreateApkInput" />
          <label class="ghost-button" for="create-release-apk">انتخاب APK</label>
        </div>
        <div v-if="createSelectedFile" class="selected-apk-row">
          <span>{{ createSelectedFile.name }}</span>
          <button class="ghost-button" type="button" @click="clearCreateApk">حذف فایل</button>
        </div>
        <button class="primary-button" type="submit" :disabled="saving">
          {{ saving ? 'در حال ساخت و آپلود...' : 'ساخت نسخه و آپلود APK' }}
        </button>
      </form>

      <section class="filters-card releases-list-card">
        <div class="panel-heading">
          <div>
            <strong>نسخه‌ها</strong>
            <span v-if="publishedRelease">نسخه منتشرشده: {{ publishedRelease.version_name }}</span>
            <span v-else>هنوز نسخه‌ای منتشر نشده است.</span>
          </div>
          <button class="ghost-button" type="button" :disabled="loading" @click="fetchReleases">بازخوانی</button>
        </div>

        <section v-if="loading" class="state-card">
          <strong>در حال بارگذاری...</strong>
          <p>لیست نسخه‌ها در حال دریافت است.</p>
        </section>
        <div v-else class="release-list">
          <article v-for="release in releases" :key="release.id" class="release-card">
            <header class="release-card__header">
              <div>
                <span :class="['release-status', release.is_published && 'release-status--published']">
                  {{ release.is_published ? 'منتشرشده' : 'آماده انتشار' }}
                </span>
                <h2>{{ release.version_name }}</h2>
                <p>
                  code {{ formatNumber(release.version_code) }}
                  <template v-if="release.release_date"> · {{ formatDate(release.release_date) }}</template>
                  <template v-if="release.file_size"> · {{ release.file_size }}</template>
                </p>
              </div>
              <a v-if="release.apk_url" class="ghost-button" :href="release.apk_url" target="_blank" rel="noreferrer">دانلود</a>
            </header>

            <ul class="release-notes">
              <li v-for="note in release.release_notes" :key="note">{{ note }}</li>
            </ul>

            <div class="release-actions">
              <label class="file-picker">
                <input type="file" accept=".apk,application/vnd.android.package-archive" @change="onFileInput(release.id, $event)" />
                <span>{{ selectedFiles[release.id]?.name || 'انتخاب APK' }}</span>
              </label>
              <button class="ghost-button" type="button" :disabled="uploadingId === release.id" @click="uploadApk(release)">
                {{ uploadingId === release.id ? 'در حال آپلود...' : 'آپلود APK' }}
              </button>
              <button class="primary-button" type="button" :disabled="!release.apk_url || publishingId === release.id" @click="publishRelease(release)">
                {{ publishingId === release.id ? 'در حال انتشار...' : 'انتشار' }}
              </button>
            </div>
          </article>
          <section v-if="releases.length === 0" class="state-card">
            <strong>نسخه‌ای ثبت نشده</strong>
            <p>از فرم سمت راست اولین نسخه را بساز.</p>
          </section>
        </div>
      </section>
    </section>
  </main>
</template>

<style scoped>
.release-grid {
  display: grid;
  grid-template-columns: 360px minmax(0, 1fr);
  gap: 18px;
  align-items: start;
}

.release-form,
.releases-list-card {
  min-width: 0;
}

.release-form {
  position: sticky;
  top: 18px;
}

.panel-heading,
.release-card__header,
.release-actions {
  display: flex;
  gap: 12px;
  align-items: flex-start;
  justify-content: space-between;
}

.panel-heading {
  margin-bottom: 14px;
}

.panel-heading div,
.release-list {
  display: grid;
  gap: 10px;
}

.panel-heading span,
.release-card p {
  color: var(--color-text-soft);
  font-size: 12px;
}

.field textarea {
  width: 100%;
  resize: vertical;
}

.apk-dropzone {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 12px;
  align-items: center;
  border: 1px dashed var(--color-border);
  border-radius: 14px;
  padding: 14px;
  background: rgba(255, 255, 255, 0.03);
  transition:
    border-color 0.2s ease,
    background 0.2s ease;
}

.apk-dropzone--active {
  border-color: var(--color-primary);
  background: rgba(98, 179, 255, 0.1);
}

.apk-dropzone input {
  display: none;
}

.apk-dropzone__copy {
  display: grid;
  gap: 4px;
  min-width: 0;
}

.apk-dropzone__copy strong,
.selected-apk-row span {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.apk-dropzone__copy span {
  color: var(--color-text-soft);
  font-size: 12px;
}

.selected-apk-row {
  display: flex;
  gap: 10px;
  align-items: center;
  justify-content: space-between;
  color: var(--color-text-soft);
  font-size: 12px;
}

.release-card {
  border: 1px solid var(--color-border);
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.04);
  padding: 14px;
}

.release-card h2 {
  margin: 8px 0 6px;
  font-size: 18px;
  line-height: 1.4;
}

.release-card p {
  margin: 0;
}

.release-status {
  display: inline-flex;
  align-items: center;
  min-height: 28px;
  border-radius: 999px;
  padding: 0 10px;
  background: rgba(255, 184, 107, 0.12);
  color: var(--color-warning);
  font-size: 12px;
}

.release-status--published {
  background: rgba(99, 230, 190, 0.12);
  color: var(--color-success);
}

.release-notes {
  margin: 14px 0;
  padding-inline-start: 22px;
  color: var(--color-text-soft);
  line-height: 1.9;
}

.release-actions {
  align-items: center;
  flex-wrap: wrap;
  justify-content: flex-start;
}

.file-picker input {
  display: none;
}

.file-picker span {
  display: inline-flex;
  align-items: center;
  min-height: 40px;
  border: 1px solid var(--color-border);
  border-radius: 12px;
  padding: 0 12px;
  color: var(--color-text-soft);
  cursor: pointer;
}

@media (max-width: 1040px) {
  .release-grid {
    grid-template-columns: 1fr;
  }

  .release-form {
    position: static;
  }
}
</style>
