export const progressKeys = {
  detail: (activityId: string) => ['student', 'activities', activityId, 'progress'] as const,
}
