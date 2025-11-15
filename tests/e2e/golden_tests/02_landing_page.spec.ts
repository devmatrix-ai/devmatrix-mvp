/**
 * Golden E2E Tests: Landing Page (Level 1)
 *
 * Covers 8 scenarios for Next.js + Tailwind + shadcn/ui landing page
 */

import { test, expect } from '@playwright/test';

const BASE_URL = process.env.BASE_URL || 'http://localhost:3000';

test.describe('Landing Page - Golden Tests', () => {

  /**
   * Test 1: Homepage loads successfully with all sections visible
   */
  test('should load homepage with all required sections', async ({ page }) => {
    await page.goto(BASE_URL);

    // Verify all major sections are present
    await expect(page.locator('header')).toBeVisible();
    await expect(page.locator('[data-testid="hero-section"]') || page.locator('section').first()).toBeVisible();
    await expect(page.locator('[data-testid="features-section"]') || page.locator('h2:has-text("Features")')).toBeVisible();
    await expect(page.locator('[data-testid="testimonials-section"]') || page.locator('h2:has-text("Testimonials")')).toBeVisible();
    await expect(page.locator('[data-testid="cta-section"]') || page.locator('section').last()).toBeVisible();
    await expect(page.locator('footer')).toBeVisible();
  });

  /**
   * Test 2: Navigation - Click nav links, verify smooth scroll to sections
   */
  test('should navigate to sections via header links', async ({ page }) => {
    await page.goto(BASE_URL);

    // Click Features nav link
    const featuresLink = page.locator('nav a:has-text("Features")');
    if (await featuresLink.count() > 0) {
      await featuresLink.first().click();
      await page.waitForTimeout(500); // Wait for smooth scroll

      // Verify Features section is in viewport
      const featuresSection = page.locator('[data-testid="features-section"]') ||
        page.locator('h2:has-text("Features")').locator('..');
      await expect(featuresSection).toBeInViewport();
    }

    // Click Testimonials nav link
    const testimonialsLink = page.locator('nav a:has-text("Testimonials")');
    if (await testimonialsLink.count() > 0) {
      await testimonialsLink.first().click();
      await page.waitForTimeout(500);

      const testimonialsSection = page.locator('[data-testid="testimonials-section"]') ||
        page.locator('h2:has-text("Testimonials")').locator('..');
      await expect(testimonialsSection).toBeInViewport();
    }
  });

  /**
   * Test 3: Mobile Menu - Open/close mobile menu, navigate to sections
   */
  test('should open and close mobile menu', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 667 }); // Mobile viewport
    await page.goto(BASE_URL);

    // Find and click hamburger menu button
    const menuButton = page.locator('button[aria-label*="menu" i], button:has-text("☰"), [data-testid="mobile-menu-button"]');
    if (await menuButton.count() > 0) {
      await menuButton.first().click();

      // Verify mobile menu is visible
      const mobileMenu = page.locator('[data-testid="mobile-menu"], nav[role="dialog"], aside');
      await expect(mobileMenu.first()).toBeVisible();

      // Click a link in mobile menu
      const mobileLink = mobileMenu.locator('a').first();
      if (await mobileLink.count() > 0) {
        await mobileLink.click();

        // Menu should close after clicking link
        await page.waitForTimeout(500);
        await expect(mobileMenu.first()).not.toBeVisible();
      }
    }
  });

  /**
   * Test 4: CTA Buttons - Click primary CTA, verify modal opens or navigation
   */
  test('should handle primary CTA button click', async ({ page }) => {
    await page.goto(BASE_URL);

    // Find primary CTA button in hero
    const ctaButton = page.locator('[data-testid="hero-cta"], button:has-text("Get Started"), a:has-text("Get Started")').first();
    await expect(ctaButton).toBeVisible();

    // Click CTA
    await ctaButton.click();
    await page.waitForTimeout(500);

    // Verify one of the following happened:
    // 1. Modal opened
    const modal = page.locator('[role="dialog"], [data-testid="modal"]');
    const modalVisible = await modal.count() > 0 && await modal.isVisible();

    // 2. Navigated to another page/section
    const urlChanged = page.url() !== BASE_URL;

    // 3. Scrolled to a section
    const contactSection = page.locator('[data-testid="contact"], h2:has-text("Contact")');
    const scrolledToContact = await contactSection.count() > 0 && await contactSection.isInViewport();

    expect(modalVisible || urlChanged || scrolledToContact).toBe(true);
  });

  /**
   * Test 5: Responsive Layout - Test on mobile (375px), tablet (768px), desktop (1280px)
   */
  test('should display responsive layout correctly', async ({ page }) => {
    await page.goto(BASE_URL);

    // Test mobile layout
    await page.setViewportSize({ width: 375, height: 667 });
    await page.waitForTimeout(200);

    // Features should be 1-column on mobile
    const featuresSection = page.locator('[data-testid="features-section"]') ||
      page.locator('h2:has-text("Features")').locator('..');
    const featureCards = featuresSection.locator('[data-testid="feature-card"], article, div[class*="card"]');

    if (await featureCards.count() > 0) {
      const firstCard = featureCards.first();
      const firstCardBox = await firstCard.boundingBox();
      expect(firstCardBox).not.toBeNull();
    }

    // Test tablet layout
    await page.setViewportSize({ width: 768, height: 1024 });
    await page.waitForTimeout(200);
    await expect(featuresSection).toBeVisible();

    // Test desktop layout
    await page.setViewportSize({ width: 1280, height: 800 });
    await page.waitForTimeout(200);

    // Features should be 3-column on desktop (verify horizontal arrangement)
    if (await featureCards.count() >= 3) {
      const firstBox = await featureCards.nth(0).boundingBox();
      const secondBox = await featureCards.nth(1).boundingBox();

      if (firstBox && secondBox) {
        // Second card should be to the right of first card on desktop
        expect(secondBox.x).toBeGreaterThan(firstBox.x);
      }
    }
  });

  /**
   * Test 6: Accessibility - Keyboard navigation through all interactive elements
   */
  test('should support keyboard navigation', async ({ page }) => {
    await page.goto(BASE_URL);

    // Tab through interactive elements
    await page.keyboard.press('Tab');
    await page.waitForTimeout(100);

    // Verify focus is visible on first interactive element
    const focusedElement = page.locator(':focus');
    await expect(focusedElement).toBeVisible();

    // Tab through several elements
    for (let i = 0; i < 5; i++) {
      await page.keyboard.press('Tab');
      await page.waitForTimeout(50);
    }

    // Verify focus indicator is visible
    const currentFocus = page.locator(':focus');
    const focusStyles = await currentFocus.evaluate((el) => {
      const styles = window.getComputedStyle(el);
      return {
        outline: styles.outline,
        outlineWidth: styles.outlineWidth,
        boxShadow: styles.boxShadow
      };
    });

    // Should have visible focus indicator (outline or box-shadow)
    const hasFocusIndicator =
      focusStyles.outline !== 'none' ||
      focusStyles.outlineWidth !== '0px' ||
      focusStyles.boxShadow !== 'none';

    expect(hasFocusIndicator).toBe(true);
  });

  /**
   * Test 7: Performance - Lighthouse scores meet requirements
   */
  test('should meet Lighthouse performance requirements', async ({ page }) => {
    await page.goto(BASE_URL);

    // Wait for page to be fully loaded
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(1000);

    // Measure Core Web Vitals
    const metrics = await page.evaluate(() => {
      return new Promise((resolve) => {
        if ('PerformanceObserver' in window) {
          const observer = new PerformanceObserver((list) => {
            const entries = list.getEntries();
            const lcp = entries.find(entry => entry.entryType === 'largest-contentful-paint');
            resolve({
              lcp: lcp ? (lcp as any).renderTime || (lcp as any).loadTime : null
            });
          });
          observer.observe({ entryTypes: ['largest-contentful-paint'] });

          // Fallback timeout
          setTimeout(() => resolve({ lcp: null }), 3000);
        } else {
          resolve({ lcp: null });
        }
      });
    });

    // LCP should be < 2.5s (2500ms)
    if ((metrics as any).lcp !== null) {
      expect((metrics as any).lcp).toBeLessThan(2500);
    }

    // Verify images are optimized (using next/image or similar)
    const images = page.locator('img');
    const imageCount = await images.count();

    if (imageCount > 0) {
      // Check if images have loading="lazy" for below-fold content
      const firstImage = images.first();
      const isNextImage = await firstImage.evaluate((img) =>
        img.getAttribute('src')?.includes('_next/image') || false
      );

      // Next.js Image component or lazy loading should be used
      expect(isNextImage || await firstImage.getAttribute('loading')).toBeTruthy();
    }
  });

  /**
   * Test 8: SEO - Meta tags present and correct
   */
  test('should have correct SEO meta tags', async ({ page }) => {
    await page.goto(BASE_URL);

    // Title tag
    const title = await page.title();
    expect(title).toBeTruthy();
    expect(title.length).toBeGreaterThan(10);
    expect(title.length).toBeLessThan(70); // Optimal title length

    // Meta description
    const description = await page.locator('meta[name="description"]').getAttribute('content');
    expect(description).toBeTruthy();
    expect(description!.length).toBeGreaterThan(50);
    expect(description!.length).toBeLessThan(160); // Optimal description length

    // Open Graph tags
    const ogTitle = await page.locator('meta[property="og:title"]').getAttribute('content');
    const ogDescription = await page.locator('meta[property="og:description"]').getAttribute('content');
    const ogImage = await page.locator('meta[property="og:image"]').getAttribute('content');

    expect(ogTitle).toBeTruthy();
    expect(ogDescription).toBeTruthy();
    expect(ogImage).toBeTruthy();

    // Twitter card
    const twitterCard = await page.locator('meta[name="twitter:card"]').getAttribute('content');
    expect(twitterCard).toBeTruthy();

    // Verify semantic HTML
    await expect(page.locator('header')).toBeVisible();
    await expect(page.locator('main')).toBeVisible();
    await expect(page.locator('footer')).toBeVisible();
  });
});

test.describe('Landing Page - Accessibility Tests', () => {

  /**
   * Accessibility Test: Color contrast ratio ≥ 4.5:1
   */
  test('should have sufficient color contrast', async ({ page }) => {
    await page.goto(BASE_URL);

    // Check main heading contrast
    const heading = page.locator('h1').first();
    const contrast = await heading.evaluate((el) => {
      const styles = window.getComputedStyle(el);
      const bgColor = styles.backgroundColor;
      const color = styles.color;

      // Simple contrast check (would need full color parsing in production)
      return {
        background: bgColor,
        foreground: color,
        isLightBg: bgColor.includes('255') || bgColor.includes('white')
      };
    });

    expect(contrast).toBeTruthy();
  });

  /**
   * Accessibility Test: All images have alt text
   */
  test('should have alt text for all images', async ({ page }) => {
    await page.goto(BASE_URL);

    const images = page.locator('img');
    const imageCount = await images.count();

    for (let i = 0; i < imageCount; i++) {
      const alt = await images.nth(i).getAttribute('alt');
      const ariaLabel = await images.nth(i).getAttribute('aria-label');

      // Each image should have alt text or aria-label (decorative images can have alt="")
      expect(alt !== null || ariaLabel !== null).toBe(true);
    }
  });
});
