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
const archivedCourse = { ...course, id: 'archived-course', title: 'Archived Course', status: 'archived' }
const listRoute = '/app/teacher-spaces/space-id/environment/courses'
const detailRoute = `${listRoute}/course-id`
const publishedRoute = `${listRoute}/published-course`
const archivedRoute = `${listRoute}/archived-course`
const endpoint = '/api/v1/teacher-spaces/space-id/environment/courses'
const publishEndpoint = `${endpoint}/course-id/publish`
const jsonResponse = (body: unknown, status = 200) =>
  new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })

const renderRoute = (entry = listRoute) => {
  const router = createMemoryRouter(routes, { initialEntries: [entry] })
  const queryClient = createQueryClient()
  const view = render(
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
    </QueryClientProvider>,
  )
  return { ...view, queryClient }
}

const courseForId = (id: string) => {
  if (id === secondCourse.id) return secondCourse
  if (id === archivedCourse.id) return archivedCourse
  return course
}

const courseDetailFetch = (
  publish: () => Promise<Response>,
  current: () => typeof course,
) =>
  vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input)
    if (url.endsWith('/api/v1/auth/me')) return jsonResponse(identity)
    if (url.endsWith('/publish')) return publish()
    if (url.endsWith(endpoint) && init?.method !== 'POST') return jsonResponse([current()])
    const id = url.slice(url.lastIndexOf('/') + 1)
    return jsonResponse(id === course.id ? current() : courseForId(id))
  })

