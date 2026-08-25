import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { FormEvent, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { ApiError } from '../../shared/api'
import { ErrorState, LoadingState } from '../../shared/ui'
import { learningUnitApi } from './learningUnitApi'
import type { LearningUnit } from './learningUnitApi'
import { learningUnitKeys } from './learningUnitQueries'

const errorMessage = (error: unknown) =>
  error instanceof ApiError || error instanceof Error ? error.message : 'Request failed.'

interface LearningUnitRowProps {
  unit: LearningUnit
  teacherSpaceId: string
  courseId: string
  sectionId: string
}

const LearningUnitRow = ({ unit, teacherSpaceId, courseId, sectionId }: LearningUnitRowProps) => {
  const queryClient = useQueryClient()
  const queryKey = learningUnitKeys.all(teacherSpaceId, courseId, sectionId)
  const [title, setTitle] = useState(unit.title)
  const [position, setPosition] = useState(unit.position)
  const updateUnit = useMutation({
    mutationFn: () => learningUnitApi.update(teacherSpaceId, courseId, sectionId, unit.id, { title, position }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey }),
  })
  const deleteUnit = useMutation({
    mutationFn: () => learningUnitApi.delete(teacherSpaceId, courseId, sectionId, unit.id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey }),
  })

  const submit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    updateUnit.mutate()
  }

  return (
    <li className="section-row">
      <form onSubmit={submit}>
        <label>
          Learning Unit title
          <input
            maxLength={120}
            onChange={(event) => setTitle(event.target.value)}
            required
            value={title}
          />
        </label>
        <label>
          Position
          <input
            min={0}
            onChange={(event) => setPosition(Number(event.target.value))}
            required
            type="number"
            value={position}
          />
        </label>
        <span className="section-position">Position {unit.position}</span>
        <Link
          className="unit-link"
          to={`/app/teacher-spaces/${teacherSpaceId}/environment/courses/${courseId}/sections/${sectionId}/learning-units/${unit.id}/activities`}
        >
          Open Activities
        </Link>
        <div className="section-actions">
          <button disabled={updateUnit.isPending} type="submit">
            {updateUnit.isPending ? 'Saving…' : 'Save'}
          </button>
          <button
            className="button-secondary"
            disabled={deleteUnit.isPending}
            onClick={() => deleteUnit.mutate()}
            type="button"
          >
            {deleteUnit.isPending ? 'Deleting…' : 'Delete'}
          </button>
        </div>
      </form>
      {updateUnit.isError && <ErrorState message={errorMessage(updateUnit.error)} />}
      {deleteUnit.isError && <ErrorState message={errorMessage(deleteUnit.error)} />}
    </li>
  )
}

export const LearningUnitsPage = () => {
  const { teacherSpaceId, courseId, sectionId } = useParams<{
    teacherSpaceId: string
    courseId: string
    sectionId: string
  }>()
  const scopeId = teacherSpaceId ?? ''
  const selectedCourseId = courseId ?? ''
  const selectedSectionId = sectionId ?? ''
  const queryClient = useQueryClient()
  const queryKey = learningUnitKeys.all(scopeId, selectedCourseId, selectedSectionId)
  const [title, setTitle] = useState('')
  const [position, setPosition] = useState(0)
  const units = useQuery({
    queryKey,
    queryFn: () => learningUnitApi.list(scopeId, selectedCourseId, selectedSectionId),
    enabled: Boolean(scopeId && selectedCourseId && selectedSectionId),
  })
  const createUnit = useMutation({
    mutationFn: () => learningUnitApi.create(scopeId, selectedCourseId, selectedSectionId, { title, position }),
    onSuccess: () => {
      setTitle('')
      setPosition(0)
      queryClient.invalidateQueries({ queryKey })
    },
  })

  const submit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    createUnit.mutate()
  }

  return (
    <section className="learning-units-page" aria-labelledby="learning-units-title">
      <div className="section-heading">
        <div>
          <p className="eyebrow">Section structure</p>
          <h1 id="learning-units-title">Learning Units</h1>
        </div>
        <Link to={`/app/teacher-spaces/${scopeId}/environment/courses/${selectedCourseId}/sections`}>
          Back to Sections
        </Link>
      </div>

      <form className="create-space" onSubmit={submit}>
        <label>
          Learning Unit title
          <input
            maxLength={120}
            onChange={(event) => setTitle(event.target.value)}
            required
            value={title}
          />
        </label>
        <label>
          Position
          <input
            min={0}
            onChange={(event) => setPosition(Number(event.target.value))}
            required
            type="number"
            value={position}
          />
        </label>
        <button disabled={createUnit.isPending} type="submit">
          {createUnit.isPending ? 'Creating…' : 'Create Learning Unit'}
        </button>
      </form>
      {createUnit.isError && <ErrorState message={errorMessage(createUnit.error)} />}

      {units.isPending && <LoadingState label="Loading Learning Units" />}
      {units.isError && <ErrorState message={errorMessage(units.error)} />}
      {units.isSuccess && units.data.length === 0 && (
        <div className="empty-state">
          <h2>No Learning Units yet</h2>
          <p>Create the first Learning Unit in this Section.</p>
        </div>
      )}
      {units.isSuccess && units.data.length > 0 && (
        <ol className="section-list">
          {units.data.map((unit) => (
            <LearningUnitRow
              courseId={selectedCourseId}
              key={unit.id}
              sectionId={selectedSectionId}
              unit={unit}
              teacherSpaceId={scopeId}
            />
          ))}
        </ol>
      )}
    </section>
  )
}
