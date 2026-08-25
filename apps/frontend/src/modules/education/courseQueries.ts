export const courseKeys = {
  all: (teacherSpaceId: string) => ['teacher-space', teacherSpaceId, 'courses'] as const,
  detail: (teacherSpaceId: string, courseId: string) =>
    ['teacher-space', teacherSpaceId, 'courses', courseId] as const,
}
