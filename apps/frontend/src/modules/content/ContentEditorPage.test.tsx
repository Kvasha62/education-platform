import { QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { createMemoryRouter, RouterProvider } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { createQueryClient } from '../../app/providers'
import { routes } from '../../app/router'
import type { ContentBody } from './body'

const identity = {
  id: 'identity-id', email: 'teacher@example.com', status: 'active',
  created_at: '2026-08-25T00:00:00Z', updated_at: '2026-08-25T00:00:00Z',
}
const metadata = {
  id: 'content-id', type: 'article', title: 'Programming Article', status: 'draft',
  created_at: '2026-08-25T00:00:00Z', updated_at: '2026-08-25T00:00:00Z',
}
const emptyArticle: ContentBody = { schema_version: 1, kind: 'article', blocks: [] }
const emptyResource: ContentBody = {
  schema_version: 1,
  kind: 'resource',
  resource: { url: null, description: '' },
}
const route = '/app/contents/content-id/edit'
const bodyEndpoint = '/api/v1/contents/content-id/body'
const detailEndpoint = '/api/v1/contents/content-id'
const jsonResponse = (body: unknown, status = 200) =>
  new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } })

const renderRoute = () => {
  const router = createMemoryRouter(routes, { initialEntries: [route] })
  const queryClient = createQueryClient()
  const view = render(
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
    </QueryClientProvider>,
  )
  return { ...view, queryClient }
}

const successfulFetch = (body: ContentBody, content = metadata) =>
  vi.fn(async (input: RequestInfo | URL) => {
    const url = String(input)
    if (url.endsWith('/api/v1/auth/me')) return jsonResponse(identity)
    if (url.endsWith(bodyEndpoint)) return jsonResponse(body)
    if (url.endsWith(detailEndpoint)) return jsonResponse(content)
    throw new Error(`Unexpected request: ${url}`)
  })

