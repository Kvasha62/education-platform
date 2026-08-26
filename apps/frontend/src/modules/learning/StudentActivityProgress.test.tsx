import { QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { createQueryClient } from '../../app/providers'
import { StudentActivityProgress } from './StudentActivityProgress'

const endpoint = '/api/v1/student/activities/activity-id/progress'
const jsonResponse = (body: unknown, status = 200) =>
  new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } })
const renderProgress = (nextActivity?: { id: string; title: string } | null) =>
  render(
    <MemoryRouter>
      <QueryClientProvider client={createQueryClient()}>
        <StudentActivityProgress
          activityId="activity-id"
          courseId="course-id"
          nextActivity={nextActivity}
        />
      </QueryClientProvider>
    </MemoryRouter>,
  )

describe('Student Activity Progress UI', () => {
  afterEach(() => vi.unstubAllGlobals())

  it('shows loading without hiding the surrounding Activity viewer', () => {
    vi.stubGlobal('fetch', vi.fn(() => new Promise<Response>(() => undefined)))
    render(
      <div>
        <h1>Visible Activity</h1>
        <QueryClientProvider client={createQueryClient()}>
          <StudentActivityProgress activityId="activity-id" />
        </QueryClientProvider>
      </div>,
    )
    expect(screen.getByRole('heading', { name: 'Visible Activity' })).toBeInTheDocument()
    expect(screen.getByText('Loading progress')).toBeInTheDocument()
  })

  it('runs the confirmed NOT_STARTED → IN_PROGRESS → COMPLETED lifecycle', async () => {
    let serverStatus: 'not_started' | 'in_progress' | 'completed' = 'not_started'
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input)
      if (url === endpoint && !init?.method && serverStatus === 'not_started') {
        return jsonResponse({ detail: 'Progress not found' }, 404)
      }
      if (url === `${endpoint}/start` && init?.method === 'POST') {
        serverStatus = 'in_progress'
        return jsonResponse({ activity_id: 'activity-id', status: serverStatus })
      }
      if (url === `${endpoint}/complete` && init?.method === 'POST') {
        serverStatus = 'completed'
        return jsonResponse({ activity_id: 'activity-id', status: serverStatus })
      }
      throw new Error(`Unexpected request: ${url}`)
    })
    vi.stubGlobal('fetch', fetchMock)
    const user = userEvent.setup()
    renderProgress()

    expect(await screen.findByText('Not started')).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Start Activity' }))
    expect(await screen.findByText('In progress')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Complete Activity' })).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Complete Activity' }))
    expect(await screen.findByText('Completed')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Start Activity' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Complete Activity' })).not.toBeInTheDocument()
    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining('/progress/start'),
      expect.objectContaining({ credentials: 'include', method: 'POST' }),
    )
  })

  it.each([
    [401, 'Authentication required'],
    [404, 'Activity not found'],
    [503, 'Progress service unavailable'],
  ])('shows GET %s as an error without inventing state', async (status, detail) => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(jsonResponse({ detail }, status)))
    renderProgress()
    expect(await screen.findByRole('alert')).toHaveTextContent(detail)
    expect(screen.queryByRole('button', { name: 'Start Activity' })).not.toBeInTheDocument()
  })

  it('does not advance NOT_STARTED when Start fails', async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input)
      if (url === endpoint && !init?.method) {
        return jsonResponse({ detail: 'Progress not found' }, 404)
      }
      return jsonResponse({ detail: 'Unable to start progress' }, 503)
    })
    vi.stubGlobal('fetch', fetchMock)
    const user = userEvent.setup()
    renderProgress()

    await user.click(await screen.findByRole('button', { name: 'Start Activity' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('Unable to start progress')
    expect(screen.getByText('Not started')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Start Activity' })).toBeEnabled()
  })

  it('shows the next Activity only after backend-confirmed completion', async () => {
    vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input)
      if (url === endpoint && !init?.method) {
        return jsonResponse({ activity_id: 'activity-id', status: 'in_progress' })
      }
      return jsonResponse({ activity_id: 'activity-id', status: 'completed' })
    }))
    const user = userEvent.setup()
    renderProgress({ id: 'next-id', title: 'Next lesson' })

    expect(await screen.findByRole('button', { name: 'Complete Activity' })).toBeInTheDocument()
    expect(screen.queryByRole('link', { name: 'Next Activity' })).not.toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Complete Activity' }))
    expect(await screen.findByRole('link', { name: 'Next Activity' })).toHaveAttribute(
      'href',
      '/app/student/courses/course-id/activities/next-id',
    )
    expect(screen.getByText('Next Activity: Next lesson')).toBeInTheDocument()
  })

  it('shows the last Activity state without claiming Course completion', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(
      jsonResponse({ activity_id: 'activity-id', status: 'completed' }),
    ))
    renderProgress(null)

    expect(await screen.findByText("You've completed the last Activity.")).toBeInTheDocument()
    expect(screen.queryByRole('link', { name: 'Next Activity' })).not.toBeInTheDocument()
    expect(screen.queryByText(/Course completed/i)).not.toBeInTheDocument()
  })

  it('does not show next Activity when Complete fails', async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input)
      if (url === endpoint && !init?.method) {
        return jsonResponse({ activity_id: 'activity-id', status: 'in_progress' })
      }
      return jsonResponse({ detail: 'Unable to complete progress' }, 503)
    })
    vi.stubGlobal('fetch', fetchMock)
    const user = userEvent.setup()
    renderProgress({ id: 'next-id', title: 'Next lesson' })

    await user.click(await screen.findByRole('button', { name: 'Complete Activity' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('Unable to complete progress')
    expect(screen.getByText('In progress')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Complete Activity' })).toBeEnabled()
    expect(screen.queryByRole('link', { name: 'Next Activity' })).not.toBeInTheDocument()
  })
})
