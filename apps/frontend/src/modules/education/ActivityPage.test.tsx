import { QueryClientProvider } from '@tanstack/react-query'
import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { createMemoryRouter, RouterProvider } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { createQueryClient } from '../../app/providers'
import { routes } from '../../app/router'

vi.mock('./ActivityContentPanel', () => ({
  ActivityContentPanel: () => <div>Content management</div>,
}))

const identity = {
  id: 'identity-id', email: 'teacher@example.com', status: 'active',
  created_at: '2026-08-25T00:00:00Z', updated_at: '2026-08-25T00:00:00Z',
}
const course = {
  id: 'course-id', educational_environment_id: 'environment-id', title: 'Foundations', status: 'draft',
  created_at: '2026-08-25T00:00:00Z', updated_at: '2026-08-25T00:00:00Z',
}
const firstActivity = {
  id: 'activity-1', learning_unit_id: 'unit-id', title: 'Lecture One', type: 'lecture', position: 0,
  created_at: '2026-08-25T00:00:00Z', updated_at: '2026-08-25T00:00:00Z', assessment_definition_id: null,
}
const secondActivity = { ...firstActivity, id: 'activity-2', title: 'Video One', type: 'video', position: 2 }
const route = '/app/teacher-spaces/space-id/environment/courses/course-id/sections/section-id/learning-units/unit-id/activities'
const endpoint = '/api/v1/teacher-spaces/space-id/environment/courses/course-id/sections/section-id/units/unit-id/activities'
const courseEndpoint = '/api/v1/teacher-spaces/space-id/environment/courses/course-id'
const jsonResponse = (body: unknown, status = 200) =>
  new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } })

const renderRoute = () => {
  const router = createMemoryRouter(routes, { initialEntries: [route] })
  return render(
    <QueryClientProvider client={createQueryClient()}>
      <RouterProvider router={router} />
    </QueryClientProvider>,
  )
}

const mutationMethod = (init?: RequestInit) =>
  init?.method === 'POST' || init?.method === 'PATCH' || init?.method === 'DELETE'

