import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { contentApi } from '../content'
import { ApiError } from '../../shared/api'
import { ErrorState, LoadingState } from '../../shared/ui'
import { activityContentApi } from './activityContentApi'
import type { ActivityContentScope } from './activityContentApi'
import { activityContentKeys } from './activityContentQueries'

const errorMessage = (error: unknown) =>
  error instanceof ApiError || error instanceof Error ? error.message : 'Request failed.'

export const ActivityContentPanel = ({ scope }: { scope: ActivityContentScope }) => {
  const queryClient = useQueryClient()
  const linkedKey = activityContentKeys.linked(scope)
  const [contentId, setContentId] = useState('')
  const linked = useQuery({ queryKey: linkedKey, queryFn: () => activityContentApi.list(scope) })
  const owned = useQuery({
    queryKey: activityContentKeys.ownedContent,
    queryFn: contentApi.list,
  })
  const attach = useMutation({
    mutationFn: () => activityContentApi.attach(scope, contentId),
    onSuccess: () => {
      setContentId('')
      queryClient.invalidateQueries({ queryKey: linkedKey })
    },
  })
  const detach = useMutation({
    mutationFn: (selectedContentId: string) => activityContentApi.detach(scope, selectedContentId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: linkedKey }),
  })
  const linkedIds = new Set(linked.data?.map((item) => item.id) ?? [])
  const available = owned.data?.filter((item) => !linkedIds.has(item.id)) ?? []

  return (
    <div className="activity-content" aria-label="Linked Content">
      <h3>Linked Content</h3>
      {(linked.isPending || owned.isPending) && <LoadingState label="Loading Content" />}
      {linked.isError && <ErrorState message={errorMessage(linked.error)} />}
      {owned.isError && <ErrorState message={errorMessage(owned.error)} />}

      {linked.isSuccess && linked.data.length === 0 && (
        <p className="content-empty">No Content linked.</p>
      )}
      {linked.isSuccess && linked.data.length > 0 && (
        <ul className="content-links">
          {linked.data.map((reference) => (
            <li key={reference.id}>
              <div>
                <strong>{reference.type ?? 'Unavailable Content'}</strong>
                <span>Status: {reference.status ?? 'unavailable'}</span>
                <span>
                  Student access: {reference.available_for_student ? 'available' : 'unavailable'}
                </span>
              </div>
              <button
                className="button-secondary"
                disabled={detach.isPending}
                onClick={() => detach.mutate(reference.id)}
                type="button"
              >
                Remove
              </button>
            </li>
          ))}
        </ul>
      )}
      {detach.isError && <ErrorState message={errorMessage(detach.error)} />}

      {owned.isSuccess && (
        <div className="attach-content">
          <label>
            Existing Content
            <select onChange={(event) => setContentId(event.target.value)} value={contentId}>
              <option value="">Select Content</option>
              {available.map((content) => (
                <option key={content.id} value={content.id}>
                  {content.title} — {content.type} — {content.status}
                </option>
              ))}
            </select>
          </label>
          <button
            disabled={!contentId || attach.isPending}
            onClick={() => attach.mutate()}
            type="button"
          >
            {attach.isPending ? 'Attaching…' : 'Attach Content'}
          </button>
        </div>
      )}
      {attach.isError && <ErrorState message={errorMessage(attach.error)} />}
    </div>
  )
}
