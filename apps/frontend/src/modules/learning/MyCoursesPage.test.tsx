import { QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { createMemoryRouter, RouterProvider } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { createQueryClient } from '../../app/providers'
import { routes } from '../../app/router'

const identity = {
  id: 'identity-id', email: 'student@example.com', status: 'active',
  created_at: '2026-08-26T00:00:00Z', updated_at: '2026-08-26T00:00:00Z',
}
const enrollments = {
  items: [
    {
      id: 'enrollment-1', course_id: 'course-1', status: 'enrolled',
      created_at: '2026-08-26T00:00:00Z',
    },
    {
      id: 'enrollment-2', course_id: 'course-2', status: 'enrolled',
      created_at: '2026-08-26T01:00:00Z',
    },
  ],
}
const course = { id: 'course-1', title: 'Course Detail', sections: [] }
const jsonResponse = (body: unknown, status = 200) =>
  new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } })

const renderRoute = (entry = '/app/student/my-courses') => {
  const router = createMemoryRouter(routes, { initialEntries: [entry] })
  return render(
    <QueryClientProvider client={createQueryClient()}>
      <RouterProvider router={router} />
    </QueryClientProvider>,
  )
}

describe('Student My Courses UI', () => {
  afterEach(() => vi.unstubAllGlobals())

  it('shows loading and explicit empty state', async () => {
    let resolveEnrollments: ((response: Response) => void) | undefined
    vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL) => {
      if (String(input).endsWith('/api/v1/auth/me')) return jsonResponse(identity)
      return new Promise<Response>((resolve) => { resolveEnrollments = resolve })
    }))
    renderRoute()

    expect(await screen.findByText('Loading enrolled Courses')).toBeInTheDocument()
    resolveEnrollments?.(jsonResponse({ items: [] }))
    expect(await screen.findByRole('heading', { name: 'No enrolled Courses yet' })).toBeInTheDocument()
  })

  it('renders only enrollment contract fields and opens existing Course Detail', async () => {
    const requests: string[] = []
    vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input)
      requests.push(url)
      if (url.endsWith('/api/v1/auth/me')) return jsonResponse(identity)
      if (url.endsWith('/api/v1/student/enrollments')) return jsonResponse(enrollments)
      if (url.endsWith('/api/v1/student/courses/course-1')) return jsonResponse(course)
      throw new Error(`Unexpected request: ${url}`)
    }))
    const user = userEvent.setup()
    renderRoute()

    expect(await screen.findByText('course-1')).toBeInTheDocument()
    expect(screen.getByText('course-2')).toBeInTheDocument()
    expect(screen.getAllByText('Status: ENROLLED')).toHaveLength(2)
    expect(screen.queryByText('Course title')).not.toBeInTheDocument()
    const links = screen.getAllByRole('link', { name: 'Open Course' })
    expect(links[0]).toHaveAttribute('href', '/app/student/courses/course-1')
    await user.click(links[0])

    expect(await screen.findByRole('heading', { name: 'Course Detail' })).toBeInTheDocument()
    expect(requests.filter((url) => url.endsWith('/api/v1/student/enrollments'))).toHaveLength(1)
  })

  it.each([
    [401, 'Authentication required'],
    [503, 'Enrollment service unavailable'],
  ])('shows GET %s failures consistently', async (status, detail) => {
    vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL) =>
      String(input).endsWith('/api/v1/auth/me')
        ? jsonResponse(identity)
        : jsonResponse({ detail }, status),
    ))
    renderRoute()

    expect(await screen.findByRole('alert')).toHaveTextContent(detail)
    expect(screen.queryByRole('link', { name: 'Open Course' })).not.toBeInTheDocument()
  })

  it('protects My Courses', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(jsonResponse({ detail: 'Authentication required' }, 401)),
    )
    renderRoute()
    expect(await screen.findByRole('heading', { name: 'Log in' })).toBeInTheDocument()
    expect(screen.queryByRole('heading', { name: 'My Courses' })).not.toBeInTheDocument()
  })
})
