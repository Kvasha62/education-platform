import { useQuery } from '@tanstack/react-query'
import { ApiError } from '../../shared/api'
import { ErrorState, LoadingState } from '../../shared/ui'
import { courseProgressApi } from './courseProgressApi'
import { studentCourseKeys } from './studentCourseQueries'

const errorMessage = (error: unknown) =>
  error instanceof ApiError || error instanceof Error ? error.message : 'Request failed.'

export const StudentCourseProgress = ({ courseId }: { courseId: string }) => {
  const progress = useQuery({
    queryKey: studentCourseKeys.progress(courseId),
    queryFn: () => courseProgressApi.get(courseId),
    retry: false,
  })
  const notFound = progress.error instanceof ApiError && progress.error.status === 404

  return (
    <section className="student-course-progress" aria-labelledby="course-progress-title">
      <h2 id="course-progress-title">Course Progress</h2>
      {progress.isPending && <LoadingState label="Loading Course Progress" />}
      {notFound && <ErrorState message="Course Progress not available." />}
      {progress.isError && !notFound && <ErrorState message={errorMessage(progress.error)} />}
      {progress.isSuccess && (
        <div className="course-progress-summary">
          <p>
            {progress.data.completed_activities} / {progress.data.total_activities} activities completed
          </p>
          <strong>{progress.data.progress_percent}%</strong>
          <progress
            aria-label="Course Progress"
            max={100}
            value={progress.data.progress_percent}
          />
        </div>
      )}
    </section>
  )
}
