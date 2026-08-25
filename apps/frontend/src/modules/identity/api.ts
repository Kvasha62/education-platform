import { apiRequest } from '../../shared/api'

export interface Identity {
  id: string
  email: string
  status: 'active' | 'disabled'
  created_at: string
  updated_at: string
}

export interface LoginInput {
  email: string
  password: string
}

export interface RegistrationInput extends LoginInput {}

export interface LoginResponse {
  user: Identity
}

export const identityApi = {
  me: () => apiRequest<Identity>('/api/v1/auth/me'),
  login: (input: LoginInput) =>
    apiRequest<LoginResponse>('/api/v1/auth/login', { method: 'POST', body: input }),
  register: (input: RegistrationInput) =>
    apiRequest<Identity>('/api/v1/auth/register', { method: 'POST', body: input }),
  logout: () => apiRequest<{ status: string }>('/api/v1/auth/logout', { method: 'POST' }),
}
