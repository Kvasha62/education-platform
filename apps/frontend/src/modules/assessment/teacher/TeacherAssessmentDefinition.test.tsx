import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { createMemoryRouter, RouterProvider } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { createQueryClient } from '../../../app/providers'
import { routes } from '../../../app/router'
import type { TeacherAssessmentDefinition } from './api'
import { teacherAssessmentKeys } from './queries'

const identity = {
  id: 'identity-id',
  email: 'teacher@example.com',
  status: 'active',
  created_at: '2026-08-26T00:00:00Z',
  updated_at: '2026-08-26T00:00:00Z',
}

const teacherSpaceId = 'space-1'
const activityId = 'activity-1'

const activeDefinition: TeacherAssessmentDefinition = {
  id: 'definition-1',
  activity_id: activityId,
  instructions: 'Read chapter three.',
  status: 'active',
}

const archivedDefinition: TeacherAssessmentDefinition = {
  ...activeDefinition,
  status: 'archived',
}

const definitionUrl = () =>
  `/api/v1/teacher-spaces/${teacherSpaceId}/activities/${activityId}/assessment-definition`

const definitionRoute = () =>
  `/app/teacher-spaces/${teacherSpaceId}/activities/${activityId}/assessment-definition`

const activityListPath =
  '/app/teacher-spaces/space-1/environment/courses/course-1/sections/section-1/learning-units/unit-1/activities'

const jsonResponse = (body: unknown, status = 200) =>
  new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })

const renderRoute = (entry: string, client?: QueryClient) => {
  const router = createMemoryRouter(routes, { initialEntries: [entry] })
  const rendered = render(
    <QueryClientProvider client={client ?? createQueryClient()}>
      <RouterProvider router={router} />
    </QueryClientProvider>,
  )
  return { ...rendered, router }
}

const authResponse = (url: string) =>
  url.endsWith('/api/v1/auth/me') ? jsonResponse(identity) : null

