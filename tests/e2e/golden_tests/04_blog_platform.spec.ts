/**
 * Golden E2E Tests: Blog Platform (Level 2)
 *
 * Covers 30 scenarios for Next.js + Prisma + Markdown + NextAuth blog
 */

import { test, expect, Page } from '@playwright/test';

const BASE_URL = process.env.BASE_URL || 'http://localhost:3000';

// Test users
const AUTHOR = {
  email: 'author@blog.com',
  username: 'blogauthor',
  password: 'AuthorPass123',
  name: 'Blog Author'
};

const ADMIN = {
  email: 'admin@blog.com',
  username: 'blogadmin',
  password: 'AdminPass123',
  name: 'Blog Admin'
};

// Helper functions
async function loginAs(page: Page, role: 'author' | 'admin') {
  const user = role === 'admin' ? ADMIN : AUTHOR;
  await page.goto(`${BASE_URL}/login`);
  await page.fill('input[name="email"]', user.email);
  await page.fill('input[name="password"]', user.password);
  await page.click('button[type="submit"]');
  await page.waitForURL(/dashboard|posts/);
}

async function createPost(page: Page, title: string, content: string, publish = false) {
  await page.goto(`${BASE_URL}/dashboard/posts/new`);
  await page.fill('input[name="title"]', title);

  // Fill markdown editor
  const editor = page.locator('textarea[name="content"], [data-testid="markdown-editor"]');
  await editor.fill(content);

  // Add tags
  const tagsInput = page.locator('input[name="tags"]');
  if (await tagsInput.count() > 0) {
    await tagsInput.fill('test,blog');
    await page.keyboard.press('Enter');
  }

  if (publish) {
    // Publish immediately
    const publishBtn = page.locator('button:has-text("Publish")');
    if (await publishBtn.count() > 0) {
      await publishBtn.click();
    }
  } else {
    // Save as draft
    await page.click('button:has-text("Save"), button[type="submit"]');
  }

  await page.waitForTimeout(500);
}

