export const teacherAssessmentKeys = {
  all: ['teacher-assessment'] as const,
  queue: (
    teacherSpaceId: string,
    activityId: string,
    status: string | undefined,
    page: number,
  ) =>
    [
      ...teacherAssessmentKeys.all,
      'queue',
      teacherSpaceId,
      activityId,
      status ?? 'all',
      page,
    ] as const,
  detail: (teacherSpaceId: string, activityId: string, attemptId: string) =>
    [...teacherAssessmentKeys.all, 'detail', teacherSpaceId, activityId, attemptId] as const,
}
