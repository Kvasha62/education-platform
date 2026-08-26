import { QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { createMemoryRouter, RouterProvider } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { createQueryClient } from '../../app/providers'
import { routes } from '../../app/router'

const identity = {
  id: 'identity-id', email: 'teacher@example.com', status: 'active',
  created_at: '2026-08-26T00:00:00Z', updated_at: '2026-08-26T00:00:00Z',
}
const content = {
  id: 'content-id', type: 'resource', title: 'Reference', status: 'draft',
  created_at: '2026-08-26T00:00:00Z', updated_at: '2026-08-26T00:00:00Z',
}
const resourceBody = {
  schema_version: 1,
  kind: 'resource',
  resource: { url: null, description: '' },
}
const jsonResponse = (body: unknown, status = 200) =>
  new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } })

const renderRoute = () => {
  const router = createMemoryRouter(routes, { initialEntries: ['/app/contents/new'] })
  return render(
    <QueryClientProvider client={createQueryClient()}>
      <RouterProvider router={router} />
    </QueryClientProvider>,
  )
}

describe('Content creation UX', () => {
  afterEach(() => vi.unstubAllGlobals())

  it('creates selected Content type with title only and opens the Content Editor', async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input)
      if (url.endsWith('/api/v1/auth/me')) return jsonResponse(identity)
      if (url.endsWith('/api/v1/contents') && init?.method === 'POST') {
        expect(JSON.parse(String(init.body))).toEqual({ title: 'Reference', type: 'resource' })
        return jsonResponse(content, 201)
      }
      if (url.endsWith('/api/v1/contents/content-id/body')) return jsonResponse(resourceBody)
      if (url.endsWith('/api/v1/contents/content-id')) return jsonResponse(content)
      throw new Error(`Unexpected request: ${url}`)
    })
    vi.stubGlobal('fetch', fetchMock)
    const user = userEvent.setup()
    renderRoute()

    const type = await screen.findByLabelText('Content type')
    expect(withinOptions(type)).toEqual(['article', 'resource'])
    await user.selectOptions(type, 'resource')
    await user.type(screen.getByLabelText('Title'), 'Reference')
    await user.click(screen.getByRole('button', { name: 'Create Content' }))

    expect(await screen.findByRole('heading', { name: 'Reference' })).toBeInTheDocument()
    expect(screen.getByText('RESOURCE · DRAFT')).toBeInTheDocument()
    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringMatching(/\/api\/v1\/contents$/),
      expect.objectContaining({ credentials: 'include', method: 'POST' }),
    )
  })

  it('uses existing title constraints and shows creation loading state', async () => {
    vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input)
      if (url.endsWith('/api/v1/auth/me')) return jsonResponse(identity)
      if (url.endsWith('/api/v1/contents') && init?.method === 'POST') {
        return new Promise<Response>(() => undefined)
      }
      throw new Error(`Unexpected request: ${url}`)
    }))
    const user = userEvent.setup()
    renderRoute()

    const title = await screen.findByLabelText('Title')
    expect(title).toBeRequired()
    expect(title).toHaveAttribute('maxlength', '120')
    await user.type(title, 'Draft Article')
    await user.click(screen.getByRole('button', { name: 'Create Content' }))
    expect(screen.getByRole('button', { name: 'Creating…' })).toBeDisabled()
  })

  it('surfaces backend creation errors', async () => {
    vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input)
      if (url.endsWith('/api/v1/auth/me')) return jsonResponse(identity)
      if (init?.method === 'POST') return jsonResponse({ detail: 'Invalid Content title' }, 422)
      throw new Error(`Unexpected request: ${url}`)
    }))
    const user = userEvent.setup()
    renderRoute()

    await user.type(await screen.findByLabelText('Title'), 'Invalid')
    await user.click(screen.getByRole('button', { name: 'Create Content' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('Invalid Content title')
  })

  it('protects the creation route', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(jsonResponse({ detail: 'Authentication required' }, 401)),
    )
    renderRoute()
    expect(await screen.findByRole('heading', { name: 'Log in' })).toBeInTheDocument()
    expect(screen.queryByRole('heading', { name: 'Create Content' })).not.toBeInTheDocument()
  })
})

const withinOptions = (select: HTMLElement) =>
  Array.from(select.querySelectorAll('option')).map((option) => option.value)
