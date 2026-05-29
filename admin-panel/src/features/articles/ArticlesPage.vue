<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'

import { ApiError, apiRequest } from '@/shared/api/client'
import { adminAuthStore } from '@/shared/auth/store'
import SummaryCard from '@/shared/components/SummaryCard.vue'
import type {
  AdminArticleDetailResponse,
  AdminArticleListResponse,
  ArticleImageUploadResponse,
  ArticlePayload,
} from '@/shared/types/api'
import { formatDate, formatNumber } from '@/shared/utils/format'

const router = useRouter()

const loading = ref(false)
const submitting = ref(false)
const uploadPreviewUrl = ref('')
const errorMessage = ref('')
const successMessage = ref('')
const listErrorMessage = ref('')
const response = ref<AdminArticleListResponse | null>(null)
const selectedImage = ref<File | null>(null)
const isDraggingImage = ref(false)
const imageDragDepth = ref(0)
const search = ref('')
const statusFilter = ref<'all' | 'draft' | 'published' | 'archived'>('all')
const categoryFilter = ref('')
const page = ref(1)
const pageSize = ref(10)
const articleJson = ref(`{
  "slug": "article-slug",
  "status": "draft",
  "category_slug": "guides",
  "author_slug": "dongino-editorial",
  "title": "عنوان مقاله",
  "summary": "خلاصه کوتاه مقاله",
  "tldr": "پاسخ سریع مقاله",
  "hero_icon": "✦",
  "hero_image_url": null,
  "reading_minutes": 6,
  "published_at": null,
  "audience": ["مخاطب هدف"],
  "body": [
    { "kind": "heading", "level": 2, "id": "why-matters", "text": "چرا مهم است؟" },
    { "kind": "prose", "paragraphs": ["متن پاراگراف اول."] }
  ],
  "related_slugs": [],
  "seo": {
    "meta_title": "عنوان سئو",
    "meta_description": "توضیح متای مقاله",
    "canonical_url": "https://splitwise.ir/articles/article-slug/",
    "og_image_url": null
  }
}`)
const sideForm = ref({
  category_slug: '',
  category_name: '',
  category_display_order: 0,
  status: 'draft' as ArticlePayload['status'],
  author_slug: 'dongino-editorial',
})

const parsedArticle = computed(() => parseArticleJson(articleJson.value))
const validationErrors = computed(() => parsedArticle.value.errors)
const articlePayload = computed(() => parsedArticle.value.payload)
const hasValidPayload = computed(() => Boolean(articlePayload.value) && validationErrors.value.length === 0)
const totalPages = computed(() => {
  if (!response.value) return 1
  return Math.max(1, Math.ceil(response.value.pagination.total / response.value.pagination.page_size))
})

watch(articlePayload, (payload) => {
  if (!payload) return
  sideForm.value.category_slug = payload.category_slug || sideForm.value.category_slug
  sideForm.value.status = payload.status || sideForm.value.status
  sideForm.value.author_slug = payload.author_slug || sideForm.value.author_slug
}, { immediate: true })

watch([search, statusFilter, categoryFilter], () => {
  page.value = 1
  void fetchArticles()
})

onMounted(() => {
  void fetchArticles()
})

onBeforeUnmount(() => {
  revokePreview()
})

