import { QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import { createMemoryRouter, RouterProvider } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { createQueryClient } from '../../app/providers'
import { routes } from '../../app/router'

vi.mock('./StudentActivityProgress', () => ({
  StudentActivityProgress: () => <div>Activity progress</div>,
}))

const identity = {
  id: 'identity-id', email: 'student@example.com', status: 'active',
  created_at: '2026-08-26T00:00:00Z', updated_at: '2026-08-26T00:00:00Z',
}
const activity = {
  id: 'activity-id',
  title: 'Learn Loops',
  type: 'lecture',
  position: 0,
  contents: [
    { id: 'article-id', type: 'article', status: 'published', available_for_student: true },
    { id: 'resource-id', type: 'resource', status: 'published', available_for_student: true },
  ],
}
const course = {
  id: 'course-id',
  title: 'Programming',
  sections: [
    {
      id: 'section-id', title: 'Iteration', position: 0,
      units: [{ id: 'unit-id', title: 'For Loops', position: 0, activities: [activity] }],
    },
  ],
}
const articleResponse = {
  id: 'article-id',
  type: 'article',
  body: {
    schema_version: 1,
    kind: 'article',
    blocks: [
      { type: 'heading', level: 2, text: 'Loop basics' },
      { type: 'paragraph', text: 'A loop repeats work.' },
      { type: 'code', language: 'python', code: 'for item in items:\n    print(item)' },
      { type: 'list', style: 'ordered', items: ['Read', 'Practice'] },
      { type: 'link', url: 'https://example.test/loops', label: 'More about loops' },
    ],
  },
}
const resourceResponse = {
  id: 'resource-id',
  type: 'resource',
  body: {
    schema_version: 1,
    kind: 'resource',
    resource: { url: 'https://example.test/resource', description: 'Loop reference' },
  },
}
const route = '/app/student/courses/course-id/activities/activity-id'
const jsonResponse = (body: unknown, status = 200) =>
  new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } })

const renderRoute = (entry = route) => {
  const router = createMemoryRouter(routes, { initialEntries: [entry] })
  return render(
    <QueryClientProvider client={createQueryClient()}>
      <RouterProvider router={router} />
    </QueryClientProvider>,
  )
}

const successFetch = () => vi.fn(async (input: RequestInfo | URL) => {
  const url = String(input)
  if (url.endsWith('/api/v1/auth/me')) return jsonResponse(identity)
  if (url.endsWith('/api/v1/student/courses/course-id')) return jsonResponse(course)
  if (url.endsWith('/api/v1/student/contents/article-id/body')) return jsonResponse(articleResponse)
  if (url.endsWith('/api/v1/student/contents/resource-id/body')) return jsonResponse(resourceResponse)
  throw new Error(`Unexpected request: ${url}`)
})

