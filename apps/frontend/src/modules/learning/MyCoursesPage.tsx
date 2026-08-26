import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { ApiError } from '../../shared/api'
import { ErrorState, LoadingState } from '../../shared/ui'
import { enrollmentApi } from './enrollmentApi'
import { enrollmentKeys } from './enrollmentQueries'

const errorMessage = (error: unknown) =>
  error instanceof ApiError || error instanceof Error ? error.message : 'Request failed.'

export const MyCoursesPage = () => {
  const enrollments = useQuery({
    queryKey: enrollmentKeys.all,
    queryFn: enrollmentApi.list,
    retry: false,
  })

  return (
    <section className="my-courses" aria-labelledby="my-courses-title">
      <div className="section-heading">
        <div>
          <p className="eyebrow">Student</p>
          <h1 id="my-courses-title">My Courses</h1>
        </div>
        <Link to="/app/student/courses">Published Courses</Link>
      </div>

      {enrollments.isPending && <LoadingState label="Loading enrolled Courses" />}
      {enrollments.isError && <ErrorState message={errorMessage(enrollments.error)} />}
      {enrollments.isSuccess && enrollments.data.items.length === 0 && (
        <div className="empty-state">
          <h2>No enrolled Courses yet</h2>
          <p>Enroll in a published Course to see it here.</p>
        </div>
      )}
      {enrollments.isSuccess && enrollments.data.items.length > 0 && (
        <ul className="my-course-list">
          {enrollments.data.items.map((enrollment) => (
            <li key={enrollment.id}>
              <div>
                <strong>Course ID</strong>
                <code>{enrollment.course_id}</code>
                <span>Status: {enrollment.status.toUpperCase()}</span>
                <span>Enrolled: {new Date(enrollment.created_at).toLocaleDateString()}</span>
              </div>
              <Link to={`/app/student/courses/${enrollment.course_id}`}>Open Course</Link>
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}
