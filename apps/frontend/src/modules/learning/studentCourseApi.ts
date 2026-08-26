import { apiRequest } from '../../shared/api'

export interface PublishedCourseSummary {
  id: string
  title: string
}

export interface PublishedCourseList {
  items: PublishedCourseSummary[]
}

export interface StudentLearningUnit {
  id: string
  title: string
  position: number
}

export interface StudentSection {
  id: string
  title: string
  position: number
  units: StudentLearningUnit[]
}

export interface StudentCourse {
  id: string
  title: string
  sections: StudentSection[]
}

export const studentCourseApi = {
  list: () => apiRequest<PublishedCourseList>('/api/v1/student/courses'),
  get: (courseId: string) =>
    apiRequest<StudentCourse>(`/api/v1/student/courses/${courseId}`),
}