describe('Student Activity and Content Viewer', () => {
  afterEach(() => vi.unstubAllGlobals())

  it('renders Activity metadata and canonical ARTICLE and RESOURCE bodies', async () => {
    const fetchMock = successFetch()
    vi.stubGlobal('fetch', fetchMock)
    renderRoute()

    expect(await screen.findByRole('heading', { name: 'Learn Loops' })).toBeInTheDocument()
    expect(screen.getByText('LECTURE · Activity 1')).toBeInTheDocument()
    expect(screen.getByText('Activity progress')).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Loop basics', level: 2 })).toBeInTheDocument()
    expect(screen.getByText('A loop repeats work.')).toBeInTheDocument()
    expect(screen.getByText(/for item in items/)).toBeInTheDocument()
    expect(screen.getByText('Read')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'More about loops' })).toHaveAttribute(
      'href',
      'https://example.test/loops',
    )
    expect(screen.getByRole('link', { name: 'Open resource' })).toHaveAttribute(
      'href',
      'https://example.test/resource',
    )
    expect(screen.getByText('Loop reference')).toBeInTheDocument()
    expect(fetchMock.mock.calls.some(([input]) => String(input).includes('/progress/'))).toBe(false)
    expect(fetchMock.mock.calls.some(([input]) => String(input).includes('enrollment'))).toBe(false)
  })

  it('keeps successful Content visible when another Content returns 404', async () => {
    vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input)
      if (url.endsWith('/api/v1/auth/me')) return jsonResponse(identity)
      if (url.endsWith('/api/v1/student/courses/course-id')) return jsonResponse(course)
      if (url.endsWith('/api/v1/student/contents/article-id/body')) {
        return jsonResponse(articleResponse)
      }
      if (url.endsWith('/api/v1/student/contents/resource-id/body')) {
        return jsonResponse({ detail: 'Content not found' }, 404)
      }
      throw new Error(`Unexpected request: ${url}`)
    }))
    renderRoute()

    expect(await screen.findByText('A loop repeats work.')).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Loop basics', level: 2 })).toBeInTheDocument()
    expect(await screen.findByRole('alert')).toHaveTextContent('Published Content not found.')
    expect(screen.queryByRole('link', { name: 'Open resource' })).not.toBeInTheDocument()
  })

  it('shows loading while published Content bodies load', async () => {
    let resolveBody: ((response: Response) => void) | undefined
    vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input)
      if (url.endsWith('/api/v1/auth/me')) return jsonResponse(identity)
      if (url.endsWith('/api/v1/student/courses/course-id')) return jsonResponse({
        ...course,
        sections: [{
          ...course.sections[0],
          units: [{ ...course.sections[0].units[0], activities: [{ ...activity, contents: [activity.contents[0]] }] }],
        }],
      })
      return new Promise<Response>((resolve) => { resolveBody = resolve })
    }))
    renderRoute()

    expect(await screen.findByText('Loading published Content')).toBeInTheDocument()
    resolveBody?.(jsonResponse(articleResponse))
    expect(await screen.findByText('A loop repeats work.')).toBeInTheDocument()
  })

  it('shows an empty state when Activity has no attached Content', async () => {
    vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input)
      if (url.endsWith('/api/v1/auth/me')) return jsonResponse(identity)
      return jsonResponse({
        ...course,
        sections: [{
          ...course.sections[0],
          units: [{ ...course.sections[0].units[0], activities: [{ ...activity, contents: [] }] }],
        }],
      })
    }))
    renderRoute()
    expect(await screen.findByRole('heading', { name: 'No published Content attached' })).toBeInTheDocument()
  })

  it('shows Activity not-found when it is absent from Course detail', async () => {
    vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL) =>
      String(input).endsWith('/api/v1/auth/me') ? jsonResponse(identity) : jsonResponse(course),
    ))
    renderRoute('/app/student/courses/course-id/activities/missing')
    expect(await screen.findByRole('alert')).toHaveTextContent('Activity not found.')
  })

  it('shows published Content 404 without fabricating a body', async () => {
    vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input)
      if (url.endsWith('/api/v1/auth/me')) return jsonResponse(identity)
      if (url.endsWith('/api/v1/student/courses/course-id')) {
        return jsonResponse({
          ...course,
          sections: [{
            ...course.sections[0],
            units: [{
              ...course.sections[0].units[0],
              activities: [{ ...activity, contents: [activity.contents[0]] }],
            }],
          }],
        })
      }
      return jsonResponse({ detail: 'Content not found' }, 404)
    }))
    renderRoute()
    expect(await screen.findByRole('alert')).toHaveTextContent('Published Content not found.')
  })

  it('shows backend errors consistently', async () => {
    vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL) =>
      String(input).endsWith('/api/v1/auth/me')
        ? jsonResponse(identity)
        : jsonResponse({ detail: 'Course service unavailable' }, 503),
    ))
    renderRoute()
    expect(await screen.findByRole('alert')).toHaveTextContent('Course service unavailable')
  })

  it('protects the Student Activity route', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(jsonResponse({ detail: 'Authentication required' }, 401)),
    )
    renderRoute()
    expect(await screen.findByRole('heading', { name: 'Log in' })).toBeInTheDocument()
    expect(screen.queryByRole('heading', { name: 'Learn Loops' })).not.toBeInTheDocument()
  })
})
