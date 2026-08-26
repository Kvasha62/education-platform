import { describe, expect, it } from 'vitest'
import { findNextActivity } from './activityProgression'
import type { StudentActivity, StudentCourse } from './studentCourseApi'

const activity = (id: string, position: number): StudentActivity => ({
  id,
  title: id,
  type: 'lecture',
  position,
  contents: [],
})

const course = (sections: StudentCourse['sections']): StudentCourse => ({
  id: 'course-id',
  title: 'Course',
  sections,
})

const section = (
  id: string,
  position: number,
  units: StudentCourse['sections'][number]['units'],
) => ({ id, title: id, position, units })

const unit = (id: string, position: number, activities: StudentActivity[]) => ({
  id,
  title: id,
  position,
  activities,
})

describe('Student Activity progression order', () => {
  it('selects the next Activity inside the same Unit without using array order', () => {
    const value = course([
      section('section', 0, [unit('unit', 0, [activity('third', 2), activity('first', 0), activity('second', 1)])]),
    ])
    expect(findNextActivity(value, 'first')?.id).toBe('second')
  })

  it('crosses a Learning Unit boundary', () => {
    const value = course([
      section('section', 0, [
        unit('later-unit', 1, [activity('next', 0)]),
        unit('current-unit', 0, [activity('current', 0)]),
      ]),
    ])
    expect(findNextActivity(value, 'current')?.id).toBe('next')
  })

  it('crosses a Section boundary', () => {
    const value = course([
      section('later-section', 1, [unit('unit-b', 0, [activity('next', 0)])]),
      section('current-section', 0, [unit('unit-a', 0, [activity('current', 0)])]),
    ])
    expect(findNextActivity(value, 'current')?.id).toBe('next')
  })

  it('uses Activity id ascending as the deterministic position tie-breaker', () => {
    const value = course([
      section('section', 0, [unit('unit', 0, [activity('activity-c', 0), activity('activity-a', 0), activity('activity-b', 0)])]),
    ])
    expect(findNextActivity(value, 'activity-a')?.id).toBe('activity-b')
  })

  it('returns no next Activity for the last Activity', () => {
    const value = course([section('section', 0, [unit('unit', 0, [activity('last', 0)])])])
    expect(findNextActivity(value, 'last')).toBeNull()
  })
})
