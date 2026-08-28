import { useQuery } from '@tanstack/react-query'
import { Link, useParams, useSearchParams } from 'react-router-dom'
import { ErrorState, LoadingState } from '../../../shared/ui'
import { teacherAssessmentApi } from './api'
import type { TeacherAssessmentStatusFilter } from './api'
import { teacherAssessmentErrorMessage, isRetryableTeacherAssessmentError } from './errors'
import { safeBackTo } from './navigation'
import { teacherAssessmentKeys } from './queries'

const PAGE_SIZE = 20

const FILTERS: Array<{ value: TeacherAssessmentStatusFilter; label: string }> = [
  { value: undefined, label: 'All' },
  { value: 'submitted', label: 'Submitted' },
  { value: 'reviewed', label: 'Reviewed' },
]

const emptyMessage = (status: TeacherAssessmentStatusFilter) => {
  if (status === 'submitted') return 'No submitted attempts to review'
  if (status === 'reviewed') return 'No reviewed attempts to correct'
  return 'No attempts to review'
}

export const TeacherAssessmentReviewQueuePage = () => {
  const { teacherSpaceId = '', activityId = '' } = useParams<{
    teacherSpaceId: string
    activityId: string
  }>()
  const [searchParams, setSearchParams] = useSearchParams()
  const backTo = safeBackTo(searchParams.get('backTo'))
  const rawStatus = searchParams.get('status') ?? ''
  const status: TeacherAssessmentStatusFilter =
    rawStatus === 'submitted' || rawStatus === 'reviewed' ? rawStatus : undefined
  const rawPage = Number(searchParams.get('page') ?? '1')
  const page = Number.isInteger(rawPage) && rawPage >= 1 ? rawPage : 1

  const queue = useQuery({
    queryKey: teacherAssessmentKeys.queue(teacherSpaceId, activityId, status, page),
    queryFn: () =>
      teacherAssessmentApi.list(teacherSpaceId, activityId, {
        status,
        page,
        pageSize: PAGE_SIZE,
      }),
    enabled: Boolean(teacherSpaceId && activityId),
    retry: false,
  })

  const selectFilter = (nextStatus: TeacherAssessmentStatusFilter) => {
    const next = new URLSearchParams()
    if (nextStatus) next.set('status', nextStatus)
    if (backTo) next.set('backTo', backTo)
    setSearchParams(next)
  }

  const selectPage = (next: number) => {
    const nextParams = new URLSearchParams()
    if (status) nextParams.set('status', status)
    nextParams.set('page', String(next))
    if (backTo) nextParams.set('backTo', backTo)
    setSearchParams(nextParams)
  }

  const detailPath = (attemptId: string) => {
    const next = new URLSearchParams()
    if (status) next.set('status', status)
    next.set('page', String(page))
    if (backTo) next.set('backTo', backTo)
    return `/app/teacher-spaces/${teacherSpaceId}/activities/${activityId}/assessment-review/${attemptId}?${next.toString()}`
  }

  return (
    <section className="teacher-assessment-queue" aria-labelledby="teacher-assessment-queue-title">
      <header className="section-heading">
        <div>
          <p className="eyebrow">Teacher assessment</p>
          <h1 id="teacher-assessment-queue-title">Assessment review</h1>
        </div>
        {backTo && <Link to={backTo}>Back to Activity</Link>}
      </header>

      <div className="assessment-filter" role="group" aria-label="Status filter">
        {FILTERS.map((filter) => (
          <button
            aria-pressed={status === filter.value}
            className={status === filter.value ? 'button-primary' : 'button-secondary'}
            key={filter.label}
            onClick={() => selectFilter(filter.value)}
            type="button"
          >
            {filter.label}
          </button>
        ))}
      </div>

      {queue.isPending && <LoadingState label="Loading Review Queue" />}
      {queue.isError && (
        <div>
          <ErrorState message={teacherAssessmentErrorMessage(queue.error)} />
          {isRetryableTeacherAssessmentError(queue.error) && (
            <button onClick={() => queue.refetch()} type="button">
              Retry
            </button>
          )}
        </div>
      )}
      {queue.isSuccess && queue.data.items.length === 0 && (
        <div className="empty-state">
          <h2>{emptyMessage(status)}</h2>
        </div>
      )}
      {queue.isSuccess && queue.data.items.length > 0 && (
        <>
          <ol className="section-list">
            {queue.data.items.map((item) => (
              <li className="section-row" key={item.id}>
                <div>
                  <p className="assessment-status">{item.status.toUpperCase()}</p>
                  <p>Student reference: {item.student_id}</p>
                </div>
                <Link to={detailPath(item.id)}>Open attempt</Link>
              </li>
            ))}
          </ol>
          <nav className="assessment-pagination" aria-label="Review queue pagination">
            <button
              className="button-secondary"
              disabled={page <= 1}
              onClick={() => selectPage(page - 1)}
              type="button"
            >
              Previous
            </button>
            <span>Page {queue.data.page}</span>
            <button
              className="button-secondary"
              disabled={!queue.data.has_next}
              onClick={() => selectPage(page + 1)}
              type="button"
            >
              Next
            </button>
          </nav>
        </>
      )}
    </section>
  )
}
