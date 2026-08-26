import { QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { createQueryClient } from '../../app/providers'
import { StudentCourseEnrollment } from './StudentCourseEnrollment'

const endpoint = '/api/v1/student/courses/course-id/enrollment'
const listEndpoint = '/api/v1/student/enrollments'
const enrollment = {
  id: 'enrollment-id',
  course_id: 'course-id',
  status: 'enrolled',
  created_at: '2026-08-26T00:00:00Z',
}
const jsonResponse = (body: unknown, status = 200) =>
  new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } })
const renderEnrollment = () =>
  render(
    <QueryClientProvider client={createQueryClient()}>
      <StudentCourseEnrollment courseId="course-id" />
    </QueryClientProvider>,
  )

describe('Student Course Enrollment UI', () => {
  afterEach(() => vi.unstubAllGlobals())

  it('shows enrollment loading independently of Course detail', () => {
    vi.stubGlobal('fetch', vi.fn(() => new Promise<Response>(() => undefined)))
    render(
      <div>
        <h1>Readable Published Course</h1>
        <QueryClientProvider client={createQueryClient()}>
          <StudentCourseEnrollment courseId="course-id" />
        </QueryClientProvider>
      </div>,
    )
    expect(screen.getByRole('heading', { name: 'Readable Published Course' })).toBeInTheDocument()
    expect(screen.getByText('Loading enrollment')).toBeInTheDocument()
  })

  it('shows Enroll for a non-enrolled published Course', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(jsonResponse({ items: [] })))
    renderEnrollment()
    expect(await screen.findByRole('button', { name: 'Enroll in Course' })).toBeInTheDocument()
  })

  it('shows confirmed existing enrollment without an unnecessary action', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(jsonResponse({ items: [enrollment] })))
    renderEnrollment()
    expect(await screen.findByText('Enrolled')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Enroll in Course' })).not.toBeInTheDocument()
  })

  it('enrolls and updates UI only from the confirmed server response', async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input)
      if (url.endsWith(listEndpoint)) return jsonResponse({ items: [] })
      if (url.endsWith(endpoint) && init?.method === 'POST') return jsonResponse(enrollment, 201)
      throw new Error(`Unexpected request: ${url}`)
    })
    vi.stubGlobal('fetch', fetchMock)
    const user = userEvent.setup()
    renderEnrollment()

    await user.click(await screen.findByRole('button', { name: 'Enroll in Course' }))
    expect(await screen.findByText('Enrolled')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Enroll in Course' })).not.toBeInTheDocument()
    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining(endpoint),
      expect.objectContaining({ credentials: 'include', method: 'POST' }),
    )
  })

  it('prevents duplicate requests while enrollment is pending', async () => {
    vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input)
      if (url.endsWith(listEndpoint)) return jsonResponse({ items: [] })
      return new Promise<Response>(() => undefined)
    }))
    const user = userEvent.setup()
    renderEnrollment()

    await user.click(await screen.findByRole('button', { name: 'Enroll in Course' }))
    expect(screen.getByRole('button', { name: 'Enrolling…' })).toBeDisabled()
  })

  it('does not mark Course enrolled when mutation fails', async () => {
    vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input)
      if (url.endsWith(listEndpoint)) return jsonResponse({ items: [] })
      return jsonResponse({ detail: 'Course not found' }, 404)
    }))
    const user = userEvent.setup()
    renderEnrollment()

    await user.click(await screen.findByRole('button', { name: 'Enroll in Course' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('Course not found')
    expect(screen.getByRole('button', { name: 'Enroll in Course' })).toBeEnabled()
    expect(screen.queryByText('Enrolled')).not.toBeInTheDocument()
  })

  it.each([
    [401, 'Authentication required'],
    [404, 'Enrollments not found'],
    [503, 'Enrollment service unavailable'],
  ])('shows enrollment list %s errors without gating Course UI', async (status, detail) => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(jsonResponse({ detail }, status)))
    renderEnrollment()
    expect(await screen.findByRole('alert')).toHaveTextContent(detail)
    expect(screen.queryByRole('button', { name: 'Enroll in Course' })).not.toBeInTheDocument()
  })
})
