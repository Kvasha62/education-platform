import { QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { createMemoryRouter, RouterProvider } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { createQueryClient } from '../../app/providers'
import { CoursePage } from './CoursePages'
import type { Course } from './courseApi'

const course = {
  id: 'course-id',
  educational_environment_id: 'environment-id',
  title: 'Foundations',
  status: 'published',
  created_at: '2026-08-25T00:00:00Z',
  updated_at: '2026-08-25T00:00:00Z',
}

const courseEndpoint =
  '/api/v1/teacher-spaces/space-id/environment/courses/course-id'
const publishEndpoint = `${courseEndpoint}/publish`
const archiveEndpoint = `${courseEndpoint}/archive`

const jsonResponse = (body: unknown, status = 200) =>
  new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })

const statusOf = (status: Course['status']): Course => ({ ...course, status })

afterEach(() => {
  vi.unstubAllGlobals()
  vi.restoreAllMocks()
})

const renderCoursePage = (initialStatus: Course['status']) => {
  const router = createMemoryRouter(
    [
      {
        path: '/app/teacher-spaces/:teacherSpaceId/environment/courses/:courseId',
        element: <CoursePage />,
      },
    ],
    {
      initialEntries: [
        '/app/teacher-spaces/space-id/environment/courses/course-id',
      ],
    },
  )
  const queryClient = createQueryClient()
  const user = userEvent.setup()

  render(
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
    </QueryClientProvider>,
  )

  return { user }
}

const archivePostCalls = (fetchMock: ReturnType<typeof vi.fn>) =>
  fetchMock.mock.calls.filter(
    ([url, init]) => String(url).endsWith(archiveEndpoint) && init?.method === 'POST',
  )

describe('Course archive request', () => {
  it('does not render an Archive action for a DRAFT Course', async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      if (String(input).endsWith(courseEndpoint)) return jsonResponse(statusOf('draft'))
      throw new Error(`Unexpected request: ${input}`)
    })
    vi.stubGlobal('fetch', fetchMock)

    await renderCoursePage('draft')

    await screen.findByText('DRAFT')
    expect(screen.queryByRole('button', { name: 'Archive Course' })).toBeNull()
    expect(archivePostCalls(fetchMock)).toHaveLength(0)
  })

  it('renders an Archive action for a PUBLISHED Course', async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      if (String(input).endsWith(courseEndpoint)) return jsonResponse(statusOf('published'))
      throw new Error(`Unexpected request: ${input}`)
    })
    vi.stubGlobal('fetch', fetchMock)

    await renderCoursePage('published')

    expect(
      await screen.findByRole('button', { name: 'Archive Course' }),
    ).toBeInTheDocument()
  })

  it('sends exactly one POST after a confirmed Archive click', async () => {
    let current = statusOf('published')
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input)
      if (url.endsWith(courseEndpoint)) return jsonResponse(current)
      if (url.endsWith(archiveEndpoint) && init?.method === 'POST') {
        current = statusOf('archived')
        return jsonResponse(current)
      }
      throw new Error(`Unexpected request: ${url}`)
    })
    vi.stubGlobal('fetch', fetchMock)
    vi.spyOn(window, 'confirm').mockReturnValue(true)

    const { user } = renderCoursePage('published')

    await user.click(await screen.findByRole('button', { name: 'Archive Course' }))
    await screen.findByText('ARCHIVED')

    expect(archivePostCalls(fetchMock)).toHaveLength(1)
  })

  it('sends zero POSTs when the confirmation is cancelled', async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      if (String(input).endsWith(courseEndpoint)) return jsonResponse(statusOf('published'))
      throw new Error(`Unexpected request: ${input}`)
    })
    vi.stubGlobal('fetch', fetchMock)
    vi.spyOn(window, 'confirm').mockReturnValue(false)

    const { user } = renderCoursePage('published')

    await user.click(await screen.findByRole('button', { name: 'Archive Course' }))

    expect(archivePostCalls(fetchMock)).toHaveLength(0)
  })

  it('shows Archiving…, disables the button, and does not resend while pending', async () => {
    let current = statusOf('published')
    let resolveArchive: (() => void) | undefined
    const archiveGate = new Promise<Response>((resolve) => {
      resolveArchive = () => resolve(jsonResponse(statusOf('archived')))
    })
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input)
      if (url.endsWith(courseEndpoint)) return jsonResponse(current)
      if (url.endsWith(archiveEndpoint) && init?.method === 'POST') {
        current = statusOf('archived')
        return archiveGate
      }
      throw new Error(`Unexpected request: ${url}`)
    })
    vi.stubGlobal('fetch', fetchMock)
    vi.spyOn(window, 'confirm').mockReturnValue(true)

    const { user } = renderCoursePage('published')

    await user.click(await screen.findByRole('button', { name: 'Archive Course' }))
    const pendingButton = await screen.findByRole('button', { name: 'Archiving…' })
    expect(pendingButton).toBeDisabled()

    await user.click(pendingButton)
    expect(archivePostCalls(fetchMock)).toHaveLength(1)

    resolveArchive?.()
    await screen.findByText('ARCHIVED')
  })

  it('updates Course detail to ARCHIVED and removes Publish/Archive actions on success', async () => {
    let current = statusOf('published')
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input)
      if (url.endsWith(courseEndpoint)) return jsonResponse(current)
      if (url.endsWith(archiveEndpoint) && init?.method === 'POST') {
        current = statusOf('archived')
        return jsonResponse(current)
      }
      throw new Error(`Unexpected request: ${url}`)
    })
    vi.stubGlobal('fetch', fetchMock)
    vi.spyOn(window, 'confirm').mockReturnValue(true)

    const { user } = renderCoursePage('published')

    await user.click(await screen.findByRole('button', { name: 'Archive Course' }))
    await screen.findByText('ARCHIVED')

    expect(screen.queryByRole('button', { name: 'Publish Course' })).toBeNull()
    expect(screen.queryByRole('button', { name: 'Archive Course' })).toBeNull()
  })

  it('does not render an Archive action for an ARCHIVED Course', async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      if (String(input).endsWith(courseEndpoint)) return jsonResponse(statusOf('archived'))
      throw new Error(`Unexpected request: ${input}`)
    })
    vi.stubGlobal('fetch', fetchMock)

    await renderCoursePage('archived')

    await screen.findByText('ARCHIVED')
    expect(screen.queryByRole('button', { name: 'Archive Course' })).toBeNull()
    expect(screen.queryByRole('button', { name: 'Publish Course' })).toBeNull()
  })

  it('renders the existing ErrorState and does not report a successful transition on failure', async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input)
      if (url.endsWith(courseEndpoint)) return jsonResponse(statusOf('published'))
      if (url.endsWith(archiveEndpoint) && init?.method === 'POST') {
        return jsonResponse(
          { detail: 'Course cannot be archived from its current status' },
          409,
        )
      }
      throw new Error(`Unexpected request: ${url}`)
    })
    vi.stubGlobal('fetch', fetchMock)
    vi.spyOn(window, 'confirm').mockReturnValue(true)

    const { user } = renderCoursePage('published')

    await user.click(await screen.findByRole('button', { name: 'Archive Course' }))
    const alert = await screen.findByRole('alert')
    expect(alert).toHaveTextContent('Course cannot be archived from its current status')

    expect(screen.getByText('PUBLISHED')).toBeInTheDocument()
    expect(screen.queryByText('ARCHIVED')).toBeNull()
  })
})
