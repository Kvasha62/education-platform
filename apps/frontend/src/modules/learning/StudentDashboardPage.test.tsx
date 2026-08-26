import { QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import { createMemoryRouter, RouterProvider } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { createQueryClient } from '../../app/providers'
import { routes } from '../../app/router'

const identity = {
  id: 'identity-id', email: 'student@example.com', status: 'active',
  created_at: '2026-08-26T00:00:00Z', updated_at: '2026-08-26T00:00:00Z',
}
const dashboard = {
  my_courses: [
    {
      course_id: 'course-id', title: 'Programming', status: 'enrolled',
      enrolled_at: '2026-08-26T00:00:00Z',
    },
  ],
  continue_learning: {
    course_id: 'course-id', activity_id: 'activity-id', status: 'in_progress',
    updated_at: '2026-08-26T01:00:00Z',
  },
}
const jsonResponse = (body: unknown, status = 200) =>
  new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } })
const renderRoute = () => {
  const router = createMemoryRouter(routes, { initialEntries: ['/app/student/dashboard'] })
  return render(
    <QueryClientProvider client={createQueryClient()}>
      <RouterProvider router={router} />
    </QueryClientProvider>,
  )
}

describe('Student Dashboard UI', () => {
  afterEach(() => vi.unstubAllGlobals())

  it('shows the Dashboard loading state', async () => {
    vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL) => {
      if (String(input).endsWith('/api/v1/auth/me')) return jsonResponse(identity)
      return new Promise<Response>(() => undefined)
    }))
    renderRoute()
    expect(await screen.findByText('Loading Student Dashboard')).toBeInTheDocument()
  })

  it('renders My Courses and Continue Learning using only Dashboard fields', async () => {
    const requests: string[] = []
    vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input)
      requests.push(url)
      if (url.endsWith('/api/v1/auth/me')) return jsonResponse(identity)
      if (url.endsWith('/api/v1/student/dashboard')) return jsonResponse(dashboard)
      throw new Error(`Unexpected request: ${url}`)
    }))
    renderRoute()

    expect(await screen.findByText('Programming')).toBeInTheDocument()
    expect(screen.getByText('ENROLLED')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Open Course' })).toHaveAttribute(
      'href', '/app/student/courses/course-id',
    )
    expect(screen.getByText('Activity in progress')).toBeInTheDocument()
    expect(screen.getByText('IN PROGRESS')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Continue Activity' })).toHaveAttribute(
      'href', '/app/student/courses/course-id/activities/activity-id',
    )
    expect(requests).toEqual(['/api/v1/auth/me', '/api/v1/student/dashboard'])
    expect(screen.queryByText('Recent Learning')).not.toBeInTheDocument()
    expect(screen.queryByText('Progress Overview')).not.toBeInTheDocument()
  })

  it('renders deterministic empty states', async () => {
    vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL) =>
      String(input).endsWith('/api/v1/auth/me')
        ? jsonResponse(identity)
        : jsonResponse({ my_courses: [], continue_learning: null }),
    ))
    renderRoute()

    expect(await screen.findByRole('heading', { name: 'No enrolled published Courses' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'No Activity in progress' })).toBeInTheDocument()
  })

  it('keeps My Courses when Continue Learning is empty', async () => {
    vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL) =>
      String(input).endsWith('/api/v1/auth/me')
        ? jsonResponse(identity)
        : jsonResponse({ ...dashboard, continue_learning: null }),
    ))
    renderRoute()

    expect(await screen.findByText('Programming')).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'No Activity in progress' })).toBeInTheDocument()
    expect(screen.queryByRole('link', { name: 'Continue Activity' })).not.toBeInTheDocument()
  })

  it.each([
    [401, 'Authentication required'],
    [503, 'Dashboard service unavailable'],
  ])('shows Dashboard %s errors consistently', async (status, detail) => {
    vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL) =>
      String(input).endsWith('/api/v1/auth/me')
        ? jsonResponse(identity)
        : jsonResponse({ detail }, status),
    ))
    renderRoute()
    expect(await screen.findByRole('alert')).toHaveTextContent(detail)
    expect(screen.queryByText('Activity in progress')).not.toBeInTheDocument()
  })

  it('protects the Student Dashboard route', async () => {
    vi.stubGlobal(
      'fetch', vi.fn().mockResolvedValue(jsonResponse({ detail: 'Authentication required' }, 401)),
    )
    renderRoute()
    expect(await screen.findByRole('heading', { name: 'Log in' })).toBeInTheDocument()
    expect(screen.queryByRole('heading', { name: 'Dashboard' })).not.toBeInTheDocument()
  })
})
