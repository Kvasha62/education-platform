import { useQuery } from '@tanstack/react-query'
import { ApiError } from '../../shared/api'
import { identityApi } from './api'
import type { Identity } from './api'

export type AuthenticationState =
  | { status: 'loading'; user: null; error: null }
  | { status: 'authenticated'; user: Identity; error: null }
  | { status: 'unauthenticated'; user: null; error: null }
  | { status: 'error'; user: null; error: ApiError | Error }

export const authQueryKey = ['identity', 'session'] as const

export const useAuthentication = (): AuthenticationState => {
  const query = useQuery({
    queryKey: authQueryKey,
    queryFn: identityApi.me,
    retry: false,
  })

  if (query.isPending) return { status: 'loading', user: null, error: null }
  if (query.isSuccess) return { status: 'authenticated', user: query.data, error: null }
  if (query.error instanceof ApiError && query.error.status === 401) {
    return { status: 'unauthenticated', user: null, error: null }
  }
  return { status: 'error', user: null, error: query.error }
}
