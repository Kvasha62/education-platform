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
const environment = {
  id: 'environment-id',
  teacher_space_id: 'space-id',
  name: 'Primary Environment',
  created_at: '2026-08-25T00:00:00Z',
  updated_at: '2026-08-25T00:00:00Z',
}
const route = '/app/teacher-spaces/space-id/environment'
const endpoint = '/api/v1/teacher-spaces/space-id/environment'
const jsonResponse = (body: unknown, status = 200) =>
  new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })

const renderRoute = () => {
  const router = createMemoryRouter(routes, { initialEntries: [route] })
  return render(
    <QueryClientProvider client={createQueryClient()}>
      <RouterProvider router={router} />
    </QueryClientProvider>,
  )
}

describe('Educational Environment UI', () => {
  afterEach(() => vi.unstubAllGlobals())

  it('shows loading and treats a missing singleton as the empty state', async () => {
    let resolveEnvironment: ((response: Response) => void) | undefined
    vi.stubGlobal(
      'fetch',
      vi.fn(async (input: RequestInfo | URL) => {
        if (String(input).endsWith('/api/v1/auth/me')) return jsonResponse(identity)
        return new Promise<Response>((resolve) => { resolveEnvironment = resolve })
      }),
    )
    renderRoute()

    expect(await screen.findByText('Loading Educational Environment')).toBeInTheDocument()
    resolveEnvironment?.(jsonResponse({ detail: 'Educational Environment not found' }, 404))
    expect(
      await screen.findByRole('heading', { name: 'No Educational Environment yet' }),
    ).toBeInTheDocument()
  })

  it('opens the Teacher Space singleton Environment', async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL) =>
      String(input).endsWith('/api/v1/auth/me') ? jsonResponse(identity) : jsonResponse(environment),
    )
    vi.stubGlobal('fetch', fetchMock)
    renderRoute()

    expect(await screen.findByRole('heading', { name: environment.name })).toBeInTheDocument()
    expect(screen.getByText(environment.teacher_space_id)).toBeInTheDocument()
    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining(endpoint),
      expect.objectContaining({ credentials: 'include' }),
    )
  })

  it('creates the singleton and updates its TanStack Query state', async () => {
    const requests: string[] = []
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input)
      requests.push(`${init?.method ?? 'GET'} ${url}`)
      if (url.endsWith('/api/v1/auth/me')) return jsonResponse(identity)
      if (url.endsWith(endpoint) && init?.method === 'POST') return jsonResponse(environment, 201)
      if (url.endsWith(endpoint)) {
        return jsonResponse({ detail: 'Educational Environment not found' }, 404)
      }
      throw new Error(`Unexpected request: ${url}`)
    })
    vi.stubGlobal('fetch', fetchMock)
    const user = userEvent.setup()
    renderRoute()

    await user.type(await screen.findByLabelText('Environment name'), environment.name)
    await user.click(screen.getByRole('button', { name: 'Create Environment' }))

    expect(await screen.findByRole('heading', { name: environment.name })).toBeInTheDocument()
    expect(requests).toContain(`POST ${endpoint}`)
    expect(screen.queryByRole('heading', { name: 'No Educational Environment yet' })).not.toBeInTheDocument()
    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining(endpoint),
      expect.objectContaining({ credentials: 'include', method: 'POST' }),
    )
  })

  it('shows non-404 API failures as errors', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async (input: RequestInfo | URL) =>
        String(input).endsWith('/api/v1/auth/me')
          ? jsonResponse(identity)
          : jsonResponse({ detail: 'Environment unavailable' }, 503),
      ),
    )
    renderRoute()

    expect(await screen.findByRole('alert')).toHaveTextContent('Environment unavailable')
    expect(screen.queryByRole('heading', { name: 'No Educational Environment yet' })).not.toBeInTheDocument()
  })

  it('protects the Environment route from unauthenticated users', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(jsonResponse({ detail: 'Authentication required' }, 401)),
    )
    renderRoute()

    expect(await screen.findByRole('heading', { name: 'Log in' })).toBeInTheDocument()
    expect(screen.queryByLabelText('Environment name')).not.toBeInTheDocument()
  })
})
