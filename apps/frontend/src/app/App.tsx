import { Link, Outlet } from 'react-router-dom'
import { useAuthentication } from '../modules/identity'
import { ErrorState, LoadingState } from '../shared/ui'
import './styles.css'

export const App = () => {
  const authentication = useAuthentication()

  return (
    <div className="app-shell">
      <header className="app-header">
        <Link className="brand" to="/">Education Platform</Link>
        <span className="session-status">
          {authentication.status === 'loading' && 'Checking session…'}
          {authentication.status === 'authenticated' && authentication.user.email}
          {authentication.status === 'unauthenticated' && 'Not signed in'}
          {authentication.status === 'error' && 'Session unavailable'}
        </span>
      </header>
      <main>
        {authentication.status === 'loading' && <LoadingState label="Loading application" />}
        {authentication.status === 'error' && (
          <ErrorState message="The application could not check your session." />
        )}
        {authentication.status !== 'loading' && authentication.status !== 'error' && <Outlet />}
      </main>
    </div>
  )
}

export const FoundationPage = () => (
  <section className="welcome" aria-labelledby="welcome-title">
    <p className="eyebrow">Frontend foundation</p>
    <h1 id="welcome-title">Ready for the next learning experience.</h1>
    <p>Routing, session bootstrap, server state, and shared API infrastructure are active.</p>
    <Link to="/foundation">Verify routing</Link>
  </section>
)

export const RoutingProofPage = () => (
  <section className="welcome" aria-labelledby="routing-title">
    <p className="eyebrow">Routing</p>
    <h1 id="routing-title">The application router is working.</h1>
    <Link to="/">Back to foundation</Link>
  </section>
)
