const ACCESS_TOKEN_KEY = 'splitwise_admin_access_token'

export function readAdminAccessToken() {
  return localStorage.getItem(ACCESS_TOKEN_KEY)
}

export function writeAdminAccessToken(token: string) {
  localStorage.setItem(ACCESS_TOKEN_KEY, token)
}

export function clearAdminAccessToken() {
  localStorage.removeItem(ACCESS_TOKEN_KEY)
}
