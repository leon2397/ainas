const { test, expect } = require('@playwright/test');

// 测试配置
test.use({
  baseURL: 'http://localhost:8000',
  headless: true,
  screenshot: 'only-on-failure',
  video: 'retain-on-failure',
});

/**
 * 认证流程 E2E 测试
 */
test.describe('认证流程', () => {
  
  test('登录页面显示正确', async ({ page }) => {
    await page.goto('/');
    
    // 验证页面标题
    await expect(page).toHaveTitle(/AI-NAS/);
    
    // 验证登录表单存在
    await expect(page.locator('input[name="username"]')).toBeVisible();
    await expect(page.locator('input[name="password"]')).toBeVisible();
    await expect(page.locator('button[type="submit"]')).toBeVisible();
    
    // 验证中文显示正确
    await expect(page.locator('text=登录')).toBeVisible();
    await expect(page.locator('text=用户名')).toBeVisible();
    await expect(page.locator('text=密码')).toBeVisible();
  });

  test('成功登录并跳转', async ({ page }) => {
    await page.goto('/');
    
    // 填写登录表单
    await page.fill('input[name="username"]', 'admin');
    await page.fill('input[name="password"]', 'admin123');
    
    // 点击登录
    await page.click('button[type="submit"]');
    
    // 等待跳转
    await page.waitForURL('**/dashboard**', { timeout: 5000 });
    
    // 验证登录成功
    await expect(page.locator('.sidebar')).toBeVisible();
    await expect(page.locator('text=仪表盘')).toBeVisible();
    
    // 验证token已存储
    const token = await page.evaluate(() => localStorage.getItem('token'));
    expect(token).toBeTruthy();
  });

  test('登录失败显示错误', async ({ page }) => {
    await page.goto('/');
    
    // 填写错误密码
    await page.fill('input[name="username"]', 'admin');
    await page.fill('input[name="password"]', 'wrong_password');
    
    // 点击登录
    await page.click('button[type="submit"]');
    
    // 验证错误提示
    await expect(page.locator('.alert-danger, .error-message')).toBeVisible();
    await expect(page.locator('text=用户名或密码错误')).toBeVisible();
    
    // 验证未跳转
    await expect(page).toHaveURL('/');
  });

  test('记住用户名功能', async ({ page }) => {
    await page.goto('/');
    
    // 填写并勾选记住我
    await page.fill('input[name="username"]', 'admin');
    await page.fill('input[name="password"]', 'admin123');
    await page.check('input[name="remember"]');
    
    // 登录
    await page.click('button[type="submit"]');
    await page.waitForURL('**/dashboard**');
    
    // 退出登录
    await page.click('text=退出');
    await page.waitForURL('/');
    
    // 验证用户名已记住
    const savedUsername = await page.inputValue('input[name="username"]');
    expect(savedUsername).toBe('admin');
  });

  test('未登录访问受保护页面重定向', async ({ page }) => {
    // 直接访问仪表盘
    await page.goto('/dashboard');
    
    // 应该重定向到登录页
    await expect(page).toHaveURL('/');
    
    // 显示提示信息
    await expect(page.locator('text=请先登录')).toBeVisible();
  });

  test('Token过期自动退出', async ({ page }) => {
    await page.goto('/');
    
    // 登录
    await page.fill('input[name="username"]', 'admin');
    await page.fill('input[name="password"]', 'admin123');
    await page.click('button[type="submit"]');
    await page.waitForURL('**/dashboard**');
    
    // 模拟token过期
    await page.evaluate(() => {
      localStorage.setItem('token', 'invalid_token');
    });
    
    // 刷新页面
    await page.reload();
    
    // 应该重定向到登录页
    await expect(page).toHaveURL('/');
  });
});
