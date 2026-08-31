import { Link } from 'react-router-dom'
import { safeBackTo } from './navigation'

interface TeacherAssessmentDefinitionEntryProps {
  teacherSpaceId: string
  activityId: string
  hasDefinition: boolean
  backTo?: string
}

export const TeacherAssessmentDefinitionEntry = ({
  teacherSpaceId,
  activityId,
  hasDefinition,
  backTo,
}: TeacherAssessmentDefinitionEntryProps) => {
  const safeBack = safeBackTo(backTo)
  const search = safeBack ? `?backTo=${encodeURIComponent(safeBack)}` : ''
  return (
    <Link
      className="teacher-assessment-definition-entry"
      to={`/app/teacher-spaces/${teacherSpaceId}/activities/${activityId}/assessment-definition${search}`}
    >
      {hasDefinition ? 'Assessment settings' : 'Set up assessment'}
    </Link>
  )
}
