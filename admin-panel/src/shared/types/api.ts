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
  sort_by: 'created_at' | 'updated_at' | 'name' | 'username' | 'groups_count' | 'active_refresh_tokens_count'
  sort_order: 'asc' | 'desc'
  page: number
  page_size: number
}

export interface AdminRuntimeSettingsResponse {
  sms_ir_api_key_masked: string | null
  sms_ir_api_key_configured: boolean
  sms_ir_verify_template_id: string | null
  sms_ir_verify_parameter_name: string | null
  sms_ir_invited_account_template_id: string | null
  sms_ir_invited_account_link_parameter_name: string | null
  sms_ir_invited_account_group_name_parameter_name: string | null
  web_app_base_url: string | null
}

export interface AdminRuntimeSettingsUpdateRequest {
  sms_ir_api_key?: string | null
  sms_ir_verify_template_id?: string | null
  sms_ir_verify_parameter_name?: string | null
  sms_ir_invited_account_template_id?: string | null
  sms_ir_invited_account_link_parameter_name?: string | null
  sms_ir_invited_account_group_name_parameter_name?: string | null
  web_app_base_url?: string | null
}
