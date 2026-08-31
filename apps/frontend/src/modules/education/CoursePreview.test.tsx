import { QueryClientProvider } from '@tanstack/react-query'
import { render, screen, within } from '@testing-library/react'
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
const baseCourse = {
  id: 'course-id',
  educational_environment_id: 'environment-id',
  title: 'Foundations',
  status: 'draft',
  created_at: '2026-08-25T00:00:00Z',
  updated_at: '2026-08-25T00:00:00Z',
}
const publishedCourse = {
  ...baseCourse,
  id: 'published-course',
  title: 'Published Course',
  status: 'published',
}
const archivedCourse = {
  ...baseCourse,
  id: 'archived-course',
  title: 'Archived Course',
  status: 'archived',
}
const section = {
  id: 'section-id',
  course_id: 'course-id',
  title: 'Introduction',
  position: 0,
  created_at: '2026-08-25T00:00:00Z',
  updated_at: '2026-08-25T00:00:00Z',
}
const unit = {
  id: 'unit-id',
  section_id: 'section-id',
  title: 'Basics',
  position: 0,
  created_at: '2026-08-25T00:00:00Z',
  updated_at: '2026-08-25T00:00:00Z',
}
const activity = {
  id: 'activity-id',
  learning_unit_id: 'unit-id',
  title: 'First Lecture',
  type: 'lecture',
  position: 0,
  created_at: '2026-08-25T00:00:00Z',
  updated_at: '2026-08-25T00:00:00Z',
  assessment_definition_id: null,
}
const reference = {
  id: 'content-id',
  type: 'article',
  status: 'published',
  available_for_student: true,
}
const body = {
  schema_version: 1,
  kind: 'article',
  blocks: [{ type: 'paragraph', text: 'Welcome to the Foundations course.' }],
}

const detailRoute = '/app/teacher-spaces/space-id/environment/courses/course-id'
const previewRoute = `${detailRoute}/preview`
const publishedDetailRoute = '/app/teacher-spaces/space-id/environment/courses/published-course'
const publishedPreviewRoute = `${publishedDetailRoute}/preview`
const archivedDetailRoute = '/app/teacher-spaces/space-id/environment/courses/archived-course'

const courseEndpoint = '/api/v1/teacher-spaces/space-id/environment/courses/course-id'
const publishedCourseEndpoint =
  '/api/v1/teacher-spaces/space-id/environment/courses/published-course'
const archivedCourseEndpoint =
  '/api/v1/teacher-spaces/space-id/environment/courses/archived-course'
const sectionsEndpoint = `${courseEndpoint}/sections`
const unitsEndpoint = `${sectionsEndpoint}/section-id/units`
const activitiesEndpoint = `${unitsEndpoint}/unit-id/activities`
const linkedEndpoint = `${activitiesEndpoint}/activity-id/contents`
const bodyEndpoint = '/api/v1/contents/content-id/body'

const jsonResponse = (payload: unknown, status = 200) =>
  new Response(JSON.stringify(payload), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })

interface MockedFetchOptions {
  course?: typeof baseCourse
  failCourse?: boolean
  emptySections?: boolean
}

const buildFetch = ({
  course,
  failCourse = false,
  emptySections = false,
}: MockedFetchOptions = {}) => {
  const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input)
    if (url.endsWith('/api/v1/auth/me')) return jsonResponse(identity)
    if (failCourse) return jsonResponse({ detail: 'Course lookup unavailable' }, 503)
    if (
      url.endsWith(courseEndpoint) ||
      url.endsWith(publishedCourseEndpoint) ||
      url.endsWith(archivedCourseEndpoint)
    ) {
      return jsonResponse(course ?? baseCourse)
    }
    if (url.endsWith(sectionsEndpoint)) return jsonResponse(emptySections ? [] : [section])
    if (url.endsWith(unitsEndpoint)) return jsonResponse([unit])
    if (url.endsWith(activitiesEndpoint)) return jsonResponse([activity])
    if (url.endsWith(linkedEndpoint)) return jsonResponse([reference])
    if (url.endsWith(bodyEndpoint)) return jsonResponse(body)
    throw new Error(`Unexpected request: ${url}`)
  })
  return { fetchMock }
}

const renderRoute = (entry: string) => {
  const router = createMemoryRouter(routes, { initialEntries: [entry] })
  return render(
    <QueryClientProvider client={createQueryClient()}>
      <RouterProvider router={router} />
    </QueryClientProvider>,
  )
}

