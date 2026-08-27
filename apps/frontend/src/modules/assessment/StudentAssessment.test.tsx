import { QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { createMemoryRouter, RouterProvider } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { createQueryClient } from '../../app/providers'
import { routes } from '../../app/router'
import { assessmentApi } from './api'
import type { AssessmentAttempt } from './api'

const identity = {
  id: 'identity-id',
  email: 'student@example.com',
  status: 'active',
  created_at: '2026-08-26T00:00:00Z',
  updated_at: '2026-08-26T00:00:00Z',
}
const draft = (id = 'attempt-id', submission: string | null = null): AssessmentAttempt => ({
  id,
  assessment_definition_id: 'definition-id',
  submission,
  status: 'draft',
  result: null,
})
const submitted = (id = 'attempt-id'): AssessmentAttempt => ({
  ...draft(id, 'Submitted answer'),
  status: 'submitted',
})
const reviewed = (feedback: string | null = 'Good work'): AssessmentAttempt => ({
  ...submitted(),
  status: 'reviewed',
  result: {
    id: 'result-id',
    attempt_id: 'attempt-id',
    score: 8,
    max_score: 10,
    feedback,
  },
})
const attemptRoute = (attemptId = 'attempt-id') =>
  `/student/activities/activity-id/assessment-attempts/${attemptId}`
const jsonResponse = (body: unknown, status = 200) =>
  new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })

const renderRoute = (entry: string) => {
  const router = createMemoryRouter(routes, { initialEntries: [entry] })
  const rendered = render(
    <QueryClientProvider client={createQueryClient()}>
      <RouterProvider router={router} />
    </QueryClientProvider>,
  )
  return { ...rendered, router }
}

const authResponse = (url: string) =>
  url.endsWith('/api/v1/auth/me') ? jsonResponse(identity) : null

const requestBody = (init?: RequestInit) =>
  init?.body ? JSON.parse(String(init.body)) as unknown : undefined


