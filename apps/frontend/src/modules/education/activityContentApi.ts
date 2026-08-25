import { apiRequest } from '../../shared/api'
import type { ContentStatus, ContentType } from '../content'

export interface ActivityContentReference {
  id: string
  type: ContentType | null
  status: ContentStatus | null
  available_for_student: boolean
}

export interface ActivityContentScope {
  teacherSpaceId: string
  courseId: string
  sectionId: string
  learningUnitId: string
  activityId: string
}

const linksPath = (scope: ActivityContentScope) =>
  `/api/v1/teacher-spaces/${scope.teacherSpaceId}/environment/courses/${scope.courseId}/sections/${scope.sectionId}/units/${scope.learningUnitId}/activities/${scope.activityId}/contents`

export const activityContentApi = {
  list: (scope: ActivityContentScope) =>
    apiRequest<ActivityContentReference[]>(linksPath(scope)),
  attach: (scope: ActivityContentScope, contentId: string) =>
    apiRequest<{ activity_id: string; content_id: string }>(linksPath(scope), {
      method: 'POST',
      body: { content_id: contentId },
    }),
  detach: (scope: ActivityContentScope, contentId: string) =>
    apiRequest<void>(`${linksPath(scope)}/${contentId}`, { method: 'DELETE' }),
}
