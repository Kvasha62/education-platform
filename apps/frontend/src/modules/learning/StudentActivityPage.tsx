import { useQueries, useQuery } from '@tanstack/react-query'
import { Link, useParams } from 'react-router-dom'
import { ApiError } from '../../shared/api'
import { ErrorState, LoadingState } from '../../shared/ui'
import { StudentContentBody } from './StudentContentBody'
import { studentCourseApi } from './studentCourseApi'
import { studentCourseKeys } from './studentCourseQueries'

const errorMessage = (error: unknown) =>
  error instanceof ApiError || error instanceof Error ? error.message : 'Request failed.'

export const StudentActivityPage = () => {
  const { courseId = '', activityId = '' } = useParams<{
    courseId: string
    activityId: string
  }>()
  const course = useQuery({
    queryKey: studentCourseKeys.detail(courseId),
    queryFn: () => studentCourseApi.get(courseId),
    enabled: Boolean(courseId),
    retry: false,
  })
  const location = course.data?.sections.flatMap((section) =>
    section.units.flatMap((unit) =>
      unit.activities
        .filter((activity) => activity.id === activityId)
        .map((activity) => ({ activity, section, unit })),
    ),
  )[0]
  const contentQueries = useQueries({
    queries: (location?.activity.contents ?? []).map((reference) => ({
      queryKey: studentCourseKeys.contentBody(reference.id),
      queryFn: () => studentCourseApi.getContentBody(reference.id),
      retry: false,
    })),
  })
  const courseNotFound = course.error instanceof ApiError && course.error.status === 404
  const contentNotFound = contentQueries.find(
    (query) => query.error instanceof ApiError && query.error.status === 404,
  )
  const contentError = contentQueries.find(
    (query) => query.isError && !(query.error instanceof ApiError && query.error.status === 404),
  )

  if (course.isPending) return <LoadingState label="Loading Activity" />
  if (courseNotFound) return <ErrorState message="Published Course not found." />
  if (course.isError) return <ErrorState message={errorMessage(course.error)} />
  if (!location) return <ErrorState message="Activity not found." />

  return (
    <section className="student-activity" aria-labelledby="student-activity-title">
      <Link to={`/app/student/courses/${courseId}`}>← {course.data.title}</Link>
      <div>
        <p className="eyebrow">{location.section.title} · {location.unit.title}</p>
        <h1 id="student-activity-title">{location.activity.title}</h1>
        <p>
          {location.activity.type.toUpperCase()} · Activity {location.activity.position + 1}
        </p>
      </div>

      {location.activity.contents.length === 0 && (
        <div className="empty-state"><h2>No published Content attached</h2></div>
      )}
      {contentQueries.some((query) => query.isPending) && (
        <LoadingState label="Loading published Content" />
      )}
      {contentNotFound && <ErrorState message="Published Content not found." />}
      {contentError && <ErrorState message={errorMessage(contentError.error)} />}
      {contentQueries.every((query) => query.isSuccess) && contentQueries.length > 0 && (
        <div className="student-content-list">
          {contentQueries.map((query) => (
            <article className="student-content" key={query.data.id}>
              <p className="eyebrow">{query.data.type}</p>
              <StudentContentBody body={query.data.body} />
            </article>
          ))}
        </div>
      )}
    </section>
  )
}
