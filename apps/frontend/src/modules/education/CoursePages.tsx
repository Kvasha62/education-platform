import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { FormEvent, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { ApiError } from '../../shared/api'
import { ErrorState, LoadingState } from '../../shared/ui'
import { courseApi } from './courseApi'
import type { Course } from './courseApi'
import { courseKeys } from './courseQueries'

const errorMessage = (error: unknown) =>
  error instanceof ApiError || error instanceof Error ? error.message : 'Request failed.'

const statusLabel = (status: Course['status']) => status.toUpperCase()

export const CoursesPage = () => {
  const { teacherSpaceId } = useParams<{ teacherSpaceId: string }>()
  const scopeId = teacherSpaceId ?? ''
  const queryClient = useQueryClient()
  const navigate = useNavigate()
  const [title, setTitle] = useState('')
  const courses = useQuery({
    queryKey: courseKeys.all(scopeId),
    queryFn: () => courseApi.list(scopeId),
    enabled: Boolean(scopeId),
  })
  const createCourse = useMutation({
    mutationFn: (input: { title: string }) => courseApi.create(scopeId, input),
    onSuccess: (created) => {
      queryClient.setQueryData<Course[]>(courseKeys.all(scopeId), (current = []) => [
        ...current,
        created,
      ])
      setTitle('')
      navigate(`/app/teacher-spaces/${scopeId}/environment/courses/${created.id}`)
    },
  })

  const submit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    createCourse.mutate({ title })
  }

  return (
    <section className="courses-page" aria-labelledby="courses-title">
      <div className="section-heading">
        <div>
          <p className="eyebrow">Educational Environment</p>
          <h1 id="courses-title">Courses</h1>
        </div>
        <Link to={`/app/teacher-spaces/${scopeId}/environment`}>Back to Environment</Link>
      </div>

      <form className="create-space" onSubmit={submit}>
        <label>
          Course title
          <input
            maxLength={120}
            name="title"
            onChange={(event) => setTitle(event.target.value)}
            required
            value={title}
          />
        </label>
        <button disabled={createCourse.isPending} type="submit">
          {createCourse.isPending ? 'Creating…' : 'Create Course'}
        </button>
      </form>
      {createCourse.isError && <ErrorState message={errorMessage(createCourse.error)} />}

      {courses.isPending && <LoadingState label="Loading Courses" />}
      {courses.isError && <ErrorState message={errorMessage(courses.error)} />}
      {courses.isSuccess && courses.data.length === 0 && (
        <div className="empty-state">
          <h2>No Courses yet</h2>
          <p>Create the first Course in this Educational Environment.</p>
        </div>
      )}
      {courses.isSuccess && courses.data.length > 0 && (
        <ul className="space-list">
          {courses.data.map((course) => (
            <li key={course.id}>
              <div>
                <strong>{course.title}</strong>
                <span>{statusLabel(course.status)}</span>
              </div>
              <Link to={`/app/teacher-spaces/${scopeId}/environment/courses/${course.id}`}>
                Open
              </Link>
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}

export const CoursePage = () => {
  const { teacherSpaceId, courseId } = useParams<{
    teacherSpaceId: string
    courseId: string
  }>()
  const scopeId = teacherSpaceId ?? ''
  const selectedCourseId = courseId ?? ''
  const queryClient = useQueryClient()
  const course = useQuery({
    queryKey: courseKeys.detail(scopeId, selectedCourseId),
    queryFn: () => courseApi.get(scopeId, selectedCourseId),
    enabled: Boolean(scopeId && selectedCourseId),
    retry: false,
  })
  const publish = useMutation({
    mutationFn: () => courseApi.publish(scopeId, selectedCourseId),
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({
          queryKey: courseKeys.detail(scopeId, selectedCourseId),
        }),
        queryClient.invalidateQueries({ queryKey: courseKeys.all(scopeId) }),
      ])
    },
  })

  const confirmPublish = () => {
    if (course.data && window.confirm(`Publish "${course.data.title}"?`)) {
      publish.mutate()
    }
  }

  return (
    <section className="course-detail" aria-labelledby="course-title">
      <Link to={`/app/teacher-spaces/${scopeId}/environment/courses`}>← Courses</Link>
      {course.isPending && <LoadingState label="Loading Course" />}
      {course.isError && <ErrorState message={errorMessage(course.error)} />}
      {course.isSuccess && (
        <div className="space-detail-card">
          <p className="eyebrow">Course</p>
          <h1 id="course-title">{course.data.title}</h1>
          <dl>
            <div><dt>Status</dt><dd>{statusLabel(course.data.status)}</dd></div>
            <div><dt>Created</dt><dd>{new Date(course.data.created_at).toLocaleDateString()}</dd></div>
          </dl>
          {course.data.status === 'draft' && (
            <button
              className="button-secondary"
              disabled={publish.isPending}
              onClick={confirmPublish}
              type="button"
            >
              {publish.isPending ? 'Publishing…' : 'Publish Course'}
            </button>
          )}
          <Link className="primary-link" to={`/app/teacher-spaces/${scopeId}/environment/courses/${selectedCourseId}/sections`}>
            Open Sections
          </Link>
        </div>
      )}
      {publish.isError && <ErrorState message={errorMessage(publish.error)} />}
    </section>
  )
}
