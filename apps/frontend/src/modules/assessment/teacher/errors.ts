import { ApiError } from '../../../shared/api'

export const teacherAssessmentErrorMessage = (error: unknown) => {
  if (error instanceof ApiError) {
    if (error.status === 401) return 'Authentication required'
    if (error.status === 403) return 'Assessment access denied'
    if (error.status === 404) return 'Assessment resource not found'
    if (error.status === 409) return 'Invalid assessment state'
    if (error.status === 422) return error.message
    if (error.status >= 500) return 'Assessment error'
    return error.message
  }
  return error instanceof Error ? error.message : 'Assessment error'
}

export const isRetryableTeacherAssessmentError = (error: unknown) =>
  error instanceof ApiError && error.status >= 500
