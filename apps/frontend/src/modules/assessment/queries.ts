export const assessmentKeys = {
  all: ['student-assessment'] as const,
  attempt: (attemptId: string) => [...assessmentKeys.all, 'attempt', attemptId] as const,
}
