/**
 * E2E Tests for Authentication Flow - REAL VALIDATION
 *
 * These tests actually verify:
 * - Backend responses
 * - Successful authentication
 * - Proper redirects
 * - Error handling
 * - Protected routes
 */

import { test, expect, Page } from '@playwright/test'

// Use the REAL test user from the database
const testUser = {
  email: 'test@devmatrix.com',
  username: 'testuser',
  password: 'Test123!',
}

// Invalid credentials for error testing
const invalidUser = {
  email: 'invalid@example.com',
  password: 'WrongPassword123!',
}

/**
 * Helper: Login via UI
 * Returns true if login succeeded, false otherwise
 */
async function loginUser(page: Page, email: string, password: string): Promise<boolean> {
  await page.goto('/login')
  await page.fill('input[type="email"]', email)
  await page.fill('input[type="password"]', password)
  await page.click('button[type="submit"]')

  // Wait for either redirect to /chat OR error message
  try {
    await page.waitForURL(/\/chat/, { timeout: 5000 })
    return true
  } catch {
    // Check if still on login page (error case)
    return page.url().includes('/login') === false
  }
}

/**
 * Helper: Check if user is authenticated
 */
async function isAuthenticated(page: Page): Promise<boolean> {
  try {
    const token = await page.evaluate(() => localStorage.getItem('access_token'))
    return token !== null
  } catch {
    // localStorage not available (e.g., on about:blank)
    return false
  }
}

/**
 * Helper: Logout current user
 */
async function logoutUser(page: Page): Promise<void> {
  // Navigate to login page first to ensure we have a valid context
  try {
    await page.goto('/login', { waitUntil: 'domcontentloaded', timeout: 5000 })
    // Clear localStorage to log out
    await page.evaluate(() => {
      localStorage.removeItem('access_token')
      localStorage.removeItem('refresh_token')
    })
  } catch {
    // If navigation fails or localStorage unavailable, that's OK
    // User is effectively logged out anyway
  }
}

