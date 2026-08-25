import { apiRequest } from '../../shared/api'

export interface Section {
  id: string
  course_id: string
  title: string
  position: number
  created_at: string
  updated_at: string
}

export interface CreateSectionInput {
  title: string
  position: number
}

export interface UpdateSectionInput {
  title?: string
  position?: number
}

const sectionsPath = (teacherSpaceId: string, courseId: string) =>
  `/api/v1/teacher-spaces/${teacherSpaceId}/environment/courses/${courseId}/sections`

export const sectionApi = {
  list: (teacherSpaceId: string, courseId: string) =>
    apiRequest<Section[]>(sectionsPath(teacherSpaceId, courseId)),
  create: (teacherSpaceId: string, courseId: string, input: CreateSectionInput) =>
    apiRequest<Section>(sectionsPath(teacherSpaceId, courseId), { method: 'POST', body: input }),
  update: (
    teacherSpaceId: string,
    courseId: string,
    sectionId: string,
    input: UpdateSectionInput,
  ) =>
    apiRequest<Section>(`${sectionsPath(teacherSpaceId, courseId)}/${sectionId}`, {
      method: 'PATCH',
      body: input,
    }),
  delete: (teacherSpaceId: string, courseId: string, sectionId: string) =>
    apiRequest<void>(`${sectionsPath(teacherSpaceId, courseId)}/${sectionId}`, {
      method: 'DELETE',
    }),
}
