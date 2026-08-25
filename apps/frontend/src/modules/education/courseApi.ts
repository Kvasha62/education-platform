import { apiRequest } from '../../shared/api'

export type CourseStatus = 'draft' | 'published' | 'archived'

export interface Course {
  id: string
  educational_environment_id: string
  title: string
  status: CourseStatus
  created_at: string
  updated_at: string
}

export interface CreateCourseInput {
  title: string
}

const coursesPath = (teacherSpaceId: string) =>
  `/api/v1/teacher-spaces/${teacherSpaceId}/environment/courses`

export const courseApi = {
  list: (teacherSpaceId: string) => apiRequest<Course[]>(coursesPath(teacherSpaceId)),
  create: (teacherSpaceId: string, input: CreateCourseInput) =>
    apiRequest<Course>(coursesPath(teacherSpaceId), { method: 'POST', body: input }),
  get: (teacherSpaceId: string, courseId: string) =>
    apiRequest<Course>(`${coursesPath(teacherSpaceId)}/${courseId}`),
}
