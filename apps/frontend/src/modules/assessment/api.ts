import { apiRequest } from '../../shared/api'

export type AssessmentAttemptStatus = 'draft' | 'submitted' | 'reviewed'

export interface AssessmentResult {
  id: string
  attempt_id: string
  score: number
  max_score: number
  feedback: string | null
}

export interface AssessmentAttempt {
  id: string
  assessment_definition_id: string
  submission: string | null
  status: AssessmentAttemptStatus
  result: AssessmentResult | null
}

export const assessmentApi = {
  createAttempt: (
    activityId: string,
    definitionId: string,
    submission?: string | null,
  ) =>
    apiRequest<AssessmentAttempt>(
      `/api/v1/student/activities/${activityId}/assessment-definitions/${definitionId}/attempts`,
      {
        method: 'POST',
        body: submission === undefined ? {} : { submission },
      },
    ),
  replaceSubmission: (attemptId: string, submission: string | null) =>
    apiRequest<AssessmentAttempt>(`/api/v1/student/assessment-attempts/${attemptId}`, {
      method: 'PUT',
      body: { submission },
    }),
  submitAttempt: (attemptId: string) =>
    apiRequest<AssessmentAttempt>(`/api/v1/student/assessment-attempts/${attemptId}/submit`, {
      method: 'POST',
    }),
  getAttempt: (attemptId: string) =>
    apiRequest<AssessmentAttempt>(`/api/v1/student/assessment-attempts/${attemptId}`),
}