describe('Course Preview', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
    vi.restoreAllMocks()
  })

  it('exposes the Preview Course action for a DRAFT Course', async () => {
    vi.stubGlobal('fetch', buildFetch().fetchMock)
    renderRoute(detailRoute)

    expect(await screen.findByRole('link', { name: 'Preview Course' })).toHaveAttribute(
      'href',
      previewRoute,
    )
  })

  it('hides the Preview Course action for a PUBLISHED Course', async () => {
    vi.stubGlobal('fetch', buildFetch({ course: publishedCourse }).fetchMock)
    renderRoute(publishedDetailRoute)

    expect(await screen.findByRole('heading', { name: publishedCourse.title })).toBeInTheDocument()
    expect(screen.queryByRole('link', { name: 'Preview Course' })).not.toBeInTheDocument()
  })

  it('hides the Preview Course action for an ARCHIVED Course', async () => {
    vi.stubGlobal('fetch', buildFetch({ course: archivedCourse }).fetchMock)
    renderRoute(archivedDetailRoute)

    expect(await screen.findByRole('heading', { name: archivedCourse.title })).toBeInTheDocument()
    expect(screen.queryByRole('link', { name: 'Preview Course' })).not.toBeInTheDocument()
  })

  it('navigates from Course detail to the dedicated Preview route', async () => {
    vi.stubGlobal('fetch', buildFetch().fetchMock)
    const user = userEvent.setup()
    renderRoute(detailRoute)

    await user.click(await screen.findByRole('link', { name: 'Preview Course' }))

    expect(await screen.findByText('Author Preview')).toBeInTheDocument()
    expect(await screen.findByText(section.title)).toBeInTheDocument()
    expect(screen.getByRole('link', { name: '← Back to Course' })).toHaveAttribute(
      'href',
      detailRoute,
    )
  })

  it('renders Course, Sections, Learning Units and Activities in composition order', async () => {
    vi.stubGlobal('fetch', buildFetch().fetchMock)
    renderRoute(previewRoute)

    expect(await screen.findByRole('heading', { name: baseCourse.title })).toBeInTheDocument()
    expect(screen.getByText('Author Preview')).toBeInTheDocument()
    const sectionTitle = await screen.findByText(section.title)
    await screen.findByText(unit.title)
    await screen.findByText(activity.title)
    const sectionItem = sectionTitle.closest('li')
    expect(within(sectionItem as HTMLElement).getByText(unit.title)).toBeInTheDocument()
    const unitItem = screen.getByText(unit.title).closest('li')
    expect(within(unitItem as HTMLElement).getByText(activity.title)).toBeInTheDocument()
  })

  it('renders attached Content references and their bodies with the low-level renderer', async () => {
    vi.stubGlobal('fetch', buildFetch().fetchMock)
    const { container } = renderRoute(previewRoute)

    expect(await screen.findByText(/article · published/)).toBeInTheDocument()
    expect(await screen.findByText(body.blocks[0].text)).toBeInTheDocument()
    expect(container.querySelector('.student-article')).not.toBeNull()
  })

  it('issues no mutation or Student API requests', async () => {
    const { fetchMock } = buildFetch()
    vi.stubGlobal('fetch', fetchMock)
    renderRoute(previewRoute)

    await screen.findByText(body.blocks[0].text)

    const mutations = fetchMock.mock.calls.filter(([, init]) => (init?.method ?? 'GET') !== 'GET')
    expect(mutations).toHaveLength(0)
    const studentCalls = fetchMock.mock.calls.filter(([url]) =>
      String(url).includes('/api/v1/student/'),
    )
    expect(studentCalls).toHaveLength(0)
  })

  it('contains no mutation controls', async () => {
    vi.stubGlobal('fetch', buildFetch().fetchMock)
    const { container } = renderRoute(previewRoute)

    await screen.findByText(body.blocks[0].text)
    expect(screen.queryByRole('button')).not.toBeInTheDocument()
    expect(container.querySelector('form')).toBeNull()
  })

  it('returns to the Course detail via Back to Course', async () => {
    vi.stubGlobal('fetch', buildFetch().fetchMock)
    const user = userEvent.setup()
    renderRoute(previewRoute)

    await user.click(await screen.findByRole('link', { name: '← Back to Course' }))

    expect(await screen.findByRole('link', { name: 'Preview Course' })).toHaveAttribute(
      'href',
      previewRoute,
    )
    expect(screen.getByText('DRAFT')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Open Sections' })).toBeInTheDocument()
  })

  it('shows an error for direct non-DRAFT access without fetching Course structure', async () => {
    const { fetchMock } = buildFetch({ course: publishedCourse })
    vi.stubGlobal('fetch', fetchMock)
    renderRoute(publishedPreviewRoute)

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Course Preview is available only for DRAFT Courses.',
    )
    expect(
      fetchMock.mock.calls.some(([url]) => String(url).endsWith(sectionsEndpoint)),
    ).toBe(false)
  })

  it('surfaces a Course lookup failure through the existing error path', async () => {
    vi.stubGlobal('fetch', buildFetch({ failCourse: true }).fetchMock)
    renderRoute(previewRoute)

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Course lookup unavailable',
    )
  })

  it('shows an explicit empty state when the Course has no Sections', async () => {
    const { fetchMock } = buildFetch({ emptySections: true })
    vi.stubGlobal('fetch', fetchMock)
    renderRoute(previewRoute)

    expect(await screen.findByRole('heading', { name: 'No Sections yet' })).toBeInTheDocument()
    expect(
      fetchMock.mock.calls.some(([url]) => String(url).endsWith(unitsEndpoint)),
    ).toBe(false)
  })
})
