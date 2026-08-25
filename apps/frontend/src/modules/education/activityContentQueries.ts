import type { ActivityContentScope } from './activityContentApi'

export const activityContentKeys = {
  linked: (scope: ActivityContentScope) => [
    'teacher-space', scope.teacherSpaceId, 'courses', scope.courseId,
    'sections', scope.sectionId, 'units', scope.learningUnitId,
    'activities', scope.activityId, 'contents',
  ] as const,
  ownedContent: ['owned-content'] as const,
}