function parseArticleJson(raw: string): { payload: ArticlePayload | null; errors: string[] } {
  const errors: string[] = []
  let value: unknown
  try {
    value = JSON.parse(raw)
  } catch {
    return { payload: null, errors: ['JSON معتبر نیست. کوتیشن، کاما و براکت‌ها را بررسی کن.'] }
  }
  if (!value || typeof value !== 'object' || Array.isArray(value)) {
    return { payload: null, errors: ['ریشه JSON باید یک object مقاله باشد.'] }
  }
  const payload = value as Partial<ArticlePayload> & Record<string, unknown>
  const requiredStringFields = ['slug', 'category_slug', 'author_slug', 'title', 'summary', 'tldr', 'hero_icon'] as const
  for (const field of requiredStringFields) {
    if (typeof payload[field] !== 'string' || !payload[field]?.trim()) errors.push(`${field} الزامی است.`)
  }
  if (!['draft', 'published', 'archived'].includes(String(payload.status))) errors.push('status باید draft، published یا archived باشد.')
  if (typeof payload.reading_minutes !== 'number') errors.push('reading_minutes باید عدد باشد.')
  if (!Array.isArray(payload.audience)) errors.push('audience باید آرایه باشد.')
  if (!Array.isArray(payload.related_slugs)) errors.push('related_slugs باید آرایه باشد.')
  if (!Array.isArray(payload.body) || payload.body.length === 0) errors.push('body باید آرایه غیرخالی باشد.')
  if (!payload.seo || typeof payload.seo !== 'object' || Array.isArray(payload.seo)) errors.push('seo باید object باشد.')
  if (Array.isArray(payload.body)) {
    payload.body.forEach((block, index) => {
      if (!block || typeof block !== 'object' || Array.isArray(block)) {
        errors.push(`body[${index}] باید object باشد.`)
        return
      }
      const item = block as Record<string, unknown>
      if (typeof item.kind !== 'string') errors.push(`body[${index}].kind الزامی است.`)
      if (item.kind !== 'heading' && 'text' in item) {
        errors.push(`body[${index}] از فیلد قدیمی text استفاده کرده؛ برای prose از paragraphs و برای callout از body استفاده کن.`)
      }
      if ('tone' in item) errors.push(`body[${index}] از tone استفاده کرده؛ مقدار درست callout.variant است.`)
      if ('q' in item || 'a' in item) errors.push(`body[${index}] FAQ باید question/answer داشته باشد، نه q/a.`)

      if (item.kind === 'heading') {
        if (!isFilledString(item.id)) errors.push(`body[${index}] heading باید id داشته باشد.`)
        if (!isFilledString(item.text)) errors.push(`body[${index}] heading باید text داشته باشد.`)
      }
      if (item.kind === 'prose') {
        if (!Array.isArray(item.paragraphs) || item.paragraphs.length === 0) {
          errors.push(`body[${index}] prose باید paragraphs غیرخالی داشته باشد.`)
        }
      }
      if (item.kind === 'callout') {
        if (!['tip', 'warning', 'note', 'highlight'].includes(String(item.variant)) || !isFilledString(item.body)) {
          errors.push(`body[${index}] callout باید variant معتبر و body داشته باشد.`)
        }
      }
      if (item.kind === 'scenario') {
        if (!Array.isArray(item.rows) || item.rows.length === 0) {
          errors.push(`body[${index}] scenario باید rows غیرخالی داشته باشد.`)
        } else {
          item.rows.forEach((row, rowIndex) => {
            if (!isRecord(row) || !isFilledString(row.label) || !isFilledString(row.value)) {
              errors.push(`body[${index}].rows[${rowIndex}] باید label و value داشته باشد.`)
            }
          })
        }
      }
      if (item.kind === 'steps') {
        if (!Array.isArray(item.steps) || item.steps.length === 0) {
          errors.push(`body[${index}] steps باید steps غیرخالی داشته باشد، نه items.`)
        } else {
          item.steps.forEach((step, stepIndex) => {
            if (!isRecord(step) || !isFilledString(step.title) || !isFilledString(step.body)) {
              errors.push(`body[${index}].steps[${stepIndex}] باید title و body داشته باشد.`)
            }
          })
        }
      }
      if (item.kind === 'comparison') {
        if (!Array.isArray(item.options) || item.options.length === 0) {
          errors.push(`body[${index}] comparison باید options غیرخالی داشته باشد.`)
        } else {
          item.options.forEach((option, optionIndex) => {
            if (!isRecord(option)) {
              errors.push(`body[${index}].options[${optionIndex}] باید object باشد.`)
              return
            }
            if ('title' in option || 'body' in option) {
              errors.push(`body[${index}].options[${optionIndex}] از title/body استفاده کرده؛ comparison option باید label, pros و cons داشته باشد.`)
            }
            if (!isFilledString(option.label)) {
              errors.push(`body[${index}].options[${optionIndex}].label الزامی است.`)
            }
            if (!Array.isArray(option.pros) || option.pros.length === 0) {
              errors.push(`body[${index}].options[${optionIndex}].pros باید آرایه غیرخالی باشد.`)
            }
            if ('cons' in option && !Array.isArray(option.cons)) {
              errors.push(`body[${index}].options[${optionIndex}].cons باید آرایه باشد.`)
            }
          })
        }
      }
      if (item.kind === 'inline-cta' && (typeof item.title !== 'string' || !item.primary)) {
        errors.push(`body[${index}] inline-cta باید title و primary داشته باشد.`)
      }
      if (item.kind === 'inline-cta' && isRecord(item.primary)) {
        if (!isFilledString(item.primary.label) || !isFilledString(item.primary.href)) {
          errors.push(`body[${index}] inline-cta.primary باید label و href داشته باشد.`)
        }
      }
      if (item.kind === 'faq') {
        if (!Array.isArray(item.items) || item.items.length === 0) {
          errors.push(`body[${index}] faq باید items غیرخالی داشته باشد.`)
        } else {
          item.items.forEach((faqItem, faqIndex) => {
            if (!isRecord(faqItem) || !isFilledString(faqItem.question) || !isFilledString(faqItem.answer)) {
              errors.push(`body[${index}].items[${faqIndex}] باید question و answer داشته باشد.`)
            }
          })
        }
      }
    })
  }
  return { payload: errors.length ? null : (payload as ArticlePayload), errors }
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return Boolean(value) && typeof value === 'object' && !Array.isArray(value)
}

