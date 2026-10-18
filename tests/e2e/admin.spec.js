/**
 * 管理员界面 E2E 测试
 * 覆盖：用户管理、角色管理、审计日志、系统配置
 */
const { test, expect } = require('@playwright/test');

// 测试配置
const TEST_ADMIN_USER = {
  username: 'admin',
  password: 'admin123'
};

const TEST_ROLES = {
  admin: { name: 'Admin', permissions: ['*'] },
  operator: { name: 'Operator', permissions: ['media:read', 'media:write'] },
  viewer: { name: 'Viewer', permissions: ['media:read'] },
  guest: { name: 'Guest', permissions: [] }
};

test.describe('管理员登录', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/login');
  });

  test('应该能够使用管理员账号登录', async ({ page }) => {
    await page.fill('[name="username"]', TEST_ADMIN_USER.username);
    await page.fill('[name="password"]', TEST_ADMIN_USER.password);
    await page.click('button[type="submit"]');
    
    // 等待登录成功，跳转到仪表板
    await page.waitForURL('**/dashboard');
    await expect(page.locator('.user-name')).toContainText('admin');
  });

  test('登录失败应该显示错误提示', async ({ page }) => {
    await page.fill('[name="username"]', 'admin');
    await page.fill('[name="password"]', 'wrongpassword');
    await page.click('button[type="submit"]');
    
    await expect(page.locator('.error-message')).toBeVisible();
    await expect(page.locator('.error-message')).toContainText('用户名或密码错误');
  });

  test('应该能够登出', async ({ page }) => {
    // 先登录
    await page.goto('/login');
    await page.fill('[name="username"]', TEST_ADMIN_USER.username);
    await page.fill('[name="password"]', TEST_ADMIN_USER.password);
    await page.click('button[type="submit"]');
    await page.waitForURL('**/dashboard');
    
    // 点击登出
    await page.click('.user-menu');
    await page.click('button:has-text("退出登录")');
    
    await page.waitForURL('**/login');
  });
});

test.describe('仪表板', () => {
  test.beforeEach(async ({ page }) => {
    // 登录
    await page.goto('/login');
    await page.fill('[name="username"]', TEST_ADMIN_USER.username);
    await page.fill('[name="password"]', TEST_ADMIN_USER.password);
    await page.click('button[type="submit"]');
    await page.waitForURL('**/dashboard');
  });

  test('应该显示系统概览', async ({ page }) => {
    await page.goto('/dashboard');
    
    // 检查关键指标
    await expect(page.locator('.stat-card:has-text("媒体文件")')).toBeVisible();
    await expect(page.locator('.stat-card:has-text("相册")')).toBeVisible();
    await expect(page.locator('.stat-card:has-text("存储空间")')).toBeVisible();
    await expect(page.locator('.stat-card:has-text("用户数")')).toBeVisible();
  });

  test('应该显示最近活动', async ({ page }) => {
    await page.goto('/dashboard');
    
    await expect(page.locator('.recent-activity')).toBeVisible();
    await expect(page.locator('.activity-list')).toBeVisible();
  });

  test('应该显示系统健康状态', async ({ page }) => {
    await page.goto('/dashboard');
    
    await expect(page.locator('.system-health')).toBeVisible();
    await expect(page.locator('.health-indicator')).toBeVisible();
  });
});

test.describe('用户管理', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/login');
    await page.fill('[name="username"]', TEST_ADMIN_USER.username);
    await page.fill('[name="password"]', TEST_ADMIN_USER.password);
    await page.click('button[type="submit"]');
    await page.waitForURL('**/dashboard');
    await page.goto('/admin/users');
  });

  test('应该显示用户列表', async ({ page }) => {
    await expect(page.locator('.user-list')).toBeVisible();
    await expect(page.locator('.user-row')).toHaveCount({ minimum: 1 });
  });

  test('应该能够搜索用户', async ({ page }) => {
    await page.fill('.search-input', 'admin');
    await page.click('.search-button');
    
    await expect(page.locator('.user-list')).toBeVisible();
  });

  test('应该能够创建新用户', async ({ page }) => {
    await page.click('.btn-create-user');
    
    // 填写用户表单
    await page.fill('[name="username"]', 'newuser');
    await page.fill('[name="email"]', 'newuser@example.com');
    await page.fill('[name="password"]', 'NewPass123!');
    await page.fill('[name="confirmPassword"]', 'NewPass123!');
    await page.selectOption('[name="role"]', 'viewer');
    
    await page.click('.btn-submit');
    
    // 验证成功
    await expect(page.locator('.toast-success')).toBeVisible();
  });

  test('应该能够编辑用户', async ({ page }) => {
    // 点击第一个用户的编辑按钮
    await page.click('.user-row:first-child .btn-edit');
    
    // 修改用户信息
    await page.fill('[name="displayName"]', 'Updated Name');
    
    await page.click('.btn-save');
    
    await expect(page.locator('.toast-success')).toBeVisible();
  });

  test('应该能够删除用户', async ({ page }) => {
    // 点击第一个用户的删除按钮
    await page.click('.user-row:first-child .btn-delete');
    
    // 确认删除
    await page.click('.confirm-dialog .btn-confirm');
    
    await expect(page.locator('.toast-success')).toBeVisible();
  });

  test('应该能够分配角色', async ({ page }) => {
    await page.click('.user-row:first-child .btn-assign-role');
    
    await page.selectOption('[name="role"]', 'operator');
    await page.click('.btn-assign');
    
    await expect(page.locator('.toast-success')).toBeVisible();
  });

  test('应该能够禁用/启用用户', async ({ page }) => {
    const initialStatus = await page.locator('.user-row:first-child .status-badge').textContent();
    
    await page.click('.user-row:first-child .btn-toggle-status');
    
    await expect(page.locator('.toast-success')).toBeVisible();
    
    const newStatus = await page.locator('.user-row:first-child .status-badge').textContent();
    expect(newStatus).not.toBe(initialStatus);
  });
});

