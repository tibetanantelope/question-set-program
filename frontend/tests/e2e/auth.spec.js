import { expect, test } from '@playwright/test'

test('shows the student login and registration entry points', async ({ page }) => {
  await page.goto('/')
  await expect(page.getByRole('heading', { name: '欢迎回来' })).toBeVisible()
  await expect(page.getByRole('button', { name: '登录', exact: true })).toBeVisible()
  await page.getByRole('button', { name: '注册', exact: true }).click()
  await expect(page.getByRole('heading', { name: '创建学生账号' })).toBeVisible()
})
