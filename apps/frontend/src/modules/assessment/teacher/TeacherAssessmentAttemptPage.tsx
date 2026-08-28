import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { FormEvent, useState } from 'react'
import { Link, useParams, useSearchParams } from 'react-router-dom'
import { ApiError } from '../../../shared/api'
import { ErrorState, LoadingState } from '../../../shared/ui'
import { teacherAssessmentApi } from './api'
import type {
  TeacherAssessmentAttemptDetail,
  TeacherAssessmentResult,
} from './api'
import { teacherAssessmentErrorMessage, isRetryableTeacherAssessmentError } from './errors'
import { teacherAssessmentKeys } from './queries'

interface ReviewFormValue {
  score: string
  maxScore: string
  feedback: string
}

const resultScore = (result: TeacherAssessmentResult) => `${result.score} / ${result.max_score}`

const ReadOnlySubmission = ({ submission }: { submission: string | null }) => (
  <pre className="assessment-submission-readonly">{submission ?? ''}</pre>
)

const readFeedbackError = (error: unknown) =>
  error instanceof ApiError && error.status === 422 ? error.message : null

const fieldErrors = (error: unknown): Record<string, string> => {
  if (error instanceof ApiError && Array.isArray(error.validationIssues)) {
    const errors: Record<string, string> = {}
    for (const issue of error.validationIssues) {
      const key = issue.loc?.at(-1)
      if (typeof key === 'string') errors[key] = issue.msg
    }
    return errors
  }
  return {}
}

