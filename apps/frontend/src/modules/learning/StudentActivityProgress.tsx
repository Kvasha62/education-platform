import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { ApiError } from '../../shared/api'
import { ErrorState, LoadingState } from '../../shared/ui'
import { progressApi } from './progressApi'
import type { ProgressStatus } from './progressApi'
import { progressKeys } from './progressQueries'

const statusLabel: Record<ProgressStatus, string> = {
  not_started: 'Not started',
  in_progress: 'In progress',
  completed: 'Completed',
}
const errorMessage = (error: unknown) =>
  error instanceof ApiError || error instanceof Error ? error.message : 'Request failed.'

export const StudentActivityProgress = ({ activityId }: { activityId: string }) => {
  const queryClient = useQueryClient()
  const queryKey = progressKeys.detail(activityId)
  const progress = useQuery({
    queryKey,
    queryFn: progressApi.get.bind(null, activityId),
    retry: false,
  })
  const start = useMutation({
    mutationFn: () => progressApi.start(activityId),
    onSuccess: (confirmed) => queryClient.setQueryData(queryKey, confirmed),
  })
  const complete = useMutation({
    mutationFn: () => progressApi.complete(activityId),
    onSuccess: (confirmed) => queryClient.setQueryData(queryKey, confirmed),
  })
  const isNotStarted =
    progress.error instanceof ApiError &&
    progress.error.status === 404 &&
    progress.error.message === 'Progress not found'
  const status: ProgressStatus | null = progress.data?.status ?? (isNotStarted ? 'not_started' : null)
  const mutationError = start.error ?? complete.error

  return (
    <aside className="student-progress" aria-labelledby="activity-progress-title">
      <h2 id="activity-progress-title">Activity progress</h2>
      {progress.isPending && <LoadingState label="Loading progress" />}
      {progress.isError && !isNotStarted && <ErrorState message={errorMessage(progress.error)} />}
      {status && (
        <>
          <p className="progress-status">{statusLabel[status]}</p>
          {status === 'not_started' && (
            <button disabled={start.isPending} onClick={() => start.mutate()} type="button">
              {start.isPending ? 'Starting…' : 'Start Activity'}
            </button>
          )}
          {status === 'in_progress' && (
            <button
              disabled={complete.isPending}
              onClick={() => complete.mutate()}
              type="button"
            >
              {complete.isPending ? 'Completing…' : 'Complete Activity'}
            </button>
          )}
        </>
      )}
      {mutationError && <ErrorState message={errorMessage(mutationError)} />}
    </aside>
  )
}
