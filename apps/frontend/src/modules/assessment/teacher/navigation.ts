const urlScheme = /^[a-z][a-z0-9+.-]*:/i

/**
 * Restricts a `backTo` value to a same-origin relative application path.
 *
 * Absolute URLs (`http://...`, `https://...`), protocol-relative URLs
 * (`//host/...`), backslash escapes, and non-path values are rejected so an
 * externally supplied `backTo` can never become an open redirect target.
 */
export const safeBackTo = (value: string | null | undefined): string | undefined => {
  if (typeof value !== 'string') return undefined
  const trimmed = value.trim()
  if (trimmed === '') return undefined
  if (trimmed.includes('\\')) return undefined
  if (!trimmed.startsWith('/')) return undefined
  if (trimmed.startsWith('//')) return undefined
  if (urlScheme.test(trimmed)) return undefined
  return trimmed
}
