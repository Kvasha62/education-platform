import { createBrowserRouter } from 'react-router-dom'
import { App, FoundationPage, RoutingProofPage } from './App'

export const routes = [
  {
    path: '/',
    element: <App />,
    children: [
      { index: true, element: <FoundationPage /> },
      { path: 'foundation', element: <RoutingProofPage /> },
    ],
  },
]

export const router = createBrowserRouter(routes)