function isFilledString(value: unknown): value is string {
  return typeof value === 'string' && value.trim().length > 0
}

function buildPayload(): ArticlePayload {
  if (!articlePayload.value) throw new Error('invalid article payload')
  return {
    ...articlePayload.value,
    status: sideForm.value.status,
    category_slug: sideForm.value.category_slug.trim(),
    author_slug: sideForm.value.author_slug.trim(),
  }
}

async function fetchArticles() {
  loading.value = true
  listErrorMessage.value = ''
  try {
    const params = new URLSearchParams()
    if (search.value.trim()) params.set('search', search.value.trim())
    if (statusFilter.value !== 'all') params.set('status', statusFilter.value)
    if (categoryFilter.value.trim()) params.set('category', categoryFilter.value.trim())
    params.set('page', String(page.value))
    params.set('page_size', String(pageSize.value))
    response.value = await apiRequest<AdminArticleListResponse>(
      `/admin/articles?${params.toString()}`,
      { method: 'GET' },
      adminAuthStore.accessToken,
    )
  } catch (error) {
    if (error instanceof ApiError && error.status === 401) {
      adminAuthStore.logout()
      await router.replace('/login')
      return
    }
    listErrorMessage.value = error instanceof ApiError ? error.message : 'دریافت مقاله‌ها ناموفق بود.'
  } finally {
    loading.value = false
  }
}

