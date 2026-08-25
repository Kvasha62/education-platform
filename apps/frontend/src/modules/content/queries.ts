export const contentKeys = {
  detail: (contentId: string) => ['content', contentId] as const,
  body: (contentId: string) => ['content', contentId, 'body'] as const,
}
