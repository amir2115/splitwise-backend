const fallbackApiBaseUrl = 'https://api.splitwise.ir/api/v1'

export const env = {
  apiBaseUrl: import.meta.env.VITE_API_BASE_URL || fallbackApiBaseUrl,
}
