import { apiRequest } from '../../shared/api'

export interface StudentCourseProgress {
  course_id: string
  completed_activities: number
  total_activities: number
  progress_percent: number
}

export const courseProgressApi = {
  get: (courseId: string) =>
    apiRequest<StudentCourseProgress>(`/api/v1/student/courses/${courseId}/progress`),
}
