import { QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { createQueryClient } from '../../app/providers'
import { ActivityContentPanel } from './ActivityContentPanel'

const scope = {
  teacherSpaceId: 'space-id',
  courseId: 'course-id',
  sectionId: 'section-id',
  learningUnitId: 'unit-id',
  activityId: 'activity-id',
}
const linksEndpoint =
  '/api/v1/teacher-spaces/space-id/environment/courses/course-id/sections/section-id/units/unit-id/activities/activity-id/contents'
const contentEndpoint = '/api/v1/contents'
const ownedContent = {
  id: 'content-id', type: 'article', title: 'Reading', status: 'draft',
  created_at: '2026-08-25T00:00:00Z', updated_at: '2026-08-25T00:00:00Z',
}
const reference = {
  id: 'content-id', type: 'article', status: 'published', available_for_student: true,
}
const jsonResponse = (body: unknown, status = 200) =>
  new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } })
const renderPanel = () =>
  render(
    <QueryClientProvider client={createQueryClient()}>
      <ActivityContentPanel scope={scope} />
    </QueryClientProvider>,
  )

describe('Activity Content management', () => {
  afterEach(() => vi.unstubAllGlobals())

  it('shows loading and empty linked Content state', async () => {
    let resolveLinks: ((response: Response) => void) | undefined
    vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input)
      if (url.endsWith(contentEndpoint)) return jsonResponse([ownedContent])
      return new Promise<Response>((resolve) => { resolveLinks = resolve })
    }))
    renderPanel()

    expect(screen.getByText('Loading Content')).toBeInTheDocument()
    resolveLinks?.(jsonResponse([]))
    expect(await screen.findByText('No Content linked.')).toBeInTheDocument()
  })

  it('displays only safe linked Content reference fields', async () => {
    vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL) =>
      String(input).endsWith(contentEndpoint) ? jsonResponse([]) : jsonResponse([reference]),
    ))
    renderPanel()

    expect(await screen.findByText('article')).toBeInTheDocument()
    expect(screen.getByText('Status: published')).toBeInTheDocument()
    expect(screen.getByText('Student access: available')).toBeInTheDocument()
    expect(screen.queryByText('Reading')).not.toBeInTheDocument()
  })

  it('selects owned Content, attaches it, and refreshes linked Content', async () => {
    let linked = [] as typeof reference[]
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input)
      if (url.endsWith(contentEndpoint)) return jsonResponse([ownedContent])
      if (url.endsWith(linksEndpoint) && init?.method === 'POST') {
        expect(JSON.parse(String(init.body))).toEqual({ content_id: 'content-id' })
        linked = [reference]
        return jsonResponse({ activity_id: 'activity-id', content_id: 'content-id' })
      }
      if (url.endsWith(linksEndpoint)) return jsonResponse(linked)
      throw new Error(`Unexpected request: ${url}`)
    })
    vi.stubGlobal('fetch', fetchMock)
    const user = userEvent.setup()
    renderPanel()

    await user.selectOptions(await screen.findByLabelText('Existing Content'), 'content-id')
    await user.click(screen.getByRole('button', { name: 'Attach Content' }))

    expect(await screen.findByText('Status: published')).toBeInTheDocument()
    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining(linksEndpoint),
      expect.objectContaining({ credentials: 'include', method: 'POST' }),
    )
  })

  it('detaches Content and refreshes the linked list', async () => {
    let linked = [reference]
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input)
      if (url.endsWith(contentEndpoint)) return jsonResponse([])
      if (url.endsWith(`${linksEndpoint}/content-id`) && init?.method === 'DELETE') {
        linked = []
        return new Response(null, { status: 204 })
      }
      if (url.endsWith(linksEndpoint)) return jsonResponse(linked)
      throw new Error(`Unexpected request: ${url}`)
    })
    vi.stubGlobal('fetch', fetchMock)
    const user = userEvent.setup()
    renderPanel()

    await user.click(await screen.findByRole('button', { name: 'Remove' }))
    expect(await screen.findByText('No Content linked.')).toBeInTheDocument()
  })

  it('shows linked-list and mutation errors', async () => {
    vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL) =>
      String(input).endsWith(contentEndpoint)
        ? jsonResponse([ownedContent])
        : jsonResponse({ detail: 'Content lookup unavailable' }, 503),
    ))
    const user = userEvent.setup()
    renderPanel()

    expect(await screen.findByRole('alert')).toHaveTextContent('Content lookup unavailable')
    await user.selectOptions(screen.getByLabelText('Existing Content'), 'content-id')
    await user.click(screen.getByRole('button', { name: 'Attach Content' }))
    expect((await screen.findAllByRole('alert')).at(-1)).toHaveTextContent(
      'Content lookup unavailable',
    )
  })
})
