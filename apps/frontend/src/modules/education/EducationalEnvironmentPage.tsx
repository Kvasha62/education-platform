import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { FormEvent, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { ApiError } from '../../shared/api'
import { ErrorState, LoadingState } from '../../shared/ui'
import { educationalEnvironmentApi } from './api'
import { educationalEnvironmentKeys } from './queries'

const errorMessage = (error: unknown) =>
  error instanceof ApiError || error instanceof Error ? error.message : 'Request failed.'

export const EducationalEnvironmentPage = () => {
  const { teacherSpaceId } = useParams<{ teacherSpaceId: string }>()
  const scopeId = teacherSpaceId ?? ''
  const queryClient = useQueryClient()
  const [name, setName] = useState('')
  const environment = useQuery({
    queryKey: educationalEnvironmentKeys.detail(scopeId),
    queryFn: () => educationalEnvironmentApi.get(scopeId),
    enabled: Boolean(scopeId),
    retry: false,
  })
  const createEnvironment = useMutation({
    mutationFn: (input: { name: string }) => educationalEnvironmentApi.create(scopeId, input),
    onSuccess: (created) => {
      queryClient.setQueryData(educationalEnvironmentKeys.detail(scopeId), created)
      setName('')
    },
  })
  const isEmpty = environment.error instanceof ApiError && environment.error.status === 404

  const submit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    createEnvironment.mutate({ name })
  }

  return (
    <section className="environment-page" aria-labelledby="environment-title">
      <Link to={`/app/teacher-spaces/${scopeId}`}>← Teacher Space</Link>

      {environment.isPending && <LoadingState label="Loading Educational Environment" />}
      {environment.isError && !isEmpty && (
        <ErrorState message={errorMessage(environment.error)} />
      )}

      {isEmpty && (
        <div className="environment-empty">
          <p className="eyebrow">Educational Environment</p>
          <h1 id="environment-title">No Educational Environment yet</h1>
          <p>Create the environment for this Teacher Space.</p>
          <form className="create-space" onSubmit={submit}>
            <label>
              Environment name
              <input
                maxLength={120}
                name="name"
                onChange={(event) => setName(event.target.value)}
                required
                value={name}
              />
            </label>
            <button disabled={createEnvironment.isPending} type="submit">
              {createEnvironment.isPending ? 'Creating…' : 'Create Environment'}
            </button>
          </form>
          {createEnvironment.isError && (
            <ErrorState message={errorMessage(createEnvironment.error)} />
          )}
        </div>
      )}

      {environment.isSuccess && (
        <div className="space-detail-card">
          <p className="eyebrow">Educational Environment</p>
          <h1 id="environment-title">{environment.data.name}</h1>
          <dl>
            <div><dt>Teacher Space</dt><dd>{environment.data.teacher_space_id}</dd></div>
            <div><dt>Created</dt><dd>{new Date(environment.data.created_at).toLocaleDateString()}</dd></div>
          </dl>
          <Link className="primary-link" to={`/app/teacher-spaces/${scopeId}/environment/courses`}>
            Open Courses
          </Link>
        </div>
      )}
    </section>
  )
}
