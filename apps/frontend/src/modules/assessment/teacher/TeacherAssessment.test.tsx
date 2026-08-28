import { QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { createMemoryRouter, RouterProvider } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { createQueryClient } from '../../../app/providers'
import { routes } from '../../../app/router'
import type {
  TeacherAssessmentAttemptDetail,
  TeacherAssessmentResult,
} from './api'
import { TeacherAssessmentReviewEntry } from './TeacherAssessmentReviewEntry'

const identity = {
  id: 'identity-id',
  email: 'teacher@example.com',
  status: 'active',
  created_at: '2026-08-26T00:00:00Z',
  updated_at: '2026-08-26T00:00:00Z',
}

const teacherSpaceId = 'space-1'
const activityId = 'activity-1'
const attemptId = 'attempt-1'
const resultId = 'result-1'

const activityWithAssessment = {
  id: activityId,
  learning_unit_id: 'unit-1',
  title: 'Assessment Activity',
  type: 'homework',
  position: 0,
  created_at: '2026-08-26T00:00:00Z',
  updated_at: '2026-08-26T00:00:00Z',
  assessment_definition_id: 'assessment-def-1',
}

const activityWithoutAssessment = {
  ...activityWithAssessment,
  assessment_definition_id: null,
  title: 'Reading Activity',
  type: 'lecture',
}

const result = (score: number, feedback: string | null): TeacherAssessmentResult => ({
  id: resultId,
  attempt_id: attemptId,
  score,
  max_score: 10,
  feedback,
})

const submittedItem = {
  id: attemptId,
  student_id: 'student-1',
  status: 'submitted' as const,
  assessment_definition_id: 'assessment-def-1',
  activity_id: activityId,
  result: null,
}

const submittedDetail: TeacherAssessmentAttemptDetail = {
  ...submittedItem,
  submission: 'Student answer',
}

const reviewedItem = {
  ...submittedItem,
  id: 'attempt-2',
  student_id: 'student-2',
  status: 'reviewed' as const,
  result: result(8, 'Good work'),
}

const reviewedDetail: TeacherAssessmentAttemptDetail = {
  ...submittedDetail,
  status: 'reviewed',
  result: result(8, 'Good work'),
}

const queueListUrl = () =>
  `/api/v1/teacher-spaces/${teacherSpaceId}/activities/${activityId}/assessment-attempts`

const asUrl = (url: string) => new URL(url, 'http://localhost')

const detailUrl = () => `${queueListUrl()}/${attemptId}`

const queueRoute = () =>
  `/app/teacher-spaces/${teacherSpaceId}/activities/${activityId}/assessment-review`

const detailRoute = () => `${queueRoute()}/${attemptId}`

const activitiesUrl = () =>
  `/api/v1/teacher-spaces/${teacherSpaceId}/environment/courses/course-1/sections/section-1/units/unit-1/activities`

const activityRoute = () =>
  `/app/teacher-spaces/${teacherSpaceId}/environment/courses/course-1/sections/section-1/learning-units/unit-1/activities`

const jsonResponse = (body: unknown, status = 200) =>
  new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })

const requestBody = (init?: RequestInit) =>
  init?.body ? (JSON.parse(String(init.body)) as unknown) : undefined

const renderRoute = (entry: string) => {
  const router = createMemoryRouter(routes, { initialEntries: [entry] })
  const rendered = render(
    <QueryClientProvider client={createQueryClient()}>
      <RouterProvider router={router} />
    </QueryClientProvider>,
  )
  return { ...rendered, router }
}

const renderEntry = (backTo?: string) => {
  const router = createMemoryRouter(
    [
      {
        path: '/',
        element: (
          <TeacherAssessmentReviewEntry
            teacherSpaceId={teacherSpaceId}
            activityId={activityId}
            backTo={backTo}
          />
        ),
      },
    ],
    { initialEntries: ['/'] },
  )
  return render(<RouterProvider router={router} />)
}

const authResponse = (url: string) =>
  url.endsWith('/api/v1/auth/me') ? jsonResponse(identity) : null

