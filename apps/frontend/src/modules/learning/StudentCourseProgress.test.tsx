import { QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { createQueryClient } from '../../app/providers'
import { StudentCourseProgress } from './StudentCourseProgress'

const endpoint = '/api/v1/student/courses/course-id/progress'
const jsonResponse = (body: unknown, status = 200) =>
  new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })
const renderProgress = () =>
  render(
    <QueryClientProvider client={createQueryClient()}>
      <StudentCourseProgress courseId="course-id" />
    </QueryClientProvider>,
  )

describe('Student Course Progress UI', () => {
  afterEach(() => vi.unstubAllGlobals())

  it('shows loading without fabricated progress', () => {
    vi.stubGlobal('fetch', vi.fn(() => new Promise<Response>(() => undefined)))
    renderProgress()

    expect(screen.getByText('Loading Course Progress')).toBeInTheDocument()
    expect(screen.queryByRole('progressbar')).not.toBeInTheDocument()
    expect(screen.queryByText(/activities completed/)).not.toBeInTheDocument()
  })

  it.each([
    [0, 10, 0],
    [3, 10, 37],
    [10, 10, 100],
    [0, 0, 0],
  ])(
    'displays backend values %s / %s and %s%% without recalculation',
    async (completed, total, percent) => {
      const fetchMock = vi.fn().mockResolvedValue(
        jsonResponse({
          course_id: 'course-id',
          completed_activities: completed,
          total_activities: total,
          progress_percent: percent,
        }),
      )
      vi.stubGlobal('fetch', fetchMock)
      renderProgress()

      expect(
        await screen.findByText(`${completed} / ${total} activities completed`),
      ).toBeInTheDocument()
      expect(screen.getByText(`${percent}%`)).toBeInTheDocument()
      expect(screen.getByRole('progressbar')).toHaveAttribute('value', String(percent))
      expect(fetchMock).toHaveBeenCalledTimes(1)
      expect(fetchMock).toHaveBeenCalledWith(
        endpoint,
        expect.objectContaining({ credentials: 'include' }),
      )
    },
  )

  it.each([
    [401, 'Authentication required'],
    [503, 'Course Progress service unavailable'],
  ])('uses the existing error state for %s', async (status, detail) => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(jsonResponse({ detail }, status)))
    renderProgress()

    expect(await screen.findByRole('alert')).toHaveTextContent(detail)
    expect(screen.queryByRole('progressbar')).not.toBeInTheDocument()
  })

  it('uses the safe Course Progress not-found state without fallback requests', async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse({ detail: 'Course not found' }, 404))
    vi.stubGlobal('fetch', fetchMock)
    renderProgress()

    expect(await screen.findByRole('alert')).toHaveTextContent('Course Progress not available.')
    expect(screen.queryByRole('progressbar')).not.toBeInTheDocument()
    expect(fetchMock).toHaveBeenCalledTimes(1)
  })

  it('shows a network error without fabricated progress', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('Network unavailable')))
    renderProgress()

    expect(await screen.findByRole('alert')).toHaveTextContent('Network unavailable')
    expect(screen.queryByRole('progressbar')).not.toBeInTheDocument()
  })
})
