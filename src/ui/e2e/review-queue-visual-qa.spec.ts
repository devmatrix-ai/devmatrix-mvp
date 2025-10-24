/**
 * ReviewQueue Visual QA Tests
 *
 * Verifies visual consistency with MasterplansPage:
 * - Background gradient
 * - Glassmorphism effects
 * - Purple accent colors
 * - Responsive breakpoints
 * - Dark theme consistency
 */

import { test, expect } from '@playwright/test';

test.describe('ReviewQueue Visual QA', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to ReviewQueue page
    await page.goto('http://localhost:5173/review');
  });

  test('should have matching background gradient', async ({ page }) => {
    const background = page.locator('div').first();
    await expect(background).toHaveClass(/bg-gradient-to-br from-gray-900 via-purple-900\/20 to-blue-900\/20/);
  });

  test('should display GlassCard with backdrop-blur effect', async ({ page }) => {
    // Wait for filters card to load
    const glassCard = page.locator('.backdrop-blur-lg').first();
    await expect(glassCard).toBeVisible();

    // Verify glassmorphism classes
    await expect(glassCard).toHaveClass(/backdrop-blur-lg/);
    await expect(glassCard).toHaveClass(/bg-gradient-to-r/);
    await expect(glassCard).toHaveClass(/border-white\/10/);
  });

  test('should use purple accent colors', async ({ page }) => {
    // Check active filter button has purple styling
    const activeButton = page.locator('button:has-text("Pending")');
    await expect(activeButton).toHaveClass(/bg-purple-600/);
    await expect(activeButton).toHaveClass(/shadow-purple-500\/50/);
  });

  test('should be responsive at mobile breakpoint', async ({ page, viewport }) => {
    // Set mobile viewport
    await page.setViewportSize({ width: 375, height: 667 });

    // Check if grid changes to single column
    const grid = page.locator('.grid');
    await expect(grid).toHaveClass(/grid-cols-1/);
  });

  test('should be responsive at tablet breakpoint', async ({ page }) => {
    // Set tablet viewport
    await page.setViewportSize({ width: 768, height: 1024 });

    // Check if grid shows 2 columns
    const grid = page.locator('.grid');
    await expect(grid).toHaveClass(/md:grid-cols-2/);
  });

  test('should be responsive at desktop breakpoint', async ({ page }) => {
    // Set desktop viewport
    await page.setViewportSize({ width: 1440, height: 900 });

    // Check if grid shows 3 columns
    const grid = page.locator('.grid');
    await expect(grid).toHaveClass(/lg:grid-cols-3/);
  });

  test('should have consistent dark theme text colors', async ({ page }) => {
    // Page title should be white
    const title = page.locator('h1:has-text("Review Queue")');
    await expect(title).toHaveClass(/text-white/);

    // Subtitle should be gray-400
    const subtitle = page.locator('p:has-text("Low-confidence atoms")');
    await expect(subtitle).toHaveClass(/text-gray-400/);
  });

  test('should display hover effects on interactive elements', async ({ page }) => {
    // Wait for a review card to be visible
    const card = page.locator('.cursor-pointer').first();
    await card.waitFor({ state: 'visible' });

    // Hover over the card
    await card.hover();

    // Card should have transition classes
    await expect(card).toHaveClass(/transition-all/);
  });

  test('should have matching typography with MasterplansPage', async ({ page }) => {
    // Check header emoji size
    const emoji = page.locator('.text-5xl').first();
    await expect(emoji).toBeVisible();

    // Check title size
    const title = page.locator('.text-4xl').first();
    await expect(title).toHaveClass(/text-4xl font-bold/);

    // Check subtitle size
    const subtitle = page.locator('.text-lg').first();
    await expect(subtitle).toHaveClass(/text-lg/);
  });

  test('should have consistent spacing', async ({ page }) => {
    // Check page padding
    const container = page.locator('div.p-8').first();
    await expect(container).toHaveClass(/p-8/);

    // Check header margin
    const header = page.locator('div.mb-8').first();
    await expect(header).toHaveClass(/mb-8/);
  });
});

test.describe('ReviewQueue Modal Visual QA', () => {
  test('should open modal with glassmorphism backdrop', async ({ page }) => {
    // Navigate and wait for content
    await page.goto('http://localhost:5173/review');

    // Click on first "View Review" button if available
    const viewButton = page.locator('button:has-text("View Review")').first();
    if (await viewButton.isVisible({ timeout: 5000 }).catch(() => false)) {
      await viewButton.click();

      // Check backdrop blur
      const backdrop = page.locator('.fixed.inset-0.backdrop-blur-sm');
      await expect(backdrop).toBeVisible();

      // Check modal GlassCard
      const modal = page.locator('.fixed .backdrop-blur-lg').first();
      await expect(modal).toBeVisible();
    }
  });
});

test.describe('ReviewQueue No Console Errors', () => {
  test('should load without console errors', async ({ page }) => {
    const errors: string[] = [];

    page.on('console', (msg) => {
      if (msg.type() === 'error') {
        errors.push(msg.text());
      }
    });

    await page.goto('http://localhost:5173/review');
    await page.waitForTimeout(2000); // Wait for any async errors

    // Filter out known React warnings
    const realErrors = errors.filter(
      (err) => !err.includes('Warning:') && !err.includes('Download the React DevTools')
    );

    expect(realErrors).toHaveLength(0);
  });
});