async function submitArticle() {
  if (!hasValidPayload.value) return
  submitting.value = true
  errorMessage.value = ''
  successMessage.value = ''
  try {
    const payload = buildPayload()
    if (sideForm.value.category_slug.trim() && sideForm.value.category_name.trim()) {
      await createCategoryIfNeeded()
    }
    const existing = await findExistingArticle(payload.slug)
    const saved = existing
      ? await apiRequest<AdminArticleDetailResponse>(
          `/admin/articles/${existing.id}`,
          { method: 'PATCH', body: JSON.stringify(payload) },
          adminAuthStore.accessToken,
        )
      : await apiRequest<AdminArticleDetailResponse>(
          '/admin/articles',
          { method: 'POST', body: JSON.stringify(payload) },
          adminAuthStore.accessToken,
        )
    let upload: ArticleImageUploadResponse | null = null
    if (selectedImage.value) {
      const formData = new FormData()
      formData.set('file', selectedImage.value)
      upload = await apiRequest<ArticleImageUploadResponse>(
        `/admin/articles/${saved.id}/hero-image`,
        { method: 'POST', body: formData },
        adminAuthStore.accessToken,
      )
    }
    successMessage.value = upload
      ? `مقاله ذخیره شد و تصویر ${upload.filename} آپلود شد.`
      : `مقاله ${existing ? 'به‌روزرسانی' : 'ساخته'} شد.`
    await fetchArticles()
  } catch (error) {
    if (error instanceof ApiError && error.status === 401) {
      adminAuthStore.logout()
      await router.replace('/login')
      return
    }
    errorMessage.value = error instanceof ApiError ? error.message : 'ذخیره مقاله ناموفق بود.'
  } finally {
    submitting.value = false
  }
}

async function createCategoryIfNeeded() {
  try {
    await apiRequest(
      '/admin/categories',
      {
        method: 'POST',
        body: JSON.stringify({
          slug: sideForm.value.category_slug.trim(),
          name: sideForm.value.category_name.trim(),
          display_order: Number(sideForm.value.category_display_order) || 0,
        }),
      },
      adminAuthStore.accessToken,
    )
  } catch (error) {
    if (error instanceof ApiError && error.status === 409) return
    throw error
  }
}

async function findExistingArticle(slug: string): Promise<AdminArticleDetailResponse | null> {
  try {
    return await apiRequest<AdminArticleDetailResponse>(`/admin/articles/slug/${slug}`, { method: 'GET' }, adminAuthStore.accessToken)
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) return null
    throw error
  }
}

function selectImage(file: File | null) {
  if (!file) return
  if (!/\.(png|webp|jpe?g)$/i.test(file.name) && !['image/png', 'image/webp', 'image/jpeg'].includes(file.type)) {
    errorMessage.value = 'فرمت تصویر باید PNG، WebP یا JPG باشد.'
    return
  }
  selectedImage.value = file
  errorMessage.value = ''
  revokePreview()
  uploadPreviewUrl.value = URL.createObjectURL(file)
}

function onImageInput(event: Event) {
  const input = event.target as HTMLInputElement
  selectImage(input.files?.[0] ?? null)
}

function onImageDrop(event: DragEvent) {
  imageDragDepth.value = 0
  isDraggingImage.value = false
  selectImage(event.dataTransfer?.files?.[0] ?? null)
}

function onImageDragEnter() {
  imageDragDepth.value += 1
  isDraggingImage.value = true
}

function onImageDragLeave() {
  imageDragDepth.value = Math.max(0, imageDragDepth.value - 1)
  isDraggingImage.value = imageDragDepth.value > 0
}

function clearImage() {
  selectedImage.value = null
  revokePreview()
}

function revokePreview() {
  if (uploadPreviewUrl.value) URL.revokeObjectURL(uploadPreviewUrl.value)
  uploadPreviewUrl.value = ''
}

function editFromList(article: { id: string }) {
  void loadArticle(article.id)
}

async function loadArticle(articleId: string) {
  errorMessage.value = ''
  try {
    const detail = await apiRequest<AdminArticleDetailResponse>(`/admin/articles/${articleId}`, { method: 'GET' }, adminAuthStore.accessToken)
    articleJson.value = JSON.stringify(
      {
        slug: detail.slug,
        status: detail.status,
        category_slug: detail.category.slug,
        author_slug: detail.author.slug,
        title: detail.title,
        summary: detail.summary,
        tldr: detail.tldr,
        hero_icon: detail.hero_icon,
        hero_image_url: detail.hero_image_url,
        reading_minutes: detail.reading_minutes,
        published_at: detail.published_at,
        audience: detail.audience,
        body: detail.body,
        related_slugs: detail.related_slugs,
        seo: detail.seo,
      },
      null,
      2,
    )
    sideForm.value.category_name = detail.category.name
    sideForm.value.category_display_order = detail.category.display_order
  } catch (error) {
    errorMessage.value = error instanceof ApiError ? error.message : 'بارگذاری مقاله ناموفق بود.'
  }
}

