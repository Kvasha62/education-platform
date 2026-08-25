import { useMutation, useQueryClient } from '@tanstack/react-query'
import { Link, Navigate, Outlet, useLocation, useNavigate } from 'react-router-dom'
import { authQueryKey, identityApi, useAuthentication } from '../modules/identity'
import { ErrorState, LoadingState } from '../shared/ui'
import './styles.css'

export const RootLayout = () => (
  <div className="app-shell">
    <header className="app-header">
      <Link className="brand" to="/">Education Platform</Link>
    </header>
    <main><Outlet /></main>
  </div>
)

export const ProtectedRoute = () => {
  const authentication = useAuthentication()
  const location = useLocation()

  if (authentication.status === 'loading') return <LoadingState label="Loading application" />
  if (authentication.status === 'unauthenticated') {
    return <Navigate replace state={{ from: location.pathname }} to="/login" />
  }
  if (authentication.status === 'error') {
    return <ErrorState message="The application could not check your session." />
  }
  return <Outlet />
}

export const ProtectedApp = () => {
  const authentication = useAuthentication()
  const queryClient = useQueryClient()
  const navigate = useNavigate()
  const logout = useMutation({
    mutationFn: identityApi.logout,
    onSuccess: () => {
      queryClient.removeQueries({ queryKey: authQueryKey })
      navigate('/login', { replace: true })
    },
  })

  if (authentication.status !== 'authenticated') return null

  return (
    <section className="welcome" aria-labelledby="app-title">
      <p className="eyebrow">Protected application</p>
      <h1 id="app-title">You are signed in.</h1>
      <p>{authentication.user.email}</p>
      {logout.isError && <ErrorState message="Logout failed. Please try again." />}
      <button disabled={logout.isPending} onClick={() => logout.mutate()} type="button">
        {logout.isPending ? 'Logging out…' : 'Log out'}
      </button>
    </section>
  )
}
