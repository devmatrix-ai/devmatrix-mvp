# E2E Testing with Playwright - REAL VALIDATION

## 🎯 Overview

These E2E tests **actually validate** that the authentication system works correctly by:

✅ **Verifying backend responses** - Tests communicate with real API
✅ **Checking authentication state** - Validates tokens in localStorage
✅ **Testing real redirects** - Ensures navigation works correctly
✅ **Validating error handling** - Confirms errors are shown to users
✅ **Testing protected routes** - Verifies authorization works

## 🚀 Prerequisites

### 1. Backend API Running
The backend must be running on `http://localhost:8000`:
```bash
cd /home/kwar/code/agentic-ai
uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --reload
```

### 2. Database with Test User
The test user must exist in the database:
```sql
Email: test@devmatrix.com
Password: Test123!
```

To create the user:
```bash
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@devmatrix.com",
    "username": "testuser",
    "password": "Test123!",
    "full_name": "Test User"
  }'
```

Or use the SQL directly:
```sql
INSERT INTO users (user_id, email, username, password_hash, full_name, is_active, is_verified)
VALUES (
  gen_random_uuid(),
  'test@devmatrix.com',
  'testuser',
  '$2b$12$QVEz1Dm1vuivZkLYk4qlkucE1IwMkOn90GQYiEyrd3uB7PGorJHGS', -- Test123!
  'Test User',
  true,
  true
);
```

### 3. Playwright Installed
```bash
npm install
npx playwright install chromium
npx playwright install-deps  # Linux only
```

## 📋 Running Tests

### Run all tests (headless)
```bash
npm run test:e2e
```

### Run tests with UI mode (interactive)
```bash
npm run test:e2e:ui
```

### Run tests in headed mode (visible browser)
```bash
npm run test:e2e:headed
```

### Debug mode
```bash
npm run test:e2e:debug
```

### View test report
```bash
npm run test:e2e:report
```

## 🧪 Test Suite Structure

### Authentication Flow - Core Features (6 tests)
✅ **Login with valid credentials**
- Fills login form
- Verifies redirect to /chat
- Checks access_token in localStorage
- Confirms login UI disappears

✅ **Login with invalid credentials**
- Attempts login with wrong password
- Verifies stays on /login
- Checks error message appears
- Confirms no token stored

✅ **Redirect to login when accessing protected route**
- Tries to access /chat while logged out
- Verifies redirect to /login
- Confirms no authentication token

✅ **Logout flow**
- Logs in first
- Finds and clicks logout button
- Verifies redirect to /login
- Checks tokens are cleared

✅ **Navigate to forgot password**
- Clicks "Forgot password" link
- Verifies navigation to /forgot-password
- Checks form elements exist

✅ **Validate email format**
- Tries to submit with invalid email
- Verifies validation prevents submission

### Protected Routes (3 tests)
✅ **Allow chat access when logged in**
- Logs in user
- Navigates to /chat
- Verifies no redirect to /login

✅ **Allow profile access when logged in**
- Logs in user
- Navigates to /profile
- Verifies profile page loads

✅ **Block profile when not logged in**
- Ensures logged out
- Tries to access /profile
- Verifies redirect to /login

### Email Verification (2 tests)
✅ **Display email verification pending page**
- Loads /verify-email-pending
- Checks instructions visible
- Verifies email input and resend button exist

✅ **Handle email verification with token**
- Visits /verify-email?token=xxx
- Checks verification UI appears
- Validates loading/success/error states

### Admin Dashboard (1 test)
✅ **Restrict admin routes to non-superusers**
- Logs in as regular user
- Tries to access /admin
- Verifies access denied or redirect

### UI Elements (2 tests)
✅ **Navigate between pages using sidebar**
- Logs in
- Tests sidebar navigation
- Verifies page transitions

✅ **Responsive design on mobile**
- Sets mobile viewport
- Checks form visibility
- Validates element sizing

### Form Validation (2 tests)
✅ **Validate email format**
- Tests HTML5 validation
- Confirms invalid email rejected

