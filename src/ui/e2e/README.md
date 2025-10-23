# E2E Testing with Playwright

End-to-end tests for the DevMatrix authentication system and UI.

## Setup

1. Install dependencies:
```bash
npm install
```

2. Install Playwright browsers:
```bash
npx playwright install chromium
```

## Running Tests

### Run all tests (headless):
```bash
npm run test:e2e
```

### Run tests with UI mode (interactive):
```bash
npm run test:e2e:ui
```

### Run tests in headed mode (visible browser):
```bash
npm run test:e2e:headed
```

### Debug mode:
```bash
npm run test:e2e:debug
```

### View test report:
```bash
npm run test:e2e:report
```

## Test Coverage

### Authentication Flow (11 tests)
- ✅ Complete registration flow
- ✅ Registration validation errors
- ✅ Successful login
- ✅ Invalid credentials error
- ✅ Protected route redirection
- ✅ Forgot password navigation
- ✅ Password strength indicator
- ✅ Password visibility toggle
- ✅ Logout flow
- ✅ Dark mode toggle
- ✅ Sidebar navigation
- ✅ Responsive design on mobile

### Email Verification Flow (3 tests)
- ✅ Email verification pending page
- ✅ Resend verification email
- ✅ Email verification with token

### User Profile (2 tests)
- ✅ Display user profile page
- ✅ Display usage statistics

### Admin Dashboard (2 tests)
- ✅ Restrict admin routes to superusers
- ✅ Admin sidebar button visibility

## Prerequisites

### Backend API Running
Some tests require the backend API to be running:
```bash
cd ../../api
uvicorn main:app --reload
```

### Test User
Tests use dynamically generated test users with timestamps to avoid conflicts.

## Test Structure

```
e2e/
├── auth.spec.ts       # Main authentication tests
└── README.md          # This file
```

## Configuration

Configuration is in `playwright.config.ts`:
- Base URL: `http://localhost:5173`
- Browser: Chromium (Desktop Chrome)
- Retries: 2 on CI, 0 locally
- Timeout: 30 seconds per test
- Screenshots: On failure
- Videos: Retain on failure
- Traces: On first retry

## Writing New Tests

Example test structure:
```typescript
test.describe('Feature Name', () => {
  test.beforeEach(async ({ page }) => {
    // Setup before each test
    await page.goto('/')
  })

  test('should do something', async ({ page }) => {
    // Test implementation
    await page.click('button')
    await expect(page).toHaveURL(/\/expected-path/)
  })
})
```

## Debugging Tips

1. **Use UI Mode**: `npm run test:e2e:ui` for interactive debugging
2. **Use Debug Mode**: `npm run test:e2e:debug` to step through tests
3. **Screenshots**: Check `test-results/` for failure screenshots
4. **Videos**: Check `test-results/` for failure videos
5. **Traces**: Use Playwright Trace Viewer for detailed execution traces

## Common Issues

### Tests Fail with "Navigation timeout"
- Ensure the dev server is running (`npm run dev`)
- Check that `http://localhost:5173` is accessible
- Playwright will auto-start the dev server if not running

### Tests Fail with API Errors
- Ensure the backend API is running on `http://localhost:8000`
- Check that database is properly migrated
- Verify test user can be created in the database

### Browser Not Found
- Run `npx playwright install chromium`
- On Linux, may need: `npx playwright install-deps`

## CI/CD Integration

For GitHub Actions:
```yaml
- name: Install Playwright
  run: npx playwright install --with-deps chromium

- name: Run E2E tests
  run: npm run test:e2e

- name: Upload test results
  if: always()
  uses: actions/upload-artifact@v3
  with:
    name: playwright-report
    path: playwright-report/
```

## Performance

- Tests run in parallel by default
- Average test execution: ~30 seconds total
- Individual test: ~2-5 seconds

## Best Practices

1. **Use Page Object Model** for complex pages
2. **Avoid hard waits** - use `waitFor` methods
3. **Test user interactions**, not implementation details
4. **Keep tests isolated** - each test should be independent
5. **Use data-testid** attributes for stable selectors
6. **Clean up test data** after tests complete

## Resources

- [Playwright Documentation](https://playwright.dev)
- [Best Practices](https://playwright.dev/docs/best-practices)
- [Selectors Guide](https://playwright.dev/docs/selectors)
- [Test Fixtures](https://playwright.dev/docs/test-fixtures)
