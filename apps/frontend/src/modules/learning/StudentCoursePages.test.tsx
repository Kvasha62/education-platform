import { QueryClientProvider } from '@tanstack/react-query'
import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { createMemoryRouter, RouterProvider } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { createQueryClient } from '../../app/providers'
import { routes } from '../../app/router'

vi.mock('./StudentCourseEnrollment', () => ({
  StudentCourseEnrollment: () => <div>Course enrollment</div>,
}))

const identity = {
  id: 'identity-id', email: 'student@example.com', status: 'active',
  created_at: '2026-08-26T00:00:00Z', updated_at: '2026-08-26T00:00:00Z',
}
const summaries = {
  items: [
    { id: 'new-course', title: 'Newest Course' },
    { id: 'old-course', title: 'Older Course' },
  ],
}
const course = {
  id: 'new-course',
  title: 'Newest Course',
  sections: [
    {
      id: 'section-1', title: 'Introduction', position: 0,
      units: [
        {
          id: 'unit-1', title: 'Welcome', position: 0,
          activities: [
            { id: 'activity-1', title: 'First Activity', type: 'lecture', position: 0, contents: [] },
          ],
        },
        { id: 'unit-2', title: 'Setup', position: 1, activities: [] },
      ],
    },
    { id: 'section-2', title: 'Next Steps', position: 1, units: [] },
  ],
}
const jsonResponse = (body: unknown, status = 200) =>
  new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } })

const renderRoute = (entry: string) => {
  const router = createMemoryRouter(routes, { initialEntries: [entry] })
  return render(
    <QueryClientProvider client={createQueryClient()}>
      <RouterProvider router={router} />
    </QueryClientProvider>,
  )
}

describe('Student Course UI', () => {
  afterEach(() => vi.unstubAllGlobals())

  it('shows list loading and empty states', async () => {
    let resolveList: ((response: Response) => void) | undefined
    vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL) => {
      if (String(input).endsWith('/api/v1/auth/me')) return jsonResponse(identity)
      return new Promise<Response>((resolve) => { resolveList = resolve })
    }))
    renderRoute('/app/student/courses')

    expect(await screen.findByText('Loading published Courses')).toBeInTheDocument()
    resolveList?.(jsonResponse({ items: [] }))
    expect(
      await screen.findByRole('heading', { name: 'No published Courses available' }),
    ).toBeInTheDocument()
  })

  it('lists published Courses and opens the selected Course without enrollment', async () => {
    const requests: string[] = []
    vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input)
      requests.push(url)
      if (url.endsWith('/api/v1/auth/me')) return jsonResponse(identity)
      if (url.endsWith('/api/v1/student/courses/new-course')) return jsonResponse(course)
      if (url.endsWith('/api/v1/student/courses')) return jsonResponse(summaries)
      throw new Error(`Unexpected request: ${url}`)
    }))
    const user = userEvent.setup()
    renderRoute('/app/student/courses')

    const links = await screen.findAllByRole('link', { name: 'Open Course' })
    expect(screen.getByText('Newest Course')).toBeInTheDocument()
    expect(screen.getByText('Older Course')).toBeInTheDocument()
    expect(links[0]).toHaveAttribute('href', '/app/student/courses/new-course')
    await user.click(links[0])

    expect(await screen.findByRole('heading', { name: 'Newest Course' })).toBeInTheDocument()
    expect(screen.getByText('Course enrollment')).toBeInTheDocument()
    expect(requests.some((url) => url.includes('enrollment'))).toBe(false)
  })

  it('renders Sections and Learning Units from Course detail', async () => {
    vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL) =>
      String(input).endsWith('/api/v1/auth/me') ? jsonResponse(identity) : jsonResponse(course),
    ))
    renderRoute('/app/student/courses/new-course')

    const introduction = await screen.findByRole('heading', { name: 'Introduction' })
    const nextSteps = screen.getByRole('heading', { name: 'Next Steps' })
    const introductionSection = introduction.closest('li')
    const nextStepsSection = nextSteps.closest('li')
    expect(introductionSection).not.toBeNull()
    expect(nextStepsSection).not.toBeNull()
    expect(within(introductionSection!).getByText('Section 1')).toBeInTheDocument()
    expect(within(nextStepsSection!).getByText('Section 2')).toBeInTheDocument()
    expect(within(introductionSection!).getByText('Unit 1')).toBeInTheDocument()
    expect(within(introductionSection!).getByText('Unit 2')).toBeInTheDocument()
    expect(within(introductionSection!).getByText('Welcome')).toBeInTheDocument()
    expect(within(introductionSection!).getByText('Setup')).toBeInTheDocument()
    expect(within(introductionSection!).getByText('Activity 1')).toBeInTheDocument()
    expect(within(introductionSection!).getByRole('link', { name: 'First Activity' })).toHaveAttribute(
      'href',
      '/app/student/courses/new-course/activities/activity-1',
    )
    expect(within(nextStepsSection!).getByText('No Learning Units available.')).toBeInTheDocument()
    expect(screen.queryByText('Section 0')).not.toBeInTheDocument()
    expect(screen.queryByText('Unit 0')).not.toBeInTheDocument()
    expect(screen.queryByText('activities')).not.toBeInTheDocument()
  })

  it('shows an explicit not-found state for unavailable Course detail', async () => {
    vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL) =>
      String(input).endsWith('/api/v1/auth/me')
        ? jsonResponse(identity)
        : jsonResponse({ detail: 'Course not found' }, 404),
    ))
    renderRoute('/app/student/courses/missing')

    expect(await screen.findByRole('alert')).toHaveTextContent('Published Course not found.')
  })

  it('shows backend errors without treating them as empty or not-found', async () => {
    vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL) =>
      String(input).endsWith('/api/v1/auth/me')
        ? jsonResponse(identity)
        : jsonResponse({ detail: 'Course service unavailable' }, 503),
    ))
    renderRoute('/app/student/courses')

    expect(await screen.findByRole('alert')).toHaveTextContent('Course service unavailable')
    expect(screen.queryByText('No published Courses available')).not.toBeInTheDocument()
  })

  it('protects Student Course routes', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(jsonResponse({ detail: 'Authentication required' }, 401)),
    )
    renderRoute('/app/student/courses')

    expect(await screen.findByRole('heading', { name: 'Log in' })).toBeInTheDocument()
    expect(screen.queryByRole('heading', { name: 'Published Courses' })).not.toBeInTheDocument()
  })
})
