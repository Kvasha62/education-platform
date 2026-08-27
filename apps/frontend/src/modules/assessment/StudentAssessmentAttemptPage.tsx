import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { ApiError } from '../../shared/api'
import { ErrorState, LoadingState } from '../../shared/ui'
import { assessmentApi } from './api'
import type { AssessmentAttempt } from './api'
import { assessmentErrorMessage, isRetryableAssessmentError } from './errors'
import { assessmentKeys } from './queries'

const ReadOnlySubmission = ({ submission }: { submission: string | null }) => (
  <pre className="assessment-submission-readonly">{submission ?? ''}</pre>
)

export const StudentAssessmentAttemptPage = () => {
  const { activityId = '', attemptId = '' } = useParams<{
    activityId: string
    attemptId: string
  }>()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const queryKey = assessmentKeys.attempt(attemptId)
  const attempt = useQuery({
    queryKey,
    queryFn: () => assessmentApi.getAttempt(attemptId),
    enabled: Boolean(attemptId),
    retry: false,
  })
  const [submission, setSubmission] = useState('')
  const [validationError, setValidationError] = useState<string | null>(null)
  const [saved, setSaved] = useState(false)

  useEffect(() => {
    if (attempt.data) setSubmission(attempt.data.submission ?? '')
  }, [attempt.data])

  const confirmAttempt = (confirmed: AssessmentAttempt) => {
    queryClient.setQueryData(queryKey, confirmed)
    setSubmission(confirmed.submission ?? '')
  }
  const save = useMutation({
    mutationFn: () => assessmentApi.replaceSubmission(attemptId, submission),
    onSuccess: (confirmed) => {
      confirmAttempt(confirmed)
      setSaved(true)
      setValidationError(null)
    },
  })
  const submit = useMutation({
    mutationFn: () => assessmentApi.submitAttempt(attemptId),
    onSuccess: (confirmed) => {
      confirmAttempt(confirmed)
      setValidationError(null)
    },
  })
  const createAnother = useMutation({
    mutationFn: (definitionId: string) =>
      assessmentApi.createAttempt(activityId, definitionId),
    onSuccess: (created) =>
      navigate(`/student/activities/${activityId}/assessment-attempts/${created.id}`),
  })

  const requestSubmit = () => {
    setSaved(false)
    if (!submission.trim()) {
      setValidationError('Submission is required')
      return
    }
    setValidationError(null)
    if (window.confirm('Submit this Attempt? You will not be able to edit it.')) {
      submit.mutate()
    }
  }

  if (attempt.isPending) return <LoadingState label="Loading Assessment Attempt" />
  if (attempt.isError && !attempt.data) {
    return (
      <section className="student-assessment-attempt">
        <ErrorState message={assessmentErrorMessage(attempt.error)} />
        {isRetryableAssessmentError(attempt.error) && (
          <button onClick={() => attempt.refetch()} type="button">Retry</button>
        )}
      </section>
    )
  }
  if (!attempt.data) return <ErrorState message="Assessment unavailable / not found" />

  const detail = attempt.data
  const saveApiValidation =
    save.error instanceof ApiError && save.error.status === 422
      ? save.error.message
      : null
  const submitApiValidation =
    submit.error instanceof ApiError && submit.error.status === 422
      ? submit.error.message
      : null
  const inlineValidation = validationError ?? saveApiValidation ?? submitApiValidation
  const mutationError =
    (save.error && !saveApiValidation ? save.error : null) ??
    (submit.error && !submitApiValidation ? submit.error : null) ??
    createAnother.error

  return (
    <section className="student-assessment-attempt" aria-labelledby="assessment-attempt-title">
      <header>
        <p className="eyebrow">Student assessment</p>
        <h1 id="assessment-attempt-title">Assessment Attempt</h1>
        <p className="assessment-status">{detail.status.toUpperCase()}</p>
      </header>

      {attempt.isError && <ErrorState message={assessmentErrorMessage(attempt.error)} />}

      {detail.status === 'draft' ? (
        <div className="assessment-editor">
          <label htmlFor="assessment-submission">Submission</label>
          <textarea
            id="assessment-submission"
            onChange={(event) => {
              setSubmission(event.target.value)
              setSaved(false)
              setValidationError(null)
            }}
            value={submission}
          />
          {inlineValidation && (
            <p className="assessment-validation" role="alert">
              {inlineValidation}
            </p>
          )}
          <div className="assessment-actions">
            <button disabled={save.isPending} onClick={() => save.mutate()} type="button">
              {save.isPending ? 'Saving…' : 'Save'}
            </button>
            <button disabled={submit.isPending} onClick={requestSubmit} type="button">
              {submit.isPending ? 'Submitting…' : 'Submit'}
            </button>
          </div>
          {saved && <p role="status">Saved.</p>}
        </div>
      ) : (
        <div className="assessment-readonly">
          <h2>Submission</h2>
          <ReadOnlySubmission submission={detail.submission} />
        </div>
      )}

      {detail.status === 'reviewed' && detail.result && (
        <section className="assessment-result" aria-labelledby="assessment-result-title">
          <h2 id="assessment-result-title">Result</h2>
          <p className="assessment-score">
            {detail.result.score} / {detail.result.max_score}
          </p>
          {detail.result.feedback !== null && (
            <p className="assessment-feedback">{detail.result.feedback}</p>
          )}
        </section>
      )}

      {detail.status === 'reviewed' && !detail.result && (
        <div className="assessment-result-error">
          <ErrorState message="Assessment error" />
          <button onClick={() => attempt.refetch()} type="button">Retry</button>
        </div>
      )}

      {(detail.status === 'submitted' || detail.status === 'reviewed') && (
        <button
          disabled={createAnother.isPending}
          onClick={() => createAnother.mutate(detail.assessment_definition_id)}
          type="button"
        >
          {createAnother.isPending ? 'Creating…' : 'Create another Attempt'}
        </button>
      )}

      {mutationError && <ErrorState message={assessmentErrorMessage(mutationError)} />}
    </section>
  )
}
