import { env } from '@/shared/config/env'

export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
    public payload: unknown,
  ) {
    super(message)
  }
}

export async function apiRequest<T>(path: string, init?: RequestInit, accessToken?: string | null): Promise<T> {
  const headers = new Headers(init?.headers)
  headers.set('Content-Type', 'application/json')
  if (accessToken) {
    headers.set('Authorization', `Bearer ${accessToken}`)
  }

  const response = await fetch(`${env.apiBaseUrl}${path}`, {
    ...init,
    headers,
  })

  if (!response.ok) {
    const payload = await parseJson(response)
    throw new ApiError(readErrorMessage(payload), response.status, payload)
  }

  if (response.status === 204) {
    return undefined as T
  }

  return parseJson(response) as Promise<T>
}

async function parseJson(response: Response) {
  const text = await response.text()
  if (!text) return null
  return JSON.parse(text)
}

function readErrorMessage(payload: unknown) {
  if (payload && typeof payload === 'object') {
    const error = (payload as { error?: { message?: unknown } }).error
    if (typeof error?.message === 'string') return error.message
  }
  return 'درخواست با خطا مواجه شد.'
}