test.describe('角色管理', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/login');
    await page.fill('[name="username"]', TEST_ADMIN_USER.username);
    await page.fill('[name="password"]', TEST_ADMIN_USER.password);
    await page.click('button[type="submit"]');
    await page.waitForURL('**/dashboard');
    await page.goto('/admin/roles');
  });

  test('应该显示角色列表', async ({ page }) => {
    await expect(page.locator('.role-list')).toBeVisible();
    
    // 检查默认角色
    for (const role of Object.values(TEST_ROLES)) {
      await expect(page.locator(`.role-card:has-text("${role.name}")`)).toBeVisible();
    }
  });

  test('应该能够查看角色详情', async ({ page }) => {
    await page.click('.role-card:first-child');
    
    await expect(page.locator('.role-detail-modal')).toBeVisible();
    await expect(page.locator('.permission-list')).toBeVisible();
  });

  test('应该能够创建新角色', async ({ page }) => {
    await page.click('.btn-create-role');
    
    await page.fill('[name="roleName"]', 'CustomRole');
    await page.fill('[name="description"]', 'A custom role for testing');
    
    // 选择权限
    await page.check('input[name="permission:media:read"]');
    await page.check('input[name="permission:media:write"]');
    
    await page.click('.btn-create');
    
    await expect(page.locator('.toast-success')).toBeVisible();
  });

  test('应该能够编辑角色权限', async ({ page }) => {
    await page.click('.role-card:first-child .btn-edit');
    
    // 修改权限
    await page.check('input[name="permission:album:write"]');
    
    await page.click('.btn-save');
    
    await expect(page.locator('.toast-success')).toBeVisible();
  });

  test('应该不能删除内置角色', async ({ page }) => {
    await page.click('.role-card:has-text("Admin") .btn-delete');
    
    await expect(page.locator('.error-message')).toBeVisible();
    await expect(page.locator('.error-message')).toContainText('不能删除内置角色');
  });
});

test.describe('审计日志', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/login');
    await page.fill('[name="username"]', TEST_ADMIN_USER.username);
    await page.fill('[name="password"]', TEST_ADMIN_USER.password);
    await page.click('button[type="submit"]');
    await page.waitForURL('**/dashboard');
    await page.goto('/admin/audit-logs');
  });

  test('应该显示审计日志列表', async ({ page }) => {
    await expect(page.locator('.audit-log-list')).toBeVisible();
  });

  test('应该能够按类型筛选', async ({ page }) => {
    await page.selectOption('[name="logType"]', 'security');
    await page.click('.btn-filter');
    
    await expect(page.locator('.audit-log-list')).toBeVisible();
  });

  test('应该能够按日期范围筛选', async ({ page }) => {
    await page.fill('[name="startDate"]', '2026-04-01');
    await page.fill('[name="endDate"]', '2026-04-06');
    await page.click('.btn-filter');
    
    await expect(page.locator('.audit-log-list')).toBeVisible();
  });

  test('应该能够按用户筛选', async ({ page }) => {
    await page.fill('[name="username"]', 'admin');
    await page.click('.btn-filter');
    
    await expect(page.locator('.audit-log-list')).toBeVisible();
  });

  test('应该能够搜索日志', async ({ page }) => {
    await page.fill('.search-input', 'login');
    await page.click('.search-button');
    
    await expect(page.locator('.audit-log-list')).toBeVisible();
  });

  test('应该能够查看日志详情', async ({ page }) => {
    await page.click('.log-row:first-child');
    
    await expect(page.locator('.log-detail-modal')).toBeVisible();
    await expect(page.locator('.log-detail-content')).toBeVisible();
  });

  test('应该能够导出日志', async ({ page }) => {
    await page.click('.btn-export');
    
    // 选择导出格式
    await page.selectOption('[name="exportFormat"]', 'csv');
    await page.click('.btn-download');
    
    // 等待下载
    await page.waitForTimeout(1000);
  });

  test('应该显示日志统计', async ({ page }) => {
    await page.goto('/admin/audit-logs/stats');
    
    await expect(page.locator('.log-stats')).toBeVisible();
    await expect(page.locator('.stat-chart')).toBeVisible();
  });
});

