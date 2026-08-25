import { env } from '../config/env'

export type ApiErrorKind =
  | 'validation'
  | 'unauthorized'
  | 'forbidden'
  | 'not-found'
  | 'conflict'
  | 'unavailable'
  | 'unknown'

export interface ValidationIssue {
  loc?: Array<string | number>
  msg: string
  type?: string
}

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    public readonly kind: ApiErrorKind,
    message: string,
    public readonly validationIssues: ValidationIssue[] = [],
  ) {
    super(message)
    this.name = 'ApiError'
  }
}

const errorKind = (status: number): ApiErrorKind => {
  if (status === 401) return 'unauthorized'
  if (status === 403) return 'forbidden'
  if (status === 404) return 'not-found'
  if (status === 409) return 'conflict'
  if (status === 422) return 'validation'
  if (status === 503) return 'unavailable'
  return 'unknown'
}

const parseError = async (response: Response): Promise<ApiError> => {
  let detail: unknown
  try {
    const payload = (await response.json()) as { detail?: unknown }
    detail = payload.detail
  } catch {
    detail = undefined
  }

  const issues = Array.isArray(detail)
    ? detail.filter(
        (item): item is ValidationIssue =>
          typeof item === 'object' && item !== null && typeof (item as ValidationIssue).msg === 'string',
      )
    : []
  const message =
    typeof detail === 'string'
      ? detail
      : issues.length > 0
        ? issues.map((issue) => issue.msg).join(', ')
        : `Request failed with status ${response.status}`

  return new ApiError(response.status, errorKind(response.status), message, issues)
}

export interface ApiRequestOptions extends Omit<RequestInit, 'body'> {
  body?: unknown
}

export const apiRequest = async <T>(path: string, options: ApiRequestOptions = {}): Promise<T> => {
  const headers = new Headers(options.headers)
  if (options.body !== undefined) headers.set('Content-Type', 'application/json')

  const response = await fetch(`${env.apiBaseUrl}${path}`, {
    ...options,
    headers,
    body: options.body === undefined ? undefined : JSON.stringify(options.body),
    credentials: 'include',
  })

  if (!response.ok) throw await parseError(response)
  if (response.status === 204) return undefined as T
  return (await response.json()) as T
}
