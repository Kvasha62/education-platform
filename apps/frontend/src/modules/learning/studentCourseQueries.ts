export const studentCourseKeys = {
  all: ['student', 'courses'] as const,
  detail: (courseId: string) => ['student', 'courses', courseId] as const,
}
