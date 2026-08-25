import { useMutation, useQueryClient } from '@tanstack/react-query'
import { FormEvent, useState } from 'react'
import { Link, Navigate, Outlet, useLocation, useNavigate } from 'react-router-dom'
import { ApiError } from '../../shared/api'
import { ErrorState, LoadingState } from '../../shared/ui'
import { authQueryKey, useAuthentication } from './auth'
import { identityApi } from './api'
import type { LoginInput, RegistrationInput } from './api'

const errorMessage = (error: unknown) =>
  error instanceof ApiError || error instanceof Error ? error.message : 'Request failed.'

export const LoginPage = () => {
  const navigate = useNavigate()
  const location = useLocation()
  const queryClient = useQueryClient()
  const initialEmail = (location.state as { email?: string } | null)?.email ?? ''
  const destination = (location.state as { from?: string } | null)?.from ?? '/app'
  const [email, setEmail] = useState(initialEmail)
  const [password, setPassword] = useState('')
  const login = useMutation({
    mutationFn: (input: LoginInput) => identityApi.login(input),
    onSuccess: ({ user }) => {
      queryClient.setQueryData(authQueryKey, user)
      navigate(destination, { replace: true })
    },
  })

  const submit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    login.mutate({ email, password })
  }

  return (
    <section className="auth-card" aria-labelledby="login-title">
      <p className="eyebrow">Welcome back</p>
      <h1 id="login-title">Log in</h1>
      <form onSubmit={submit}>
        <label>
          Email
          <input
            autoComplete="email"
            name="email"
            type="email"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            required
          />
        </label>
        <label>
          Password
          <input
            autoComplete="current-password"
            name="password"
            type="password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            required
          />
        </label>
        {login.isError && <ErrorState message={errorMessage(login.error)} />}
        <button disabled={login.isPending} type="submit">
          {login.isPending ? 'Logging in…' : 'Log in'}
        </button>
      </form>
      <p>New here? <Link to="/register">Create an account</Link>.</p>
    </section>
  )
}

export const RegisterPage = () => {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const register = useMutation({
    mutationFn: async (input: RegistrationInput) => {
      await identityApi.register(input)
      await identityApi.login(input)
      return identityApi.me()
    },
    onSuccess: (identity) => {
      queryClient.setQueryData(authQueryKey, identity)
      navigate('/app', { replace: true })
    },
  })

  const submit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    register.mutate({ email, password })
  }

  return (
    <section className="auth-card" aria-labelledby="register-title">
      <p className="eyebrow">Get started</p>
      <h1 id="register-title">Create an account</h1>
      <form onSubmit={submit}>
        <label>
          Email
          <input
            autoComplete="email"
            name="email"
            type="email"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            required
          />
        </label>
        <label>
          Password
          <input
            autoComplete="new-password"
            minLength={12}
            name="password"
            type="password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            required
          />
        </label>
        <p className="form-hint">Use at least 12 characters.</p>
        {register.isError && <ErrorState message={errorMessage(register.error)} />}
        <button disabled={register.isPending} type="submit">
          {register.isPending ? 'Creating account…' : 'Create account'}
        </button>
      </form>
      <p>Already registered? <Link to="/login">Log in</Link>.</p>
    </section>
  )
}

export const PublicOnlyRoute = () => {
  const authentication = useAuthentication()
  if (authentication.status === 'loading') return <LoadingState label="Checking session" />
  if (authentication.status === 'authenticated') return <Navigate replace to="/app" />
  return <>{authentication.status === 'error' ? <ErrorState message="Session check failed." /> : <Outlet />}</>
}
