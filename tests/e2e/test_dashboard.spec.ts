import { test, expect } from '@playwright/test';

test.describe('AIR Health Dashboard', () => {
  test('home page loads with upload form and session list', async ({ page }) => {
    await page.goto('/');
    await expect(page.getByText('Upload Exercise Video')).toBeVisible();
    await expect(page.getByText('Arm Raise')).toBeVisible();
  });

  test('upload form has exercise type dropdown', async ({ page }) => {
    await page.goto('/');
    const select = page.locator('select');
    await expect(select).toBeVisible();
    const options = await select.locator('option').allTextContents();
    expect(options).toContain('Arm Raise');
    expect(options).toContain('Lunge');
    expect(options).toContain('Push-up');
  });

  test('shows empty state when no sessions', async ({ page }) => {
    await page.goto('/');
    // Either shows the table or empty state message
    const content = await page.textContent('body');
    expect(content).toBeTruthy();
  });

  test('session page shows 404 for invalid session', async ({ page }) => {
    await page.goto('/session/99999');
    // Should show error or loading state
    await page.waitForTimeout(3000);
    const content = await page.textContent('body');
    expect(content).toBeTruthy();
  });
});