describe('Teacher Assessment Review UI', () => {
  afterEach(() => {
    vi.restoreAllMocks()
    vi.unstubAllGlobals()
  })

  it('does not render the Assessment Review CTA for Activities without a definition', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async (input: RequestInfo | URL) => {
        const url = String(input)
        return (
          authResponse(url) ??
          (url.endsWith(activitiesUrl()) ? jsonResponse([activityWithoutAssessment]) : jsonResponse([]))
        )
      }),
    )
    renderRoute(activityRoute())

    expect(await screen.findByDisplayValue('Reading Activity')).toBeInTheDocument()
    expect(screen.queryByRole('link', { name: 'Assessment review' })).not.toBeInTheDocument()
  })

  it('renders the Assessment Review CTA for an assessment-bearing Activity and navigates', async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input)
      if (url.endsWith('/api/v1/auth/me')) return jsonResponse(identity)
      if (url.endsWith(activitiesUrl())) return jsonResponse([activityWithAssessment])
      if (url.startsWith(queueListUrl())) {
        return jsonResponse({ items: [], page: 1, page_size: 20, has_next: false })
      }
      throw new Error(`Unexpected request: ${url}`)
    })
    vi.stubGlobal('fetch', fetchMock)
    const user = userEvent.setup()
    const { router } = renderRoute(activityRoute())

    const cta = await screen.findByRole('link', { name: 'Assessment review' })
    expect(cta.getAttribute('href')).toContain(queueRoute())
    expect(cta.getAttribute('href')).toContain('backTo=')
    await user.click(cta)

    expect(router.state.location.pathname).toBe(queueRoute())
    expect(await screen.findByRole('heading', { name: 'Assessment review' })).toBeInTheDocument()
    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining(`${queueListUrl()}?`),
      expect.objectContaining({ credentials: 'include' }),
    )
  })

  it('preserves a valid relative backTo and rejects absolute/protocol-relative URLs on the entry', () => {
    const validRelative = '/app/teacher-spaces/space-1/environment/courses/course-1'

    const { unmount: unmountValid } = renderEntry(validRelative)
    const validLink = screen.getByRole('link', { name: 'Assessment review' })
    expect(validLink.getAttribute('href')).toContain(`backTo=${encodeURIComponent(validRelative)}`)
    expect(asUrl(validLink.getAttribute('href') ?? '').searchParams.get('backTo')).toBe(validRelative)
    unmountValid()

    const { unmount: unmountAbsolute } = renderEntry('https://evil.example/redirect')
    const absoluteLink = screen.getByRole('link', { name: 'Assessment review' })
    expect(absoluteLink.getAttribute('href')).toBe(queueRoute())
    expect(absoluteLink.getAttribute('href')).not.toContain('backTo=')
    unmountAbsolute()

    const { unmount: unmountProtocolRelative } = renderEntry('//evil.example/redirect')
    const protocolRelativeLink = screen.getByRole('link', { name: 'Assessment review' })
    expect(protocolRelativeLink.getAttribute('href')).toBe(queueRoute())
    expect(protocolRelativeLink.getAttribute('href')).not.toContain('backTo=')
    unmountProtocolRelative()
  })

  it('never uses an external or protocol-relative backTo as a navigation target in the queue', async () => {
    const emptyQueueFetch = () =>
      vi.fn(async (input: RequestInfo | URL) =>
        authResponse(String(input)) ?? jsonResponse({ items: [], page: 1, page_size: 20, has_next: false }),
      )

    vi.stubGlobal('fetch', emptyQueueFetch())
    const absoluteView = renderRoute(`${queueRoute()}?backTo=${encodeURIComponent('https://evil.example/redirect')}`)
    expect(await screen.findByRole('heading', { name: 'Assessment review' })).toBeInTheDocument()
    expect(screen.queryByRole('link', { name: 'Back to Activity' })).not.toBeInTheDocument()
    absoluteView.unmount()

    vi.unstubAllGlobals()
    vi.stubGlobal('fetch', emptyQueueFetch())
    const protocolRelativeView = renderRoute(`${queueRoute()}?backTo=${encodeURIComponent('//evil.example/redirect')}`)
    expect(await screen.findByRole('heading', { name: 'Assessment review' })).toBeInTheDocument()
    expect(screen.queryByRole('link', { name: 'Back to Activity' })).not.toBeInTheDocument()
    protocolRelativeView.unmount()

    vi.unstubAllGlobals()
    vi.stubGlobal('fetch', emptyQueueFetch())
    const validRelative = '/app/teacher-spaces/space-1/environment/courses/course-1'
    const validView = renderRoute(`${queueRoute()}?backTo=${encodeURIComponent(validRelative)}`)
    expect(
      await screen.findByRole('link', { name: 'Back to Activity' }),
    ).toHaveAttribute('href', validRelative)
    validView.unmount()
  })

  it('loads, renders, and paginates the Review Queue with API params', async () => {
    const requests: Array<{ url: string; init?: RequestInit }> = []
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input)
      requests.push({ url, init })
      const auth = authResponse(url)
      if (auth) return auth
      if (asUrl(url).pathname === queueListUrl()) {
        const search = asUrl(url).searchParams
        if (search.get('status') === 'reviewed') {
          return jsonResponse({
            items: [
              { ...reviewedItem, id: 'attempt-2', student_id: 'student-2' },
            ],
            page: 2,
            page_size: 20,
            has_next: false,
          })
        }
        if (search.get('page') === '2') {
          return jsonResponse({
            items: [{ ...submittedItem, id: 'attempt-2', student_id: 'student-2' }],
            page: 2,
            page_size: 20,
            has_next: false,
          })
        }
        return jsonResponse({
          items: [submittedItem, reviewedItem],
          page: 1,
          page_size: 20,
          has_next: true,
        })
      }
      throw new Error(`Unexpected request: ${url}`)
    })
    vi.stubGlobal('fetch', fetchMock)
    const user = userEvent.setup()
    renderRoute(queueRoute())

    expect(await screen.findByText('SUBMITTED')).toBeInTheDocument()
    expect(screen.getByText('REVIEWED')).toBeInTheDocument()
    expect(screen.getByText('Student reference: student-1')).toBeInTheDocument()

    const firstQueueCall = requests.find(({ url }) => url.startsWith(queueListUrl()))
    expect(String(firstQueueCall?.url)).toContain('page=1')
    expect(String(firstQueueCall?.url)).toContain('page_size=20')

    await user.click(screen.getByRole('button', { name: 'Submitted' }))
    expect(await screen.findByText('Student reference: student-2')).toBeInTheDocument()
    const statusCall = requests.find(
      ({ url }) => asUrl(url).searchParams.get('status') === 'submitted',
    )
    expect(statusCall).toBeDefined()
    expect(asUrl(String(statusCall?.url)).searchParams.get('status')).toBe('submitted')

    await user.click(screen.getByRole('button', { name: 'All' }))
    await user.click(screen.getByRole('button', { name: 'Next' }))
    expect(await screen.findByText('Page 2')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Next' })).toBeDisabled()
    await user.click(screen.getByRole('button', { name: 'Previous' }))
    expect(await screen.findByText('Page 1')).toBeInTheDocument()
  })

  it('shows an empty state and maps Review Queue errors', async () => {
    const emptyFetch = vi.fn(async (input: RequestInfo | URL) =>
      authResponse(String(input)) ?? jsonResponse({ items: [], page: 1, page_size: 20, has_next: false }),
    )
    vi.stubGlobal('fetch', emptyFetch)
    renderRoute(queueRoute())
    expect(await screen.findByText('No attempts to review')).toBeInTheDocument()

    vi.unstubAllGlobals()
    const errorFetch = vi.fn(async (input: RequestInfo | URL) =>
      authResponse(String(input)) ?? jsonResponse({ detail: 'Assessment access denied' }, 403),
    )
    vi.stubGlobal('fetch', errorFetch)
    renderRoute(queueRoute())
    expect(await screen.findByRole('alert')).toHaveTextContent('Assessment access denied')
  })

  it('loads and renders Attempt Detail with a read-only submission and Result', async () => {
    let current: TeacherAssessmentAttemptDetail = reviewedDetail
    const requests: string[] = []
    vi.stubGlobal(
      'fetch',
      vi.fn(async (input: RequestInfo | URL) => {
        const url = String(input)
        requests.push(url)
        return authResponse(url) ?? jsonResponse(current)
      }),
    )
    renderRoute(detailRoute())

    expect(await screen.findByText('REVIEWED')).toBeInTheDocument()
    expect(screen.getByText('Student answer')).toBeInTheDocument()
    expect(screen.getByText('8 / 10')).toBeInTheDocument()
    expect(screen.getByText('Good work')).toBeInTheDocument()
    expect(screen.queryByRole('textbox')).not.toBeInTheDocument()
    expect(requests).toEqual([
      expect.stringContaining('/api/v1/auth/me'),
      expect.stringContaining(detailUrl()),
    ])
  })

  it('shows loading and maps Attempt Detail errors', async () => {
    let resolveDetail: ((response: Response) => void) | undefined
    vi.stubGlobal(
      'fetch',
      vi.fn(async (input: RequestInfo | URL) => {
        const url = String(input)
        if (authResponse(url)) return authResponse(url)
        return new Promise<Response>((resolve) => {
          resolveDetail = resolve
        })
      }),
    )
    renderRoute(detailRoute())
    expect(await screen.findByText('Loading Assessment Attempt')).toBeInTheDocument()
    resolveDetail?.(jsonResponse(submittedDetail))
    expect(await screen.findByText('SUBMITTED')).toBeInTheDocument()

    vi.unstubAllGlobals()
    vi.stubGlobal(
      'fetch',
      vi.fn(async (input: RequestInfo | URL) =>
        authResponse(String(input)) ?? jsonResponse({ detail: 'Assessment resource not found' }, 404),
      ),
    )
    renderRoute(detailRoute())
    expect(await screen.findByRole('alert')).toHaveTextContent('Assessment resource not found')
  })

  it('only offers Review for SUBMITTED and disables it in-flight; success shows REVIEWED Result', async () => {
    let current: TeacherAssessmentAttemptDetail = submittedDetail
    let reviewResolve: ((response: Response) => void) | undefined
    const requests: Array<{ url: string; init?: RequestInit }> = []
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input)
      requests.push({ url, init })
      const auth = authResponse(url)
      if (auth) return auth
      if (url.endsWith('/review')) {
        return new Promise<Response>((resolve) => {
          reviewResolve = resolve
        })
      }
      return jsonResponse(current)
    })
    vi.stubGlobal('fetch', fetchMock)
    const user = userEvent.setup()
    renderRoute(detailRoute())

    expect(await screen.findByText('SUBMITTED')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Review' })).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Edit' })).not.toBeInTheDocument()

    await user.type(screen.getByLabelText('Score'), '8')
    await user.type(screen.getByLabelText('Max score'), '10')
    await user.type(screen.getByLabelText('Feedback'), 'Good work')
    await user.click(screen.getByRole('button', { name: 'Review' }))

    await waitFor(() => expect(reviewResolve).toBeDefined())
    expect(screen.getByRole('button', { name: 'Reviewing…' })).toBeDisabled()

    current = { ...current, status: 'reviewed', result: result(8, 'Good work') }
    reviewResolve?.(jsonResponse(result(8, 'Good work')))

    expect(await screen.findByText('REVIEWED')).toBeInTheDocument()
    expect(screen.getByText('8 / 10')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Review' })).not.toBeInTheDocument()
    const reviewCall = requests.find(({ url }) => url.endsWith('/review'))
    expect(reviewCall?.init?.method).toBe('POST')
    expect(requestBody(reviewCall?.init)).toEqual({
      score: 8,
      max_score: 10,
      feedback: 'Good work',
    })
  })

  it('shows a mutation error and keeps the Review UI usable', async () => {
    let current: TeacherAssessmentAttemptDetail = submittedDetail
    vi.stubGlobal(
      'fetch',
      vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
        const url = String(input)
        const auth = authResponse(url)
        if (auth) return auth
        if (init?.method === 'POST' && url.endsWith('/review')) {
          return jsonResponse({ detail: 'Invalid assessment state' }, 409)
        }
        return jsonResponse(current)
      }),
    )
    const user = userEvent.setup()
    renderRoute(detailRoute())

    await user.type(await screen.findByLabelText('Score'), '8')
    await user.type(screen.getByLabelText('Max score'), '10')
    await user.click(screen.getByRole('button', { name: 'Review' }))

    expect(await screen.findByRole('alert')).toHaveTextContent('Invalid assessment state')
    expect(screen.getByRole('button', { name: 'Review' })).toBeEnabled()
    expect(screen.getByText('SUBMITTED')).toBeInTheDocument()
  })

  it('offers Correction for REVIEWED, uses the existing result_id, and shows the updated Result', async () => {
    let current: TeacherAssessmentAttemptDetail = reviewedDetail
    vi.stubGlobal(
      'fetch',
      vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
        const url = String(input)
        const auth = authResponse(url)
        if (auth) return auth
        if (init?.method === 'POST' && url.endsWith('/correction')) {
          const body = requestBody(init) as { result_id: string; score: number; feedback: string }
          expect(body.result_id).toBe(resultId)
          current = {
            ...current,
            result: result(body.score, body.feedback),
          }
          return jsonResponse(current.result)
        }
        return jsonResponse(current)
      }),
    )
    const user = userEvent.setup()
    renderRoute(detailRoute())

    const edit = await screen.findByRole('button', { name: 'Edit' })
    expect(screen.queryByRole('button', { name: 'Review' })).not.toBeInTheDocument()
    await user.click(edit)

    expect(screen.getByText('Max score: 10')).toBeInTheDocument()
    await user.type(screen.getByLabelText('Score'), '9')
    await user.type(screen.getByLabelText('Feedback'), 'Improved')
    await user.click(screen.getByRole('button', { name: 'Save' }))

    expect(await screen.findByText('9 / 10')).toBeInTheDocument()
    expect(screen.getByText('Improved')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Save' })).not.toBeInTheDocument()
  })

  it('shows a Correction mutation error and keeps the editing form available', async () => {
    let current: TeacherAssessmentAttemptDetail = reviewedDetail
    vi.stubGlobal(
      'fetch',
      vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
        const url = String(input)
        const auth = authResponse(url)
        if (auth) return auth
        if (init?.method === 'POST' && url.endsWith('/correction')) {
          return jsonResponse({ detail: 'Invalid score or feedback' }, 422)
        }
        return jsonResponse(current)
      }),
    )
    const user = userEvent.setup()
    renderRoute(detailRoute())

    await user.click(await screen.findByRole('button', { name: 'Edit' }))
    await user.type(screen.getByLabelText('Score'), '9')
    await user.click(screen.getByRole('button', { name: 'Save' }))

    expect(await screen.findByText('Invalid score or feedback')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Save' })).toBeEnabled()
  })

  it('cancels Correction and returns to the current Result without mutation', async () => {
    let current: TeacherAssessmentAttemptDetail = reviewedDetail
    vi.stubGlobal(
      'fetch',
      vi.fn(async (input: RequestInfo | URL) =>
        authResponse(String(input)) ?? jsonResponse(current),
      ),
    )
    const user = userEvent.setup()
    renderRoute(detailRoute())

    await user.click(await screen.findByRole('button', { name: 'Edit' }))
    expect(screen.getByRole('button', { name: 'Cancel' })).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Cancel' }))

    expect(screen.getByText('8 / 10')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Cancel' })).not.toBeInTheDocument()
  })

  it('runs Activity → CTA → Queue → Detail → Review → Correction as one integration flow', async () => {
    let current: TeacherAssessmentAttemptDetail = submittedDetail
    const requests: Array<{ url: string; init?: RequestInit }> = []
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input)
      requests.push({ url, init })
      const auth = authResponse(url)
      if (auth) return auth
      if (url.endsWith(activitiesUrl())) return jsonResponse([activityWithAssessment])
      if (asUrl(url).pathname === queueListUrl()) {
        return jsonResponse({
          items: [submittedItem],
          page: 1,
          page_size: 20,
          has_next: false,
        })
      }
      if (init?.method === 'POST' && url.endsWith('/review')) {
        current = { ...submittedDetail, status: 'reviewed', result: result(8, 'Good work') }
        return jsonResponse(current.result)
      }
      if (init?.method === 'POST' && url.endsWith('/correction')) {
        const body = requestBody(init) as { score: number; feedback: string }
        current = { ...current, result: result(body.score, body.feedback) }
        return jsonResponse(current.result)
      }
      if (url.endsWith(detailUrl())) return jsonResponse(current)
      throw new Error(`Unexpected request: ${url}`)
    })
    vi.stubGlobal('fetch', fetchMock)
    const user = userEvent.setup()
    const { router } = renderRoute(activityRoute())

    await user.click(await screen.findByRole('link', { name: 'Assessment review' }))
    expect(router.state.location.pathname).toBe(queueRoute())
    await user.click(await screen.findByRole('link', { name: 'Open attempt' }))

    expect(router.state.location.pathname).toBe(detailRoute())
    expect(await screen.findByText('Student answer')).toBeInTheDocument()

    await user.type(screen.getByLabelText('Score'), '8')
    await user.type(screen.getByLabelText('Max score'), '10')
    await user.type(screen.getByLabelText('Feedback'), 'Good work')
    await user.click(screen.getByRole('button', { name: 'Review' }))
    expect(await screen.findByText('8 / 10')).toBeInTheDocument()
    expect(screen.getByText('Good work')).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: 'Edit' }))
    await user.type(screen.getByLabelText('Score'), '9')
    await user.type(screen.getByLabelText('Feedback'), 'Improved')
    await user.click(screen.getByRole('button', { name: 'Save' }))
    expect(await screen.findByText('9 / 10')).toBeInTheDocument()
    expect(screen.getByText('Improved')).toBeInTheDocument()

    const reviewCall = requests.find(({ url }) => url.endsWith('/review'))
    const correctionCall = requests.find(({ url }) => url.endsWith('/correction'))
    expect(reviewCall?.init?.method).toBe('POST')
    expect(requestBody(reviewCall?.init)).toEqual({ score: 8, max_score: 10, feedback: 'Good work' })
    expect(correctionCall?.init?.method).toBe('POST')
    expect(requestBody(correctionCall?.init)).toEqual({
      result_id: resultId,
      score: 9,
      feedback: 'Improved',
    })
  })
})
