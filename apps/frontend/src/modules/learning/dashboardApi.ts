import { apiRequest } from '../../shared/api'

export interface DashboardCourse {
  course_id: string
  title: string
  status: 'enrolled'
  enrolled_at: string
}

export interface DashboardContinueLearning {
  course_id: string
  activity_id: string
  status: 'in_progress'
  updated_at: string
}

export interface StudentDashboard {
  my_courses: DashboardCourse[]
  continue_learning: DashboardContinueLearning | null
}

export const dashboardApi = {
  get: () => apiRequest<StudentDashboard>('/api/v1/student/dashboard'),
}
