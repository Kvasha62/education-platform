import type { StudentActivity, StudentCourse } from './studentCourseApi'

const compareActivities = (
  left: { sectionPosition: number; unitPosition: number; activity: StudentActivity },
  right: { sectionPosition: number; unitPosition: number; activity: StudentActivity },
) =>
  left.sectionPosition - right.sectionPosition ||
  left.unitPosition - right.unitPosition ||
  left.activity.position - right.activity.position ||
  (left.activity.id < right.activity.id ? -1 : left.activity.id > right.activity.id ? 1 : 0)

export const findNextActivity = (
  course: StudentCourse,
  currentActivityId: string,
): StudentActivity | null => {
  const activities = course.sections
    .flatMap((section) =>
      section.units.flatMap((unit) =>
        unit.activities.map((activity) => ({
          sectionPosition: section.position,
          unitPosition: unit.position,
          activity,
        })),
      ),
    )
    .sort(compareActivities)
  const currentIndex = activities.findIndex(({ activity }) => activity.id === currentActivityId)
  return currentIndex >= 0 ? activities[currentIndex + 1]?.activity ?? null : null
}