describe('Student Assessment UI', () => {
  afterEach(() => {
    vi.restoreAllMocks()
    vi.unstubAllGlobals()
  })

  it('opens Assessment from Activity and explicitly creates a DRAFT before canonical navigation', async () => {
    const requests: Array<{ url: string; init?: RequestInit }> = []
    const course = {
      id: 'course-id',
      title: 'Course',
      sections: [{
        id: 'section-id',
        title: 'Section',
        position: 0,
        units: [{
          id: 'unit-id',
          title: 'Unit',
          position: 0,
          activities: [{
            id: 'activity-id',
            title: 'Assessment Activity',
            type: 'homework',
            position: 0,
            contents: [],
            assessment_definition_id: 'definition-id',
          }],
        }],
      }],
    }
    const created = draft()
    vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input)
      requests.push({ url, init })
      const auth = authResponse(url)
      if (auth) return auth
      if (url.endsWith('/api/v1/student/courses/course-id')) return jsonResponse(course)
      if (url.endsWith('/api/v1/student/activities/activity-id/progress')) {
        return jsonResponse({ detail: 'Progress not found' }, 404)
      }
      if (url.endsWith('/activities/activity-id/assessment-definitions/definition-id/attempts')) {
        return jsonResponse(created, 201)
      }
      if (url.endsWith('/api/v1/student/assessment-attempts/attempt-id')) {
        return jsonResponse(created)
      }
      throw new Error(`Unexpected request: ${url}`)
    }))
    const user = userEvent.setup()
    const { router } = renderRoute('/app/student/courses/course-id/activities/activity-id')

    const open = await screen.findByRole('button', { name: 'Open assessment' })
    expect(requests.some(({ url }) => url.includes('/assessment-definitions/'))).toBe(false)
    await user.click(open)
    expect(screen.getByRole('button', { name: 'Create DRAFT' })).toBeInTheDocument()
    expect(requests.some(({ url }) => url.includes('/assessment-definitions/'))).toBe(false)
    await user.click(screen.getByRole('button', { name: 'Create DRAFT' }))

    expect(await screen.findByRole('heading', { name: 'Assessment Attempt' })).toBeInTheDocument()
    expect(router.state.location.pathname).toBe(attemptRoute())
    const create = requests.find(({ url }) => url.includes('/assessment-definitions/'))
    expect(create?.init?.method).toBe('POST')
    expect(requestBody(create?.init)).toEqual({})
  })

  it('does not show Assessment entry when Activity has no Definition', async () => {
    const course = {
      id: 'course-id',
      title: 'Course',
      sections: [{
        id: 'section-id', title: 'Section', position: 0,
        units: [{
          id: 'unit-id', title: 'Unit', position: 0,
          activities: [{
            id: 'activity-id', title: 'Reading', type: 'lecture', position: 0,
            contents: [], assessment_definition_id: null,
          }],
        }],
      }],
    }
    vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input)
      return authResponse(url) ?? (
        url.endsWith('/progress')
          ? jsonResponse({ detail: 'Progress not found' }, 404)
          : jsonResponse(course)
      )
    }))
    renderRoute('/app/student/courses/course-id/activities/activity-id')

    expect(await screen.findByRole('heading', { name: 'Reading' })).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Open assessment' })).not.toBeInTheDocument()
  })

  it('supports explicit Save replacement, clearing, and blank normalization without autosave', async () => {
    let confirmed = draft()
    const requests: Array<{ url: string; init?: RequestInit }> = []
    vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input)
      requests.push({ url, init })
      const auth = authResponse(url)
      if (auth) return auth
      if (init?.method === 'PUT') {
        const body = requestBody(init) as { submission: string | null }
        confirmed = draft(
          'attempt-id',
          body.submission && body.submission.trim() ? body.submission : null,
        )
        return jsonResponse(confirmed)
      }
      return jsonResponse(confirmed)
    }))
    const user = userEvent.setup()
    renderRoute(attemptRoute())
    const textarea = await screen.findByRole('textbox', { name: 'Submission' })

    await user.type(textarea, 'First answer')
    expect(requests.filter(({ init }) => init?.method === 'PUT')).toHaveLength(0)
    await user.click(screen.getByRole('button', { name: 'Save' }))
    await screen.findByText('Saved.')
    expect(requestBody(requests.find(({ init }) => init?.method === 'PUT')?.init)).toEqual({
      submission: 'First answer',
    })

    await user.clear(textarea)
    await user.click(screen.getByRole('button', { name: 'Save' }))
    await waitFor(() => expect(textarea).toHaveValue(''))
    expect(confirmed.submission).toBeNull()

    await user.type(textarea, '   ')
    await user.click(screen.getByRole('button', { name: 'Save' }))
    await waitFor(() => expect(confirmed.submission).toBeNull())
    expect(requests.filter(({ init }) => init?.method === 'PUT')).toHaveLength(3)
  })

  it('sends an optional initial submission through the typed API client', async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse(draft('new-id', 'Initial'), 201))
    vi.stubGlobal('fetch', fetchMock)

    await assessmentApi.createAttempt('activity-id', 'definition-id', 'Initial')

    expect(fetchMock).toHaveBeenCalledOnce()
    expect(String(fetchMock.mock.calls[0][0])).toContain(
      '/activities/activity-id/assessment-definitions/definition-id/attempts',
    )
    expect(requestBody(fetchMock.mock.calls[0][1])).toEqual({ submission: 'Initial' })
  })

  it('validates submission, confirms the irreversible action, and renders SUBMITTED read-only', async () => {
    let current = draft()
    let submitRequests = 0
    vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input)
      const auth = authResponse(url)
      if (auth) return auth
      if (url.endsWith('/submit')) {
        submitRequests += 1
        current = submitted()
      }
      return jsonResponse(current)
    }))
    const confirm = vi.spyOn(window, 'confirm').mockReturnValue(false)
    const user = userEvent.setup()
    renderRoute(attemptRoute())
    const textarea = await screen.findByRole('textbox', { name: 'Submission' })

    await user.type(textarea, '   ')
    await user.click(screen.getByRole('button', { name: 'Submit' }))
    expect(await screen.findByText('Submission is required')).toBeInTheDocument()
    expect(submitRequests).toBe(0)

    await user.clear(textarea)
    await user.type(textarea, 'Ready answer')
    await user.click(screen.getByRole('button', { name: 'Submit' }))
    expect(confirm).toHaveBeenCalledOnce()
    expect(submitRequests).toBe(0)

    confirm.mockReturnValue(true)
    await user.click(screen.getByRole('button', { name: 'Submit' }))
    expect(await screen.findByText('SUBMITTED')).toBeInTheDocument()
    expect(screen.getByText('Submitted answer')).toBeInTheDocument()
    expect(screen.queryByRole('textbox')).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Save' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Submit' })).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Create another Attempt' })).toBeInTheDocument()
  })

  it('creates another DRAFT from SUBMITTED with route Activity context', async () => {
    let current = submitted()
    const requests: string[] = []
    vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input)
      requests.push(url)
      const auth = authResponse(url)
      if (auth) return auth
      if (url.includes('/assessment-definitions/') && init?.method === 'POST') {
        current = draft('new-attempt')
        return jsonResponse(current, 201)
      }
      return jsonResponse(current)
    }))
    const user = userEvent.setup()
    const { router } = renderRoute(attemptRoute())

    await user.click(await screen.findByRole('button', { name: 'Create another Attempt' }))

    expect(router.state.location.pathname).toBe(attemptRoute('new-attempt'))
    expect(requests.some((url) =>
      url.endsWith('/activities/activity-id/assessment-definitions/definition-id/attempts'),
    )).toBe(true)
  })

  it('leaves route Activity and Definition binding authoritative to the backend', async () => {
    vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input)
      const auth = authResponse(url)
      if (auth) return auth
      if (url.includes('/assessment-definitions/') && init?.method === 'POST') {
        return jsonResponse({ detail: 'Assessment Attempt not found' }, 404)
      }
      return jsonResponse(submitted())
    }))
    const user = userEvent.setup()
    const { router } = renderRoute(
      '/student/activities/mismatched-activity/assessment-attempts/attempt-id',
    )

    await user.click(await screen.findByRole('button', { name: 'Create another Attempt' }))

    expect(await screen.findByRole('alert')).toHaveTextContent('Assessment unavailable / not found')
    expect(router.state.location.pathname).toBe(
      '/student/activities/mismatched-activity/assessment-attempts/attempt-id',
    )
  })

  it('renders REVIEWED Result and creates another DRAFT without mutating the Result', async () => {
    let current = reviewed('Good work')
    const requests: string[] = []
    vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input)
      requests.push(url)
      const auth = authResponse(url)
      if (auth) return auth
      if (url.includes('/assessment-definitions/') && init?.method === 'POST') {
        current = draft('reviewed-new-attempt')
        return jsonResponse(current, 201)
      }
      return jsonResponse(current)
    }))
    const user = userEvent.setup()
    const { router } = renderRoute(attemptRoute())

    expect(await screen.findByText('REVIEWED')).toBeInTheDocument()
    expect(screen.getByText('Submitted answer')).toBeInTheDocument()
    expect(screen.getByText('8 / 10')).toBeInTheDocument()
    expect(screen.getByText('Good work')).toBeInTheDocument()
    expect(screen.queryByRole('textbox')).not.toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Create another Attempt' }))

    expect(router.state.location.pathname).toBe(attemptRoute('reviewed-new-attempt'))
    expect(requests.some((url) =>
      url.endsWith('/activities/activity-id/assessment-definitions/definition-id/attempts'),
    )).toBe(true)
  })

  it('omits the feedback section when reviewed feedback is null', async () => {
    vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL) =>
      authResponse(String(input)) ?? jsonResponse(reviewed(null)),
    ))
    const { container } = renderRoute(attemptRoute())

    expect(await screen.findByText('8 / 10')).toBeInTheDocument()
    expect(container.querySelector('.assessment-feedback')).toBeNull()
    expect(screen.queryByText('No feedback provided')).not.toBeInTheDocument()
  })

  it('shows a retryable error for REVIEWED without Result and requests no partial snapshot', async () => {
    let detailRequests = 0
    vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input)
      const auth = authResponse(url)
      if (auth) return auth
      detailRequests += 1
      return jsonResponse({ detail: 'Internal Server Error' }, 500)
    }))
    const user = userEvent.setup()
    renderRoute(attemptRoute())

    expect(await screen.findByRole('alert')).toHaveTextContent('Assessment error')
    expect(screen.queryByText('Submission')).not.toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Retry' }))
    await waitFor(() => expect(detailRequests).toBe(2))
  })

  it.each([
    [401, 'Authentication required'],
    [403, 'Assessment access denied'],
    [404, 'Assessment unavailable / not found'],
    [500, 'Assessment error'],
  ])('maps GET %s to its approved error state', async (status, message) => {
    vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL) =>
      authResponse(String(input)) ?? jsonResponse({ detail: message }, status),
    ))
    renderRoute(attemptRoute())

    expect(await screen.findByRole('alert')).toHaveTextContent(message)
  })

  it('shows lifecycle conflict and server validation mutation errors', async () => {
    let putStatus = 409
    vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input)
      const auth = authResponse(url)
      if (auth) return auth
      if (init?.method === 'PUT') {
        return jsonResponse(
          { detail: putStatus === 409 ? 'Conflict' : 'Invalid submission' },
          putStatus,
        )
      }
      if (url.endsWith('/submit')) return jsonResponse({ detail: 'Invalid submission' }, 422)
      return jsonResponse(draft('attempt-id', 'answer'))
    }))
    vi.spyOn(window, 'confirm').mockReturnValue(true)
    const user = userEvent.setup()
    renderRoute(attemptRoute())

    await user.click(await screen.findByRole('button', { name: 'Save' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('Assessment lifecycle conflict')
    putStatus = 422
    await user.click(screen.getByRole('button', { name: 'Save' }))
    expect(await screen.findByText('Invalid submission')).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Submit' }))
    expect(await screen.findByText('Invalid submission')).toBeInTheDocument()
  })

  it.each([
    ['submitted', submitted()],
    ['reviewed', reviewed()],
  ])('opens historical %s detail directly without ActivityProgress or Course access', async (_, value) => {
    const requests: string[] = []
    vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input)
      requests.push(url)
      return authResponse(url) ?? jsonResponse(value)
    }))
    renderRoute(attemptRoute())

    expect(await screen.findByText(value.status.toUpperCase())).toBeInTheDocument()
    expect(requests).toEqual([
      expect.stringContaining('/api/v1/auth/me'),
      expect.stringContaining('/api/v1/student/assessment-attempts/attempt-id'),
    ])
    expect(screen.queryByText(/history/i)).not.toBeInTheDocument()
    expect(requests.some((url) => url.includes('/progress'))).toBe(false)
    expect(requests.some((url) => url.includes('/courses/'))).toBe(false)
  })
})
