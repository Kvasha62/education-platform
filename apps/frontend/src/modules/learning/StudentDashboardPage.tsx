import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { ApiError } from '../../shared/api'
import { ErrorState, LoadingState } from '../../shared/ui'
import { dashboardApi } from './dashboardApi'
import { dashboardKeys } from './dashboardQueries'

const errorMessage = (error: unknown) =>
  error instanceof ApiError || error instanceof Error ? error.message : 'Request failed.'

export const StudentDashboardPage = () => {
  const dashboard = useQuery({
    queryKey: dashboardKeys.detail,
    queryFn: dashboardApi.get,
    retry: false,
  })

  return (
    <section className="student-dashboard" aria-labelledby="student-dashboard-title">
      <div className="section-heading">
        <div>
          <p className="eyebrow">Student</p>
          <h1 id="student-dashboard-title">Dashboard</h1>
        </div>
        <div className="student-course-nav">
          <Link to="/app/student/courses">Published Courses</Link>
          <Link to="/app/student/my-courses">My Courses</Link>
        </div>
      </div>

      {dashboard.isPending && <LoadingState label="Loading Student Dashboard" />}
      {dashboard.isError && <ErrorState message={errorMessage(dashboard.error)} />}
      {dashboard.isSuccess && (
        <>
          <section className="dashboard-panel" aria-labelledby="dashboard-courses-title">
            <h2 id="dashboard-courses-title">My Courses</h2>
            {dashboard.data.my_courses.length === 0 ? (
              <div className="empty-state">
                <h3>No enrolled published Courses</h3>
                <p>Enroll in a published Course to see it here.</p>
              </div>
            ) : (
              <ul className="dashboard-course-list">
                {dashboard.data.my_courses.map((course) => (
                  <li key={course.course_id}>
                    <div>
                      <strong>{course.title}</strong>
                      <span>{course.status.toUpperCase()}</span>
                      <span>Enrolled: {new Date(course.enrolled_at).toLocaleDateString()}</span>
                    </div>
                    <Link to={`/app/student/courses/${course.course_id}`}>Open Course</Link>
                  </li>
                ))}
              </ul>
            )}
          </section>

          <section className="dashboard-panel" aria-labelledby="continue-learning-title">
            <h2 id="continue-learning-title">Continue Learning</h2>
            {dashboard.data.continue_learning ? (
              <div className="continue-learning-card">
                <div>
                  <strong>{dashboard.data.continue_learning.activity_title}</strong>
                  <span>IN PROGRESS</span>
                </div>
                <Link
                  to={`/app/student/courses/${dashboard.data.continue_learning.course_id}/activities/${dashboard.data.continue_learning.activity_id}`}
                >
                  Continue Activity
                </Link>
              </div>
            ) : (
              <div className="empty-state">
                <h3>No Activity in progress</h3>
                <p>Start an Activity to continue it from the Dashboard.</p>
              </div>
            )}
          </section>
        </>
      )}
    </section>
  )
}
