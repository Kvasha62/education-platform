import { apiRequest } from '../../shared/api'

export interface StudentCourseProgress {
  course_id: string
  completed_activities: number
  total_activities: number
  progress_percent: number
}

const isNonNegativeInteger = (value: unknown): value is number =>
  typeof value === 'number' && Number.isInteger(value) && value >= 0

const validateCourseProgress = (value: unknown): StudentCourseProgress => {
  if (
    typeof value !== 'object' ||
    value === null ||
    typeof (value as StudentCourseProgress).course_id !== 'string' ||
    !isNonNegativeInteger((value as StudentCourseProgress).completed_activities) ||
    !isNonNegativeInteger((value as StudentCourseProgress).total_activities) ||
    !isNonNegativeInteger((value as StudentCourseProgress).progress_percent) ||
    (value as StudentCourseProgress).progress_percent > 100
  ) {
    throw new Error('Invalid Course Progress response.')
  }
  return value as StudentCourseProgress
}

export const courseProgressApi = {
  get: async (courseId: string) =>
    validateCourseProgress(
      await apiRequest<unknown>(`/api/v1/student/courses/${courseId}/progress`),
    ),
}
