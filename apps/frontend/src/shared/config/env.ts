const configuredApiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? ''

export const env = {
  apiBaseUrl: configuredApiBaseUrl.replace(/\/$/, ''),
} as const
