export const studentCourseKeys = {
  all: ['student', 'courses'] as const,
  detail: (courseId: string) => ['student', 'courses', courseId] as const,
  progress: (courseId: string) => ['student', 'courses', courseId, 'progress'] as const,
  contentBody: (contentId: string) => ['student', 'contents', contentId, 'body'] as const,
}