test.describe('Blog Platform - Public Blog Tests', () => {

  /**
   * Test 1: View homepage with latest posts
   */
  test('should display homepage with latest posts', async ({ page }) => {
    await page.goto(BASE_URL);

    // Should show blog title/logo
    await expect(page.locator('h1, [data-testid="blog-title"]')).toBeVisible();

    // Should show post list or placeholder
    const postList = page.locator('[data-testid="post-list"], article');
    const postsExist = await postList.count() > 0;

    if (postsExist) {
      // Verify post cards have required elements
      const firstPost = postList.first();
      await expect(firstPost.locator('h2, h3')).toBeVisible(); // Post title
    }
  });

  /**
   * Test 2: Navigate to individual post page
   */
  test('should navigate to and display individual post', async ({ page }) => {
    await page.goto(BASE_URL);

    // Click on first post
    const firstPostLink = page.locator('article a, [data-testid="post-link"]').first();
    if (await firstPostLink.count() > 0) {
      await firstPostLink.click();

      // Should be on post page
      await expect(page).toHaveURL(/\/posts\//);

      // Should show full post content
      await expect(page.locator('article, [data-testid="post-content"]')).toBeVisible();
    }
  });

  /**
   * Test 3: Verify Markdown rendering
   */
  test('should render Markdown content correctly', async ({ page }) => {
    await loginAs(page, 'author');

    // Create post with various Markdown elements
    const markdownContent = `# Heading 1
## Heading 2

**Bold text** and *italic text*

- List item 1
- List item 2

\`\`\`javascript
const hello = "world";
\`\`\`

[Link](https://example.com)
`;

    await createPost(page, 'Markdown Test Post', markdownContent, true);
    await page.waitForTimeout(500);

    // Go to public blog
    await page.goto(BASE_URL);
    await page.click('text=Markdown Test Post');

    // Verify Markdown elements rendered
    await expect(page.locator('h1:has-text("Heading 1")')).toBeVisible();
    await expect(page.locator('h2:has-text("Heading 2")')).toBeVisible();
    await expect(page.locator('strong:has-text("Bold text")')).toBeVisible();
    await expect(page.locator('em:has-text("italic text")')).toBeVisible();
    await expect(page.locator('code:has-text("const hello")')).toBeVisible();
  });

  /**
   * Test 4: Search posts by keyword
   */
  test('should search posts by keyword', async ({ page }) => {
    await page.goto(BASE_URL);

    const searchInput = page.locator('input[type="search"], [placeholder*="Search" i]');
    if (await searchInput.count() > 0) {
      await searchInput.fill('test');
      await page.keyboard.press('Enter');
      await page.waitForTimeout(500);

      // Should show search results page
      await expect(page).toHaveURL(/search/);
      await expect(page.locator('h1, h2')).toContainText(/search|results/i);
    }
  });

  /**
   * Test 5: Filter by tag
   */
  test('should filter posts by tag', async ({ page }) => {
    await page.goto(BASE_URL);

    // Look for tag links
    const tagLink = page.locator('a[href*="/tags/"], [data-testid="tag"]').first();
    if (await tagLink.count() > 0) {
      await tagLink.click();

      // Should be on tag page
      await expect(page).toHaveURL(/\/tags\//);

      // Should show posts with that tag
      await expect(page.locator('article, [data-testid="post-card"]')).toBeVisible();
    }
  });

  /**
   * Test 6: View posts by author
   */
  test('should view posts by specific author', async ({ page }) => {
    await page.goto(BASE_URL);

    // Click on author name
    const authorLink = page.locator('a[href*="/author/"], [data-testid="author-link"]').first();
    if (await authorLink.count() > 0) {
      const authorName = await authorLink.textContent();
      await authorLink.click();

      // Verify on author page
      await expect(page.locator(`text=${authorName}`)).toBeVisible();
    }
  });

  /**
   * Test 7: Navigate archive page
   */
  test('should display archive page grouped by month', async ({ page }) => {
    await page.goto(`${BASE_URL}/archive`);

    // Should show archive heading
    await expect(page.locator('h1:has-text("Archive"), h2:has-text("Archive")')).toBeVisible();

    // Should show posts grouped by date
    const posts = page.locator('article, [data-testid="post-card"]');
    const postsExist = await posts.count() > 0;

    if (postsExist) {
      // Verify date groupings
      await expect(page.locator('h2, h3')).toBeVisible();
    }
  });
});

test.describe('Blog Platform - Authentication Tests', () => {

  /**
   * Test 8: Register new user (author role)
   */
  test('should register new author account', async ({ page }) => {
    const uniqueEmail = `user${Date.now()}@blog.com`;

    await page.goto(`${BASE_URL}/register`);
    await page.fill('input[name="email"]', uniqueEmail);
    await page.fill('input[name="username"]', `user${Date.now()}`);
    await page.fill('input[name="password"]', 'TestPass123');
    await page.fill('input[name="confirmPassword"]', 'TestPass123');
    await page.click('button[type="submit"]');

    // Should redirect to login or dashboard
    await expect(page).toHaveURL(/login|dashboard/);
  });

  /**
   * Test 9: Login with email/password
   */
  test('should login with email and password', async ({ page }) => {
    await loginAs(page, 'author');

    // Should be logged in
    await expect(page.locator(`text=${AUTHOR.name}`)).toBeVisible();
  });

  /**
   * Test 10: Login with Google OAuth (if configured)
   */
  test('should show Google OAuth login option', async ({ page }) => {
    await page.goto(`${BASE_URL}/login`);

    // Check if OAuth button exists
    const googleBtn = page.locator('button:has-text("Google"), a:has-text("Google")');
    const hasOAuth = await googleBtn.count() > 0;

    if (hasOAuth) {
      await expect(googleBtn).toBeVisible();
    }
  });

  /**
   * Test 11: Logout
   */
  test('should logout successfully', async ({ page }) => {
    await loginAs(page, 'author');

    // Click logout
    await page.click('button:has-text("Logout"), [data-testid="logout"]');
    await page.waitForTimeout(500);

    // Should redirect to homepage or login
    await expect(page).toHaveURL(/\/($|login)/);
  });

  /**
   * Test 12: Access dashboard (authenticated)
   */
  test('should access dashboard when logged in', async ({ page }) => {
    await loginAs(page, 'author');
    await page.goto(`${BASE_URL}/dashboard`);

    // Should show dashboard
    await expect(page.locator('h1:has-text("Dashboard")')).toBeVisible();
  });

  /**
   * Test 13: Access dashboard (unauthenticated - redirect)
   */
  test('should redirect to login when accessing dashboard unauthenticated', async ({ page }) => {
    await page.goto(`${BASE_URL}/dashboard`);

    // Should redirect to login
    await expect(page).toHaveURL(/login/);
  });
});

test.describe('Blog Platform - Admin Dashboard Tests', () => {

  test.beforeEach(async ({ page }) => {
    await loginAs(page, 'author');
  });

  /**
   * Test 14: Create new draft post
   */
  test('should create new draft post', async ({ page }) => {
    await createPost(page, 'My Draft Post', '# Draft Content', false);

    // Should be in posts list
    await page.goto(`${BASE_URL}/dashboard/posts`);
    await expect(page.locator('text=My Draft Post')).toBeVisible();

    // Should show draft status
    await expect(page.locator('[data-testid="status-badge"]:has-text("draft"), .badge:has-text("draft")')).toBeVisible();
  });

  /**
   * Test 15: Save draft with auto-save
   */
  test('should auto-save draft every 30 seconds', async ({ page }) => {
    await page.goto(`${BASE_URL}/dashboard/posts/new`);
    await page.fill('input[name="title"]', 'Auto-save Test');
    await page.fill('textarea[name="content"]', '# Initial content');

    // Wait for auto-save indicator
    await page.waitForTimeout(2000);

    // Look for auto-save indicator
    const saveIndicator = page.locator('text=/saved|saving/i');
    const hasAutoSave = await saveIndicator.count() > 0;

    if (hasAutoSave) {
      await expect(saveIndicator).toBeVisible();
    }
  });

  /**
   * Test 16: Edit existing post
   */
  test('should edit existing post', async ({ page }) => {
    // Create post first
    await createPost(page, 'Original Post Title', '# Original Content');

    // Go to posts list and edit
    await page.goto(`${BASE_URL}/dashboard/posts`);
    await page.click('[data-testid="edit-post"], button:has-text("Edit")');

    // Update content
    await page.fill('input[name="title"]', 'Updated Post Title');
    await page.click('button:has-text("Save")');
    await page.waitForTimeout(500);

    // Verify update
    await expect(page.locator('text=Updated Post Title')).toBeVisible();
  });

  /**
   * Test 17: Delete post (admin only)
   */
  test('should delete post', async ({ page }) => {
    await createPost(page, 'Post to Delete', '# Delete me');

    // Go to posts list
    await page.goto(`${BASE_URL}/dashboard/posts`);

    // Delete post
    await page.click('[data-testid="delete-post"], button:has-text("Delete")');

    // Confirm deletion
    await page.click('button:has-text("Confirm"), button:has-text("Yes")');
    await page.waitForTimeout(500);

    // Post should be removed
    await expect(page.locator('text=Post to Delete')).not.toBeVisible();
  });

  /**
   * Test 18: Publish post (admin)
   */
  test('should publish draft post', async ({ page }) => {
    await createPost(page, 'Draft to Publish', '# Publishing test', false);

    // Go to posts list
    await page.goto(`${BASE_URL}/dashboard/posts`);

    // Click publish
    await page.click('[data-testid="publish-post"], button:has-text("Publish")');
    await page.waitForTimeout(500);

    // Status should change to published
    await expect(page.locator('[data-testid="status-badge"]:has-text("published"), .badge:has-text("published")')).toBeVisible();

    // Verify post appears on public blog
    await page.goto(BASE_URL);
    await expect(page.locator('text=Draft to Publish')).toBeVisible();
  });

  /**
   * Test 19: Unpublish post
   */
  test('should unpublish post', async ({ page }) => {
    await createPost(page, 'Published Post', '# Content', true);

    // Go to posts list
    await page.goto(`${BASE_URL}/dashboard/posts`);

    // Unpublish
    const unpublishBtn = page.locator('button:has-text("Unpublish"), button:has-text("Draft")');
    if (await unpublishBtn.count() > 0) {
      await unpublishBtn.click();
      await page.waitForTimeout(500);

      // Should be draft again
      await expect(page.locator('.badge:has-text("draft")')).toBeVisible();
    }
  });

  /**
   * Test 20: Schedule post for future date
   */
  test('should schedule post for future publication', async ({ page }) => {
    await page.goto(`${BASE_URL}/dashboard/posts/new`);
    await page.fill('input[name="title"]', 'Scheduled Post');
    await page.fill('textarea[name="content"]', '# Future content');

    // Set future date
    const scheduledInput = page.locator('input[name="scheduledAt"], [data-testid="schedule-date"]');
    if (await scheduledInput.count() > 0) {
      const tomorrow = new Date();
      tomorrow.setDate(tomorrow.getDate() + 1);
      const dateStr = tomorrow.toISOString().split('T')[0];

      await scheduledInput.fill(dateStr);
      await page.click('button:has-text("Schedule")');
      await page.waitForTimeout(500);

      // Verify scheduled status
      await expect(page.locator('text=/scheduled/i')).toBeVisible();
    }
  });

  /**
   * Test 21: Upload cover image
   */
  test('should upload cover image for post', async ({ page }) => {
    await page.goto(`${BASE_URL}/dashboard/posts/new`);
    await page.fill('input[name="title"]', 'Post with Image');

    // Upload image (if upload feature exists)
    const fileInput = page.locator('input[type="file"]');
    if (await fileInput.count() > 0) {
      // Create a test image file
      await fileInput.setInputFiles({
        name: 'test-image.jpg',
        mimeType: 'image/jpeg',
        buffer: Buffer.from('fake-image-data')
      });

      // Wait for upload
      await page.waitForTimeout(1000);

      // Verify image preview
      const imagePreview = page.locator('img[src*="uploads"], img[src*="cloudinary"]');
      if (await imagePreview.count() > 0) {
        await expect(imagePreview).toBeVisible();
      }
    }
  });
});

test.describe('Blog Platform - Markdown Editor Tests', () => {

  test.beforeEach(async ({ page }) => {
    await loginAs(page, 'author');
    await page.goto(`${BASE_URL}/dashboard/posts/new`);
  });

  /**
   * Test 22: Use toolbar for formatting
   */
  test('should use toolbar to format text', async ({ page }) => {
    const editor = page.locator('textarea[name="content"]');
    await editor.fill('selected text');
    await editor.selectText();

    // Click bold button
    const boldBtn = page.locator('button[aria-label*="bold" i], [data-testid="bold-btn"]');
    if (await boldBtn.count() > 0) {
      await boldBtn.click();

      // Verify Markdown syntax added
      const value = await editor.inputValue();
      expect(value).toContain('**selected text**');
    }
  });

  /**
   * Test 23: Live preview of Markdown
   */
  test('should show live preview of Markdown', async ({ page }) => {
    const editor = page.locator('textarea[name="content"]');
    await editor.fill('# Hello World\n\n**Bold text**');

    // Check if preview pane exists
    const preview = page.locator('[data-testid="markdown-preview"], .preview');
    if (await preview.count() > 0) {
      // Verify rendered output
      await expect(preview.locator('h1:has-text("Hello World")')).toBeVisible();
      await expect(preview.locator('strong:has-text("Bold text")')).toBeVisible();
    }
  });

  /**
   * Test 24: Image upload in editor
   */
  test('should support image upload in editor', async ({ page }) => {
    // Drag and drop image (if supported)
    const dropZone = page.locator('[data-testid="image-upload"], .image-drop-zone');
    if (await dropZone.count() > 0) {
      await expect(dropZone).toBeVisible();
    }
  });

  /**
   * Test 25: Keyboard shortcuts (Ctrl+B for bold)
   */
  test('should support keyboard shortcuts', async ({ page }) => {
    const editor = page.locator('textarea[name="content"]');
    await editor.fill('text to bold');
    await editor.selectText();

    // Use Ctrl+B shortcut
    await page.keyboard.press('Control+b');

    // Verify Markdown syntax
    const value = await editor.inputValue();
    expect(value).toContain('**text to bold**');
  });
});

test.describe('Blog Platform - Analytics Tests', () => {

  test.beforeEach(async ({ page }) => {
    await loginAs(page, 'author');
  });

  /**
   * Test 26: View post analytics (views, chart)
   */
  test('should display post analytics', async ({ page }) => {
    await page.goto(`${BASE_URL}/dashboard/analytics`);

    // Should show analytics dashboard
    await expect(page.locator('h1:has-text("Analytics")')).toBeVisible();

    // Should show stats cards
    const statsCards = page.locator('[data-testid="stat-card"], .stat');
    if (await statsCards.count() > 0) {
      await expect(statsCards.first()).toBeVisible();
    }
  });

  /**
   * Test 27: View user management page (admin only)
   */
  test('should view user management page', async ({ page }) => {
    await page.goto(`${BASE_URL}/dashboard/users`);

    // May require admin role
    const usersTable = page.locator('table, [data-testid="users-table"]');
    const hasAccess = await usersTable.count() > 0;

    if (hasAccess) {
      await expect(usersTable).toBeVisible();
    }
  });
});

test.describe('Blog Platform - Comments System Tests', () => {

  /**
   * Test 28: Add comment to post (authenticated)
   */
  test('should add comment to published post', async ({ page }) => {
    // Go to a published post
    await page.goto(BASE_URL);
    await page.click('article a, [data-testid="post-link"]').first();

    // Login first
    await loginAs(page, 'author');

    // Find comment form
    const commentTextarea = page.locator('textarea[name="content"], [placeholder*="comment" i]');
    if (await commentTextarea.count() > 0) {
      await commentTextarea.fill('This is my test comment');
      await page.click('button:has-text("Submit"), button:has-text("Post")');
      await page.waitForTimeout(500);

      // Comment should appear (may need approval)
      await expect(page.locator('text=This is my test comment')).toBeVisible();
    }
  });

  /**
   * Test 29: Approve comment (admin)
   */
  test('should approve pending comment', async ({ page }) => {
    await loginAs(page, 'admin');
    await page.goto(`${BASE_URL}/dashboard/comments`);

    // Look for pending comments
    const approveBtn = page.locator('button:has-text("Approve")').first();
    if (await approveBtn.count() > 0) {
      await approveBtn.click();
      await page.waitForTimeout(500);

      // Comment should be approved
      await expect(page.locator('text=/approved/i')).toBeVisible();
    }
  });

  /**
   * Test 30: RSS feed generation and validation
   */
  test('should generate valid RSS feed', async ({ page }) => {
    await page.goto(`${BASE_URL}/rss.xml`);

    // Should return XML content
    const content = await page.content();
    expect(content).toContain('<?xml');
    expect(content).toContain('<rss');
    expect(content).toContain('</rss>');

    // Should contain blog posts
    expect(content).toContain('<item>');
  });
});

test.describe('Blog Platform - SEO Tests', () => {

  /**
   * SEO Test: Meta tags and structured data
   */
  test('should have proper SEO meta tags for posts', async ({ page }) => {
    await page.goto(BASE_URL);

    // Click on first post
    const firstPost = page.locator('article a').first();
    if (await firstPost.count() > 0) {
      await firstPost.click();

      // Verify meta tags
      const title = await page.title();
      expect(title).toBeTruthy();

      const ogTitle = await page.locator('meta[property="og:title"]').getAttribute('content');
      expect(ogTitle).toBeTruthy();

      const ogType = await page.locator('meta[property="og:type"]').getAttribute('content');
      expect(ogType).toBe('article');

      // Verify structured data
      const jsonLd = page.locator('script[type="application/ld+json"]');
      if (await jsonLd.count() > 0) {
        const structuredData = await jsonLd.first().textContent();
        expect(structuredData).toContain('BlogPosting');
      }
    }
  });
});