test.describe('系统配置', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/login');
    await page.fill('[name="username"]', TEST_ADMIN_USER.username);
    await page.fill('[name="password"]', TEST_ADMIN_USER.password);
    await page.click('button[type="submit"]');
    await page.waitForURL('**/dashboard');
    await page.goto('/admin/settings');
  });

  test('应该显示基础配置', async ({ page }) => {
    await expect(page.locator('.settings-section:has-text("基础设置")')).toBeVisible();
  });

  test('应该能够修改系统名称', async ({ page }) => {
    await page.fill('[name="systemName"]', 'AI-NAS Media Manager Pro');
    await page.click('.btn-save');
    
    await expect(page.locator('.toast-success')).toBeVisible();
  });

  test('应该能够修改存储配置', async ({ page }) => {
    await page.goto('/admin/settings/storage');
    
    await page.fill('[name="storagePath"]', '/data/media');
    await page.fill('[name="maxStorageSize"]', '1000');
    await page.click('.btn-save');
    
    await expect(page.locator('.toast-success')).toBeVisible();
  });

  test('应该能够修改安全配置', async ({ page }) => {
    await page.goto('/admin/settings/security');
    
    await page.fill('[name="sessionTimeout"]', '3600');
    await page.check('[name="enable2FA"]');
    await page.click('.btn-save');
    
    await expect(page.locator('.toast-success')).toBeVisible();
  });

  test('应该能够配置邮件通知', async ({ page }) => {
    await page.goto('/admin/settings/notifications');
    
    await page.fill('[name="smtpHost"]', 'smtp.example.com');
    await page.fill('[name="smtpPort"]', '587');
    await page.fill('[name="smtpUser"]', 'noreply@example.com');
    await page.fill('[name="smtpPassword"]', 'password123');
    
    await page.click('.btn-test');
    await expect(page.locator('.toast:has-text("测试邮件已发送")')).toBeVisible({ timeout: 5000 });
    
    await page.click('.btn-save');
    await expect(page.locator('.toast-success')).toBeVisible();
  });

  test('应该能够备份配置', async ({ page }) => {
    await page.goto('/admin/settings/backup');
    
    await page.click('.btn-backup');
    
    await page.waitForTimeout(1000);
    await expect(page.locator('.toast-success')).toBeVisible();
  });

  test('应该能够恢复配置', async ({ page }) => {
    await page.goto('/admin/settings/backup');
    
    await page.setInputFiles('input[type="file"]', './test-backup.json');
    
    await page.click('.btn-restore');
    await page.click('.confirm-dialog .btn-confirm');
    
    await expect(page.locator('.toast-success')).toBeVisible();
  });
});

test.describe('权限验证', () => {
  test('非管理员不应看到管理菜单', async ({ page }) => {
    // 使用普通用户登录
    await page.goto('/login');
    await page.fill('[name="username"]', 'viewer');
    await page.fill('[name="password"]', 'viewer123');
    await page.click('button[type="submit"]');
    await page.waitForURL('**/dashboard');
    
    await expect(page.locator('.sidebar .admin-menu')).not.toBeVisible();
  });

  test('非管理员访问管理页面应被拒绝', async ({ page }) => {
    await page.goto('/login');
    await page.fill('[name="username"]', 'viewer');
    await page.fill('[name="password"]', 'viewer123');
    await page.click('button[type="submit"]');
    await page.waitForURL('**/dashboard');
    
    await page.goto('/admin/users');
    
    await expect(page.locator('.error-page')).toBeVisible();
    await expect(page.locator('.error-code')).toContainText('403');
  });

  test('操作员只能查看不能编辑用户', async ({ page }) => {
    await page.goto('/login');
    await page.fill('[name="username"]', 'operator');
    await page.fill('[name="password"]', 'operator123');
    await page.click('button[type="submit"]');
    await page.waitForURL('**/dashboard');
    
    await page.goto('/admin/users');
    
    await expect(page.locator('.btn-create-user')).not.toBeVisible();
    await expect(page.locator('.btn-delete')).not.toBeVisible();
  });
});
