export const activityKeys = {
  all: (teacherSpaceId: string, courseId: string, sectionId: string, learningUnitId: string) =>
    [
      'teacher-space', teacherSpaceId, 'courses', courseId,
      'sections', sectionId, 'units', learningUnitId, 'activities',
    ] as const,
}
