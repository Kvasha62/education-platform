import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { FormEvent, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { ApiError } from '../../shared/api'
import { ErrorState, LoadingState } from '../../shared/ui'
import { teacherSpaceApi } from './api'
import type { TeacherSpace } from './api'
import { teacherSpaceKeys } from './queries'

const errorMessage = (error: unknown) =>
  error instanceof ApiError || error instanceof Error ? error.message : 'Request failed.'

export const TeacherSpacesPage = () => {
  const queryClient = useQueryClient()
  const [name, setName] = useState('')
  const spaces = useQuery({ queryKey: teacherSpaceKeys.all, queryFn: teacherSpaceApi.list })
  const createSpace = useMutation({
    mutationFn: teacherSpaceApi.create,
    onSuccess: (created) => {
      queryClient.setQueryData<TeacherSpace[]>(teacherSpaceKeys.all, (current = []) => [
        ...current,
        created,
      ])
      setName('')
    },
  })

  const submit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    createSpace.mutate({ name })
  }

  return (
    <section className="teacher-spaces" aria-labelledby="teacher-spaces-title">
      <div className="section-heading">
        <div>
          <p className="eyebrow">Teacher Spaces</p>
          <h1 id="teacher-spaces-title">My Teacher Spaces</h1>
        </div>
        <Link to="/app">Back to app</Link>
      </div>

      <form className="create-space" onSubmit={submit}>
        <label>
          Teacher Space name
          <input
            maxLength={120}
            name="name"
            onChange={(event) => setName(event.target.value)}
            required
            value={name}
          />
        </label>
        <button disabled={createSpace.isPending} type="submit">
          {createSpace.isPending ? 'Creating…' : 'Create Teacher Space'}
        </button>
      </form>
      {createSpace.isError && <ErrorState message={errorMessage(createSpace.error)} />}

      {spaces.isPending && <LoadingState label="Loading Teacher Spaces" />}
      {spaces.isError && <ErrorState message={errorMessage(spaces.error)} />}
      {spaces.isSuccess && spaces.data.length === 0 && (
        <div className="empty-state">
          <h2>No Teacher Spaces yet</h2>
          <p>Create your first space to begin.</p>
        </div>
      )}
      {spaces.isSuccess && spaces.data.length > 0 && (
        <ul className="space-list">
          {spaces.data.map((space) => (
            <li key={space.id}>
              <div>
                <strong>{space.name}</strong>
                <span>{space.status}</span>
              </div>
              <Link to={`/app/teacher-spaces/${space.id}`}>Open</Link>
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}

export const TeacherSpacePage = () => {
  const { teacherSpaceId } = useParams<{ teacherSpaceId: string }>()
  const space = useQuery({
    queryKey: teacherSpaceKeys.detail(teacherSpaceId ?? ''),
    queryFn: () => teacherSpaceApi.get(teacherSpaceId ?? ''),
    enabled: Boolean(teacherSpaceId),
  })

  return (
    <section className="teacher-space-detail" aria-labelledby="teacher-space-title">
      <Link to="/app/teacher-spaces">← My Teacher Spaces</Link>
      {space.isPending && <LoadingState label="Loading Teacher Space" />}
      {space.isError && <ErrorState message={errorMessage(space.error)} />}
      {space.isSuccess && (
        <div className="space-detail-card">
          <p className="eyebrow">Teacher Space</p>
          <h1 id="teacher-space-title">{space.data.name}</h1>
          <dl>
            <div><dt>Status</dt><dd>{space.data.status}</dd></div>
            <div><dt>Created</dt><dd>{new Date(space.data.created_at).toLocaleDateString()}</dd></div>
          </dl>
          <Link className="primary-link" to={`/app/teacher-spaces/${space.data.id}/environment`}>
            Open Educational Environment
          </Link>
        </div>
      )}
    </section>
  )
}
