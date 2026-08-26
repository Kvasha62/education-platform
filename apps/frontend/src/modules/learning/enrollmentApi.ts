import { apiRequest } from '../../shared/api'

export interface Enrollment {
  id: string
  course_id: string
  status: 'enrolled'
  created_at: string
}

export interface EnrollmentList {
  items: Enrollment[]
}

export const enrollmentApi = {
  list: () => apiRequest<EnrollmentList>('/api/v1/student/enrollments'),
  enroll: (courseId: string) =>
    apiRequest<Enrollment>(`/api/v1/student/courses/${courseId}/enrollment`, {
      method: 'POST',
    }),
}
