import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { FormEvent, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { ApiError } from '../../shared/api'
import { ErrorState, LoadingState } from '../../shared/ui'
import { activityApi } from './activityApi'
import type { Activity, ActivityType } from './activityApi'
import { activityKeys } from './activityQueries'

const activityTypes: Array<{ value: ActivityType; label: string }> = [
  { value: 'lecture', label: 'Lecture' },
  { value: 'video', label: 'Video' },
  { value: 'homework', label: 'Homework' },
]
const errorMessage = (error: unknown) =>
  error instanceof ApiError || error instanceof Error ? error.message : 'Request failed.'

interface ActivityRowProps {
  activity: Activity
  teacherSpaceId: string
  courseId: string
  sectionId: string
  learningUnitId: string
}

const ActivityRow = ({
  activity,
  teacherSpaceId,
  courseId,
  sectionId,
  learningUnitId,
}: ActivityRowProps) => {
  const queryClient = useQueryClient()
  const queryKey = activityKeys.all(teacherSpaceId, courseId, sectionId, learningUnitId)
  const [title, setTitle] = useState(activity.title)
  const [position, setPosition] = useState(activity.position)
  const updateActivity = useMutation({
    mutationFn: () =>
      activityApi.update(teacherSpaceId, courseId, sectionId, learningUnitId, activity.id, {
        title,
        position,
      }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey }),
  })
  const deleteActivity = useMutation({
    mutationFn: () =>
      activityApi.delete(teacherSpaceId, courseId, sectionId, learningUnitId, activity.id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey }),
  })

  const submit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    updateActivity.mutate()
  }

  return (
    <li className="section-row">
      <form onSubmit={submit}>
        <label>
          Activity title
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
        <span className="activity-type">{activity.type}</span>
        <span className="section-position">Position {activity.position}</span>
        <div className="section-actions">
          <button disabled={updateActivity.isPending} type="submit">
            {updateActivity.isPending ? 'Saving…' : 'Save'}
          </button>
          <button
            className="button-secondary"
            disabled={deleteActivity.isPending}
            onClick={() => deleteActivity.mutate()}
            type="button"
          >
            {deleteActivity.isPending ? 'Deleting…' : 'Delete'}
          </button>
        </div>
      </form>
      {updateActivity.isError && <ErrorState message={errorMessage(updateActivity.error)} />}
      {deleteActivity.isError && <ErrorState message={errorMessage(deleteActivity.error)} />}
    </li>
  )
}

export const ActivitiesPage = () => {
  const { teacherSpaceId, courseId, sectionId, learningUnitId } = useParams<{
    teacherSpaceId: string
    courseId: string
    sectionId: string
    learningUnitId: string
  }>()
  const scopeId = teacherSpaceId ?? ''
  const selectedCourseId = courseId ?? ''
  const selectedSectionId = sectionId ?? ''
  const selectedUnitId = learningUnitId ?? ''
  const queryClient = useQueryClient()
  const queryKey = activityKeys.all(scopeId, selectedCourseId, selectedSectionId, selectedUnitId)
  const [title, setTitle] = useState('')
  const [type, setType] = useState<ActivityType>('lecture')
  const [position, setPosition] = useState(0)
  const activities = useQuery({
    queryKey,
    queryFn: () => activityApi.list(scopeId, selectedCourseId, selectedSectionId, selectedUnitId),
    enabled: Boolean(scopeId && selectedCourseId && selectedSectionId && selectedUnitId),
  })
  const createActivity = useMutation({
    mutationFn: () =>
      activityApi.create(scopeId, selectedCourseId, selectedSectionId, selectedUnitId, {
        title,
        type,
        position,
      }),
    onSuccess: () => {
      setTitle('')
      setType('lecture')
      setPosition(0)
      queryClient.invalidateQueries({ queryKey })
    },
  })

  const submit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    createActivity.mutate()
  }

  return (
    <section className="activities-page" aria-labelledby="activities-title">
      <div className="section-heading">
        <div>
          <p className="eyebrow">Learning Unit structure</p>
          <h1 id="activities-title">Activities</h1>
        </div>
        <Link
          to={`/app/teacher-spaces/${scopeId}/environment/courses/${selectedCourseId}/sections/${selectedSectionId}/learning-units`}
        >
          Back to Learning Units
        </Link>
      </div>

      <form className="create-space" onSubmit={submit}>
        <label>
          Activity title
          <input
            maxLength={120}
            onChange={(event) => setTitle(event.target.value)}
            required
            value={title}
          />
        </label>
        <label>
          Type
          <select onChange={(event) => setType(event.target.value as ActivityType)} value={type}>
            {activityTypes.map((item) => (
              <option key={item.value} value={item.value}>{item.label}</option>
            ))}
          </select>
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
        <button disabled={createActivity.isPending} type="submit">
          {createActivity.isPending ? 'Creating…' : 'Create Activity'}
        </button>
      </form>
      {createActivity.isError && <ErrorState message={errorMessage(createActivity.error)} />}

      {activities.isPending && <LoadingState label="Loading Activities" />}
      {activities.isError && <ErrorState message={errorMessage(activities.error)} />}
      {activities.isSuccess && activities.data.length === 0 && (
        <div className="empty-state">
          <h2>No Activities yet</h2>
          <p>Create the first Activity in this Learning Unit.</p>
        </div>
      )}
      {activities.isSuccess && activities.data.length > 0 && (
        <ol className="section-list">
          {activities.data.map((activity) => (
            <ActivityRow
              activity={activity}
              courseId={selectedCourseId}
              key={activity.id}
              learningUnitId={selectedUnitId}
              sectionId={selectedSectionId}
              teacherSpaceId={scopeId}
            />
          ))}
        </ol>
      )}
    </section>
  )
}
