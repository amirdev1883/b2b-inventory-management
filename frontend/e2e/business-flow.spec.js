import { test, expect } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

async function register(page) {
  await page.goto('/');
  await page.getByRole('button', { name: 'Create a workspace' }).click();
  await page.getByLabel('Business name').fill('Cedar Test Supply');
  await page.getByLabel('First name').fill('Amir');
  await page.getByLabel('Last name').fill('Arani');
  await page.getByLabel('Email address').fill(`e2e-${crypto.randomUUID()}@example.com`);
  await page.getByLabel('Password', { exact: true }).fill('Test-password-9384!');
  await page.getByRole('button', { name: 'Create workspace', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Hello, Amir.' })).toBeVisible();
}

test('complete purchasing, sales, invoice and session workflow', async ({ page }) => {
  const errors = [];
  page.on('pageerror', (error) => errors.push(error.message));
  await register(page);
  await expect(page.getByText('Shipped revenue', { exact: true })).toBeVisible();
  const accessibility = await new AxeBuilder({ page })
    .withTags(['wcag2a', 'wcag2aa', 'wcag21aa'])
    .analyze();
  expect(accessibility.violations).toEqual([]);
  await page.getByRole('link', { name: 'Suppliers', exact: true }).click();
  await page.getByRole('button', { name: 'Add supplier', exact: true }).click();
  await page.getByLabel('Supplier name').fill('Maple Partner');
  await page.getByRole('dialog').getByRole('button', { name: 'Add supplier', exact: true }).click();
  await expect(page.getByRole('dialog')).toHaveCount(0);
  await page.getByRole('link', { name: 'Inventory', exact: true }).click();
  await page.getByRole('button', { name: 'Add product', exact: true }).click();
  await page.getByLabel('Product name').fill('Test Desk Lamp');
  await page.getByLabel('SKU', { exact: true }).fill('LAMP-E2E');
  await page.getByLabel('Cost price').fill('10.00');
  await page.getByLabel('Sale price').fill('25.25');
  await page.getByLabel('Supplier', { exact: true }).selectOption({ label: 'Maple Partner' });
  await page.getByRole('dialog').getByRole('button', { name: 'Add product', exact: true }).click();
  await expect(page.getByRole('dialog')).toHaveCount(0);
  await expect(page.getByText('Test Desk Lamp', { exact: true })).toBeVisible();
  await page.getByRole('link', { name: 'Purchase orders', exact: true }).click();
  await page.getByRole('button', { name: 'New purchase order', exact: true }).click();
  await page.getByLabel('Supplier', { exact: true }).selectOption({ label: 'Maple Partner' });
  await page.getByLabel('Product 1', { exact: true }).selectOption({ index: 1 });
  await page.getByLabel('Quantity 1', { exact: true }).fill('10');
  await page.getByRole('button', { name: 'Create draft order' }).click();
  await expect(page.getByRole('button', { name: 'Receive stock', exact: true })).toBeVisible();
  await page.getByRole('button', { name: 'Receive stock', exact: true }).click();
  await page
    .getByRole('dialog')
    .last()
    .getByRole('button', { name: 'Receive stock', exact: true })
    .click();
  await expect(page.getByText('Received', { exact: true }).last()).toBeVisible();
  await expect(page.getByRole('dialog')).toHaveCount(1);
  await page.getByRole('button', { name: 'Close dialog', exact: true }).click();
  await page.getByRole('link', { name: 'Overview', exact: true }).click();
  await page.getByRole('link', { name: 'New sales order', exact: false }).click();
  await page.getByLabel('Customer name').fill('Cedar Studio');
  await page.getByLabel('Product 1', { exact: true }).selectOption({ index: 1 });
  await page.getByLabel('Quantity 1', { exact: true }).fill('3');
  await page.getByLabel('Tax rate (%)', { exact: true }).fill('13');
  await page.getByRole('button', { name: 'Create draft order' }).click();
  await expect(page.getByRole('button', { name: 'Confirm order', exact: true })).toBeVisible();
  await page.reload();
  await page.getByRole('button', { name: 'Confirm order', exact: true }).click();
  await page
    .getByRole('dialog')
    .last()
    .getByRole('button', { name: 'Confirm order', exact: true })
    .click();
  await expect(page.getByRole('button', { name: 'Ship order', exact: true })).toBeVisible();
  await page.getByRole('button', { name: 'Ship order', exact: true }).click();
  await page
    .getByRole('dialog')
    .last()
    .getByRole('button', { name: 'Ship order', exact: true })
    .click();
  await expect(page.getByRole('dialog')).toHaveCount(1);
  const downloadEvent = page.waitForEvent('download');
  await page.getByRole('button', { name: 'Download invoice' }).click();
  const download = await downloadEvent;
  expect(download.suggestedFilename()).toMatch(/^INV-.*\.pdf$/);
  await page.getByRole('button', { name: 'Close dialog', exact: true }).click();
  await page.reload();
  await expect(page.getByRole('heading', { name: 'Sales orders', exact: true })).toBeVisible();
  await page.getByRole('link', { name: 'Inventory', exact: true }).click();
  const row = page.getByRole('row').filter({ hasText: 'Test Desk Lamp' });
  await expect(row.getByRole('cell', { name: '7', exact: true }).first()).toBeVisible();
  await page.getByRole('link', { name: 'Stock activity', exact: true }).click();
  await expect(page.getByRole('cell', { name: '-3', exact: true }).first()).toBeVisible();
  expect(errors).toEqual([]);
});

test('mobile navigation, empty states and sign out', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await register(page);
  await expect(page.getByText('Shipped revenue', { exact: true })).toBeVisible();
  const accessibility = await new AxeBuilder({ page })
    .withTags(['wcag2a', 'wcag2aa', 'wcag21aa'])
    .analyze();
  expect(accessibility.violations).toEqual([]);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(
    true,
  );
  await page.getByRole('button', { name: 'Open navigation' }).click();
  await page.getByRole('link', { name: 'Inventory', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Inventory', exact: true })).toBeVisible();
  await expect(page.getByRole('heading', { name: 'No products found' })).toBeVisible();
  await page.getByRole('button', { name: 'Open navigation' }).click();
  await page.getByRole('button', { name: 'Sign out', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Welcome back.' })).toBeVisible();
});
