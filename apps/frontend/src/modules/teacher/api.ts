import { apiRequest } from '../../shared/api'

export interface TeacherSpace {
  id: string
  name: string
  status: 'active' | 'disabled'
  created_at: string
  updated_at: string
}

export interface CreateTeacherSpaceInput {
  name: string
}

export const teacherSpaceApi = {
  list: () => apiRequest<TeacherSpace[]>('/api/v1/teacher-spaces'),
  create: (input: CreateTeacherSpaceInput) =>
    apiRequest<TeacherSpace>('/api/v1/teacher-spaces', { method: 'POST', body: input }),
  get: (teacherSpaceId: string) =>
    apiRequest<TeacherSpace>(`/api/v1/teacher-spaces/${teacherSpaceId}`),
}
