import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { FormEvent, useState } from 'react'
import { Link, useParams, useSearchParams } from 'react-router-dom'
import { ApiError } from '../../../shared/api'
import { ErrorState, LoadingState } from '../../../shared/ui'
import { teacherAssessmentApi } from './api'
import type { TeacherAssessmentDefinition } from './api'
import { teacherAssessmentErrorMessage } from './errors'
import { safeBackTo } from './navigation'
import { teacherAssessmentKeys } from './queries'

const isMissingDefinition = (error: unknown) =>
  error instanceof ApiError &&
  error.status === 404 &&
  error.message === 'Assessment Definition not found'

const normalizeInstructions = (value: string): string | null =>
  value.trim() === '' ? null : value

interface DefinitionFormProps {
  pendingLabel: string
  submitLabel: string
  instructions: string
  pending: boolean
  error: unknown
  onInstructionsChange: (value: string) => void
  onSubmit: () => void
  onCancel?: () => void
}

const DefinitionForm = ({
  pendingLabel,
  submitLabel,
  instructions,
  pending,
  error,
  onInstructionsChange,
  onSubmit,
  onCancel,
}: DefinitionFormProps) => {
  const submit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    onSubmit()
  }
  return (
    <form className="assessment-editor" onSubmit={submit}>
      <label>
        Instructions
        <textarea
          disabled={pending}
          onChange={(event) => onInstructionsChange(event.target.value)}
          rows={4}
          value={instructions}
        />
      </label>
      <div className="assessment-actions">
        <button disabled={pending} type="submit">
          {pending ? pendingLabel : submitLabel}
        </button>
        {onCancel && (
          <button
            className="button-secondary"
            disabled={pending}
            onClick={onCancel}
            type="button"
          >
            Cancel
          </button>
        )}
      </div>
      {error != null && <ErrorState message={teacherAssessmentErrorMessage(error)} />}
    </form>
  )
}

const DefinitionDetails = ({ definition }: { definition: TeacherAssessmentDefinition }) => (
  <dl className="assessment-definition-details">
    <dt>Definition</dt>
    <dd>{definition.id}</dd>
    <dt>Activity</dt>
    <dd>{definition.activity_id}</dd>
    <dt>Instructions</dt>
    <dd>{definition.instructions ?? 'No instructions'}</dd>
    <dt>Status</dt>
    <dd>{definition.status}</dd>
  </dl>
)

export const TeacherAssessmentDefinitionPage = () => {
  const { teacherSpaceId = '', activityId = '' } = useParams<{
    teacherSpaceId: string
    activityId: string
  }>()
  const [searchParams] = useSearchParams()
  const backTo = safeBackTo(searchParams.get('backTo'))
  const queryClient = useQueryClient()
  const definitionKey = teacherAssessmentKeys.definition(teacherSpaceId, activityId)

  const definitionQuery = useQuery({
    queryKey: definitionKey,
    queryFn: () => teacherAssessmentApi.getDefinition(teacherSpaceId, activityId),
    enabled: Boolean(teacherSpaceId && activityId),
    retry: false,
  })

  const [createDraft, setCreateDraft] = useState('')
  const [editing, setEditing] = useState(false)
  const [editDraft, setEditDraft] = useState('')

  const applyDefinition = (definition: TeacherAssessmentDefinition) => {
    // The mutation response is the immediate source of truth for this page:
    // it carries the complete normative Definition representation (ADR-0014),
    // so it is written straight into the cache without an invalidating re-GET.
    queryClient.setQueryData(definitionKey, definition)
    setEditing(false)
  }

  const create = useMutation({
    mutationFn: () =>
      teacherAssessmentApi.createDefinition(teacherSpaceId, activityId, {
        instructions: normalizeInstructions(createDraft),
      }),
    onSuccess: applyDefinition,
  })

  const update = useMutation({
    mutationFn: () =>
      teacherAssessmentApi.updateDefinition(teacherSpaceId, activityId, {
        instructions: normalizeInstructions(editDraft),
      }),
    onSuccess: applyDefinition,
  })

  const archive = useMutation({
    mutationFn: () => teacherAssessmentApi.archiveDefinition(teacherSpaceId, activityId),
    onSuccess: applyDefinition,
  })

  const confirmArchive = () => {
    if (window.confirm('Archive this Assessment Definition? New attempts will be blocked.')) {
      archive.mutate()
    }
  }

  const startEditing = () => {
    setEditDraft(definitionQuery.data?.instructions ?? '')
    setEditing(true)
  }

  if (definitionQuery.isPending) return <LoadingState label="Loading Assessment Definition" />

  const missing = definitionQuery.isError && isMissingDefinition(definitionQuery.error)
  if (definitionQuery.isError && !missing) {
    return (
      <section className="teacher-assessment-definition">
        <ErrorState message={teacherAssessmentErrorMessage(definitionQuery.error)} />
        {backTo && <Link to={backTo}>Back to Activity</Link>}
      </section>
    )
  }

  if (missing) {
    return (
      <section
        className="teacher-assessment-definition"
        aria-labelledby="teacher-assessment-definition-title"
      >
        <header className="section-heading">
          <div>
            <p className="eyebrow">Teacher assessment</p>
            <h1 id="teacher-assessment-definition-title">Set up assessment</h1>
            <p>This Activity has no Assessment Definition yet.</p>
          </div>
          <nav className="assessment-navigation" aria-label="Assessment navigation">
            {backTo && <Link to={backTo}>Back to Activity</Link>}
          </nav>
        </header>
        <DefinitionForm
          error={create.isError ? create.error : null}
          instructions={createDraft}
          onInstructionsChange={setCreateDraft}
          onSubmit={() => create.mutate()}
          pending={create.isPending}
          pendingLabel="Creating…"
          submitLabel="Create assessment"
        />
      </section>
    )
  }

  if (!definitionQuery.data) return <ErrorState message="Assessment resource not found" />

  const definition = definitionQuery.data
  const isActive = definition.status === 'active'

  return (
    <section
      className="teacher-assessment-definition"
      aria-labelledby="teacher-assessment-definition-title"
    >
      <header className="section-heading">
        <div>
          <p className="eyebrow">Teacher assessment</p>
          <h1 id="teacher-assessment-definition-title">Assessment settings</h1>
          <p className="assessment-status">{definition.status.toUpperCase()}</p>
        </div>
        <nav className="assessment-navigation" aria-label="Assessment navigation">
          {backTo && <Link to={backTo}>Back to Activity</Link>}
        </nav>
      </header>

      <DefinitionDetails definition={definition} />

      {isActive && !editing && (
        <div className="assessment-actions">
          <button disabled={archive.isPending} onClick={startEditing} type="button">
            Edit instructions
          </button>
          <button
            className="button-secondary"
            disabled={archive.isPending}
            onClick={confirmArchive}
            type="button"
          >
            {archive.isPending ? 'Archiving…' : 'Archive assessment'}
          </button>
        </div>
      )}

      {isActive && editing && (
        <DefinitionForm
          error={update.isError ? update.error : null}
          instructions={editDraft}
          onCancel={() => setEditing(false)}
          onInstructionsChange={setEditDraft}
          onSubmit={() => update.mutate()}
          pending={update.isPending}
          pendingLabel="Saving…"
          submitLabel="Save instructions"
        />
      )}

      {archive.isError && <ErrorState message={teacherAssessmentErrorMessage(archive.error)} />}
    </section>
  )
}