✅ **Require password field**
- Tests required field validation
- Confirms empty password rejected

## ✨ Key Differences from Previous Tests

### ❌ OLD (False Positives):
```typescript
test('should login successfully', async ({ page }) => {
  await page.fill('input[type="email"]', email)
  await page.fill('input[type="password"]', password)
  await page.click('button[type="submit"]')

  // ❌ Just checks if email field still visible
  await expect(page.locator('input[type="email"]')).toBeVisible()
})
```
**Problem**: Test passes even if login fails (stays on same page)

### ✅ NEW (Real Validation):
```typescript
test('should login successfully', async ({ page }) => {
  await page.fill('input[type="email"]', email)
  await page.fill('input[type="password"]', password)
  await page.click('button[type="submit"]')

  // ✅ Verifies redirect happened
  await expect(page).toHaveURL(/\/chat/, { timeout: 10000 })

  // ✅ Verifies authentication token exists
  const token = await page.evaluate(() => localStorage.getItem('access_token'))
  expect(token).not.toBeNull()

  // ✅ Verifies UI changed
  await expect(page.locator('text=/sign in|login/i')).not.toBeVisible()
})
```
**Success**: Test only passes if login actually works!

## 🔧 Helper Functions

### `loginUser(page, email, password)`
Logs in a user via UI and returns success status
```typescript
const success = await loginUser(page, 'test@devmatrix.com', 'Test123!')
expect(success).toBe(true)
```

### `isAuthenticated(page)`
Checks if user has valid access_token
```typescript
const isAuth = await isAuthenticated(page)
expect(isAuth).toBe(true)
```

### `logoutUser(page)`
Clears authentication tokens
```typescript
await logoutUser(page)
```

## 📊 Expected Results

When backend is working correctly:
- **~14 tests should PASS**
- **~2 tests may SKIP** (if features not implemented)
- **0 tests should FAIL** (if everything works)

If tests fail, it means:
- ❌ Backend is not responding
- ❌ Backend returns errors
- ❌ Authentication flow is broken
- ❌ Redirects don't work
- ❌ Protected routes aren't protected

## 🐛 Troubleshooting

### "Timed out waiting for redirect"
**Cause**: Backend not responding or login failing
**Fix**: Check backend logs, verify test user exists, check network tab

### "Error: locator.toBeVisible() failed"
**Cause**: UI element doesn't exist or wrong selector
**Fix**: Inspect page with headed mode, check element actually exists

### "Test user not found"
**Cause**: Database doesn't have test@devmatrix.com
**Fix**: Create test user using SQL or registration endpoint

### "All tests fail immediately"
**Cause**: Frontend dev server not running
**Fix**: Start vite with `npm run dev`, verify port 3002 or 5173

## 📈 CI/CD Integration

For GitHub Actions:
```yaml
- name: Start Backend
  run: |
    cd /home/kwar/code/agentic-ai
    uvicorn src.api.main:app --host 0.0.0.0 --port 8000 &
    sleep 5

- name: Start Frontend
  run: |
    cd src/ui
    npm run dev &
    sleep 10

- name: Run E2E Tests
  run: |
    cd src/ui
    npm run test:e2e

- name: Upload Test Results
  if: always()
  uses: actions/upload-artifact@v3
  with:
    name: playwright-report
    path: src/ui/playwright-report/
```

## 🎓 Best Practices

1. **Always use real test user** - Don't create random users each run
2. **Verify actual behavior** - Check redirects, tokens, error messages
3. **Wait for async operations** - Use proper timeouts for API calls
4. **Clean state between tests** - Use `beforeEach` to logout
5. **Test both success and failure** - Invalid credentials are important
6. **Don't just check DOM** - Verify functionality works end-to-end

## 📚 Resources

- [Playwright Documentation](https://playwright.dev)
- [Best Practices](https://playwright.dev/docs/best-practices)
- [Authentication Testing](https://playwright.dev/docs/auth)
- [Debugging Tests](https://playwright.dev/docs/debug)
