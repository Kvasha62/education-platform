import { createBrowserRouter, Navigate } from 'react-router-dom'
import { CoursePage, CoursesPage, EducationalEnvironmentPage, LearningUnitsPage, SectionsPage } from '../modules/education'
import { LoginPage, PublicOnlyRoute, RegisterPage } from '../modules/identity/AuthPages'
import { TeacherSpacePage, TeacherSpacesPage } from '../modules/teacher'
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
        children: [
          { path: 'app', element: <ProtectedApp /> },
          { path: 'app/teacher-spaces', element: <TeacherSpacesPage /> },
          { path: 'app/teacher-spaces/:teacherSpaceId', element: <TeacherSpacePage /> },
          {
            path: 'app/teacher-spaces/:teacherSpaceId/environment',
            element: <EducationalEnvironmentPage />,
          },
          {
            path: 'app/teacher-spaces/:teacherSpaceId/environment/courses',
            element: <CoursesPage />,
          },
          {
            path: 'app/teacher-spaces/:teacherSpaceId/environment/courses/:courseId',
            element: <CoursePage />,
          },
          {
            path: 'app/teacher-spaces/:teacherSpaceId/environment/courses/:courseId/sections',
            element: <SectionsPage />,
          },
          {
            path: 'app/teacher-spaces/:teacherSpaceId/environment/courses/:courseId/sections/:sectionId/learning-units',
            element: <LearningUnitsPage />,
          },
        ],
      },
    ],
  },
]

export const router = createBrowserRouter(routes)
