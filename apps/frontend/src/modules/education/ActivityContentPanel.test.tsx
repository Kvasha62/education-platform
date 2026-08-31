import { QueryClientProvider } from '@tanstack/react-query'
import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, useLocation } from 'react-router-dom'
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
const isContentRequest = (url: string) => url.includes(`${contentEndpoint}?`)
const ownedContent = {
  id: 'content-id', type: 'article', title: 'Reading', status: 'draft',
  created_at: '2026-08-25T00:00:00Z', updated_at: '2026-08-25T00:00:00Z',
}
const reference = {
  id: 'content-id', type: 'article', status: 'published', available_for_student: true,
}
const jsonResponse = (body: unknown, status = 200) =>
  new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } })
const contentPage = (items: unknown[], page = 1, hasNext = false) => ({
  items,
  page,
  page_size: 20,
  has_next: hasNext,
})
const LocationProbe = () => <output aria-label="Current route">{useLocation().pathname}</output>

const renderPanel = (readOnly = false) =>
  render(
    <QueryClientProvider client={createQueryClient()}>
      <MemoryRouter>
        <ActivityContentPanel readOnly={readOnly} scope={scope} />
        <LocationProbe />
      </MemoryRouter>
    </QueryClientProvider>,
  )

const mutationMethod = (init?: RequestInit) =>
  init?.method === 'POST' || init?.method === 'DELETE'

describe('Activity Content management', () => {
  afterEach(() => vi.unstubAllGlobals())

  it('shows loading and empty linked Content state', async () => {
    let resolveLinks: ((response: Response) => void) | undefined
    vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input)
      if (isContentRequest(url)) return jsonResponse(contentPage([]))
      return new Promise<Response>((resolve) => { resolveLinks = resolve })
    }))
    renderPanel()

    expect(screen.getByText('Loading Content')).toBeInTheDocument()
    resolveLinks?.(jsonResponse([]))
    expect(await screen.findByText('No Content linked.')).toBeInTheDocument()
    expect(within(screen.getByLabelText('Existing Content')).getAllByRole('option')).toHaveLength(1)
    expect(screen.queryByRole('button', { name: 'Load more' })).not.toBeInTheDocument()
  })

  it('displays only safe linked Content reference fields', async () => {
    vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL) =>
      isContentRequest(String(input)) ? jsonResponse(contentPage([])) : jsonResponse([reference]),
    ))
    const user = userEvent.setup()
    renderPanel()

    expect(await screen.findByText('article')).toBeInTheDocument()
    expect(screen.getByText('Status: published')).toBeInTheDocument()
    expect(screen.getByText('Student access: available')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Edit Content' })).toHaveAttribute(
      'href',
      '/app/contents/content-id/edit',
    )
    expect(screen.queryByText('Reading')).not.toBeInTheDocument()
    await user.click(screen.getByRole('link', { name: 'Edit Content' }))
    expect(screen.getByLabelText('Current route')).toHaveTextContent(
      '/app/contents/content-id/edit',
    )
  })

  it('selects owned Content, attaches it, and refreshes linked Content', async () => {
    let linked = [] as typeof reference[]
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input)
      if (isContentRequest(url)) return jsonResponse(contentPage([ownedContent]))
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
      if (isContentRequest(url)) return jsonResponse(contentPage([]))
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
      isContentRequest(String(input))
        ? jsonResponse(contentPage([ownedContent]))
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
  it('loads additional Content pages and appends their items', async () => {
    const secondContent = { ...ownedContent, id: 'content-2', title: 'Second Reading' }
    const requests: string[] = []
    let resolveSecondPage: ((response: Response) => void) | undefined
    vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input)
      requests.push(url)
      if (url.includes('page=1&page_size=20')) {
        return jsonResponse(contentPage([ownedContent], 1, true))
      }
      if (url.includes('page=2&page_size=20')) {
        return new Promise<Response>((resolve) => { resolveSecondPage = resolve })
      }
      if (url.endsWith(linksEndpoint)) return jsonResponse([])
      throw new Error(`Unexpected request: ${url}`)
    }))
    const user = userEvent.setup()
    renderPanel()

    const select = await screen.findByLabelText('Existing Content')
    expect(within(select).getByRole('option', { name: /Reading/ })).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Load more' }))
    expect(screen.getByRole('button', { name: 'Loading more…' })).toBeDisabled()
    resolveSecondPage?.(jsonResponse(contentPage([secondContent], 2, false)))

    expect(await within(select).findByRole('option', { name: /Second Reading/ })).toBeInTheDocument()
    expect(within(select).getByRole('option', { name: /^Reading/ })).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Load more' })).not.toBeInTheDocument()
    expect(requests.some((url) => url.includes('page=2&page_size=20'))).toBe(true)
  })

  it('disables attach/detach in read-only mode and sends no mutation requests', async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input)
      if (isContentRequest(url)) return jsonResponse(contentPage([ownedContent]))
      if (url.endsWith(linksEndpoint)) return jsonResponse([reference])
      throw new Error(`Unexpected request: ${url}`)
    })
    vi.stubGlobal('fetch', fetchMock)
    const user = userEvent.setup()
    renderPanel(true)

    expect(await screen.findByText('Status: published')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Attach Content' })).toBeDisabled()
    expect(screen.getByRole('button', { name: 'Remove' })).toBeDisabled()
    expect(screen.getByLabelText('Existing Content')).toBeDisabled()
    expect(screen.getByRole('link', { name: 'Edit Content' })).toHaveAttribute(
      'href',
      '/app/contents/content-id/edit',
    )
    await user.click(screen.getByRole('button', { name: 'Attach Content' }))
    await user.click(screen.getByRole('button', { name: 'Remove' }))
    expect(fetchMock.mock.calls.filter(([, init]) => mutationMethod(init))).toHaveLength(0)
  })

  it('keeps Load more pagination available in read-only mode', async () => {
    const secondContent = { ...ownedContent, id: 'content-2', title: 'Second Reading' }
    let resolveSecondPage: ((response: Response) => void) | undefined
    vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input)
      if (url.includes('page=1&page_size=20')) {
        return jsonResponse(contentPage([ownedContent], 1, true))
      }
      if (url.includes('page=2&page_size=20')) {
        return new Promise<Response>((resolve) => { resolveSecondPage = resolve })
      }
      if (url.endsWith(linksEndpoint)) return jsonResponse([])
      throw new Error(`Unexpected request: ${url}`)
    }))
    const user = userEvent.setup()
    renderPanel(true)

    const select = await screen.findByLabelText('Existing Content')
    expect(within(select).getByRole('option', { name: /Reading/ })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Load more' })).toBeEnabled()
    await user.click(screen.getByRole('button', { name: 'Load more' }))
    resolveSecondPage?.(jsonResponse(contentPage([secondContent], 2, false)))

    expect(await within(select).findByRole('option', { name: /Second Reading/ })).toBeInTheDocument()
  })
})
