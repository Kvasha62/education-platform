export const learningUnitKeys = {
  all: (teacherSpaceId: string, courseId: string, sectionId: string) =>
    ['teacher-space', teacherSpaceId, 'courses', courseId, 'sections', sectionId, 'units'] as const,
}