describe('Activity UI', () => {
  afterEach(() => vi.unstubAllGlobals())

  it('shows loading and an explicit empty state', async () => {
    let resolveActivities: ((response: Response) => void) | undefined
    vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL) => {
      if (String(input).endsWith('/api/v1/auth/me')) return jsonResponse(identity)
      return new Promise<Response>((resolve) => { resolveActivities = resolve })
    }))
    renderRoute()

    expect(await screen.findByText('Loading Activities')).toBeInTheDocument()
    resolveActivities?.(jsonResponse([]))
    expect(await screen.findByRole('heading', { name: 'No Activities yet' })).toBeInTheDocument()
  })

  it('renders Activities in the server-provided position order', async () => {
    vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input)
      if (url.endsWith('/api/v1/auth/me')) return jsonResponse(identity)
      if (url.endsWith(courseEndpoint)) return jsonResponse(course)
      return jsonResponse([firstActivity, secondActivity])
    }))
    renderRoute()

    const rows = await screen.findAllByRole('listitem')
    expect(within(rows[0]).getByDisplayValue('Lecture One')).toBeInTheDocument()
    expect(within(rows[0]).getByLabelText('Position')).toHaveValue(0)
    expect(within(rows[1]).getByDisplayValue('Video One')).toBeInTheDocument()
    expect(within(rows[1]).getByLabelText('Position')).toHaveValue(2)
  })

  it('creates an Activity and refetches the scoped list', async () => {
    let activities = [] as typeof firstActivity[]
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input)
      if (url.endsWith('/api/v1/auth/me')) return jsonResponse(identity)
      if (url.endsWith(courseEndpoint)) return jsonResponse(course)
      if (url.endsWith(endpoint) && init?.method === 'POST') {
        expect(JSON.parse(String(init.body))).toEqual({ title: 'Lecture One', type: 'homework', position: 0 })
        activities = [firstActivity]
        return jsonResponse(firstActivity, 201)
      }
      if (url.endsWith(endpoint)) return jsonResponse(activities)
      throw new Error(`Unexpected request: ${url}`)
    })
    vi.stubGlobal('fetch', fetchMock)
    const user = userEvent.setup()
    renderRoute()

    await user.type(await screen.findByLabelText('Activity title'), 'Lecture One')
    expect(within(screen.getByLabelText('Type')).getAllByRole('option').map((option) => option.getAttribute('value'))).toEqual([
      'lecture',
      'video',
      'homework',
    ])
    await user.selectOptions(screen.getByLabelText('Type'), 'homework')
    await user.click(screen.getByRole('button', { name: 'Create Activity' }))

    expect(await screen.findByDisplayValue('Lecture One')).toBeInTheDocument()
    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining(endpoint),
      expect.objectContaining({ credentials: 'include', method: 'POST' }),
    )
  })

  it('updates Activity title and position through the existing API', async () => {
    let activity = firstActivity
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input)
      if (url.endsWith('/api/v1/auth/me')) return jsonResponse(identity)
      if (url.endsWith(courseEndpoint)) return jsonResponse(course)
      if (url.endsWith(`${endpoint}/activity-1`) && init?.method === 'PATCH') {
        expect(JSON.parse(String(init.body))).toEqual({ title: 'Updated Activity', position: 3 })
        activity = { ...activity, title: 'Updated Activity', position: 3 }
        return jsonResponse(activity)
      }
      if (url.endsWith(endpoint)) return jsonResponse([activity])
      throw new Error(`Unexpected request: ${url}`)
    })
    vi.stubGlobal('fetch', fetchMock)
    const user = userEvent.setup()
    renderRoute()

    const row = await screen.findByRole('listitem')
    const title = within(row).getByLabelText('Activity title')
    await user.clear(title)
    await user.type(title, 'Updated Activity')
    const position = within(row).getByLabelText('Position')
    await user.clear(position)
    await user.type(position, '3')
    await user.click(within(row).getByRole('button', { name: 'Save' }))

    expect(await within(row).findByDisplayValue('Updated Activity')).toBeInTheDocument()
    expect(within(row).getByLabelText('Position')).toHaveValue(3)
  })

  it('deletes an Activity and refetches the list', async () => {
    let activities = [firstActivity]
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input)
      if (url.endsWith('/api/v1/auth/me')) return jsonResponse(identity)
      if (url.endsWith(courseEndpoint)) return jsonResponse(course)
      if (url.endsWith(`${endpoint}/activity-1`) && init?.method === 'DELETE') {
        activities = []
        return new Response(null, { status: 204 })
      }
      if (url.endsWith(endpoint)) return jsonResponse(activities)
      throw new Error(`Unexpected request: ${url}`)
    })
    vi.stubGlobal('fetch', fetchMock)
    const user = userEvent.setup()
    renderRoute()

    await user.click(within(await screen.findByRole('listitem')).getByRole('button', { name: 'Delete' }))
    expect(await screen.findByRole('heading', { name: 'No Activities yet' })).toBeInTheDocument()
  })

  it('shows API errors and protects the route', async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL) =>
      String(input).endsWith('/api/v1/auth/me')
        ? jsonResponse(identity)
        : jsonResponse({ detail: 'Published or archived Course is read-only' }, 409),
    )
    vi.stubGlobal('fetch', fetchMock)
    const view = renderRoute()
    expect(await screen.findByRole('alert')).toHaveTextContent('Published or archived Course is read-only')

    view.unmount()
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(jsonResponse({ detail: 'Authentication required' }, 401)))
    renderRoute()
    expect(await screen.findByRole('heading', { name: 'Log in' })).toBeInTheDocument()
  })

  it('renders a PUBLISHED Course read-only and sends no mutation requests', async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input)
      if (url.endsWith('/api/v1/auth/me')) return jsonResponse(identity)
      if (url.endsWith(courseEndpoint)) return jsonResponse({ ...course, status: 'published' })
      if (url.endsWith(endpoint)) return jsonResponse([firstActivity])
      throw new Error(`Unexpected request: ${url}`)
    })
    vi.stubGlobal('fetch', fetchMock)
    const user = userEvent.setup()
    renderRoute()

    expect(await screen.findByText('Published — read-only')).toBeInTheDocument()
    const row = await screen.findByRole('listitem')
    expect(within(row).getByDisplayValue('Lecture One')).toBeInTheDocument()
    expect(within(row).getByRole('button', { name: 'Save' })).toBeDisabled()
    expect(within(row).getByRole('button', { name: 'Delete' })).toBeDisabled()
    expect(within(row).getByLabelText('Activity title')).toBeDisabled()
    expect(within(row).getByLabelText('Position')).toBeDisabled()
    expect(screen.getByRole('button', { name: 'Create Activity' })).toBeDisabled()
    expect(screen.getAllByLabelText('Activity title').every((input) => input.hasAttribute('disabled'))).toBe(true)
    expect(screen.getByLabelText('Type')).toBeDisabled()
    expect(screen.getByRole('link', { name: 'Back to Learning Units' })).toHaveAttribute(
      'href',
      '/app/teacher-spaces/space-id/environment/courses/course-id/sections/section-id/learning-units',
    )
    expect(screen.getByText('Content management')).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: 'Create Activity' }))
    await user.click(within(row).getByRole('button', { name: 'Save' }))
    await user.click(within(row).getByRole('button', { name: 'Delete' }))

    expect(fetchMock.mock.calls.some(([url, init]) =>
      String(url).endsWith(courseEndpoint) && !init?.method,
    )).toBe(true)
    expect(fetchMock.mock.calls.filter(([, init]) => mutationMethod(init))).toHaveLength(0)
  })

  it('renders an ARCHIVED Course read-only and sends no mutation requests', async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input)
      if (url.endsWith('/api/v1/auth/me')) return jsonResponse(identity)
      if (url.endsWith(courseEndpoint)) return jsonResponse({ ...course, status: 'archived' })
      if (url.endsWith(endpoint)) return jsonResponse([firstActivity])
      throw new Error(`Unexpected request: ${url}`)
    })
    vi.stubGlobal('fetch', fetchMock)
    const user = userEvent.setup()
    renderRoute()

    expect(await screen.findByText('Archived — read-only')).toBeInTheDocument()
    const row = await screen.findByRole('listitem')
    expect(within(row).getByDisplayValue('Lecture One')).toBeInTheDocument()
    expect(within(row).getByRole('button', { name: 'Save' })).toBeDisabled()
    expect(within(row).getByRole('button', { name: 'Delete' })).toBeDisabled()
    expect(screen.getByRole('button', { name: 'Create Activity' })).toBeDisabled()
    expect(screen.getByText('Content management')).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: 'Create Activity' }))
    await user.click(within(row).getByRole('button', { name: 'Save' }))
    await user.click(within(row).getByRole('button', { name: 'Delete' }))

    expect(fetchMock.mock.calls.filter(([, init]) => mutationMethod(init))).toHaveLength(0)
  })
})
