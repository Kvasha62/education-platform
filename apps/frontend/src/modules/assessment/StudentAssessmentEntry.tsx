import { useMutation } from '@tanstack/react-query'
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { ErrorState } from '../../shared/ui'
import { assessmentApi } from './api'
import { assessmentErrorMessage } from './errors'

interface StudentAssessmentEntryProps {
  activityId: string
  assessmentDefinitionId: string
}

export const StudentAssessmentEntry = ({
  activityId,
  assessmentDefinitionId,
}: StudentAssessmentEntryProps) => {
  const navigate = useNavigate()
  const [opened, setOpened] = useState(false)
  const create = useMutation({
    mutationFn: () => assessmentApi.createAttempt(activityId, assessmentDefinitionId),
    onSuccess: (attempt) =>
      navigate(`/student/activities/${activityId}/assessment-attempts/${attempt.id}`),
  })

  if (!opened) {
    return (
      <button onClick={() => setOpened(true)} type="button">
        Open assessment
      </button>
    )
  }

  return (
    <aside className="student-assessment-entry" aria-labelledby="student-assessment-entry-title">
      <h2 id="student-assessment-entry-title">Assessment</h2>
      <p>Create a new draft when you are ready to write your submission.</p>
      <button disabled={create.isPending} onClick={() => create.mutate()} type="button">
        {create.isPending ? 'Creating…' : 'Create DRAFT'}
      </button>
      {create.isError && <ErrorState message={assessmentErrorMessage(create.error)} />}
    </aside>
  )
}
