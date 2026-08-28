import { Link } from 'react-router-dom'
import { safeBackTo } from './navigation'

interface TeacherAssessmentReviewEntryProps {
  teacherSpaceId: string
  activityId: string
  backTo?: string
}

export const TeacherAssessmentReviewEntry = ({
  teacherSpaceId,
  activityId,
  backTo,
}: TeacherAssessmentReviewEntryProps) => {
  const safeBack = safeBackTo(backTo)
  const search = safeBack ? `?backTo=${encodeURIComponent(safeBack)}` : ''
  return (
    <Link
      className="teacher-assessment-entry"
      to={`/app/teacher-spaces/${teacherSpaceId}/activities/${activityId}/assessment-review${search}`}
    >
      Assessment review
    </Link>
  )
}