describe('Content Editor Foundation', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
    vi.restoreAllMocks()
  })

  it('renders the protected route and loading state', async () => {
    let resolveBody: ((response: Response) => void) | undefined
    vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input)
      if (url.endsWith('/api/v1/auth/me')) return jsonResponse(identity)
      if (url.endsWith(detailEndpoint)) return jsonResponse(metadata)
      return new Promise<Response>((resolve) => { resolveBody = resolve })
    }))
    renderRoute()

    expect(await screen.findByText('Loading Content Editor')).toBeInTheDocument()
    resolveBody?.(jsonResponse(emptyArticle))
    expect(await screen.findByRole('heading', { name: metadata.title })).toBeInTheDocument()
  })

  it('loads and saves an empty DRAFT ARTICLE as the complete canonical body', async () => {
    let bodyGets = 0
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input)
      if (url.endsWith('/api/v1/auth/me')) return jsonResponse(identity)
      if (url.endsWith(detailEndpoint)) return jsonResponse(metadata)
      if (url.endsWith(bodyEndpoint) && init?.method === 'PUT') {
        expect(JSON.parse(String(init.body))).toEqual(emptyArticle)
        return jsonResponse(emptyArticle)
      }
      if (url.endsWith(bodyEndpoint)) {
        bodyGets += 1
        return jsonResponse(emptyArticle)
      }
      throw new Error(`Unexpected request: ${url}`)
    })
    vi.stubGlobal('fetch', fetchMock)
    const user = userEvent.setup()
    renderRoute()

    expect(await screen.findByText('No blocks yet.')).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Save Content' }))
    await waitFor(() => expect(bodyGets).toBeGreaterThanOrEqual(2))
    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining(bodyEndpoint),
      expect.objectContaining({ credentials: 'include', method: 'PUT' }),
    )
  })

  it('adds, edits, and removes approved ARTICLE blocks', async () => {
    vi.stubGlobal('fetch', successfulFetch(emptyArticle))
    const user = userEvent.setup()
    renderRoute()

    const typeSelect = await screen.findByLabelText('Block type')
    expect(within(typeSelect).getAllByRole('option').map((option) => option.getAttribute('value'))).toEqual([
      'paragraph', 'heading', 'code', 'list', 'link',
    ])
    await user.click(screen.getByRole('button', { name: 'Add block' }))
    await user.type(screen.getByLabelText('Text'), 'Hello learners')
    expect(screen.getByDisplayValue('Hello learners')).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Remove block' }))
    expect(screen.getByText('No blocks yet.')).toBeInTheDocument()

    await user.selectOptions(typeSelect, 'link')
    await user.click(screen.getByRole('button', { name: 'Add block' }))
    expect(screen.getByLabelText('URL')).toHaveValue('')
  })

  it('loads and saves an empty DRAFT RESOURCE with edited URL and description', async () => {
    const savedBodies: unknown[] = []
    const resourceMetadata = { ...metadata, type: 'resource' }
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input)
      if (url.endsWith('/api/v1/auth/me')) return jsonResponse(identity)
      if (url.endsWith(detailEndpoint)) return jsonResponse(resourceMetadata)
      if (url.endsWith(bodyEndpoint) && init?.method === 'PUT') {
        const saved = JSON.parse(String(init.body))
        savedBodies.push(saved)
        return jsonResponse(saved)
      }
      if (url.endsWith(bodyEndpoint)) return jsonResponse(emptyResource)
      throw new Error(`Unexpected request: ${url}`)
    })
    vi.stubGlobal('fetch', fetchMock)
    const user = userEvent.setup()
    renderRoute()

    const url = await screen.findByLabelText('Resource URL')
    expect(url).toHaveValue('')
    await user.click(screen.getByRole('button', { name: 'Save Content' }))
    await waitFor(() => expect(savedBodies).toHaveLength(1))
    expect(savedBodies[0]).toEqual(emptyResource)

    await user.type(url, 'https://example.test/resource')
    await user.type(screen.getByLabelText('Description'), 'Reference material')
    await user.click(screen.getByRole('button', { name: 'Save Content' }))
    await waitFor(() => expect(savedBodies).toHaveLength(2))
    expect(savedBodies[1]).toEqual({
      schema_version: 1,
      kind: 'resource',
      resource: { url: 'https://example.test/resource', description: 'Reference material' },
    })
  })

  it('surfaces backend save errors', async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input)
      if (url.endsWith('/api/v1/auth/me')) return jsonResponse(identity)
      if (url.endsWith(detailEndpoint)) return jsonResponse(metadata)
      if (url.endsWith(bodyEndpoint) && init?.method === 'PUT') {
        return jsonResponse({ detail: 'Invalid Content body' }, 422)
      }
      if (url.endsWith(bodyEndpoint)) return jsonResponse(emptyArticle)
      throw new Error(`Unexpected request: ${url}`)
    })
    vi.stubGlobal('fetch', fetchMock)
    const user = userEvent.setup()
    renderRoute()

    await user.click(await screen.findByRole('button', { name: 'Save Content' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('Invalid Content body')
  })

  it('renders PUBLISHED Content read-only and never sends PUT', async () => {
    const published = { ...metadata, status: 'published' }
    const fetchMock = successfulFetch({
      schema_version: 1,
      kind: 'article',
      blocks: [{ type: 'paragraph', text: 'Published body' }],
    }, published)
    vi.stubGlobal('fetch', fetchMock)
    renderRoute()

    expect(await screen.findByText('Published Content is read-only.')).toBeInTheDocument()
    expect(screen.getByLabelText('Text')).toBeDisabled()
    expect(screen.queryByRole('button', { name: 'Save Content' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Publish Content' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Add block' })).not.toBeInTheDocument()
    expect(
      fetchMock.mock.calls.filter(([input]) => String(input).endsWith(bodyEndpoint)),
    ).toHaveLength(1)
  })

  it('publishes saved DRAFT Content, refetches queries, and becomes read-only', async () => {
    let status = 'draft'
    let metadataGets = 0
    let bodyGets = 0
    const publishableBody: ContentBody = {
      schema_version: 1,
      kind: 'article',
      blocks: [{ type: 'paragraph', text: 'Ready to publish' }],
    }
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input)
      if (url.endsWith('/api/v1/auth/me')) return jsonResponse(identity)
      if (url.endsWith(`${detailEndpoint}/publish`) && init?.method === 'POST') {
        status = 'published'
        return jsonResponse({ ...metadata, status })
      }
      if (url.endsWith(bodyEndpoint)) {
        bodyGets += 1
        return jsonResponse(publishableBody)
      }
      if (url.endsWith(detailEndpoint)) {
        metadataGets += 1
        return jsonResponse({ ...metadata, status })
      }
      throw new Error(`Unexpected request: ${url}`)
    })
    vi.stubGlobal('fetch', fetchMock)
    const user = userEvent.setup()
    renderRoute()

    await user.click(await screen.findByRole('button', { name: 'Publish Content' }))
    expect(await screen.findByText('Published Content is read-only.')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Save Content' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Publish Content' })).not.toBeInTheDocument()
    expect(metadataGets).toBeGreaterThanOrEqual(2)
    expect(bodyGets).toBeGreaterThanOrEqual(2)
    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining(`${detailEndpoint}/publish`),
      expect.objectContaining({ credentials: 'include', method: 'POST' }),
    )
  })

  it('surfaces backend publish validation errors and remains editable', async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input)
      if (url.endsWith('/api/v1/auth/me')) return jsonResponse(identity)
      if (url.endsWith(`${detailEndpoint}/publish`) && init?.method === 'POST') {
        return jsonResponse({ detail: 'Content body is not publishable' }, 409)
      }
      if (url.endsWith(bodyEndpoint)) return jsonResponse(emptyArticle)
      if (url.endsWith(detailEndpoint)) return jsonResponse(metadata)
      throw new Error(`Unexpected request: ${url}`)
    })
    vi.stubGlobal('fetch', fetchMock)
    const user = userEvent.setup()
    renderRoute()

    await user.click(await screen.findByRole('button', { name: 'Publish Content' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('Content body is not publishable')
    expect(screen.getByRole('button', { name: 'Publish Content' })).toBeEnabled()
    expect(screen.getByRole('button', { name: 'Save Content' })).toBeEnabled()
  })

  it('requires explicit Save before publishing local body changes', async () => {
    const fetchMock = successfulFetch(emptyArticle)
    vi.stubGlobal('fetch', fetchMock)
    const user = userEvent.setup()
    renderRoute()

    await user.click(await screen.findByRole('button', { name: 'Add block' }))
    expect(screen.getByText('Save changes before publishing.')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Publish Content' })).toBeDisabled()
    expect(
      fetchMock.mock.calls.some(([input]) => String(input).endsWith('/publish')),
    ).toBe(false)
  })

  it.each(['draft', 'published'])(
    'confirms and deletes %s Content, invalidates queries, and returns to Teacher Workspace',
    async (contentStatus) => {
      const currentMetadata = { ...metadata, status: contentStatus }
      const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
        const url = String(input)
        if (url.endsWith('/api/v1/auth/me')) return jsonResponse(identity)
        if (url.endsWith(bodyEndpoint)) return jsonResponse(emptyArticle)
        if (url.endsWith(detailEndpoint) && init?.method === 'DELETE') {
          return new Response(null, { status: 204 })
        }
        if (url.endsWith(detailEndpoint)) return jsonResponse(currentMetadata)
        throw new Error(`Unexpected request: ${url}`)
      })
      vi.stubGlobal('fetch', fetchMock)
      vi.spyOn(window, 'confirm').mockReturnValue(true)
      const user = userEvent.setup()
      const { queryClient } = renderRoute()
      const invalidate = vi.spyOn(queryClient, 'invalidateQueries')

      await user.click(await screen.findByRole('button', { name: 'Delete Content' }))
      expect(window.confirm).toHaveBeenCalledWith('Permanently delete "Programming Article"?')
      expect(await screen.findByRole('heading', { name: 'Teacher Workspace' })).toBeInTheDocument()
      expect(fetchMock).toHaveBeenCalledWith(
        expect.stringContaining(detailEndpoint),
        expect.objectContaining({ credentials: 'include', method: 'DELETE' }),
      )
      expect(invalidate).toHaveBeenCalledWith({ queryKey: ['owned-content'] })
      expect(fetchMock.mock.calls.some(([, init]) => init?.method === 'PUT')).toBe(false)
      expect(fetchMock.mock.calls.some(([input]) => String(input).endsWith('/publish'))).toBe(false)
    },
  )

  it('cancels deletion without sending a mutation', async () => {
    const fetchMock = successfulFetch(emptyArticle)
    vi.stubGlobal('fetch', fetchMock)
    vi.spyOn(window, 'confirm').mockReturnValue(false)
    const user = userEvent.setup()
    renderRoute()

    await user.click(await screen.findByRole('button', { name: 'Delete Content' }))
    expect(window.confirm).toHaveBeenCalledOnce()
    expect(fetchMock).toHaveBeenCalledTimes(3)
    expect(screen.getByRole('heading', { name: metadata.title })).toBeInTheDocument()
  })

  it('prevents duplicate deletion while loading and surfaces backend errors', async () => {
    let rejectDelete: ((response: Response) => void) | undefined
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input)
      if (url.endsWith('/api/v1/auth/me')) return jsonResponse(identity)
      if (url.endsWith(bodyEndpoint)) return jsonResponse(emptyArticle)
      if (url.endsWith(detailEndpoint) && init?.method === 'DELETE') {
        return new Promise<Response>((resolve) => { rejectDelete = resolve })
      }
      if (url.endsWith(detailEndpoint)) return jsonResponse(metadata)
      throw new Error(`Unexpected request: ${url}`)
    })
    vi.stubGlobal('fetch', fetchMock)
    vi.spyOn(window, 'confirm').mockReturnValue(true)
    const user = userEvent.setup()
    renderRoute()

    await user.click(await screen.findByRole('button', { name: 'Delete Content' }))
    expect(screen.getByRole('button', { name: 'Deleting…' })).toBeDisabled()
    rejectDelete?.(jsonResponse({ detail: 'Content not found' }, 404))
    expect(await screen.findByRole('alert')).toHaveTextContent('Content not found')
    expect(screen.getByRole('button', { name: 'Delete Content' })).toBeEnabled()
  })

  it('protects the Content Editor route', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(jsonResponse({ detail: 'Authentication required' }, 401)),
    )
    renderRoute()
    expect(await screen.findByRole('heading', { name: 'Log in' })).toBeInTheDocument()
    expect(screen.queryByText('Content Editor')).not.toBeInTheDocument()
  })
})
