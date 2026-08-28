import { Link } from 'react-router-dom'

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
  const search = backTo ? `?backTo=${encodeURIComponent(backTo)}` : ''
  return (
    <Link
      className="teacher-assessment-entry"
      to={`/app/teacher-spaces/${teacherSpaceId}/activities/${activityId}/assessment-review${search}`}
    >
      Assessment review
    </Link>
  )
}
