import { useMutation } from '@tanstack/react-query'
import { FormEvent, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { ApiError } from '../../shared/api'
import { ErrorState } from '../../shared/ui'
import { contentApi } from './api'
import type { ContentType, CreateContentInput } from './api'

const errorMessage = (error: unknown) =>
  error instanceof ApiError || error instanceof Error ? error.message : 'Request failed.'

export const CreateContentPage = () => {
  const navigate = useNavigate()
  const [title, setTitle] = useState('')
  const [type, setType] = useState<ContentType>('article')
  const create = useMutation({
    mutationFn: (input: CreateContentInput) => contentApi.create(input),
    onSuccess: (content) => navigate(`/app/contents/${content.id}/edit`, { replace: true }),
  })

  const submit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    create.mutate({ title, type })
  }

  return (
    <section className="auth-card" aria-labelledby="create-content-title">
      <Link to="/app">← Teacher Workspace</Link>
      <p className="eyebrow">Content</p>
      <h1 id="create-content-title">Create Content</h1>
      <form onSubmit={submit}>
        <label>
          Content type
          <select onChange={(event) => setType(event.target.value as ContentType)} value={type}>
            <option value="article">Article</option>
            <option value="resource">Resource</option>
          </select>
        </label>
        <label>
          Title
          <input
            maxLength={120}
            name="title"
            onChange={(event) => setTitle(event.target.value)}
            required
            value={title}
          />
        </label>
        {create.isError && <ErrorState message={errorMessage(create.error)} />}
        <button disabled={create.isPending} type="submit">
          {create.isPending ? 'Creating…' : 'Create Content'}
        </button>
      </form>
    </section>
  )
}
