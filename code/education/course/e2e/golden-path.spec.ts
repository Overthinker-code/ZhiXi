/**
 * Golden Path E2E checklist (requires: npx playwright install)
 * Run: npx playwright test e2e/golden-path.spec.ts
 */
import { test, expect } from '@playwright/test';

test.describe('ZhiXi Golden Path', () => {
  test('student login lands on AI tutor', async ({ page }) => {
    await page.goto('/login');
    await page.fill('input[type="email"], input[placeholder*="邮箱"]', 'student@example.com');
    await page.fill('input[type="password"]', 'student123456');
    await page.click('button[type="submit"]');
    await page.waitForURL(/\/tutor/);
    await expect(page).toHaveURL(/\/tutor/);
  });

  test('teacher profile shows class insights menu target', async ({ page }) => {
    await page.goto('/login');
    await page.fill('input[type="email"], input[placeholder*="邮箱"]', 'admin@example.com');
    await page.fill('input[type="password"]', 'changethis');
    await page.click('button[type="submit"]');
    await page.waitForURL(/\/dashboard/);
    await page.goto('/profile/class-insights');
    await expect(page.getByText('班级学情洞察')).toBeVisible();
  });
});