describe('Teacher Assessment Definition management UI', () => {
  afterEach(() => {
    vi.restoreAllMocks()
    vi.unstubAllGlobals()
  })

  it('renders the create state only for the normative missing-Definition 404; other errors show ErrorState', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async (input: RequestInfo | URL) => {
        const url = String(input)
        return (
          authResponse(url) ??
          (url.endsWith(definitionUrl())
            ? jsonResponse({ detail: 'Assessment Definition not found' }, 404)
            : jsonResponse([]))
        )
      }),
    )
    const createView = renderRoute(definitionRoute())
    expect(
      await screen.findByRole('heading', { name: 'Set up assessment' }),
    ).toBeInTheDocument()
    expect(screen.getByText('This Activity has no Assessment Definition yet.')).toBeInTheDocument()
    expect(screen.getByLabelText('Instructions')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Create assessment' })).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Archive assessment' })).not.toBeInTheDocument()
    createView.unmount()

    vi.stubGlobal(
      'fetch',
      vi.fn(async (input: RequestInfo | URL) =>
        authResponse(String(input)) ?? jsonResponse({ detail: 'Assessment access denied' }, 403),
      ),
    )
    renderRoute(definitionRoute())
    expect(await screen.findByRole('alert')).toHaveTextContent('Assessment access denied')
    expect(screen.queryByRole('heading', { name: 'Set up assessment' })).not.toBeInTheDocument()
  })

  it('creates a Definition with null instructions for empty input, invalidates the definition key, and shows the view state', async () => {
    let current: TeacherAssessmentDefinition | null = null
    const bodies: unknown[] = []
    let reads = 0
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input)
      const auth = authResponse(url)
      if (auth) return auth
      if (url.endsWith(definitionUrl()) && init?.method === 'POST') {
        bodies.push(JSON.parse(String(init.body)))
        current = { ...activeDefinition, instructions: null }
        return jsonResponse(current, 201)
      }
      if (url.endsWith(definitionUrl())) {
        reads += 1
        return current
          ? jsonResponse(current)
          : jsonResponse({ detail: 'Assessment Definition not found' }, 404)
      }
      throw new Error(`Unexpected request: ${url}`)
    })
    vi.stubGlobal('fetch', fetchMock)
    const client = createQueryClient()
    const invalidateSpy = vi.spyOn(client, 'invalidateQueries')
    const user = userEvent.setup()
    renderRoute(definitionRoute(), client)

    await user.click(await screen.findByRole('button', { name: 'Create assessment' }))

    expect(await screen.findByRole('heading', { name: 'Assessment settings' })).toBeInTheDocument()
    expect(bodies).toEqual([{ instructions: null }])
    expect(screen.getByText('No instructions')).toBeInTheDocument()
    expect(screen.getByText('ACTIVE')).toBeInTheDocument()
    expect(
      invalidateSpy.mock.calls.some(([options]) =>
        JSON.stringify(options?.queryKey) ===
        JSON.stringify(teacherAssessmentKeys.definition(teacherSpaceId, activityId)),
      ),
    ).toBe(true)
    await waitFor(() => expect(reads).toBeGreaterThanOrEqual(2))
  })

  it('sends typed instructions exactly as entered', async () => {
    const bodies: unknown[] = []
    vi.stubGlobal(
      'fetch',
      vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
        const url = String(input)
        const auth = authResponse(url)
        if (auth) return auth
        if (url.endsWith(definitionUrl()) && init?.method === 'POST') {
          bodies.push(JSON.parse(String(init.body)))
          return jsonResponse({ ...activeDefinition, instructions: 'Read chapter three.' }, 201)
        }
        if (url.endsWith(definitionUrl())) {
          return jsonResponse({ detail: 'Assessment Definition not found' }, 404)
        }
        throw new Error(`Unexpected request: ${url}`)
      }),
    )
    const user = userEvent.setup()
    renderRoute(definitionRoute())

    await user.type(await screen.findByLabelText('Instructions'), 'Read chapter three.')
    await user.click(screen.getByRole('button', { name: 'Create assessment' }))

    expect(await screen.findByText('Read chapter three.')).toBeInTheDocument()
    expect(bodies).toEqual([{ instructions: 'Read chapter three.' }])
  })

  it('maps a duplicate create conflict to an error and keeps the create state', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
        const url = String(input)
        const auth = authResponse(url)
        if (auth) return auth
        if (url.endsWith(definitionUrl()) && init?.method === 'POST') {
          return jsonResponse({ detail: 'Assessment Definition already exists' }, 409)
        }
        if (url.endsWith(definitionUrl())) {
          return jsonResponse({ detail: 'Assessment Definition not found' }, 404)
        }
        throw new Error(`Unexpected request: ${url}`)
      }),
    )
    const user = userEvent.setup()
    renderRoute(definitionRoute())

    await user.click(await screen.findByRole('button', { name: 'Create assessment' }))

    expect(await screen.findByRole('alert')).toHaveTextContent('Invalid assessment state')
    expect(screen.getByRole('heading', { name: 'Set up assessment' })).toBeInTheDocument()
    expect(screen.queryByRole('heading', { name: 'Assessment settings' })).not.toBeInTheDocument()
  })

  it('renders the exact contract fields in the view state', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async (input: RequestInfo | URL) => {
        const url = String(input)
        return authResponse(url) ?? (url.endsWith(definitionUrl()) ? jsonResponse(activeDefinition) : jsonResponse([]))
      }),
    )
    renderRoute(definitionRoute())

    expect(await screen.findByRole('heading', { name: 'Assessment settings' })).toBeInTheDocument()
    expect(screen.getByText('ACTIVE')).toBeInTheDocument()
    expect(screen.getByText('definition-1')).toBeInTheDocument()
    expect(screen.getByText('activity-1')).toBeInTheDocument()
    expect(screen.getByText('Read chapter three.')).toBeInTheDocument()
    expect(screen.getByText('active')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Edit instructions' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Archive assessment' })).toBeInTheDocument()
  })

  it('renders an archived Definition read-only and never calls the update path', async () => {
    const requests: Array<{ url: string; method: string }> = []
    vi.stubGlobal(
      'fetch',
      vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
        const url = String(input)
        requests.push({ url, method: init?.method ?? 'GET' })
        return authResponse(url) ?? (url.endsWith(definitionUrl()) ? jsonResponse(archivedDefinition) : jsonResponse([]))
      }),
    )
    renderRoute(definitionRoute())

    expect(await screen.findByText('ARCHIVED')).toBeInTheDocument()
    expect(screen.getByText('archived')).toBeInTheDocument()
    expect(screen.getByText('Read chapter three.')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Edit instructions' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Archive assessment' })).not.toBeInTheDocument()
    expect(screen.queryByLabelText('Instructions')).not.toBeInTheDocument()
    expect(requests.every(({ method }) => method === 'GET')).toBe(true)
  })

  it('updates instructions and supports clearing them to null', async () => {
    let current: TeacherAssessmentDefinition = activeDefinition
    const bodies: unknown[] = []
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input)
      const auth = authResponse(url)
      if (auth) return auth
      if (url.endsWith(definitionUrl()) && init?.method === 'PATCH') {
        const body = JSON.parse(String(init.body)) as { instructions: string | null }
        bodies.push(body)
        current = { ...current, instructions: body.instructions }
        return jsonResponse(current)
      }
      if (url.endsWith(definitionUrl())) return jsonResponse(current)
      throw new Error(`Unexpected request: ${url}`)
    })
    vi.stubGlobal('fetch', fetchMock)
    const user = userEvent.setup()
    renderRoute(definitionRoute())

    await user.click(await screen.findByRole('button', { name: 'Edit instructions' }))
    const editor = screen.getByLabelText('Instructions')
    expect(editor).toHaveValue('Read chapter three.')
    await user.clear(editor)
    await user.type(editor, 'Answer the questions.')
    await user.click(screen.getByRole('button', { name: 'Save instructions' }))

    expect(await screen.findByText('Answer the questions.')).toBeInTheDocument()
    expect(bodies).toEqual([{ instructions: 'Answer the questions.' }])
    expect(screen.queryByLabelText('Instructions')).not.toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: 'Edit instructions' }))
    const clearedEditor = screen.getByLabelText('Instructions')
    await user.clear(clearedEditor)
    await user.click(screen.getByRole('button', { name: 'Save instructions' }))

    expect(await screen.findByText('No instructions')).toBeInTheDocument()
    expect(bodies).toEqual([{ instructions: 'Answer the questions.' }, { instructions: null }])
  })

  it('archives only after confirmation and switches to the read-only archived view', async () => {
    let current: TeacherAssessmentDefinition = activeDefinition
    const archiveBodies: unknown[] = []
    vi.stubGlobal(
      'fetch',
      vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
        const url = String(input)
        const auth = authResponse(url)
        if (auth) return auth
        if (url.endsWith(`${definitionUrl()}/archive`) && init?.method === 'POST') {
          archiveBodies.push(init.body ?? null)
          current = archivedDefinition
          return jsonResponse(current)
        }
        if (url.endsWith(definitionUrl())) return jsonResponse(current)
        throw new Error(`Unexpected request: ${url}`)
      }),
    )
    const confirmSpy = vi.spyOn(window, 'confirm').mockReturnValue(true)
    const user = userEvent.setup()
    renderRoute(definitionRoute())

    await user.click(await screen.findByRole('button', { name: 'Archive assessment' }))

    expect(confirmSpy).toHaveBeenCalledTimes(1)
    expect(await screen.findByText('ARCHIVED')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Edit instructions' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Archive assessment' })).not.toBeInTheDocument()
    expect(archiveBodies).toHaveLength(1)
  })

  it('sends no archive request when the confirmation is cancelled', async () => {
    const requested: string[] = []
    vi.stubGlobal(
      'fetch',
      vi.fn(async (input: RequestInfo | URL) => {
        const url = String(input)
        requested.push(url)
        return authResponse(url) ?? (url.endsWith(definitionUrl()) ? jsonResponse(activeDefinition) : jsonResponse([]))
      }),
    )
    vi.spyOn(window, 'confirm').mockReturnValue(false)
    const user = userEvent.setup()
    renderRoute(definitionRoute())

    await user.click(await screen.findByRole('button', { name: 'Archive assessment' }))

    expect(screen.queryByText('ARCHIVED')).not.toBeInTheDocument()
    expect(requested.every((url) => !url.endsWith(`${definitionUrl()}/archive`))).toBe(true)
  })

  it('surfaces a raced repeat archive conflict as an error', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
        const url = String(input)
        const auth = authResponse(url)
        if (auth) return auth
        if (url.endsWith(`${definitionUrl()}/archive`) && init?.method === 'POST') {
          return jsonResponse({ detail: 'Assessment Definition is already archived' }, 409)
        }
        if (url.endsWith(definitionUrl())) return jsonResponse(activeDefinition)
        throw new Error(`Unexpected request: ${url}`)
      }),
    )
    vi.spyOn(window, 'confirm').mockReturnValue(true)
    const user = userEvent.setup()
    renderRoute(definitionRoute())

    await user.click(await screen.findByRole('button', { name: 'Archive assessment' }))

    expect(await screen.findByRole('alert')).toHaveTextContent('Invalid assessment state')
    expect(screen.getByRole('button', { name: 'Archive assessment' })).toBeInTheDocument()
  })

  it('disables mutating controls while requests are pending', async () => {
    let created: TeacherAssessmentDefinition | null = null
    let releaseCreate: (() => void) | undefined
    vi.stubGlobal(
      'fetch',
      vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
        const url = String(input)
        const auth = authResponse(url)
        if (auth) return auth
        if (url.endsWith(definitionUrl()) && init?.method === 'POST') {
          return new Promise<Response>((resolve) => {
            releaseCreate = () => {
              created = activeDefinition
              resolve(jsonResponse(activeDefinition, 201))
            }
          })
        }
        if (url.endsWith(definitionUrl())) {
          return created
            ? jsonResponse(created)
            : jsonResponse({ detail: 'Assessment Definition not found' }, 404)
        }
        throw new Error(`Unexpected request: ${url}`)
      }),
    )
    const user = userEvent.setup()
    renderRoute(definitionRoute())

    await user.click(await screen.findByRole('button', { name: 'Create assessment' }))

    expect(await screen.findByRole('button', { name: 'Creating…' })).toBeDisabled()
    expect(screen.getByLabelText('Instructions')).toBeDisabled()
    releaseCreate?.()
    expect(await screen.findByRole('heading', { name: 'Assessment settings' })).toBeInTheDocument()
  })

  it('uses only sanitized same-origin backTo targets for the Back to Activity link', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async (input: RequestInfo | URL) =>
        authResponse(String(input)) ?? jsonResponse(activeDefinition),
      ),
    )
    const validView = renderRoute(`${definitionRoute()}?backTo=${encodeURIComponent(activityListPath)}`)
    expect(await screen.findByRole('link', { name: 'Back to Activity' })).toHaveAttribute(
      'href',
      activityListPath,
    )
    validView.unmount()

    const evilView = renderRoute(
      `${definitionRoute()}?backTo=${encodeURIComponent('https://evil.example/redirect')}`,
    )
    expect(await screen.findByRole('heading', { name: 'Assessment settings' })).toBeInTheDocument()
    expect(screen.queryByRole('link', { name: 'Back to Activity' })).not.toBeInTheDocument()
    evilView.unmount()
  })
})
