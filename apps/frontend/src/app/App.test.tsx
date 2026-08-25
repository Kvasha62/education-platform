import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen } from '@testing-library/react'
import { createMemoryRouter, RouterProvider } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { routes } from './router'

const renderApplication = () => {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  const router = createMemoryRouter(routes, { initialEntries: ['/'] })
  return render(
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
    </QueryClientProvider>,
  )
}

describe('frontend foundation', () => {
  afterEach(() => vi.unstubAllGlobals())

  it('bootstraps an authenticated session and renders the application', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        new Response(
          JSON.stringify({
            id: 'identity-id',
            email: 'student@example.com',
            status: 'active',
            created_at: '2026-08-25T00:00:00Z',
            updated_at: '2026-08-25T00:00:00Z',
          }),
          { status: 200, headers: { 'Content-Type': 'application/json' } },
        ),
      ),
    )

    renderApplication()
    expect(screen.getByRole('status')).toHaveTextContent('Loading application')
    expect(await screen.findByText('student@example.com')).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: /ready for the next learning experience/i })).toBeInTheDocument()
  })

  it('handles an unauthenticated session and proves routing works', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify({ detail: 'Authentication required' }), {
          status: 401,
          headers: { 'Content-Type': 'application/json' },
        }),
      ),
    )

    renderApplication()
    expect(await screen.findByText('Not signed in')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('link', { name: 'Verify routing' }))
    expect(await screen.findByRole('heading', { name: /application router is working/i })).toBeInTheDocument()
  })

  it('renders a reusable error state when session bootstrap fails', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response('', { status: 503 })))
    renderApplication()
    expect(await screen.findByRole('alert')).toHaveTextContent(/could not check your session/i)
  })
})
