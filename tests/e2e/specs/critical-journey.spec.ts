import { expect, test } from '@playwright/test'

/**
 * EDU-085 — the first critical E2E journey from ARCHITECTURE.md §26:
 *
 * Login → Teacher Dashboard → Create Educational Environment → Create Course
 * → Create Section → Create Learning Unit → Create Activity → Save Draft
 * → Preview → Publish
 *
 * The test drives the real UI only (roles, labels and text — no CSS selectors,
 * no React/TanStack Query internals, no direct API calls, no domain imports).
 * The test user is registered through the public registration UI and is unique
 * per run, which keeps runs isolated even against a shared local database.
 */

const userPassword = 'Edu085-Journey-Pass!42'

test('critical journey: login → dashboard → environment → course → section → unit → activity → draft → preview → publish', async ({
  page,
}) => {
  const runId = `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`
  const email = `edu085+${runId}@example.com`
  const spaceName = `Journey Space ${runId}`
  const environmentName = `Journey Environment ${runId}`
  const courseTitle = `Journey Course ${runId}`
  const sectionTitle = `Journey Section ${runId}`
  const unitTitle = `Journey Unit ${runId}`
  const activityTitle = `Journey Activity ${runId}`

  // --- Test user: register through the UI, then log out so the journey
  // --- genuinely starts at Login.
  await page.goto('/register')
  await page.getByLabel('Email').fill(email)
  await page.getByLabel('Password').fill(userPassword)
  await page.getByRole('button', { name: 'Create account' }).click()
  await expect(page).toHaveURL(/\/app$/)
  await expect(page.getByRole('heading', { name: 'Teacher Workspace' })).toBeVisible()

  await page.getByRole('button', { name: 'Log out' }).click()
  await expect(page).toHaveURL(/\/login$/)

  // --- 1. Login -------------------------------------------------------------
  await page.getByLabel('Email').fill(email)
  await page.getByLabel('Password').fill(userPassword)
  await page.getByRole('button', { name: 'Log in' }).click()
  await expect(page).toHaveURL(/\/app$/)

  // --- 2. Teacher Dashboard -------------------------------------------------
  await expect(page.getByRole('heading', { name: 'Teacher Workspace' })).toBeVisible()
  await expect(page.getByText(`Welcome, ${email}.`)).toBeVisible()

  // --- 3. Teacher Space + Educational Environment ---------------------------
  await page.getByRole('link', { name: 'Open Teacher Spaces' }).click()
  await expect(page).toHaveURL(/\/app\/teacher-spaces$/)
  await expect(page.getByRole('heading', { name: 'My Teacher Spaces' })).toBeVisible()

  await page.getByLabel('Teacher Space name').fill(spaceName)
  await page.getByRole('button', { name: 'Create Teacher Space' }).click()
  const spaceRow = page.getByRole('listitem').filter({ hasText: spaceName })
  await expect(spaceRow).toBeVisible()
  await spaceRow.getByRole('link', { name: 'Open' }).click()
  await expect(page).toHaveURL(/\/app\/teacher-spaces\/[^/]+$/)
  await expect(page.getByRole('heading', { level: 1, name: spaceName })).toBeVisible()

  await page.getByRole('link', { name: 'Open Educational Environment' }).click()
  await expect(page).toHaveURL(/\/environment$/)

  await page.getByLabel('Environment name').fill(environmentName)
  await page.getByRole('button', { name: 'Create Environment' }).click()
  await expect(page.getByRole('heading', { level: 1, name: environmentName })).toBeVisible()

  // --- 4. Course (created as DRAFT) ------------------------------------------
  await page.getByRole('link', { name: 'Open Courses' }).click()
  await expect(page).toHaveURL(/\/courses$/)

  await page.getByLabel('Course title').fill(courseTitle)
  await page.getByRole('button', { name: 'Create Course' }).click()
  await expect(page).toHaveURL(/\/courses\/[^/]+$/)
  await expect(page.getByRole('heading', { level: 1, name: courseTitle })).toBeVisible()
  await expect(page.getByText('DRAFT', { exact: true })).toBeVisible()

  // --- 5. Section -------------------------------------------------------------
  await page.getByRole('link', { name: 'Open Sections' }).click()
  await expect(page).toHaveURL(/\/sections$/)
  await expect(page.getByRole('heading', { name: 'Sections', exact: true })).toBeVisible()

  await page.getByLabel('Section title').fill(sectionTitle)
  await page.getByRole('button', { name: 'Create Section' }).click()
  // The row renders the title as an editable input; locate it by its labeled
  // textbox and assert the value.
  const sectionRow = page
    .getByRole('listitem')
    .filter({ has: page.getByRole('textbox', { name: 'Section title' }) })
  await expect(sectionRow.getByRole('textbox', { name: 'Section title' })).toHaveValue(
    sectionTitle,
  )

  // --- 6. Learning Unit --------------------------------------------------------
  await sectionRow.getByRole('link', { name: 'Open Units' }).click()
  await expect(page).toHaveURL(/\/sections\/[^/]+\/learning-units$/)
  await expect(
    page.getByRole('heading', { name: 'Learning Units', exact: true }),
  ).toBeVisible()

  await page.getByLabel('Learning Unit title').fill(unitTitle)
  await page.getByRole('button', { name: 'Create Learning Unit' }).click()
  const unitRow = page
    .getByRole('listitem')
    .filter({ has: page.getByRole('textbox', { name: 'Learning Unit title' }) })
  await expect(unitRow.getByRole('textbox', { name: 'Learning Unit title' })).toHaveValue(
    unitTitle,
  )

  // --- 7. Activity (saved draft structure) --------------------------------------
  await unitRow.getByRole('link', { name: 'Open Activities' }).click()
  await expect(page).toHaveURL(/\/learning-units\/[^/]+\/activities$/)
  await expect(page.getByRole('heading', { name: 'Activities', exact: true })).toBeVisible()

  await page.getByLabel('Activity title').fill(activityTitle)
  await expect(page.getByLabel('Type')).toHaveValue('lecture')
  await page.getByRole('button', { name: 'Create Activity' }).click()
  const activityRow = page
    .getByRole('listitem')
    .filter({ has: page.getByRole('textbox', { name: 'Activity title' }) })
  await expect(activityRow.getByRole('textbox', { name: 'Activity title' })).toHaveValue(
    activityTitle,
  )
  await expect(activityRow.getByText('lecture')).toBeVisible()

  // --- 8. Draft is persisted: navigate back to the Course ----------------------
  await page.getByRole('link', { name: 'Back to Learning Units' }).click()
  await expect(page).toHaveURL(/\/learning-units$/)
  await page.getByRole('link', { name: 'Back to Sections' }).click()
  await expect(page).toHaveURL(/\/sections$/)
  await page.getByRole('link', { name: 'Back to Course' }).click()
  await expect(page).toHaveURL(/\/courses\/[^/]+$/)
  await expect(page.getByRole('heading', { level: 1, name: courseTitle })).toBeVisible()
  await expect(page.getByText('DRAFT', { exact: true })).toBeVisible()

  // --- 9. Preview -----------------------------------------------------------------
  await page.getByRole('link', { name: 'Preview Course' }).click()
  await expect(page).toHaveURL(/\/preview$/)
  await expect(page.getByRole('region', { name: 'Course Preview' })).toBeVisible()
  await expect(page.getByRole('heading', { level: 1, name: courseTitle })).toBeVisible()
  await expect(page.getByText('Author Preview')).toBeVisible()
  await expect(page.getByRole('heading', { level: 2, name: sectionTitle })).toBeVisible()
  await expect(page.getByText('Unit 1', { exact: true })).toBeVisible()
  await expect(page.getByText(unitTitle, { exact: true })).toBeVisible()
  await expect(page.getByText('Activity 1', { exact: true })).toBeVisible()
  await expect(page.getByText(activityTitle, { exact: true })).toBeVisible()
  await expect(page.getByText('lecture', { exact: true })).toBeVisible()

  // --- 10. Publish ------------------------------------------------------------------
  await page.getByRole('link', { name: /Back to Course/ }).click()
  await expect(page).toHaveURL(/\/courses\/[^/]+$/)

  page.once('dialog', (dialog) => {
    void dialog.accept()
  })
  await page.getByRole('button', { name: 'Publish Course' }).click()

  await expect(page.getByText('PUBLISHED', { exact: true })).toBeVisible()
  await expect(page.getByRole('button', { name: 'Archive Course' })).toBeVisible()
  await expect(page.getByRole('link', { name: 'Preview Course' })).toHaveCount(0)
})
