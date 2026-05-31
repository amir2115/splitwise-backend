export interface AdminIdentity {
  username: string
}

export interface AdminAuthResponse {
  admin: AdminIdentity
  access_token: string
  token_type: string
}

export interface AdminUserListItem {
  id: string
  name: string
  username: string
  phone_number: string | null
  is_phone_verified: boolean
  must_change_password: boolean
  client_platform: 'android' | 'frontend' | 'unknown' | null
  android_variant: 'bazaar' | 'myket' | 'organic' | null
  last_client_seen_at: string | null
  created_at: string
  updated_at: string
  groups_count: number
  active_refresh_tokens_count: number
}

export interface AdminUserUpdateRequest {
  name?: string
  phone_number?: string | null
  is_phone_verified?: boolean
}

export interface AdminUserListResponse {
  items: AdminUserListItem[]
  pagination: {
    page: number
    page_size: number
    total: number
  }
  summary: {
    total_users: number
    must_change_password_count: number
    android_users_count: number
    frontend_users_count: number
    unknown_client_users_count: number
  }
}

export interface ArticleCategoryResponse {
  slug: string
  name: string
  description: string | null
  display_order: number
  count: number | null
}

export interface ArticleAuthorResponse {
  slug: string
  name: string
  role: string | null
  bio: string | null
  avatar_url: string | null
}

export interface ArticleSeoPayload {
  meta_title?: string | null
  meta_description?: string | null
  canonical_url?: string | null
  og_image_url?: string | null
}

export interface ArticlePayload {
  slug: string
  status: 'draft' | 'published' | 'archived'
  category_slug: string
  category_name?: string
  category_display_order?: number
  author_slug: string
  title: string
  summary: string
  tldr: string
  hero_icon: string
  hero_image_url?: string | null
  reading_minutes: number
  published_at?: string | null
  audience: string[]
  body: unknown[]
  related_slugs: string[]
  seo: ArticleSeoPayload
}

export interface ArticleListItem {
  id: string
  slug: string
  title: string
  summary: string
  category: ArticleCategoryResponse
  author: ArticleAuthorResponse
  reading_minutes: number
  hero_icon: string
  hero_image_url: string | null
  status: 'draft' | 'published' | 'archived'
  published_at: string | null
  updated_at: string
}

export interface AdminArticleListItem extends ArticleListItem {
  related_slugs: string[]
  missing_related_slugs: string[]
}

export interface ArticleDetailResponse extends ArticleListItem {
  tldr: string
  body: unknown[]
  toc: Array<{ id: string; title: string }>
  audience: string[]
  related: Array<{
    slug: string
    title: string
    excerpt: string
    category: string
    reading_minutes: number
  }>
  seo: ArticleSeoPayload
}

export interface AdminArticleDetailResponse extends ArticleDetailResponse {
  related_slugs: string[]
  missing_related_slugs: string[]
}

export interface AdminArticleListResponse {
  items: AdminArticleListItem[]
  pagination: {
    page: number
    page_size: number
    total: number
  }
  summary: {
    total_articles: number
    draft_count: number
    published_count: number
    archived_count: number
  }
}

export interface ArticleImageUploadResponse {
  filename: string
  stored_path: string
  hero_image_url: string
}

export interface AppReleaseItem {
  id: string
  version_name: string
  version_code: number
  title: string
  subtitle: string
  app_icon_url: string | null
  release_date: string | null
  file_size: string | null
  bazaar_url: string | null
  myket_url: string | null
  release_notes: string[]
  primary_badge_text: string | null
  min_supported_version_code: number | null
  update_mode: 'none' | 'soft' | 'hard' | null
  update_title: string | null
  update_message: string | null
  apk_object_key: string | null
  apk_url: string | null
  is_published: boolean
  published_at: string | null
  created_at: string
  updated_at: string
}

export interface AppReleaseListResponse {
  items: AppReleaseItem[]
}

export interface AppReleaseCreateRequest {
  version_name: string
  version_code: number
  title: string
  subtitle: string
  app_icon_url?: string | null
  release_date?: string | null
  file_size?: string | null
  bazaar_url?: string | null
  myket_url?: string | null
  release_notes: string[]
  primary_badge_text?: string | null
  min_supported_version_code?: number | null
  update_mode?: 'none' | 'soft' | 'hard' | null
  update_title?: string | null
  update_message?: string | null
}

export interface AppReleaseApkUploadResponse {
  id: string
  filename: string
  apk_object_key: string
  apk_url: string
}

export interface AdminArticleExportResponse {
  generated_at: string
  articles: Array<ArticlePayload & {
    category_name: string
    category_display_order: number
    missing_related_slugs: string[]
  }>
  categories: ArticleCategoryResponse[]
  authors: ArticleAuthorResponse[]
}

export interface AdminUserListFilters {
  search: string
  must_change_password: 'all' | 'true' | 'false'
  client_platform: 'all' | 'android' | 'frontend' | 'unknown'
  android_variant: 'all' | 'bazaar' | 'myket' | 'organic' | 'unknown'
  sort_by:
    | 'created_at'
    | 'updated_at'
    | 'name'
    | 'username'
    | 'groups_count'
    | 'active_refresh_tokens_count'
    | 'has_phone_number'
    | 'is_phone_verified'
    | 'client_platform'
    | 'android_variant'
    | 'last_client_seen_at'
  sort_order: 'asc' | 'desc'
  page: number
  page_size: number
}

export interface AdminRuntimeSettingsResponse {
  phone_verification_required: boolean
  sms_ir_api_key_masked: string | null
  sms_ir_api_key_configured: boolean
  sms_ir_verify_template_id: string | null
  sms_ir_verify_template_id_android: string | null
  sms_ir_verify_parameter_name: string | null
  sms_otp_bypass_enabled: boolean
  sms_ir_invited_account_template_id: string | null
  sms_ir_invited_account_link_parameter_name: string | null
  sms_ir_invited_account_group_name_parameter_name: string | null
  web_app_base_url: string | null
  support_email: string | null
  support_url: string | null
  twitter_url: string | null
  instagram_url: string | null
  telegram_url: string | null
  linkedin_url: string | null
  enamad_url: string | null
  pwa_url: string | null
  bazaar_url: string | null
  myket_url: string | null
  apk_url: string | null
  footer_short_text: string | null
  contact_body: string | null
}

export interface AdminRuntimeSettingsUpdateRequest {
  phone_verification_required?: boolean | null
  sms_ir_api_key?: string | null
  sms_ir_verify_template_id?: string | null
  sms_ir_verify_template_id_android?: string | null
  sms_ir_verify_parameter_name?: string | null
  sms_otp_bypass_enabled?: boolean | null
  sms_ir_invited_account_template_id?: string | null
  sms_ir_invited_account_link_parameter_name?: string | null
  sms_ir_invited_account_group_name_parameter_name?: string | null
  web_app_base_url?: string | null
  support_email?: string | null
  support_url?: string | null
  twitter_url?: string | null
  instagram_url?: string | null
  telegram_url?: string | null
  linkedin_url?: string | null
  enamad_url?: string | null
  pwa_url?: string | null
  bazaar_url?: string | null
  myket_url?: string | null
  apk_url?: string | null
  footer_short_text?: string | null
  contact_body?: string | null
}
