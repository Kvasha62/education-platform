import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { ApiError } from '../../shared/api'
import { ErrorState, LoadingState } from '../../shared/ui'
import { contentApi } from './api'
import type { ArticleBlock, ArticleBlockType, ContentBody } from './body'
import { createBlock } from './body'
import { contentKeys } from './queries'

const blockTypes: Array<{ value: ArticleBlockType; label: string }> = [
  { value: 'paragraph', label: 'Paragraph' },
  { value: 'heading', label: 'Heading' },
  { value: 'code', label: 'Code' },
  { value: 'list', label: 'List' },
  { value: 'link', label: 'Link' },
]
const errorMessage = (error: unknown) =>
  error instanceof ApiError || error instanceof Error ? error.message : 'Request failed.'

interface BlockEditorProps {
  block: ArticleBlock
  disabled: boolean
  onChange: (block: ArticleBlock) => void
  onRemove: () => void
}

const BlockEditor = ({ block, disabled, onChange, onRemove }: BlockEditorProps) => (
  <li className="content-block">
    <strong>{block.type}</strong>
    {block.type === 'paragraph' && (
      <label>
        Text
        <textarea
          disabled={disabled}
          onChange={(event) => onChange({ ...block, text: event.target.value })}
          value={block.text}
        />
      </label>
    )}
    {block.type === 'heading' && (
      <>
        <label>
          Level
          <input
            disabled={disabled}
            max={4}
            min={1}
            onChange={(event) => onChange({ ...block, level: Number(event.target.value) })}
            type="number"
            value={block.level}
          />
        </label>
        <label>
          Text
          <input
            disabled={disabled}
            onChange={(event) => onChange({ ...block, text: event.target.value })}
            value={block.text}
          />
        </label>
      </>
    )}
    {block.type === 'code' && (
      <>
        <label>
          Language
          <input
            disabled={disabled}
            onChange={(event) => onChange({ ...block, language: event.target.value || null })}
            value={block.language ?? ''}
          />
        </label>
        <label>
          Code
          <textarea
            disabled={disabled}
            onChange={(event) => onChange({ ...block, code: event.target.value })}
            value={block.code}
          />
        </label>
      </>
    )}
    {block.type === 'list' && (
      <>
        <label>
          Style
          <select
            disabled={disabled}
            onChange={(event) =>
              onChange({ ...block, style: event.target.value as 'ordered' | 'unordered' })
            }
            value={block.style}
          >
            <option value="unordered">Unordered</option>
            <option value="ordered">Ordered</option>
          </select>
        </label>
        <label>
          Items, one per line
          <textarea
            disabled={disabled}
            onChange={(event) => onChange({ ...block, items: event.target.value.split('\n') })}
            value={block.items.join('\n')}
          />
        </label>
      </>
    )}
    {block.type === 'link' && (
      <>
        <label>
          URL
          <input
            disabled={disabled}
            onChange={(event) => onChange({ ...block, url: event.target.value })}
            value={block.url}
          />
        </label>
        <label>
          Label
          <input
            disabled={disabled}
            onChange={(event) => onChange({ ...block, label: event.target.value })}
            value={block.label}
          />
        </label>
      </>
    )}
    {!disabled && (
      <button className="button-secondary" onClick={onRemove} type="button">
        Remove block
      </button>
    )}
  </li>
)

export const ContentEditorPage = () => {
  const { contentId = '' } = useParams<{ contentId: string }>()
  const queryClient = useQueryClient()
  const metadata = useQuery({
    queryKey: contentKeys.detail(contentId),
    queryFn: () => contentApi.get(contentId),
    enabled: Boolean(contentId),
  })
  const body = useQuery({
    queryKey: contentKeys.body(contentId),
    queryFn: () => contentApi.getBody(contentId),
    enabled: Boolean(contentId),
  })
  const [draft, setDraft] = useState<ContentBody | null>(null)
  const [newBlockType, setNewBlockType] = useState<ArticleBlockType>('paragraph')
  useEffect(() => {
    if (body.data) setDraft(body.data)
  }, [body.data])
  const save = useMutation({
    mutationFn: (value: ContentBody) => contentApi.replaceBody(contentId, value),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: contentKeys.body(contentId) }),
  })
  const readOnly = metadata.data?.status === 'published'

  if (metadata.isError) return <ErrorState message={errorMessage(metadata.error)} />
  if (body.isError) return <ErrorState message={errorMessage(body.error)} />
  if (metadata.isPending || body.isPending || !draft) {
    return <LoadingState label="Loading Content Editor" />
  }

  const saveDraft = () => {
    if (!readOnly) save.mutate(draft)
  }

  return (
    <section className="content-editor" aria-labelledby="content-editor-title">
      <Link to="/app">← Teacher Workspace</Link>
      <div>
        <p className="eyebrow">Content Editor</p>
        <h1 id="content-editor-title">{metadata.data.title}</h1>
        <p>{draft.kind.toUpperCase()} · {metadata.data.status.toUpperCase()}</p>
      </div>
      {readOnly && <div className="state">Published Content is read-only.</div>}

      {draft.kind === 'article' ? (
        <div className="article-editor">
          <h2>Article blocks</h2>
          {draft.blocks.length === 0 && <p className="content-empty">No blocks yet.</p>}
          <ol className="content-blocks">
            {draft.blocks.map((block, index) => (
              <BlockEditor
                block={block}
                disabled={readOnly}
                key={index}
                onChange={(updated) =>
                  setDraft({ ...draft, blocks: draft.blocks.map((item, itemIndex) =>
                    itemIndex === index ? updated : item,
                  ) })
                }
                onRemove={() =>
                  setDraft({ ...draft, blocks: draft.blocks.filter((_, itemIndex) =>
                    itemIndex !== index,
                  ) })
                }
              />
            ))}
          </ol>
          {!readOnly && (
            <div className="editor-actions">
              <label>
                Block type
                <select
                  onChange={(event) => setNewBlockType(event.target.value as ArticleBlockType)}
                  value={newBlockType}
                >
                  {blockTypes.map((item) => (
                    <option key={item.value} value={item.value}>{item.label}</option>
                  ))}
                </select>
              </label>
              <button
                onClick={() => setDraft({ ...draft, blocks: [...draft.blocks, createBlock(newBlockType)] })}
                type="button"
              >
                Add block
              </button>
            </div>
          )}
        </div>
      ) : (
        <div className="resource-editor">
          <label>
            Resource URL
            <input
              disabled={readOnly}
              onChange={(event) =>
                setDraft({ ...draft, resource: { ...draft.resource, url: event.target.value || null } })
              }
              type="url"
              value={draft.resource.url ?? ''}
            />
          </label>
          <label>
            Description
            <textarea
              disabled={readOnly}
              onChange={(event) =>
                setDraft({ ...draft, resource: { ...draft.resource, description: event.target.value } })
              }
              value={draft.resource.description}
            />
          </label>
        </div>
      )}

      {save.isError && <ErrorState message={errorMessage(save.error)} />}
      {!readOnly && (
        <button disabled={save.isPending} onClick={saveDraft} type="button">
          {save.isPending ? 'Saving…' : 'Save Content'}
        </button>
      )}
    </section>
  )
}