describe('Course UI', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
    vi.restoreAllMocks()
  })

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
    expect(screen.getByRole('link', { name: 'Open Sections' })).toHaveAttribute(
      'href',
      '/app/teacher-spaces/space-id/environment/courses/course-id/sections',
    )
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

  it('offers Publish Course for a DRAFT Course', async () => {
    vi.stubGlobal('fetch', courseDetailFetch(async () => jsonResponse(course), () => course))
    renderRoute(detailRoute)

    expect(
      await screen.findByRole('button', { name: 'Publish Course' }),
    ).toBeInTheDocument()
  })

  it('hides Publish Course for a PUBLISHED Course', async () => {
    vi.stubGlobal(
      'fetch',
      courseDetailFetch(async () => jsonResponse(secondCourse), () => secondCourse),
    )
    renderRoute(publishedRoute)

    expect(await screen.findByRole('heading', { name: secondCourse.title })).toBeInTheDocument()
    expect(screen.getByText('PUBLISHED')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Publish Course' })).not.toBeInTheDocument()
  })

  it('hides Publish Course for an ARCHIVED Course', async () => {
    vi.stubGlobal(
      'fetch',
      courseDetailFetch(async () => jsonResponse(archivedCourse), () => archivedCourse),
    )
    renderRoute(archivedRoute)

    expect(await screen.findByRole('heading', { name: archivedCourse.title })).toBeInTheDocument()
    expect(screen.getByText('ARCHIVED')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Publish Course' })).not.toBeInTheDocument()
  })

  it('cancels publication without sending a request', async () => {
    const fetchMock = courseDetailFetch(async () => jsonResponse(course), () => course)
    vi.stubGlobal('fetch', fetchMock)
    const confirm = vi.spyOn(window, 'confirm').mockReturnValue(false)
    const user = userEvent.setup()
    renderRoute(detailRoute)

    await user.click(await screen.findByRole('button', { name: 'Publish Course' }))

    expect(confirm).toHaveBeenCalledWith(`Publish "${course.title}"?`)
    expect(
      fetchMock.mock.calls.some(([url, init]) => String(url).endsWith('/publish') && init?.method === 'POST'),
    ).toBe(false)
    expect(screen.getByRole('button', { name: 'Publish Course' })).toBeEnabled()
  })

  it('publishes with a bodyless POST after confirmation', async () => {
    const fetchMock = courseDetailFetch(async () => jsonResponse(course), () => course)
    vi.stubGlobal('fetch', fetchMock)
    vi.spyOn(window, 'confirm').mockReturnValue(true)
    const user = userEvent.setup()
    renderRoute(detailRoute)

    await user.click(await screen.findByRole('button', { name: 'Publish Course' }))

    const publishCall = fetchMock.mock.calls.find(([url]) => String(url).endsWith(publishEndpoint))
    expect(String(publishCall?.[0]).endsWith(publishEndpoint)).toBe(true)
    expect(publishCall?.[1]).toEqual(
      expect.objectContaining({ credentials: 'include', method: 'POST' }),
    )
    expect(publishCall?.[1]?.body).toBeUndefined()
  })

  it('disables the action and shows a pending label while publishing', async () => {
    let resolvePublish: ((response: Response) => void) | undefined
    const fetchMock = courseDetailFetch(
      () => new Promise<Response>((resolve) => { resolvePublish = resolve }),
      () => course,
    )
    vi.stubGlobal('fetch', fetchMock)
    vi.spyOn(window, 'confirm').mockReturnValue(true)
    const user = userEvent.setup()
    renderRoute(detailRoute)

    await user.click(await screen.findByRole('button', { name: 'Publish Course' }))

    expect(await screen.findByRole('button', { name: 'Publishing…' })).toBeDisabled()
    resolvePublish?.(jsonResponse(course))
  })

  it('invalidates the Course detail and Course list queries after a successful publish', async () => {
    let current = course
    const fetchMock = courseDetailFetch(async () => {
      current = { ...course, status: 'published' }
      return jsonResponse(current)
    }, () => current)
    vi.stubGlobal('fetch', fetchMock)
    vi.spyOn(window, 'confirm').mockReturnValue(true)
    const user = userEvent.setup()
    const { queryClient } = renderRoute(detailRoute)
    const invalidate = vi.spyOn(queryClient, 'invalidateQueries')

    await user.click(await screen.findByRole('button', { name: 'Publish Course' }))

    expect(await screen.findByText('PUBLISHED')).toBeInTheDocument()
    expect(invalidate).toHaveBeenCalledWith({
      queryKey: ['teacher-space', 'space-id', 'courses', 'course-id'],
    })
    expect(invalidate).toHaveBeenCalledWith({
      queryKey: ['teacher-space', 'space-id', 'courses'],
    })
  })

  it('shows the published status and removes the action after a successful publish', async () => {
    let current = course
    const fetchMock = courseDetailFetch(async () => {
      current = { ...course, status: 'published' }
      return jsonResponse(current)
    }, () => current)
    vi.stubGlobal('fetch', fetchMock)
    vi.spyOn(window, 'confirm').mockReturnValue(true)
    const user = userEvent.setup()
    renderRoute(detailRoute)

    await user.click(await screen.findByRole('button', { name: 'Publish Course' }))

    expect(await screen.findByText('PUBLISHED')).toBeInTheDocument()
    expect(screen.queryByText('DRAFT')).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Publish Course' })).not.toBeInTheDocument()
    expect(screen.getByRole('heading', { name: course.title })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Open Sections' })).toBeInTheDocument()
  })

  it('surfaces a readiness conflict and keeps the DRAFT Course publishable', async () => {
    const fetchMock = courseDetailFetch(
      async () => jsonResponse({ detail: 'Course is not ready for publication' }, 409),
      () => course,
    )
    vi.stubGlobal('fetch', fetchMock)
    vi.spyOn(window, 'confirm').mockReturnValue(true)
    const user = userEvent.setup()
    renderRoute(detailRoute)

    await user.click(await screen.findByRole('button', { name: 'Publish Course' }))

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Course is not ready for publication',
    )
    expect(screen.getByRole('heading', { name: course.title })).toBeInTheDocument()
    expect(screen.getByText('DRAFT')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Publish Course' })).toBeEnabled()
  })

  it('surfaces a disabled Teacher Space conflict through the existing error path', async () => {
    const fetchMock = courseDetailFetch(
      async () => jsonResponse({ detail: 'Disabled Teacher Space is read-only' }, 409),
      () => course,
    )
    vi.stubGlobal('fetch', fetchMock)
    vi.spyOn(window, 'confirm').mockReturnValue(true)
    const user = userEvent.setup()
    renderRoute(detailRoute)

    await user.click(await screen.findByRole('button', { name: 'Publish Course' }))

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Disabled Teacher Space is read-only',
    )
    expect(screen.getByText('DRAFT')).toBeInTheDocument()
  })

  it('keeps the loaded Course rendered when publication is rejected', async () => {
    const fetchMock = courseDetailFetch(
      async () => jsonResponse({ detail: 'Untrusted request origin' }, 403),
      () => course,
    )
    vi.stubGlobal('fetch', fetchMock)
    vi.spyOn(window, 'confirm').mockReturnValue(true)
    const user = userEvent.setup()
    renderRoute(detailRoute)

    await user.click(await screen.findByRole('button', { name: 'Publish Course' }))

    expect(await screen.findByRole('alert')).toHaveTextContent('Untrusted request origin')
    expect(screen.getByRole('heading', { name: course.title })).toBeInTheDocument()
    expect(screen.getByText('DRAFT')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Open Sections' })).toBeInTheDocument()
  })
})