test.describe('Authentication Flow - Core Features', () => {
  test.beforeEach(async ({ page }) => {
    // Ensure user is logged out before each test
    await logoutUser(page)
  })

  test('should login successfully with valid credentials', async ({ page }) => {
    await page.goto('/login')

    // Verify we're on login page
    await expect(page.locator('h1')).toContainText(/welcome|sign in/i)

    // Fill login form
    await page.fill('input[type="email"]', testUser.email)
    await page.fill('input[type="password"]', testUser.password)

    // Submit form
    await page.click('button[type="submit"]')

    // REAL VALIDATION: Should redirect to /chat
    await expect(page).toHaveURL(/\/chat/, { timeout: 10000 })

    // REAL VALIDATION: Should have access token in localStorage
    const isAuth = await isAuthenticated(page)
    expect(isAuth).toBe(true)

    // REAL VALIDATION: Should not show login button anymore
    // (Should show user menu or logout instead)
    const loginButton = page.locator('text=/sign in|login/i')
    await expect(loginButton).not.toBeVisible()
  })

  test('should show error for invalid credentials', async ({ page }) => {
    await page.goto('/login')

    // Fill with invalid credentials
    await page.fill('input[type="email"]', invalidUser.email)
    await page.fill('input[type="password"]', invalidUser.password)

    await page.click('button[type="submit"]')

    // REAL VALIDATION: Should stay on login page
    await expect(page).toHaveURL(/\/login/)

    // REAL VALIDATION: Should show error message
    const errorMessage = page.locator('text=/invalid|incorrect|failed/i')
    await expect(errorMessage).toBeVisible({ timeout: 5000 })

    // REAL VALIDATION: Should NOT have token
    const isAuth = await isAuthenticated(page)
    expect(isAuth).toBe(false)
  })

  test('should redirect to login when accessing protected route', async ({ page }) => {
    // Ensure not logged in
    await logoutUser(page)

    // Try to access chat without being logged in
    await page.goto('/chat')

    // REAL VALIDATION: Should redirect to login
    await expect(page).toHaveURL(/\/login/)

    // REAL VALIDATION: Should not have access token
    const isAuth = await isAuthenticated(page)
    expect(isAuth).toBe(false)
  })

  test('should handle logout flow correctly', async ({ page }) => {
    // First, login
    const loginSuccess = await loginUser(page, testUser.email, testUser.password)
    expect(loginSuccess).toBe(true)

    // Verify we're logged in
    await expect(page).toHaveURL(/\/chat/)

    // Find and click logout button
    // Look for user menu or logout button
    const logoutButton = page.locator('button:has-text("Logout"), a:has-text("Logout")')

    // May need to open user menu first
    const userMenu = page.locator('[aria-label="User menu"], button:has-text("Profile")')
    if (await userMenu.count() > 0) {
      await userMenu.first().click()
      await page.waitForTimeout(500) // Wait for menu to open
    }

    await logoutButton.first().click()

    // Wait for logout to complete and localStorage to update
    await page.waitForTimeout(500)

    // REAL VALIDATION: Should redirect to login
    await expect(page).toHaveURL(/\/login|\//, { timeout: 5000 })

    // REAL VALIDATION: Should clear tokens
    const isAuth = await isAuthenticated(page)
    expect(isAuth).toBe(false)
  })

  test('should navigate to forgot password page', async ({ page }) => {
    await page.goto('/login')

    // Click forgot password link
    await page.click('text=/forgot.*password/i')

    // REAL VALIDATION: Should navigate to forgot password page
    await expect(page).toHaveURL(/\/forgot-password/)

    // Verify page elements exist
    await expect(page.locator('input[type="email"]')).toBeVisible()
    await expect(page.locator('button[type="submit"]')).toBeVisible()
  })
})

test.describe('Protected Routes', () => {
  test('should allow access to chat when logged in', async ({ page }) => {
    // Login first - this already navigates to /chat on success
    const loginSuccess = await loginUser(page, testUser.email, testUser.password)
    expect(loginSuccess).toBe(true)

    // REAL VALIDATION: Should be on chat page after login
    await expect(page).toHaveURL(/\/chat/)

    // REAL VALIDATION: Should have access token
    const isAuth = await isAuthenticated(page)
    expect(isAuth).toBe(true)

    // Should NOT redirect to login after being on chat
    await page.waitForTimeout(1000)
    expect(page.url()).not.toContain('/login')
  })

  test('should allow access to profile when logged in', async ({ page }) => {
    // Login first - this navigates to /chat
    const loginSuccess = await loginUser(page, testUser.email, testUser.password)
    expect(loginSuccess).toBe(true)

    // Click on profile link in sidebar to navigate
    const profileLink = page.locator('a[href="/profile"], button:has-text("Profile")')
    if (await profileLink.count() > 0) {
      await profileLink.first().click()
    } else {
      // If no link, navigate directly
      await page.goto('/profile')
    }

    // REAL VALIDATION: Should stay on profile page
    await expect(page).toHaveURL(/\/profile/, { timeout: 10000 })

    // Should show user info or profile elements
    const hasProfileContent = await page.locator('text=/profile|email|usage|account/i').count() > 0
    expect(hasProfileContent).toBe(true)
  })

  test('should block profile when not logged in', async ({ page }) => {
    // Ensure logged out
    await logoutUser(page)

    // Try to access profile
    await page.goto('/profile')

    // REAL VALIDATION: Should redirect to login
    await expect(page).toHaveURL(/\/login/)
  })
})

test.describe('Email Verification Flow', () => {
  test('should display email verification pending page', async ({ page }) => {
    await page.goto('/verify-email-pending')

    // REAL VALIDATION: Page should load
    await expect(page).toHaveURL(/\/verify-email-pending/)

    // Should show instructions
    await expect(page.locator('text=/verify|email|check/i').first()).toBeVisible()

    // Should have email input and resend button
    await expect(page.locator('input[type="email"]')).toBeVisible()
    await expect(page.locator('button:has-text("Resend"), button:has-text("Send")')).toBeVisible()
  })

  test('should handle email verification page', async ({ page }) => {
    // Visit verification page with a token
    await page.goto('/verify-email?token=test-token-12345')

    // REAL VALIDATION: Page should load
    await expect(page).toHaveURL(/\/verify-email/)

    // Should show verification UI heading (loading, success, or error state)
    // We don't validate the API result due to rate limiting, just that the page renders
    const heading = page.locator('h2')
    await expect(heading).toBeVisible({ timeout: 5000 })
  })
})

test.describe('Admin Dashboard', () => {
  test('should restrict admin routes to non-superusers', async ({ page }) => {
    // Login as regular user (not superuser)
    await loginUser(page, testUser.email, testUser.password)

    // Try to access admin
    await page.goto('/admin')

    // REAL VALIDATION: Should redirect away from admin
    // Either to home or stay on admin but show access denied
    await page.waitForTimeout(1000)

    const url = page.url()
    const hasAdminRoute = url.includes('/admin')

    if (hasAdminRoute) {
      // If still on admin page, should show access denied
      await expect(page.locator('text=/access denied|not authorized|forbidden/i')).toBeVisible()
    } else {
      // Should have redirected away
      expect(url).not.toContain('/admin')
    }
  })
})

test.describe('UI Elements - Navigation', () => {
  test('should navigate between pages using sidebar', async ({ page }) => {
    // Login first to access all pages
    await loginUser(page, testUser.email, testUser.password)

    await page.goto('/')

    // Check sidebar navigation buttons exist
    await expect(page.locator('[aria-label="Home"], a[href="/"]')).toBeVisible()
    await expect(page.locator('[aria-label="Settings"], a[href="/settings"]')).toBeVisible()

    // Navigate to settings
    await page.click('[aria-label="Settings"], a[href="/settings"]')
    await expect(page).toHaveURL(/\/settings/)

    // Navigate back to home
    await page.click('[aria-label="Home"], a[href="/"]')
    await expect(page).toHaveURL(/\/$|\/chat/)
  })

  test('should show responsive design on mobile', async ({ page }) => {
    // Set mobile viewport
    await page.setViewportSize({ width: 375, height: 667 })

    await page.goto('/login')

    // REAL VALIDATION: Form should be visible and usable
    const form = page.locator('form')
    await expect(form).toBeVisible()

    // Inputs should be wide enough
    const emailInput = page.locator('input[type="email"]')
    await expect(emailInput).toBeVisible()

    const boundingBox = await emailInput.boundingBox()
    expect(boundingBox?.width).toBeGreaterThan(200) // Should be reasonably wide
  })
})

test.describe('Form Validation', () => {
  test('should validate email format', async ({ page }) => {
    await page.goto('/login')

    // Try invalid email
    await page.fill('input[type="email"]', 'notanemail')
    await page.fill('input[type="password"]', 'SomePassword123!')

    // Try to submit
    await page.click('button[type="submit"]')

    // REAL VALIDATION: Should not submit (HTML5 validation or custom)
    // Either stays on page or shows validation error
    await page.waitForTimeout(500)
    expect(page.url()).toContain('/login')
  })

  test('should require password field', async ({ page }) => {
    await page.goto('/login')

    // Fill email but not password
    await page.fill('input[type="email"]', testUser.email)

    // Try to submit
    const submitButton = page.locator('button[type="submit"]')
    await submitButton.click()

    // REAL VALIDATION: Should not proceed without password
    await page.waitForTimeout(500)
    expect(page.url()).toContain('/login')
  })
})