export const TeacherAssessmentAttemptPage = () => {
  const { teacherSpaceId = '', activityId = '', attemptId = '' } = useParams<{
    teacherSpaceId: string
    activityId: string
    attemptId: string
  }>()
  const [searchParams] = useSearchParams()
  const backTo = searchParams.get('backTo') ?? undefined
  const status = searchParams.get('status') ?? undefined
  const page = Number(searchParams.get('page') ?? '1')
  const queryClient = useQueryClient()
  const queryKey = teacherAssessmentKeys.detail(teacherSpaceId, activityId, attemptId)

  const attempt = useQuery({
    queryKey,
    queryFn: () => teacherAssessmentApi.get(teacherSpaceId, activityId, attemptId),
    enabled: Boolean(teacherSpaceId && activityId && attemptId),
    retry: false,
  })

  const [reviewForm, setReviewForm] = useState<ReviewFormValue>({
    score: '',
    maxScore: '',
    feedback: '',
  })
  const [reviewError, setReviewError] = useState<string | null>(null)
  const [correcting, setCorrecting] = useState(false)
  const [correctionForm, setCorrectionForm] = useState<{ score: string; feedback: string }>({
    score: '',
    feedback: '',
  })
  const [correctionError, setCorrectionError] = useState<string | null>(null)

  const confirmDetail = (confirmed: TeacherAssessmentAttemptDetail) => {
    queryClient.setQueryData(queryKey, confirmed)
  }

  const applyResultMutation = (result: TeacherAssessmentResult, reviewed: boolean) => {
    setReviewError(null)
    setCorrectionError(null)
    setCorrectionForm({ score: '', feedback: '' })
    setCorrecting(false)
    const current = queryClient.getQueryData<TeacherAssessmentAttemptDetail>(queryKey)
    if (current) {
      confirmDetail({
        ...current,
        status: reviewed ? 'reviewed' : current.status,
        result,
      })
    }
  }

  const review = useMutation({
    mutationFn: () =>
      teacherAssessmentApi.review(teacherSpaceId, activityId, attemptId, {
        score: Number(reviewForm.score),
        max_score: Number(reviewForm.maxScore),
        feedback: reviewForm.feedback.trim() === '' ? null : reviewForm.feedback,
      }),
    onSuccess: (result) => applyResultMutation(result, true),
  })

  const correct = useMutation({
    mutationFn: () =>
      teacherAssessmentApi.correct(teacherSpaceId, activityId, attemptId, {
        result_id: attempt.data?.result?.id ?? '',
        score: Number(correctionForm.score),
        feedback: correctionForm.feedback.trim() === '' ? null : correctionForm.feedback,
      }),
    onSuccess: (result) => applyResultMutation(result, false),
  })

  const validateReview = (): string | null => {
    const score = Number(reviewForm.score)
    const maxScore = Number(reviewForm.maxScore)
    if (reviewForm.score === '' || reviewForm.maxScore === '') {
      return 'Score and max score are required'
    }
    if (!Number.isInteger(score) || !Number.isInteger(maxScore)) {
      return 'Score and max score must be integers'
    }
    if (maxScore <= 0) return 'Max score must be greater than zero'
    if (score < 0 || score > maxScore) return 'Score must be between 0 and the max score'
    return null
  }

  const validateCorrection = (maxScore: number): string | null => {
    const score = Number(correctionForm.score)
    if (correctionForm.score === '') return 'Score is required'
    if (!Number.isInteger(score)) return 'Score must be an integer'
    if (score < 0 || score > maxScore) return 'Score must be between 0 and the max score'
    return null
  }

  const submitReview = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    setReviewError(null)
    const validation = validateReview()
    if (validation) {
      setReviewError(validation)
      return
    }
    review.mutate()
  }

  const submitCorrection = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    setCorrectionError(null)
    const detail = attempt.data
    if (!detail?.result) return
    const validation = validateCorrection(detail.result.max_score)
    if (validation) {
      setCorrectionError(validation)
      return
    }
    correct.mutate()
  }

  const reviewPageError = readFeedbackError(review.error)
  const correctionPageError = readFeedbackError(correct.error)

  if (attempt.isPending) return <LoadingState label="Loading Assessment Attempt" />
  if (attempt.isError && !attempt.data) {
    return (
      <section className="teacher-assessment-attempt">
        <ErrorState message={teacherAssessmentErrorMessage(attempt.error)} />
        {isRetryableTeacherAssessmentError(attempt.error) && (
          <button onClick={() => attempt.refetch()} type="button">
            Retry
          </button>
        )}
      </section>
    )
  }
  if (!attempt.data) return <ErrorState message="Assessment resource not found" />

  const detail = attempt.data
  const queueSearch = new URLSearchParams({
    ...(status ? { status } : {}),
    ...(page > 1 ? { page: String(page) } : {}),
    ...(backTo ? { backTo } : {}),
  }).toString()
  const queueUrl = `/app/teacher-spaces/${teacherSpaceId}/activities/${activityId}/assessment-review${
    queueSearch ? `?${queueSearch}` : ''
  }`
  const reviewApiValidation = fieldErrors(review.error)
  const correctionApiValidation = fieldErrors(correct.error)
  const reviewValidationError = reviewError ?? reviewPageError ?? reviewApiValidation.score
  const correctionValidationError =
    correctionError ?? correctionPageError ?? correctionApiValidation.score

  return (
    <section className="teacher-assessment-attempt" aria-labelledby="teacher-assessment-attempt-title">
      <header className="section-heading">
        <div>
          <p className="eyebrow">Teacher assessment</p>
          <h1 id="teacher-assessment-attempt-title">Attempt</h1>
          <p className="assessment-status">{detail.status.toUpperCase()}</p>
          <p>Student reference: {detail.student_id}</p>
        </div>
        <nav className="assessment-navigation" aria-label="Assessment navigation">
          <Link to={queueUrl}>Back to queue</Link>
          {backTo && <Link to={backTo}>Back to Activity</Link>}
        </nav>
      </header>

      {attempt.isError && <ErrorState message={teacherAssessmentErrorMessage(attempt.error)} />}

      <div className="assessment-readonly">
        <h2>Submission</h2>
        <ReadOnlySubmission submission={detail.submission} />
      </div>

      {detail.status === 'submitted' && (
        <form className="assessment-editor" onSubmit={submitReview}>
          <h2>Review</h2>
          <label>
            Score
            <input
              disabled={review.isPending}
              min={0}
              onChange={(event) => setReviewForm({ ...reviewForm, score: event.target.value })}
              required
              type="number"
              value={reviewForm.score}
            />
          </label>
          <label>
            Max score
            <input
              disabled={review.isPending}
              min={1}
              onChange={(event) => setReviewForm({ ...reviewForm, maxScore: event.target.value })}
              required
              type="number"
              value={reviewForm.maxScore}
            />
          </label>
          <label>
            Feedback
            <textarea
              disabled={review.isPending}
              onChange={(event) => setReviewForm({ ...reviewForm, feedback: event.target.value })}
              rows={3}
              value={reviewForm.feedback}
            />
          </label>
          {reviewValidationError && (
            <p className="assessment-validation" role="alert">
              {reviewValidationError}
            </p>
          )}
          <div className="assessment-actions">
            <button disabled={review.isPending} type="submit">
              {review.isPending ? 'Reviewing…' : 'Review'}
            </button>
          </div>
          {review.isError && !readFeedbackError(review.error) && (
            <ErrorState message={teacherAssessmentErrorMessage(review.error)} />
          )}
        </form>
      )}

      {detail.status === 'reviewed' && !detail.result && (
        <div className="assessment-result-error">
          <ErrorState message="Assessment error" />
          <button onClick={() => attempt.refetch()} type="button">
            Retry
          </button>
        </div>
      )}

      {detail.status === 'reviewed' && detail.result && !correcting && (
        <section className="assessment-result" aria-labelledby="assessment-result-title">
          <h2 id="assessment-result-title">Result</h2>
          <p className="assessment-score">{resultScore(detail.result)}</p>
          {detail.result.feedback !== null && (
            <p className="assessment-feedback">{detail.result.feedback}</p>
          )}
          <div className="assessment-actions">
            <button onClick={() => setCorrecting(true)} type="button">
              Edit
            </button>
          </div>
        </section>
      )}

      {detail.status === 'reviewed' && detail.result && correcting && (
        <form className="assessment-editor" onSubmit={submitCorrection}>
          <h2>Correct Result</h2>
          <p>Max score: {detail.result.max_score}</p>
          <label>
            Score
            <input
              autoFocus
              disabled={correct.isPending}
              min={0}
              max={detail.result.max_score}
              onChange={(event) =>
                setCorrectionForm({ ...correctionForm, score: event.target.value })
              }
              required
              type="number"
              value={correctionForm.score}
            />
          </label>
          <label>
            Feedback
            <textarea
              disabled={correct.isPending}
              onChange={(event) =>
                setCorrectionForm({ ...correctionForm, feedback: event.target.value })
              }
              rows={3}
              value={correctionForm.feedback}
            />
          </label>
          {correctionValidationError && (
            <p className="assessment-validation" role="alert">
              {correctionValidationError}
            </p>
          )}
          <div className="assessment-actions">
            <button disabled={correct.isPending} type="submit">
              {correct.isPending ? 'Saving…' : 'Save'}
            </button>
            <button
              className="button-secondary"
              disabled={correct.isPending}
              onClick={() => {
                setCorrecting(false)
                setCorrectionForm({ score: '', feedback: '' })
                setCorrectionError(null)
              }}
              type="button"
            >
              Cancel
            </button>
          </div>
          {correct.isError && !readFeedbackError(correct.error) && (
            <ErrorState message={teacherAssessmentErrorMessage(correct.error)} />
          )}
        </form>
      )}
    </section>
  )
}
