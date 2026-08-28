import { apiRequest } from '../../../shared/api'

export type TeacherAssessmentStatus = 'submitted' | 'reviewed'
export type TeacherAssessmentStatusFilter = TeacherAssessmentStatus | undefined

export interface TeacherAssessmentResult {
  id: string
  attempt_id: string
  score: number
  max_score: number
  feedback: string | null
}

export interface TeacherAssessmentAttemptItem {
  id: string
  student_id: string
  status: TeacherAssessmentStatus
  assessment_definition_id: string
  activity_id: string
  result: TeacherAssessmentResult | null
}

export interface TeacherAssessmentAttemptDetail extends TeacherAssessmentAttemptItem {
  submission: string | null
}

export interface TeacherAssessmentAttemptPageResponse {
  items: TeacherAssessmentAttemptItem[]
  page: number
  page_size: number
  has_next: boolean
}

export interface ReviewAssessmentInput {
  score: number
  max_score: number
  feedback?: string | null
}

export interface CorrectAssessmentInput {
  result_id: string
  score: number
  feedback: string | null
}

const attemptsPath = (teacherSpaceId: string, activityId: string) =>
  `/api/v1/teacher-spaces/${teacherSpaceId}/activities/${activityId}/assessment-attempts`

const attemptPath = (teacherSpaceId: string, activityId: string, attemptId: string) =>
  `${attemptsPath(teacherSpaceId, activityId)}/${attemptId}`

export const teacherAssessmentApi = {
  list: (
    teacherSpaceId: string,
    activityId: string,
    options: { status?: TeacherAssessmentStatusFilter; page?: number; pageSize?: number } = {},
  ) => {
    const search = new URLSearchParams()
    search.set('page', String(options.page ?? 1))
    search.set('page_size', String(options.pageSize ?? 20))
    if (options.status) search.set('status', options.status)
    return apiRequest<TeacherAssessmentAttemptPageResponse>(
      `${attemptsPath(teacherSpaceId, activityId)}?${search.toString()}`,
    )
  },
  get: (teacherSpaceId: string, activityId: string, attemptId: string) =>
    apiRequest<TeacherAssessmentAttemptDetail>(
      attemptPath(teacherSpaceId, activityId, attemptId),
    ),
  review: (
    teacherSpaceId: string,
    activityId: string,
    attemptId: string,
    input: ReviewAssessmentInput,
  ) =>
    apiRequest<TeacherAssessmentResult>(`${attemptPath(teacherSpaceId, activityId, attemptId)}/review`, {
      method: 'POST',
      body: input,
    }),
  correct: (
    teacherSpaceId: string,
    activityId: string,
    attemptId: string,
    input: CorrectAssessmentInput,
  ) =>
    apiRequest<TeacherAssessmentResult>(
      `${attemptPath(teacherSpaceId, activityId, attemptId)}/correction`,
      { method: 'POST', body: input },
    ),
}
