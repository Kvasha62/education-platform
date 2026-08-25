import { apiRequest } from '../../shared/api'

export type ContentType = 'article' | 'resource'
export type ContentStatus = 'draft' | 'published'

export interface Content {
  id: string
  type: ContentType
  title: string
  status: ContentStatus
  created_at: string
  updated_at: string
}

export const contentApi = {
  list: () => apiRequest<Content[]>('/api/v1/contents'),
}
