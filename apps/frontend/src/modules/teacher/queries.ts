export const teacherSpaceKeys = {
  all: ['teacher-spaces'] as const,
  detail: (teacherSpaceId: string) => ['teacher-spaces', teacherSpaceId] as const,
}
