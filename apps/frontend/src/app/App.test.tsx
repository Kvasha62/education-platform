import { QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { createMemoryRouter, RouterProvider } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { createQueryClient } from './providers'
import { routes } from './router'

const identity = {
  id: 'identity-id',
  email: 'person@example.com',
  status: 'active',
  created_at: '2026-08-25T00:00:00Z',
  updated_at: '2026-08-25T00:00:00Z',
}

const jsonResponse = (body: unknown, status = 200) =>
  new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })

const renderApplication = (initialEntry: string) => {
  const queryClient = createQueryClient()
  const router = createMemoryRouter(routes, { initialEntries: [initialEntry] })
  return render(
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
    </QueryClientProvider>,
  )
}

describe('authentication UI', () => {
  afterEach(() => vi.unstubAllGlobals())

  it('restores an authenticated session and renders the protected app', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(jsonResponse(identity)))
    renderApplication('/app')

    expect(screen.getByRole('status')).toHaveTextContent('Loading application')
    expect(await screen.findByRole('heading', { name: 'Teacher Workspace' })).toBeInTheDocument()
    expect(screen.getByText(/welcome, person@example.com/i)).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Open Teacher Spaces' })).toHaveAttribute(
      'href',
      '/app/teacher-spaces',
    )
  })

  it('redirects an unauthenticated visitor away from the protected app', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(jsonResponse({ detail: 'Authentication required' }, 401)),
    )
    renderApplication('/app')

    expect(await screen.findByRole('heading', { name: 'Log in' })).toBeInTheDocument()
  })

  it('automatically logs in after registration, bootstraps auth, and logs out', async () => {
    let authenticated = false
    const requests: string[] = []
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input)
      requests.push(`${init?.method ?? 'GET'} ${url}`)
      if (url.endsWith('/api/v1/auth/me')) {
        return authenticated
          ? jsonResponse(identity)
          : jsonResponse({ detail: 'Authentication required' }, 401)
      }
      if (url.endsWith('/api/v1/auth/register')) return jsonResponse(identity, 201)
      if (url.endsWith('/api/v1/auth/login')) {
        authenticated = true
        return jsonResponse({ user: identity })
      }
      if (url.endsWith('/api/v1/auth/logout')) {
        authenticated = false
        return jsonResponse({ status: 'logged_out' })
      }
      throw new Error(`Unexpected request: ${url} ${init?.method ?? 'GET'}`)
    })
    vi.stubGlobal('fetch', fetchMock)
    const user = userEvent.setup()
    renderApplication('/register')

    await user.type(await screen.findByLabelText('Email'), identity.email)
    await user.type(screen.getByLabelText('Password'), 'a secure password')
    await user.click(screen.getByRole('button', { name: 'Create account' }))

    expect(await screen.findByRole('heading', { name: 'Teacher Workspace' })).toBeInTheDocument()
    expect(requests).toEqual([
      'GET /api/v1/auth/me',
      'POST /api/v1/auth/register',
      'POST /api/v1/auth/login',
      'GET /api/v1/auth/me',
    ])
    for (const call of fetchMock.mock.calls) {
      expect(call[1]).toEqual(expect.objectContaining({ credentials: 'include' }))
    }

    await user.click(screen.getByRole('button', { name: 'Log out' }))
    expect(await screen.findByRole('heading', { name: 'Log in' })).toBeInTheDocument()
    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining('/api/v1/auth/logout'),
      expect.objectContaining({ credentials: 'include', method: 'POST' }),
    )
  })

  it('does not authenticate when automatic login fails after registration', async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input)
      if (url.endsWith('/api/v1/auth/me')) {
        return jsonResponse({ detail: 'Authentication required' }, 401)
      }
      if (url.endsWith('/api/v1/auth/register')) return jsonResponse(identity, 201)
      if (url.endsWith('/api/v1/auth/login')) {
        return jsonResponse({ detail: 'Invalid email or password' }, 401)
      }
      throw new Error(`Unexpected request: ${url}`)
    })
    vi.stubGlobal('fetch', fetchMock)
    const user = userEvent.setup()
    renderApplication('/register')

    await user.type(await screen.findByLabelText('Email'), identity.email)
    await user.type(screen.getByLabelText('Password'), 'a secure password')
    await user.click(screen.getByRole('button', { name: 'Create account' }))

    expect(await screen.findByRole('alert')).toHaveTextContent('Invalid email or password')
    expect(screen.getByRole('heading', { name: 'Create an account' })).toBeInTheDocument()
    expect(screen.queryByRole('heading', { name: 'Teacher Workspace' })).not.toBeInTheDocument()
  })

  it('presents normalized authentication failures', async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input)
      if (url.endsWith('/api/v1/auth/me')) {
        return jsonResponse({ detail: 'Authentication required' }, 401)
      }
      return jsonResponse({ detail: 'Invalid email or password' }, 401)
    })
    vi.stubGlobal('fetch', fetchMock)
    const user = userEvent.setup()
    renderApplication('/login')

    await user.type(await screen.findByLabelText('Email'), identity.email)
    await user.type(screen.getByLabelText('Password'), 'wrong password')
    await user.click(screen.getByRole('button', { name: 'Log in' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('Invalid email or password')
  })
})