function statusLabel(status: string) {
  if (status === 'published') return 'منتشرشده'
  if (status === 'archived') return 'آرشیوشده'
  return 'پیش‌نویس'
}

function goToPreviousPage() {
  if (page.value <= 1) return
  page.value -= 1
  void fetchArticles()
}

function goToNextPage() {
  if (page.value >= totalPages.value) return
  page.value += 1
  void fetchArticles()
}
</script>

<template>
  <main class="dashboard-shell articles-page">
    <header class="dashboard-hero articles-hero">
      <div>
        <span class="eyebrow">انتشار مقاله</span>
        <h1>Article Publisher</h1>
        <p>JSON معتبر backend را paste کن، تصویر را drag کن، و مقاله را بدون فایل shell منتشر یا به‌روزرسانی کن.</p>
      </div>
    </header>

    <section class="summary-grid">
      <SummaryCard label="کل مقاله‌ها" :value="formatNumber(response?.summary.total_articles ?? 0)" tone="accent" />
      <SummaryCard label="منتشرشده" :value="formatNumber(response?.summary.published_count ?? 0)" />
      <SummaryCard label="پیش‌نویس" :value="formatNumber(response?.summary.draft_count ?? 0)" tone="warning" />
    </section>

    <section class="articles-workspace">
      <div class="article-editor-panel">
        <div class="panel-heading">
          <div>
            <strong>JSON مقاله</strong>
            <span>schema بک‌اند بدون تغییر استفاده می‌شود.</span>
          </div>
          <span :class="['validation-pill', hasValidPayload ? 'validation-pill--ok' : 'validation-pill--bad']">
            {{ hasValidPayload ? 'معتبر' : 'نیازمند اصلاح' }}
          </span>
        </div>

        <textarea v-model="articleJson" class="article-json-editor" dir="ltr" spellcheck="false"></textarea>

        <div v-if="validationErrors.length" class="validation-box">
          <strong>خطاهای قبل از submit</strong>
          <ul>
            <li v-for="error in validationErrors" :key="error">{{ error }}</li>
          </ul>
        </div>
        <p v-if="errorMessage" class="inline-error">{{ errorMessage }}</p>
        <p v-if="successMessage" class="field-success">{{ successMessage }}</p>
      </div>

      <aside class="article-submit-panel">
        <div class="panel-heading">
          <div>
            <strong>تنظیمات انتشار</strong>
            <span>این مقادیر روی JSON اعمال می‌شوند.</span>
          </div>
        </div>

        <label class="field">
          <span>وضعیت</span>
          <select v-model="sideForm.status">
            <option value="draft">پیش‌نویس</option>
            <option value="published">منتشرشده</option>
            <option value="archived">آرشیوشده</option>
          </select>
        </label>

        <label class="field">
          <span>AUTHOR_SLUG</span>
          <input v-model.trim="sideForm.author_slug" type="text" placeholder="dongino-editorial" />
        </label>

        <label class="field">
          <span>CATEGORY_SLUG</span>
          <input v-model.trim="sideForm.category_slug" type="text" placeholder="guides" />
        </label>

        <label class="field">
          <span>نام دسته برای ساخت خودکار</span>
          <input v-model.trim="sideForm.category_name" type="text" placeholder="راهنما" />
          <small class="field-hint">اگر خالی باشد، دسته ساخته نمی‌شود و باید از قبل وجود داشته باشد.</small>
        </label>

        <label class="field">
          <span>ترتیب نمایش دسته</span>
          <input v-model.number="sideForm.category_display_order" type="number" inputmode="numeric" />
        </label>

        <div
          :class="['image-dropzone', isDraggingImage && 'image-dropzone--active']"
          @dragenter.prevent.stop="onImageDragEnter"
          @dragover.prevent.stop="isDraggingImage = true"
          @dragleave.prevent.stop="onImageDragLeave"
          @drop.prevent.stop="onImageDrop"
        >
          <img v-if="uploadPreviewUrl" :src="uploadPreviewUrl" alt="" />
          <div v-else class="image-dropzone__empty">
            <strong>Hero image</strong>
            <span>PNG, WebP یا JPG را اینجا بکش.</span>
          </div>
          <input id="article-image" type="file" accept=".png,.webp,.jpg,.jpeg,image/png,image/webp,image/jpeg" @change="onImageInput" />
          <label class="ghost-button" for="article-image">انتخاب فایل</label>
        </div>

        <div v-if="selectedImage" class="selected-image-row">
          <span>{{ selectedImage.name }}</span>
          <button class="ghost-button" type="button" @click="clearImage">حذف تصویر</button>
        </div>

        <button class="primary-button" type="button" :disabled="!hasValidPayload || submitting" @click="submitArticle">
          {{ submitting ? 'در حال ذخیره...' : 'ثبت / به‌روزرسانی مقاله' }}
        </button>
      </aside>
    </section>

    <section class="filters-card articles-list-card">
      <div class="panel-heading">
        <div>
          <strong>مقاله‌های موجود</strong>
          <span>برای ویرایش، مقاله را از لیست بارگذاری کن.</span>
        </div>
      </div>
      <div class="article-filters">
        <label class="field">
          <span>جست‌وجو</span>
          <input v-model.trim="search" type="search" placeholder="slug، عنوان یا خلاصه" />
        </label>
        <label class="field">
          <span>وضعیت</span>
          <select v-model="statusFilter">
            <option value="all">همه</option>
            <option value="draft">پیش‌نویس</option>
            <option value="published">منتشرشده</option>
            <option value="archived">آرشیوشده</option>
          </select>
        </label>
        <label class="field">
          <span>دسته</span>
          <input v-model.trim="categoryFilter" type="text" placeholder="category-slug" />
        </label>
      </div>

      <section v-if="listErrorMessage" class="state-card state-card--error">
        <strong>خطا در دریافت مقاله‌ها</strong>
        <p>{{ listErrorMessage }}</p>
      </section>
      <section v-else-if="loading" class="state-card">
        <strong>در حال بارگذاری...</strong>
        <p>لیست مقاله‌ها در حال دریافت است.</p>
      </section>
      <div v-else class="article-list">
        <article v-for="article in response?.items ?? []" :key="article.id" class="article-row-card">
          <div>
            <span class="article-status">{{ statusLabel(article.status) }}</span>
            <h2>{{ article.title }}</h2>
            <p>{{ article.slug }} · {{ article.category.name }} · {{ formatDate(article.updated_at) }}</p>
            <small v-if="article.missing_related_slugs?.length" class="article-related-warning">
              related ناموجود: {{ article.missing_related_slugs.join('، ') }}
            </small>
          </div>
          <button class="ghost-button" type="button" @click="editFromList(article)">ویرایش</button>
        </article>
        <section v-if="response && response.items.length === 0" class="state-card">
          <strong>مقاله‌ای پیدا نشد</strong>
          <p>فیلترها را تغییر بده یا مقاله جدید بساز.</p>
        </section>
      </div>
      <footer class="pagination-bar">
        <span>صفحه {{ formatNumber(page) }} از {{ formatNumber(totalPages) }}</span>
        <div class="pagination-bar__actions">
          <button class="ghost-button" type="button" :disabled="page <= 1" @click="goToPreviousPage">صفحه قبل</button>
          <button class="ghost-button" type="button" :disabled="page >= totalPages" @click="goToNextPage">صفحه بعد</button>
        </div>
      </footer>
    </section>
  </main>
