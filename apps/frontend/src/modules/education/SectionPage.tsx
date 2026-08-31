import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { FormEvent, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { ApiError } from '../../shared/api'
import { ErrorState, LoadingState } from '../../shared/ui'
import { courseApi } from './courseApi'
import { courseKeys } from './courseQueries'
import { sectionApi } from './sectionApi'
import type { Section } from './sectionApi'
import { sectionKeys } from './sectionQueries'

const errorMessage = (error: unknown) =>
  error instanceof ApiError || error instanceof Error ? error.message : 'Request failed.'

interface SectionRowProps {
  section: Section
  teacherSpaceId: string
  courseId: string
  readOnly: boolean
}

const SectionRow = ({ section, teacherSpaceId, courseId, readOnly }: SectionRowProps) => {
  const queryClient = useQueryClient()
  const queryKey = sectionKeys.all(teacherSpaceId, courseId)
  const [title, setTitle] = useState(section.title)
  const [position, setPosition] = useState(section.position)
  const updateSection = useMutation({
    mutationFn: () => sectionApi.update(teacherSpaceId, courseId, section.id, { title, position }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey }),
  })
  const deleteSection = useMutation({
    mutationFn: () => sectionApi.delete(teacherSpaceId, courseId, section.id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey }),
  })

  const submit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    if (readOnly) return
    updateSection.mutate()
  }

  const remove = () => {
    if (readOnly) return
    deleteSection.mutate()
  }

  return (
    <li className="section-row">
      <form onSubmit={submit}>
        <label>
          Section title
          <input
            disabled={readOnly}
            maxLength={120}
            onChange={(event) => setTitle(event.target.value)}
            required
            value={title}
          />
        </label>
        <label>
          Position
          <input
            disabled={readOnly}
            min={0}
            onChange={(event) => setPosition(Number(event.target.value))}
            required
            type="number"
            value={position}
          />
        </label>
        <span className="section-position">Position {section.position}</span>
        <Link
          className="unit-link"
          to={`/app/teacher-spaces/${teacherSpaceId}/environment/courses/${courseId}/sections/${section.id}/learning-units`}
        >
          Open Units
        </Link>
        <div className="section-actions">
          <button disabled={readOnly || updateSection.isPending} type="submit">
            {updateSection.isPending ? 'Saving…' : 'Save'}
          </button>
          <button
            className="button-secondary"
            disabled={readOnly || deleteSection.isPending}
            onClick={remove}
            type="button"
          >
            {deleteSection.isPending ? 'Deleting…' : 'Delete'}
          </button>
        </div>
      </form>
      {updateSection.isError && <ErrorState message={errorMessage(updateSection.error)} />}
      {deleteSection.isError && <ErrorState message={errorMessage(deleteSection.error)} />}
    </li>
  )
}

export const SectionsPage = () => {
  const { teacherSpaceId, courseId } = useParams<{
    teacherSpaceId: string
    courseId: string
  }>()
  const scopeId = teacherSpaceId ?? ''
  const selectedCourseId = courseId ?? ''
  const queryClient = useQueryClient()
  const queryKey = sectionKeys.all(scopeId, selectedCourseId)
  const [title, setTitle] = useState('')
  const [position, setPosition] = useState(0)
  const course = useQuery({
    queryKey: courseKeys.detail(scopeId, selectedCourseId),
    queryFn: () => courseApi.get(scopeId, selectedCourseId),
    enabled: Boolean(scopeId && selectedCourseId),
    retry: false,
  })
  const readOnly = course.data?.status === 'published' || course.data?.status === 'archived'
  const readOnlyMessage =
    course.data?.status === 'published' ? 'Published — read-only' : 'Archived — read-only'
  const sections = useQuery({
    queryKey,
    queryFn: () => sectionApi.list(scopeId, selectedCourseId),
    enabled: Boolean(scopeId && selectedCourseId),
  })
  const createSection = useMutation({
    mutationFn: () => sectionApi.create(scopeId, selectedCourseId, { title, position }),
    onSuccess: () => {
      setTitle('')
      setPosition(0)
      queryClient.invalidateQueries({ queryKey })
    },
  })

  const submit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    if (readOnly) return
    createSection.mutate()
  }

  return (
    <section className="sections-page" aria-labelledby="sections-title">
      <div className="section-heading">
        <div>
          <p className="eyebrow">Course structure</p>
          <h1 id="sections-title">Sections</h1>
        </div>
        <Link to={`/app/teacher-spaces/${scopeId}/environment/courses/${selectedCourseId}`}>
          Back to Course
        </Link>
      </div>
      {readOnly && <div className="state">{readOnlyMessage}</div>}

      <form className="create-space" onSubmit={submit}>
        <label>
          Section title
          <input
            disabled={readOnly}
            maxLength={120}
            onChange={(event) => setTitle(event.target.value)}
            required
            value={title}
          />
        </label>
        <label>
          Position
          <input
            disabled={readOnly}
            min={0}
            onChange={(event) => setPosition(Number(event.target.value))}
            required
            type="number"
            value={position}
          />
        </label>
        <button disabled={readOnly || createSection.isPending} type="submit">
          {createSection.isPending ? 'Creating…' : 'Create Section'}
        </button>
      </form>
      {createSection.isError && <ErrorState message={errorMessage(createSection.error)} />}

      {sections.isPending && <LoadingState label="Loading Sections" />}
      {sections.isError && <ErrorState message={errorMessage(sections.error)} />}
      {sections.isSuccess && sections.data.length === 0 && (
        <div className="empty-state">
          <h2>No Sections yet</h2>
          <p>Create the first Section in this Course.</p>
        </div>
      )}
      {sections.isSuccess && sections.data.length > 0 && (
        <ol className="section-list">
          {sections.data.map((section) => (
            <SectionRow
              courseId={selectedCourseId}
              key={section.id}
              readOnly={readOnly}
              section={section}
              teacherSpaceId={scopeId}
            />
          ))}
        </ol>
      )}
    </section>
  )
}
