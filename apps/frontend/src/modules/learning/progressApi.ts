import { apiRequest } from '../../shared/api'

export type ProgressStatus = 'not_started' | 'in_progress' | 'completed'

export interface ActivityProgress {
  activity_id: string
  status: Exclude<ProgressStatus, 'not_started'>
}

const progressPath = (activityId: string) =>
  `/api/v1/student/activities/${activityId}/progress`

export const progressApi = {
  get: (activityId: string) => apiRequest<ActivityProgress>(progressPath(activityId)),
  start: (activityId: string) =>
    apiRequest<ActivityProgress>(`${progressPath(activityId)}/start`, { method: 'POST' }),
  complete: (activityId: string) =>
    apiRequest<ActivityProgress>(`${progressPath(activityId)}/complete`, { method: 'POST' }),
}
