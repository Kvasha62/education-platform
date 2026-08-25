import { QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { createMemoryRouter, RouterProvider } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { createQueryClient } from '../../app/providers'
import { routes } from '../../app/router'

const identity = {
  id: 'identity-id',
  email: 'teacher@example.com',
  status: 'active',
  created_at: '2026-08-25T00:00:00Z',
  updated_at: '2026-08-25T00:00:00Z',
}
const teacherSpace = {
  id: 'space-id',
  name: 'My School',
  status: 'active',
  created_at: '2026-08-25T00:00:00Z',
  updated_at: '2026-08-25T00:00:00Z',
}
const jsonResponse = (body: unknown, status = 200) =>
  new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })

const renderRoute = (entry = '/app/teacher-spaces') => {
  const router = createMemoryRouter(routes, { initialEntries: [entry] })
  return render(
    <QueryClientProvider client={createQueryClient()}>
      <RouterProvider router={router} />
    </QueryClientProvider>,
  )
}

describe('Teacher Spaces UI', () => {
  afterEach(() => vi.unstubAllGlobals())

  it('shows loading and empty states for an authenticated user', async () => {
    let resolveList: ((response: Response) => void) | undefined
    vi.stubGlobal(
      'fetch',
      vi.fn(async (input: RequestInfo | URL) => {
        const url = String(input)
        if (url.endsWith('/api/v1/auth/me')) return jsonResponse(identity)
        return new Promise<Response>((resolve) => { resolveList = resolve })
      }),
    )
    renderRoute()

    expect(await screen.findByText('Loading Teacher Spaces')).toBeInTheDocument()
    resolveList?.(jsonResponse([]))
    expect(await screen.findByRole('heading', { name: 'No Teacher Spaces yet' })).toBeInTheDocument()
  })

  it('lists own Teacher Spaces', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async (input: RequestInfo | URL) =>
        String(input).endsWith('/api/v1/auth/me') ? jsonResponse(identity) : jsonResponse([teacherSpace]),
      ),
    )
    renderRoute()

    expect(await screen.findByText('My School')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Open' })).toHaveAttribute(
      'href',
      '/app/teacher-spaces/space-id',
    )
  })

  it('creates a Teacher Space, updates the list, and opens its API detail', async () => {
    const requests: string[] = []
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input)
      requests.push(`${init?.method ?? 'GET'} ${url}`)
      if (url.endsWith('/api/v1/auth/me')) return jsonResponse(identity)
      if (url.endsWith('/api/v1/teacher-spaces') && init?.method === 'POST') {
        return jsonResponse(teacherSpace, 201)
      }
      if (url.endsWith('/api/v1/teacher-spaces')) return jsonResponse([])
      if (url.endsWith('/api/v1/teacher-spaces/space-id')) return jsonResponse(teacherSpace)
      throw new Error(`Unexpected request: ${url}`)
    })
    vi.stubGlobal('fetch', fetchMock)
    const user = userEvent.setup()
    renderRoute()

    await user.type(await screen.findByLabelText('Teacher Space name'), 'My School')
    await user.click(screen.getByRole('button', { name: 'Create Teacher Space' }))
    await user.click(await screen.findByRole('link', { name: 'Open' }))

    expect(await screen.findByRole('heading', { name: 'My School' })).toBeInTheDocument()
    expect(requests).toContain('POST /api/v1/teacher-spaces')
    expect(requests).toContain('GET /api/v1/teacher-spaces/space-id')
    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining('/api/v1/teacher-spaces'),
      expect.objectContaining({ credentials: 'include', method: 'POST' }),
    )
  })

  it('shows a normalized list error', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async (input: RequestInfo | URL) =>
        String(input).endsWith('/api/v1/auth/me')
          ? jsonResponse(identity)
          : jsonResponse({ detail: 'Teacher Spaces unavailable' }, 503),
      ),
    )
    renderRoute()

    expect(await screen.findByRole('alert')).toHaveTextContent('Teacher Spaces unavailable')
  })

  it('protects the Teacher Spaces route from unauthenticated users', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(jsonResponse({ detail: 'Authentication required' }, 401)),
    )
    renderRoute()

    expect(await screen.findByRole('heading', { name: 'Log in' })).toBeInTheDocument()
    expect(screen.queryByRole('heading', { name: 'My Teacher Spaces' })).not.toBeInTheDocument()
  })
})
