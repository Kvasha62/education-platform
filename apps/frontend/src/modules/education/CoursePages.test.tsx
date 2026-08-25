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
const course = {
  id: 'course-id',
  educational_environment_id: 'environment-id',
  title: 'Foundations',
  status: 'draft',
  created_at: '2026-08-25T00:00:00Z',
  updated_at: '2026-08-25T00:00:00Z',
}
const secondCourse = { ...course, id: 'published-course', title: 'Published Course', status: 'published' }
const listRoute = '/app/teacher-spaces/space-id/environment/courses'
const detailRoute = `${listRoute}/course-id`
const endpoint = '/api/v1/teacher-spaces/space-id/environment/courses'
const jsonResponse = (body: unknown, status = 200) =>
  new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })

const renderRoute = (entry = listRoute) => {
  const router = createMemoryRouter(routes, { initialEntries: [entry] })
  return render(
    <QueryClientProvider client={createQueryClient()}>
      <RouterProvider router={router} />
    </QueryClientProvider>,
  )
}

describe('Course UI', () => {
  afterEach(() => vi.unstubAllGlobals())

  it('shows loading and an explicit empty Courses state', async () => {
    let resolveCourses: ((response: Response) => void) | undefined
    vi.stubGlobal(
      'fetch',
      vi.fn(async (input: RequestInfo | URL) => {
        if (String(input).endsWith('/api/v1/auth/me')) return jsonResponse(identity)
        return new Promise<Response>((resolve) => { resolveCourses = resolve })
      }),
    )
    renderRoute()

    expect(await screen.findByText('Loading Courses')).toBeInTheDocument()
    resolveCourses?.(jsonResponse([]))
    expect(await screen.findByRole('heading', { name: 'No Courses yet' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Create Course' })).toBeInTheDocument()
  })

  it('renders multiple Courses with server-controlled statuses', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async (input: RequestInfo | URL) =>
        String(input).endsWith('/api/v1/auth/me')
          ? jsonResponse(identity)
          : jsonResponse([course, secondCourse]),
      ),
    )
    renderRoute()

    expect(await screen.findByText(course.title)).toBeInTheDocument()
    expect(screen.getByText(secondCourse.title)).toBeInTheDocument()
    expect(screen.getByText('DRAFT')).toBeInTheDocument()
    expect(screen.getByText('PUBLISHED')).toBeInTheDocument()
    expect(screen.getAllByRole('link', { name: 'Open' })).toHaveLength(2)
  })

  it('creates with title only, updates the list, and opens the created Course', async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input)
      if (url.endsWith('/api/v1/auth/me')) return jsonResponse(identity)
      if (url.endsWith(endpoint) && init?.method === 'POST') return jsonResponse(course, 201)
      if (url.endsWith(endpoint)) return jsonResponse([])
      if (url.endsWith(`${endpoint}/course-id`)) return jsonResponse(course)
      throw new Error(`Unexpected request: ${url}`)
    })
    vi.stubGlobal('fetch', fetchMock)
    const user = userEvent.setup()
    renderRoute()

    await user.type(await screen.findByLabelText('Course title'), course.title)
    await user.click(screen.getByRole('button', { name: 'Create Course' }))

    expect(await screen.findByRole('heading', { name: course.title })).toBeInTheDocument()
    expect(screen.getByText('DRAFT')).toBeInTheDocument()
    const createCall = fetchMock.mock.calls.find(
      ([url, options]) => String(url).endsWith(endpoint) && options?.method === 'POST',
    )
    expect(createCall?.[1]).toEqual(
      expect.objectContaining({
        body: JSON.stringify({ title: course.title }),
        credentials: 'include',
        method: 'POST',
      }),
    )
    expect(JSON.parse(String(createCall?.[1]?.body))).toEqual({ title: course.title })
  })

  it('loads and displays Course detail', async () => {
    let resolveCourse: ((response: Response) => void) | undefined
    vi.stubGlobal(
      'fetch',
      vi.fn(async (input: RequestInfo | URL) => {
        if (String(input).endsWith('/api/v1/auth/me')) return jsonResponse(identity)
        return new Promise<Response>((resolve) => { resolveCourse = resolve })
      }),
    )
    renderRoute(detailRoute)

    expect(await screen.findByText('Loading Course')).toBeInTheDocument()
    resolveCourse?.(jsonResponse(course))
    expect(await screen.findByRole('heading', { name: course.title })).toBeInTheDocument()
    expect(screen.getByText('DRAFT')).toBeInTheDocument()
  })

  it('keeps Course detail 404 as a not-found error', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async (input: RequestInfo | URL) =>
        String(input).endsWith('/api/v1/auth/me')
          ? jsonResponse(identity)
          : jsonResponse({ detail: 'Course not found' }, 404),
      ),
    )
    renderRoute(detailRoute)

    expect(await screen.findByRole('alert')).toHaveTextContent('Course not found')
    expect(screen.queryByRole('heading', { name: course.title })).not.toBeInTheDocument()
  })

  it('shows a Courses API failure instead of an empty state', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async (input: RequestInfo | URL) =>
        String(input).endsWith('/api/v1/auth/me')
          ? jsonResponse(identity)
          : jsonResponse({ detail: 'Courses unavailable' }, 503),
      ),
    )
    renderRoute()

    expect(await screen.findByRole('alert')).toHaveTextContent('Courses unavailable')
    expect(screen.queryByRole('heading', { name: 'No Courses yet' })).not.toBeInTheDocument()
  })

  it('protects Course routes from unauthenticated users', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(jsonResponse({ detail: 'Authentication required' }, 401)),
    )
    renderRoute()

    expect(await screen.findByRole('heading', { name: 'Log in' })).toBeInTheDocument()
    expect(screen.queryByRole('heading', { name: 'Courses' })).not.toBeInTheDocument()
  })
})