</template>

<style scoped>
.articles-workspace {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 360px;
  gap: 18px;
  align-items: start;
}

.article-editor-panel,
.article-submit-panel {
  border: 1px solid var(--color-border);
  border-radius: var(--radius-xl);
  background: linear-gradient(180deg, rgba(19, 33, 46, 0.9), rgba(10, 19, 28, 0.95));
  box-shadow: var(--shadow-xl);
  padding: 18px;
}

.article-submit-panel {
  position: sticky;
  top: 18px;
}

.panel-heading {
  display: flex;
  justify-content: space-between;
  gap: 14px;
  align-items: flex-start;
  margin-bottom: 14px;
}

.panel-heading div {
  display: grid;
  gap: 5px;
}

.panel-heading span,
.article-row-card p {
  color: var(--color-text-soft);
  font-size: 12px;
}

.validation-pill,
.article-status {
  display: inline-flex;
  align-items: center;
  min-height: 30px;
  border-radius: 999px;
  padding: 0 10px;
  background: rgba(255, 255, 255, 0.06);
  color: var(--color-text-soft);
  font-size: 12px;
  white-space: nowrap;
}

.validation-pill--ok {
  color: var(--color-success);
}

.validation-pill--bad {
  color: var(--color-warning);
}

.article-json-editor {
  width: 100%;
  min-height: 620px;
  resize: vertical;
  border: 1px solid var(--color-border);
  border-radius: 18px;
  background: rgba(3, 8, 14, 0.72);
  color: var(--color-text);
  padding: 16px;
  outline: none;
  font: 13px/1.7 ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
}

