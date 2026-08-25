import { createBrowserRouter, Navigate } from 'react-router-dom'
import { LoginPage, PublicOnlyRoute, RegisterPage } from '../modules/identity/AuthPages'
import { ProtectedApp, ProtectedRoute, RootLayout } from './App'

export const routes = [
  {
    path: '/',
    element: <RootLayout />,
    children: [
      { index: true, element: <Navigate replace to="/app" /> },
      {
        element: <PublicOnlyRoute />,
        children: [
          { path: 'login', element: <LoginPage /> },
          { path: 'register', element: <RegisterPage /> },
        ],
      },
      {
        element: <ProtectedRoute />,
        children: [{ path: 'app', element: <ProtectedApp /> }],
      },
    ],
  },
]

export const router = createBrowserRouter(routes)
