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
  }
}

export interface AdminUserListFilters {
  search: string
  must_change_password: 'all' | 'true' | 'false'
  sort_by:
    | 'created_at'
    | 'updated_at'
    | 'name'
    | 'username'
    | 'groups_count'
    | 'active_refresh_tokens_count'
    | 'has_phone_number'
    | 'is_phone_verified'
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