.article-json-editor:focus {
  border-color: var(--color-primary);
  box-shadow: 0 0 0 4px rgba(92, 200, 255, 0.12);
}

.validation-box {
  margin-top: 14px;
  border: 1px solid rgba(255, 184, 107, 0.3);
  border-radius: 16px;
  background: rgba(255, 184, 107, 0.08);
  padding: 14px;
}

.validation-box ul {
  margin: 10px 0 0;
  padding-inline-start: 22px;
  color: var(--color-text-soft);
  line-height: 1.9;
}

.image-dropzone {
  display: grid;
  gap: 12px;
  justify-items: center;
  border: 1px dashed var(--color-border-strong);
  border-radius: 20px;
  background: rgba(255, 255, 255, 0.04);
  padding: 16px;
  margin-bottom: 14px;
  text-align: center;
}

.image-dropzone--active {
  border-color: var(--color-primary);
  background: rgba(92, 200, 255, 0.1);
}

.image-dropzone img {
  width: 100%;
  aspect-ratio: 1;
  object-fit: cover;
  border-radius: 16px;
}

.image-dropzone input {
  display: none;
}

.image-dropzone__empty {
  display: grid;
  gap: 6px;
  min-height: 160px;
  place-items: center;
  color: var(--color-text-soft);
}

.selected-image-row,
.article-filters,
.article-row-card,
.pagination-bar {
  display: flex;
  gap: 12px;
  align-items: center;
}

.selected-image-row {
  justify-content: space-between;
  margin-bottom: 14px;
  color: var(--color-text-soft);
  font-size: 12px;
}

.articles-list-card {
  margin-top: 18px;
}

.article-filters {
  align-items: end;
}

.article-filters .field {
  flex: 1;
}

.article-list {
  display: grid;
  gap: 10px;
}

.article-row-card {
  justify-content: space-between;
  border: 1px solid var(--color-border);
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.04);
  padding: 14px;
}

.article-row-card h2 {
  margin: 8px 0 6px;
  font-size: 16px;
  line-height: 1.5;
}

.article-row-card p {
  margin: 0;
}

.article-related-warning {
  display: inline-flex;
  width: fit-content;
  margin-top: 10px;
  border-radius: 999px;
  background: rgba(255, 184, 107, 0.12);
  color: var(--color-warning);
  padding: 6px 10px;
  font-size: 12px;
  line-height: 1.6;
}

@media (max-width: 1040px) {
  .articles-workspace {
    grid-template-columns: 1fr;
  }

  .article-submit-panel {
    position: static;
  }
}

@media (max-width: 720px) {
  .article-filters,
  .article-row-card {
    align-items: stretch;
    flex-direction: column;
  }
}
</style>
