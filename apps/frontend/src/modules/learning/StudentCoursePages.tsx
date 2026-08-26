import { useQuery } from '@tanstack/react-query'
import { Link, useParams } from 'react-router-dom'
import { ApiError } from '../../shared/api'
import { ErrorState, LoadingState } from '../../shared/ui'
import { StudentCourseEnrollment } from './StudentCourseEnrollment'
import { studentCourseApi } from './studentCourseApi'
import { studentCourseKeys } from './studentCourseQueries'

const errorMessage = (error: unknown) =>
  error instanceof ApiError || error instanceof Error ? error.message : 'Request failed.'

export const StudentCoursesPage = () => {
  const courses = useQuery({
    queryKey: studentCourseKeys.all,
    queryFn: studentCourseApi.list,
  })

  return (
    <section className="student-courses" aria-labelledby="student-courses-title">
      <div className="section-heading">
        <div>
          <p className="eyebrow">Student</p>
          <h1 id="student-courses-title">Published Courses</h1>
        </div>
        <Link to="/app">Back to workspace</Link>
      </div>

      {courses.isPending && <LoadingState label="Loading published Courses" />}
      {courses.isError && <ErrorState message={errorMessage(courses.error)} />}
      {courses.isSuccess && courses.data.items.length === 0 && (
        <div className="empty-state">
          <h2>No published Courses available</h2>
          <p>Published Courses will appear here.</p>
        </div>
      )}
      {courses.isSuccess && courses.data.items.length > 0 && (
        <ul className="student-course-list">
          {courses.data.items.map((course) => (
            <li key={course.id}>
              <strong>{course.title}</strong>
              <Link to={`/app/student/courses/${course.id}`}>Open Course</Link>
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}

export const StudentCoursePage = () => {
  const { courseId = '' } = useParams<{ courseId: string }>()
  const course = useQuery({
    queryKey: studentCourseKeys.detail(courseId),
    queryFn: () => studentCourseApi.get(courseId),
    enabled: Boolean(courseId),
    retry: false,
  })
  const notFound = course.error instanceof ApiError && course.error.status === 404

  return (
    <section className="student-course-detail" aria-labelledby="student-course-title">
      <Link to="/app/student/courses">← Published Courses</Link>
      {course.isPending && <LoadingState label="Loading Course" />}
      {notFound && <ErrorState message="Published Course not found." />}
      {course.isError && !notFound && <ErrorState message={errorMessage(course.error)} />}
      {course.isSuccess && (
        <>
          <div>
            <p className="eyebrow">Published Course</p>
            <h1 id="student-course-title">{course.data.title}</h1>
          </div>
          <StudentCourseEnrollment courseId={course.data.id} />
          {course.data.sections.length === 0 && (
            <div className="empty-state">
              <h2>No Sections available</h2>
            </div>
          )}
          {course.data.sections.length > 0 && (
            <ol className="student-section-list">
              {course.data.sections.map((section) => (
                <li key={section.id}>
                  <div className="student-section-heading">
                    <span>Section {section.position + 1}</span>
                    <h2>{section.title}</h2>
                  </div>
                  {section.units.length === 0 ? (
                    <p className="content-empty">No Learning Units available.</p>
                  ) : (
                    <ol className="student-unit-list">
                      {section.units.map((unit) => (
                        <li key={unit.id}>
                          <span>Unit {unit.position + 1}</span>
                          <strong>{unit.title}</strong>
                          {unit.activities.length === 0 ? (
                            <span>No Activities available.</span>
                          ) : (
                            <ul className="student-activity-list">
                              {unit.activities.map((activity) => (
                                <li key={activity.id}>
                                  <span>Activity {activity.position + 1}</span>
                                  <Link
                                    to={`/app/student/courses/${courseId}/activities/${activity.id}`}
                                  >
                                    {activity.title}
                                  </Link>
                                </li>
                              ))}
                            </ul>
                          )}
                        </li>
                      ))}
                    </ol>
                  )}
                </li>
              ))}
            </ol>
          )}
        </>
      )}
    </section>
  )
}
