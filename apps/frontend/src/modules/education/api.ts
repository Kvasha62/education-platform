import { apiRequest } from '../../shared/api'

export interface EducationalEnvironment {
  id: string
  teacher_space_id: string
  name: string
  created_at: string
  updated_at: string
}

export interface CreateEnvironmentInput {
  name: string
}

const environmentPath = (teacherSpaceId: string) =>
  `/api/v1/teacher-spaces/${teacherSpaceId}/environment`

export const educationalEnvironmentApi = {
  get: (teacherSpaceId: string) =>
    apiRequest<EducationalEnvironment>(environmentPath(teacherSpaceId)),
  create: (teacherSpaceId: string, input: CreateEnvironmentInput) =>
    apiRequest<EducationalEnvironment>(environmentPath(teacherSpaceId), {
      method: 'POST',
      body: input,
    }),
}
