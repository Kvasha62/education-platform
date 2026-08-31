import { QueryClientProvider } from '@tanstack/react-query'
import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { createMemoryRouter, RouterProvider } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { createQueryClient } from '../../app/providers'
import { routes } from '../../app/router'

const identity = {
  id: 'identity-id', email: 'teacher@example.com', status: 'active',
  created_at: '2026-08-25T00:00:00Z', updated_at: '2026-08-25T00:00:00Z',
}
const course = {
  id: 'course-id', educational_environment_id: 'environment-id', title: 'Foundations', status: 'draft',
  created_at: '2026-08-25T00:00:00Z', updated_at: '2026-08-25T00:00:00Z',
}
const firstUnit = {
  id: 'unit-1', section_id: 'section-id', title: 'Lesson One', position: 0,
  created_at: '2026-08-25T00:00:00Z', updated_at: '2026-08-25T00:00:00Z',
}
const secondUnit = { ...firstUnit, id: 'unit-2', title: 'Lesson Two', position: 2 }
const route = '/app/teacher-spaces/space-id/environment/courses/course-id/sections/section-id/learning-units'
const endpoint = '/api/v1/teacher-spaces/space-id/environment/courses/course-id/sections/section-id/units'
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

describe('Learning Unit UI', () => {
  afterEach(() => vi.unstubAllGlobals())

  it('shows loading and an explicit empty state', async () => {
    let resolveUnits: ((response: Response) => void) | undefined
    vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL) => {
      if (String(input).endsWith('/api/v1/auth/me')) return jsonResponse(identity)
      return new Promise<Response>((resolve) => { resolveUnits = resolve })
    }))
    renderRoute()

    expect(await screen.findByText('Loading Learning Units')).toBeInTheDocument()
    resolveUnits?.(jsonResponse([]))
    expect(await screen.findByRole('heading', { name: 'No Learning Units yet' })).toBeInTheDocument()
  })

  it('renders Learning Units in the server-provided position order', async () => {
    vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input)
      if (url.endsWith('/api/v1/auth/me')) return jsonResponse(identity)
      if (url.endsWith(courseEndpoint)) return jsonResponse(course)
      return jsonResponse([firstUnit, secondUnit])
    }))
    renderRoute()

    const rows = await screen.findAllByRole('listitem')
    expect(within(rows[0]).getByDisplayValue('Lesson One')).toBeInTheDocument()
    expect(within(rows[0]).getByText('Position 0')).toBeInTheDocument()
    expect(within(rows[1]).getByDisplayValue('Lesson Two')).toBeInTheDocument()
    expect(within(rows[1]).getByText('Position 2')).toBeInTheDocument()
    expect(within(rows[0]).getByRole('link', { name: 'Open Activities' })).toHaveAttribute(
      'href',
      '/app/teacher-spaces/space-id/environment/courses/course-id/sections/section-id/learning-units/unit-1/activities',
    )
  })

  it('creates a Learning Unit and refetches the scoped list', async () => {
    let units = [] as typeof firstUnit[]
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input)
      if (url.endsWith('/api/v1/auth/me')) return jsonResponse(identity)
      if (url.endsWith(courseEndpoint)) return jsonResponse(course)
      if (url.endsWith(endpoint) && init?.method === 'POST') {
        expect(JSON.parse(String(init.body))).toEqual({ title: 'Lesson One', position: 0 })
        units = [firstUnit]
        return jsonResponse(firstUnit, 201)
      }
      if (url.endsWith(endpoint)) return jsonResponse(units)
      throw new Error(`Unexpected request: ${url}`)
    })
    vi.stubGlobal('fetch', fetchMock)
    const user = userEvent.setup()
    renderRoute()

    await user.type(await screen.findByLabelText('Learning Unit title'), 'Lesson One')
    await user.click(screen.getByRole('button', { name: 'Create Learning Unit' }))

    expect(await screen.findByDisplayValue('Lesson One')).toBeInTheDocument()
    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining(endpoint),
      expect.objectContaining({ credentials: 'include', method: 'POST' }),
    )
  })

  it('updates Learning Unit title and position through the existing API', async () => {
    let unit = firstUnit
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input)
      if (url.endsWith('/api/v1/auth/me')) return jsonResponse(identity)
      if (url.endsWith(courseEndpoint)) return jsonResponse(course)
      if (url.endsWith(`${endpoint}/unit-1`) && init?.method === 'PATCH') {
        expect(JSON.parse(String(init.body))).toEqual({ title: 'Updated Unit', position: 3 })
        unit = { ...unit, title: 'Updated Unit', position: 3 }
        return jsonResponse(unit)
      }
      if (url.endsWith(endpoint)) return jsonResponse([unit])
      throw new Error(`Unexpected request: ${url}`)
    })
    vi.stubGlobal('fetch', fetchMock)
    const user = userEvent.setup()
    renderRoute()

    const row = await screen.findByRole('listitem')
    const title = within(row).getByLabelText('Learning Unit title')
    await user.clear(title)
    await user.type(title, 'Updated Unit')
    const position = within(row).getByLabelText('Position')
    await user.clear(position)
    await user.type(position, '3')
    await user.click(within(row).getByRole('button', { name: 'Save' }))

    expect(await within(row).findByDisplayValue('Updated Unit')).toBeInTheDocument()
    expect(await within(row).findByText('Position 3')).toBeInTheDocument()
  })

  it('deletes a Learning Unit and refetches the list', async () => {
    let units = [firstUnit]
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input)
      if (url.endsWith('/api/v1/auth/me')) return jsonResponse(identity)
      if (url.endsWith(courseEndpoint)) return jsonResponse(course)
      if (url.endsWith(`${endpoint}/unit-1`) && init?.method === 'DELETE') {
        units = []
        return new Response(null, { status: 204 })
      }
      if (url.endsWith(endpoint)) return jsonResponse(units)
      throw new Error(`Unexpected request: ${url}`)
    })
    vi.stubGlobal('fetch', fetchMock)
    const user = userEvent.setup()
    renderRoute()

    await user.click(within(await screen.findByRole('listitem')).getByRole('button', { name: 'Delete' }))
    expect(await screen.findByRole('heading', { name: 'No Learning Units yet' })).toBeInTheDocument()
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
      if (url.endsWith(endpoint)) return jsonResponse([firstUnit])
      throw new Error(`Unexpected request: ${url}`)
    })
    vi.stubGlobal('fetch', fetchMock)
    const user = userEvent.setup()
    renderRoute()

    expect(await screen.findByText('Published — read-only')).toBeInTheDocument()
    const row = await screen.findByRole('listitem')
    expect(within(row).getByDisplayValue('Lesson One')).toBeInTheDocument()
    expect(within(row).getByText('Position 0')).toBeInTheDocument()
    expect(within(row).getByRole('button', { name: 'Save' })).toBeDisabled()
    expect(within(row).getByRole('button', { name: 'Delete' })).toBeDisabled()
    expect(within(row).getByLabelText('Learning Unit title')).toBeDisabled()
    expect(within(row).getByLabelText('Position')).toBeDisabled()
    expect(within(row).getByRole('link', { name: 'Open Activities' })).toHaveAttribute(
      'href',
      '/app/teacher-spaces/space-id/environment/courses/course-id/sections/section-id/learning-units/unit-1/activities',
    )
    expect(screen.getByRole('button', { name: 'Create Learning Unit' })).toBeDisabled()
    expect(screen.getAllByLabelText('Learning Unit title').every((input) => input.hasAttribute('disabled'))).toBe(true)
    expect(screen.getByRole('link', { name: 'Back to Sections' })).toHaveAttribute(
      'href',
      '/app/teacher-spaces/space-id/environment/courses/course-id/sections',
    )

    await user.click(screen.getByRole('button', { name: 'Create Learning Unit' }))
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
      if (url.endsWith(endpoint)) return jsonResponse([firstUnit])
      throw new Error(`Unexpected request: ${url}`)
    })
    vi.stubGlobal('fetch', fetchMock)
    const user = userEvent.setup()
    renderRoute()

    expect(await screen.findByText('Archived — read-only')).toBeInTheDocument()
    const row = await screen.findByRole('listitem')
    expect(within(row).getByDisplayValue('Lesson One')).toBeInTheDocument()
    expect(within(row).getByRole('button', { name: 'Save' })).toBeDisabled()
    expect(within(row).getByRole('button', { name: 'Delete' })).toBeDisabled()
    expect(within(row).getByRole('link', { name: 'Open Activities' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Create Learning Unit' })).toBeDisabled()

    await user.click(screen.getByRole('button', { name: 'Create Learning Unit' }))
    await user.click(within(row).getByRole('button', { name: 'Save' }))
    await user.click(within(row).getByRole('button', { name: 'Delete' }))

    expect(fetchMock.mock.calls.filter(([, init]) => mutationMethod(init))).toHaveLength(0)
  })
})
