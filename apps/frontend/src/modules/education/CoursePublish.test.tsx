import { QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { createMemoryRouter, RouterProvider } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { createQueryClient } from '../../app/providers'
import { CoursePage } from './CoursePages'

const course = {
  id: 'course-id',
  educational_environment_id: 'environment-id',
  title: 'Foundations',
  status: 'draft',
  created_at: '2026-08-25T00:00:00Z',
  updated_at: '2026-08-25T00:00:00Z',
}

const courseEndpoint =
  '/api/v1/teacher-spaces/space-id/environment/courses/course-id'
const publishEndpoint = `${courseEndpoint}/publish`

const jsonResponse = (body: unknown, status = 200) =>
  new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })

afterEach(() => {
  vi.unstubAllGlobals()
  vi.restoreAllMocks()
})

describe('Course publish request', () => {
  it('sends exactly one POST after a confirmed Publish Course click', async () => {
    let current = course
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input)
      if (url.endsWith(courseEndpoint)) return jsonResponse(current)
      if (url.endsWith(publishEndpoint) && init?.method === 'POST') {
        current = { ...course, status: 'published' }
        return jsonResponse(current)
      }
      throw new Error(`Unexpected request: ${url}`)
    })
    vi.stubGlobal('fetch', fetchMock)
    vi.spyOn(window, 'confirm').mockReturnValue(true)

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

    await user.click(await screen.findByRole('button', { name: 'Publish Course' }))
    expect(await screen.findByText('PUBLISHED')).toBeInTheDocument()

    const publishCalls = fetchMock.mock.calls.filter(
      ([url, init]) => String(url).endsWith(publishEndpoint) && init?.method === 'POST',
    )
    expect(publishCalls).toHaveLength(1)
  })
})
