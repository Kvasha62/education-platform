import { apiRequest } from '../../shared/api'
import type { ContentBody, ContentType } from '../content'

export interface PublishedCourseSummary {
  id: string
  title: string
}

export interface PublishedCourseList {
  items: PublishedCourseSummary[]
}

export interface StudentContentReference {
  id: string
  type: ContentType
  status: 'published'
  available_for_student: true
}

export interface StudentActivity {
  id: string
  title: string
  type: 'lecture' | 'video' | 'homework'
  position: number
  contents: StudentContentReference[]
  assessment_definition_id: string | null
}

export interface StudentLearningUnit {
  id: string
  title: string
  position: number
  activities: StudentActivity[]
}

export interface StudentPublishedContentBody {
  id: string
  type: ContentType
  body: ContentBody
}

export interface StudentSection {
  id: string
  title: string
  position: number
  units: StudentLearningUnit[]
}

export interface StudentCourse {
  id: string
  title: string
  sections: StudentSection[]
}

export const studentCourseApi = {
  list: () => apiRequest<PublishedCourseList>('/api/v1/student/courses'),
  get: (courseId: string) =>
    apiRequest<StudentCourse>(`/api/v1/student/courses/${courseId}`),
  getContentBody: (contentId: string) =>
    apiRequest<StudentPublishedContentBody>(`/api/v1/student/contents/${contentId}/body`),
}
