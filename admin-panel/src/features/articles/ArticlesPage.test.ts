import { mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import ArticlesPage from './ArticlesPage.vue'

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
    apiRequest: vi.fn(),
    MockApiError,
  }
})
const createObjectURL = vi.fn(() => 'blob:preview')
const revokeObjectURL = vi.fn()

vi.mock('vue-router', () => ({
  useRouter: () => ({ replace: mocks.replace }),
}))

vi.mock('@/shared/auth/store', () => ({
  adminAuthStore: {
    accessToken: 'admin-token',
    logout: vi.fn(),
  },
}))

vi.mock('@/shared/api/client', () => ({
  ApiError: mocks.MockApiError,
  apiRequest: (...args: unknown[]) => mocks.apiRequest(...args),
}))

const listResponse = {
  items: [],
  pagination: { page: 1, page_size: 10, total: 0 },
  summary: { total_articles: 0, draft_count: 0, published_count: 0, archived_count: 0 },
}

const articlePayload = {
  slug: 'valid-article',
  status: 'draft',
  category_slug: 'guides',
  author_slug: 'dongino-editorial',
  title: 'عنوان مقاله',
  summary: 'خلاصه',
  tldr: 'پاسخ کوتاه',
  hero_icon: '✦',
  hero_image_url: null,
  reading_minutes: 5,
  published_at: null,
  audience: ['کاربر'],
  body: [
    { kind: 'heading', level: 2, id: 'why-matters', text: 'چرا مهم است؟' },
    { kind: 'prose', paragraphs: ['پاراگراف'] },
  ],
  related_slugs: [],
  seo: {
    meta_title: 'عنوان سئو',
    meta_description: 'توضیح',
    canonical_url: 'https://splitwise.ir/articles/valid-article/',
    og_image_url: null,
  },
}

function flushPromises() {
  return new Promise((resolve) => setTimeout(resolve, 0))
}

describe('ArticlesPage', () => {
  beforeEach(() => {
    mocks.apiRequest.mockReset()
    mocks.replace.mockReset()
    createObjectURL.mockClear()
    revokeObjectURL.mockClear()
    mocks.apiRequest.mockResolvedValue(listResponse)
    vi.stubGlobal('URL', {
      createObjectURL,
      revokeObjectURL,
    })
  })

  it('does not submit invalid JSON', async () => {
    const wrapper = mount(ArticlesPage)
    await flushPromises()
    mocks.apiRequest.mockClear()

    await wrapper.find('textarea').setValue('{bad json')
    await wrapper.find('button.primary-button').trigger('click')
    await flushPromises()

    expect(wrapper.text()).toContain('JSON معتبر نیست')
    expect(mocks.apiRequest).not.toHaveBeenCalled()
  })

  it('rejects comparison options that do not match the backend schema before submit', async () => {
    const wrapper = mount(ArticlesPage)
    await flushPromises()
    mocks.apiRequest.mockClear()

    await wrapper.find('textarea').setValue(JSON.stringify({
      ...articlePayload,
      body: [
        ...articlePayload.body,
        {
          kind: 'comparison',
          title: 'مقایسه روش‌ها',
          options: [
            { title: 'بدون ثبت هزینه', body: 'تسویه سخت می‌شود.' },
            { title: 'ثبت شفاف', body: 'تسویه سریع‌تر انجام می‌شود.' },
          ],
        },
      ],
    }))
    await wrapper.find('button.primary-button').trigger('click')
    await flushPromises()

    expect(wrapper.text()).toContain('comparison option باید label, pros و cons داشته باشد')
    expect(mocks.apiRequest).not.toHaveBeenCalled()
  })

  it('creates a new article when slug does not exist', async () => {
    mocks.apiRequest.mockImplementation((path: string, init?: RequestInit) => {
      if (path.startsWith('/admin/articles?')) return Promise.resolve(listResponse)
      if (path === '/admin/categories') return Promise.resolve({ slug: 'guides' })
      if (path === '/admin/articles/slug/valid-article') return Promise.reject(new mocks.MockApiError('not found', 404, null))
      if (path === '/admin/articles' && init?.method === 'POST') return Promise.resolve({ ...articlePayload, id: 'article-id' })
      return Promise.resolve(listResponse)
    })
    const wrapper = mount(ArticlesPage)
    await flushPromises()

    await wrapper.find('textarea').setValue(JSON.stringify(articlePayload))
    await flushPromises()
    await wrapper.find('input[placeholder="راهنما"]').setValue('راهنما')
    await wrapper.find('button.primary-button').trigger('click')
    await flushPromises()

    expect(mocks.apiRequest).toHaveBeenCalledWith('/admin/articles', expect.objectContaining({ method: 'POST' }), 'admin-token')
  })

  it('updates an existing article when slug exists', async () => {
    mocks.apiRequest.mockImplementation((path: string, init?: RequestInit) => {
      if (path.startsWith('/admin/articles?')) return Promise.resolve(listResponse)
      if (path === '/admin/categories') return Promise.resolve({ slug: 'guides' })
      if (path === '/admin/articles/slug/valid-article') return Promise.resolve({ ...articlePayload, id: 'existing-id' })
      if (path === '/admin/articles/existing-id' && init?.method === 'PATCH') {
        return Promise.resolve({ ...articlePayload, id: 'existing-id' })
      }
      return Promise.resolve(listResponse)
    })
    const wrapper = mount(ArticlesPage)
    await flushPromises()

    await wrapper.find('textarea').setValue(JSON.stringify(articlePayload))
    await flushPromises()
    await wrapper.find('input[placeholder="راهنما"]').setValue('راهنما')
    await wrapper.find('button.primary-button').trigger('click')
    await flushPromises()

    expect(mocks.apiRequest).toHaveBeenCalledWith('/admin/articles/existing-id', expect.objectContaining({ method: 'PATCH' }), 'admin-token')
  })

  it('stores a dropped image preview before upload', async () => {
    const wrapper = mount(ArticlesPage)
    await flushPromises()

    const file = new File(['image'], 'cover.png', { type: 'image/png' })
    await wrapper.find('.image-dropzone').trigger('drop', {
      dataTransfer: { files: [file] },
    })

    expect(wrapper.text()).toContain('cover.png')
    expect(createObjectURL).toHaveBeenCalledWith(file)
  })
})
