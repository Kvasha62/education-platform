import { QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import { createMemoryRouter, RouterProvider } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { createQueryClient } from '../../app/providers'
import { routes } from '../../app/router'
import type { StudentActivity, StudentCourse } from './studentCourseApi'

const identity = {
  id: 'identity-id',
  email: 'student@example.com',
  status: 'active',
  created_at: '2026-08-26T00:00:00Z',
  updated_at: '2026-08-26T00:00:00Z',
}
const activity = (id: string, title: string, position: number): StudentActivity => ({
  id,
  title,
  type: 'lecture',
  position,
  contents: [],
  assessment_definition_id: null,
})
const course = (activities: StudentActivity[]): StudentCourse => ({
  id: 'course-id',
  title: 'Programming',
  sections: [
    {
      id: 'section-id',
      title: 'Section',
      position: 0,
      units: [{ id: 'unit-id', title: 'Unit', position: 0, activities }],
    },
  ],
})
const jsonResponse = (body: unknown, status = 200) =>
  new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })

const renderCompletedActivity = (courseResponse: StudentCourse, activityId: string) => {
  vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL) => {
    const url = String(input)
    if (url.endsWith('/api/v1/auth/me')) return jsonResponse(identity)
    if (url.endsWith('/api/v1/student/courses/course-id')) return jsonResponse(courseResponse)
    if (url.endsWith(`/api/v1/student/activities/${activityId}/progress`)) {
      return jsonResponse({ activity_id: activityId, status: 'completed' })
    }
    throw new Error(`Unexpected request: ${url}`)
  }))
  const router = createMemoryRouter(routes, {
    initialEntries: [`/app/student/courses/course-id/activities/${activityId}`],
  })
  render(
    <QueryClientProvider client={createQueryClient()}>
      <RouterProvider router={router} />
    </QueryClientProvider>,
  )
}

describe('already completed Student Activity progression', () => {
  afterEach(() => vi.unstubAllGlobals())

  it('shows the next Activity through the existing Student Activity route', async () => {
    renderCompletedActivity(
      course([
        activity('current-id', 'Current Activity', 0),
        activity('next-id', 'Next lesson', 1),
      ]),
      'current-id',
    )

    expect(await screen.findByText('Completed')).toBeInTheDocument()
    expect(screen.getByText('Next Activity: Next lesson')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Next Activity' })).toHaveAttribute(
      'href',
      '/app/student/courses/course-id/activities/next-id',
    )
  })

  it('shows the last Activity message without claiming Course completion', async () => {
    renderCompletedActivity(course([activity('last-id', 'Last Activity', 0)]), 'last-id')

    expect(await screen.findByText('Completed')).toBeInTheDocument()
    expect(screen.getByText("You've completed the last Activity.")).toBeInTheDocument()
    expect(screen.queryByRole('link', { name: 'Next Activity' })).not.toBeInTheDocument()
    expect(screen.queryByText(/Course completed/i)).not.toBeInTheDocument()
  })
})
