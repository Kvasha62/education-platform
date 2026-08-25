import { apiRequest } from '../../shared/api'

export type ActivityType = 'lecture' | 'video' | 'homework'

export interface Activity {
  id: string
  learning_unit_id: string
  title: string
  type: ActivityType
  position: number
  created_at: string
  updated_at: string
}

export interface CreateActivityInput {
  title: string
  type: ActivityType
  position: number
}

export interface UpdateActivityInput {
  title?: string
  position?: number
}

const activitiesPath = (
  teacherSpaceId: string,
  courseId: string,
  sectionId: string,
  learningUnitId: string,
) =>
  `/api/v1/teacher-spaces/${teacherSpaceId}/environment/courses/${courseId}/sections/${sectionId}/units/${learningUnitId}/activities`

export const activityApi = {
  list: (teacherSpaceId: string, courseId: string, sectionId: string, learningUnitId: string) =>
    apiRequest<Activity[]>(activitiesPath(teacherSpaceId, courseId, sectionId, learningUnitId)),
  create: (
    teacherSpaceId: string,
    courseId: string,
    sectionId: string,
    learningUnitId: string,
    input: CreateActivityInput,
  ) =>
    apiRequest<Activity>(activitiesPath(teacherSpaceId, courseId, sectionId, learningUnitId), {
      method: 'POST',
      body: input,
    }),
  update: (
    teacherSpaceId: string,
    courseId: string,
    sectionId: string,
    learningUnitId: string,
    activityId: string,
    input: UpdateActivityInput,
  ) =>
    apiRequest<Activity>(
      `${activitiesPath(teacherSpaceId, courseId, sectionId, learningUnitId)}/${activityId}`,
      { method: 'PATCH', body: input },
    ),
  delete: (
    teacherSpaceId: string,
    courseId: string,
    sectionId: string,
    learningUnitId: string,
    activityId: string,
  ) =>
    apiRequest<void>(
      `${activitiesPath(teacherSpaceId, courseId, sectionId, learningUnitId)}/${activityId}`,
      { method: 'DELETE' },
    ),
}
