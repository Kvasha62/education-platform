export const sectionKeys = {
  all: (teacherSpaceId: string, courseId: string) =>
    ['teacher-space', teacherSpaceId, 'courses', courseId, 'sections'] as const,
}
