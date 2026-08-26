import { apiRequest } from '../../shared/api'
import type { ContentBody } from './body'

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

export interface ContentPage {
  items: Content[]
  page: number
  page_size: number
  has_next: boolean
}

export const contentApi = {
  list: (page = 1, pageSize = 20) =>
    apiRequest<ContentPage>(`/api/v1/contents?page=${page}&page_size=${pageSize}`),
  get: (contentId: string) => apiRequest<Content>(`/api/v1/contents/${contentId}`),
  getBody: (contentId: string) =>
    apiRequest<ContentBody>(`/api/v1/contents/${contentId}/body`),
  replaceBody: (contentId: string, body: ContentBody) =>
    apiRequest<ContentBody>(`/api/v1/contents/${contentId}/body`, {
      method: 'PUT',
      body,
    }),
  publish: (contentId: string) =>
    apiRequest<Content>(`/api/v1/contents/${contentId}/publish`, { method: 'POST' }),
}
