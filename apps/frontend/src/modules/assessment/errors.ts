import { ApiError } from '../../shared/api'

export const assessmentErrorMessage = (error: unknown) => {
  if (error instanceof ApiError) {
    if (error.status === 401) return 'Authentication required'
    if (error.status === 403) return 'Assessment access denied'
    if (error.status === 404) return 'Assessment unavailable / not found'
    if (error.status === 409) return 'Assessment lifecycle conflict'
    if (error.status >= 500) return 'Assessment error'
    return error.message
  }
  return error instanceof Error ? error.message : 'Assessment error'
}

export const isRetryableAssessmentError = (error: unknown) =>
  error instanceof ApiError && error.status >= 500
