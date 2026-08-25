import { apiRequest } from '../../shared/api'

export interface LearningUnit {
  id: string
  section_id: string
  title: string
  position: number
  created_at: string
  updated_at: string
}

export interface CreateLearningUnitInput {
  title: string
  position: number
}

export interface UpdateLearningUnitInput {
  title?: string
  position?: number
}

const unitsPath = (teacherSpaceId: string, courseId: string, sectionId: string) =>
  `/api/v1/teacher-spaces/${teacherSpaceId}/environment/courses/${courseId}/sections/${sectionId}/units`

export const learningUnitApi = {
  list: (teacherSpaceId: string, courseId: string, sectionId: string) =>
    apiRequest<LearningUnit[]>(unitsPath(teacherSpaceId, courseId, sectionId)),
  create: (
    teacherSpaceId: string,
    courseId: string,
    sectionId: string,
    input: CreateLearningUnitInput,
  ) =>
    apiRequest<LearningUnit>(unitsPath(teacherSpaceId, courseId, sectionId), {
      method: 'POST',
      body: input,
    }),
  update: (
    teacherSpaceId: string,
    courseId: string,
    sectionId: string,
    unitId: string,
    input: UpdateLearningUnitInput,
  ) =>
    apiRequest<LearningUnit>(`${unitsPath(teacherSpaceId, courseId, sectionId)}/${unitId}`, {
      method: 'PATCH',
      body: input,
    }),
  delete: (teacherSpaceId: string, courseId: string, sectionId: string, unitId: string) =>
    apiRequest<void>(`${unitsPath(teacherSpaceId, courseId, sectionId)}/${unitId}`, {
      method: 'DELETE',
    }),
}
