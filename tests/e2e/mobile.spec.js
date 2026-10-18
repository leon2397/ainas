/**
 * 移动端同步界面 E2E 测试
 * 覆盖：设备管理、同步设置、照片同步
 */
const { test, expect } = require('@playwright/test');

// 测试配置
const TEST_CREDENTIALS = {
  username: 'admin',
  password: 'admin123'
};

test.describe('移动端同步概览', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/login');
    await page.fill('[name="username"]', TEST_CREDENTIALS.username);
    await page.fill('[name="password"]', TEST_CREDENTIALS.password);
    await page.click('button[type="submit"]');
    await page.waitForURL('**/dashboard');
  });

  test('应该显示移动同步入口', async ({ page }) => {
    await page.goto('/dashboard');
    
    await expect(page.locator('.mobile-menu, .sync-section')).toBeVisible();
  });

  test('应该显示已连接设备', async ({ page }) => {
    await page.goto('/mobile');
    
    await expect(page.locator('.device-list')).toBeVisible();
  });

  test('应该显示同步统计', async ({ page }) => {
    await page.goto('/mobile');
    
    await expect(page.locator('.sync-stats')).toBeVisible();
  });
});

test.describe('设备管理', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/login');
    await page.fill('[name="username"]', TEST_CREDENTIALS.username);
    await page.fill('[name="password"]', TEST_CREDENTIALS.password);
    await page.click('button[type="submit"]');
    await page.waitForURL('**/dashboard');
    await page.goto('/mobile/devices');
  });

  test('应该显示设备列表', async ({ page }) => {
    await expect(page.locator('.device-list')).toBeVisible();
  });

  test('应该能够查看设备详情', async ({ page }) => {
    const device = page.locator('.device-card').first();
    if (await device.isVisible()) {
      await device.click();
      
      await expect(page.locator('.device-detail-modal')).toBeVisible();
    }
  });

  test('应该能够设置设备别名', async ({ page }) => {
    const device = page.locator('.device-card').first();
    if (await device.isVisible()) {
      await device.hover();
      await page.click('.device-card:first-child .btn-edit');
      
      await page.fill('[name="deviceAlias"]', '我的iPhone');
      await page.click('.btn-save');
      
      await expect(page.locator('.toast-success')).toBeVisible({ timeout: 5000 });
    }
  });

  test('应该能够设置设备同步选项', async ({ page }) => {
    const device = page.locator('.device-card').first();
    if (await device.isVisible()) {
      await device.click();
      
      await page.check('[name="autoSync"]');
      await page.check('[name="wifiOnly"]');
      await page.selectOption('[name="syncQuality"]', 'original');
      
      await page.click('.btn-save');
      
      await expect(page.locator('.toast-success')).toBeVisible({ timeout: 5000 });
    }
  });

  test('应该能够重命名设备', async ({ page }) => {
    const device = page.locator('.device-card').first();
    if (await device.isVisible()) {
      await device.hover();
      await page.click('.device-card:first-child .btn-rename');
      
      await page.fill('[name="newName"]', 'New Device Name');
      await page.click('.btn-confirm');
      
      await expect(page.locator('.toast-success')).toBeVisible({ timeout: 5000 });
    }
  });

  test('应该能够移除设备', async ({ page }) => {
    const device = page.locator('.device-card').first();
    if (await device.isVisible()) {
      await device.hover();
      await page.click('.device-card:first-child .btn-remove');
      
      await page.click('.confirm-dialog .btn-confirm');
      
      await expect(page.locator('.toast-success')).toBeVisible({ timeout: 5000 });
    }
  });

  test('应该能够查看设备存储使用', async ({ page }) => {
    const device = page.locator('.device-card').first();
    if (await device.isVisible()) {
      await device.click();
      
      await expect(page.locator('.storage-usage')).toBeVisible();
    }
  });
});

test.describe('同步设置', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/login');
    await page.fill('[name="username"]', TEST_CREDENTIALS.username);
    await page.fill('[name="password"]', TEST_CREDENTIALS.password);
    await page.click('button[type="submit"]');
    await page.waitForURL('**/dashboard');
    await page.goto('/mobile/settings');
  });

  test('应该显示同步设置选项', async ({ page }) => {
    await expect(page.locator('.sync-settings-form')).toBeVisible();
  });

  test('应该能够设置同步方向', async ({ page }) => {
    await page.click('.sync-direction-option:has-text("上传到云端")');
    
    await page.click('.btn-save');
    
    await expect(page.locator('.toast-success')).toBeVisible({ timeout: 5000 });
  });

  test('应该能够设置WiFi同步', async ({ page }) => {
    await page.check('[name="wifiOnly"]');
    
    await page.click('.btn-save');
    
    await expect(page.locator('.toast-success')).toBeVisible({ timeout: 5000 });
  });

  test('应该能够设置同步质量', async ({ page }) => {
    await page.selectOption('[name="syncQuality"]', 'original');
    
    await page.click('.btn-save');
    
    await expect(page.locator('.toast-success')).toBeVisible({ timeout: 5000 });
  });

  test('应该能够设置同步时间', async ({ page }) => {
    await page.check('[name="scheduledSync"]');
    await page.fill('[name="syncTime"]', '22:00');
    
    await page.click('.btn-save');
    
    await expect(page.locator('.toast-success')).toBeVisible({ timeout: 5000 });
  });

  test('应该能够设置同步频率', async ({ page }) => {
    await page.selectOption('[name="syncFrequency"]', 'hourly');
    
    await page.click('.btn-save');
    
    await expect(page.locator('.toast-success')).toBeVisible({ timeout: 5000 });
  });

  test('应该能够设置电池保护', async ({ page }) => {
    await page.check('[name="batteryProtection"]');
    await page.fill('[name="minBatteryLevel"]', '30');
    
    await page.click('.btn-save');
    
    await expect(page.locator('.toast-success')).toBeVisible({ timeout: 5000 });
  });
});

test.describe('照片同步', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/login');
    await page.fill('[name="username"]', TEST_CREDENTIALS.username);
    await page.fill('[name="password"]', TEST_CREDENTIALS.password);
    await page.click('button[type="submit"]');
    await page.waitForURL('**/dashboard');
    await page.goto('/mobile/photos');
  });

  test('应该显示待同步照片列表', async ({ page }) => {
    await expect(page.locator('.photo-queue')).toBeVisible();
  });

  test('应该能够筛选照片', async ({ page }) => {
    await page.click('.filter-tab:has-text("未同步")');
    await page.waitForTimeout(500);
  });

  test('应该能够按日期筛选', async ({ page }) => {
    await page.fill('[name="startDate"]', '2026-04-01');
    await page.fill('[name="endDate"]', '2026-04-06');
    await page.click('.btn-filter');
    
    await page.waitForTimeout(500);
  });

  test('应该能够选择照片同步', async ({ page }) => {
    await page.click('.photo-item:first-child');
    
    const isSelected = await page.locator('.photo-item.selected').isVisible();
    expect(isSelected).toBeTruthy();
  });

  test('应该能够全选照片', async ({ page }) => {
    await page.click('.select-all');
    
    const selectedCount = await page.locator('.photo-item.selected').count();
    const totalCount = await page.locator('.photo-item').count();
    expect(selectedCount).toBe(totalCount);
  });

  test('应该能够批量同步选中照片', async ({ page }) => {
    await page.click('.photo-item:first-child');
    await page.click('.photo-item:nth-child(2)');
    
    await page.click('.btn-sync-selected');
    
    await expect(page.locator('.sync-progress')).toBeVisible();
  });

  test('应该能够同步所有照片', async ({ page }) => {
    await page.click('.btn-sync-all');
    
    await page.waitForSelector('.sync-complete, .toast-success', { timeout: 180000 });
  });

  test('应该能够查看同步进度', async ({ page }) => {
    await page.click('.btn-sync-all');
    
    await expect(page.locator('.sync-progress-bar')).toBeVisible();
  });
});

test.describe('相册同步', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/login');
    await page.fill('[name="username"]', TEST_CREDENTIALS.username);
    await page.fill('[name="password"]', TEST_CREDENTIALS.password);
    await page.click('button[type="submit"]');
    await page.waitForURL('**/dashboard');
    await page.goto('/mobile/albums');
  });

  test('应该显示相册列表', async ({ page }) => {
    await expect(page.locator('.album-list')).toBeVisible();
  });

  test('应该能够选择相册同步', async ({ page }) => {
    const album = page.locator('.album-item').first();
    if (await album.isVisible()) {
      await album.click();
      
      const isSelected = await page.locator('.album-item.selected').isVisible();
      expect(isSelected).toBeTruthy();
    }
  });

  test('应该能够同步选中相册', async ({ page }) => {
    const album = page.locator('.album-item').first();
    if (await album.isVisible()) {
      await album.click();
      
      await page.click('.btn-sync-selected');
      
      await expect(page.locator('.sync-progress')).toBeVisible();
    }
  });

  test('应该能够设置相册同步选项', async ({ page }) => {
    const album = page.locator('.album-item').first();
    if (await album.isVisible()) {
      await album.hover();
      await page.click('.album-item:first-child .btn-settings');
      
      await page.check('[name="autoSync"]');
      await page.selectOption('[name="syncQuality"]', 'high');
      
      await page.click('.btn-save');
      
      await expect(page.locator('.toast-success')).toBeVisible({ timeout: 5000 });
    }
  });
});

test.describe('同步历史', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/login');
    await page.fill('[name="username"]', TEST_CREDENTIALS.username);
    await page.fill('[name="password"]', TEST_CREDENTIALS.password);
    await page.click('button[type="submit"]');
    await page.waitForURL('**/dashboard');
    await page.goto('/mobile/history');
  });

  test('应该显示同步历史记录', async ({ page }) => {
    await expect(page.locator('.sync-history')).toBeVisible();
  });

  test('应该能够按设备筛选', async ({ page }) => {
    await page.selectOption('[name="deviceFilter"]', 'all');
    await page.click('.btn-filter');
    
    await page.waitForTimeout(500);
  });

  test('应该能够按日期筛选', async ({ page }) => {
    await page.fill('[name="startDate"]', '2026-04-01');
    await page.fill('[name="endDate"]', '2026-04-06');
    await page.click('.btn-filter');
    
    await page.waitForTimeout(500);
  });

  test('应该能够按类型筛选', async ({ page }) => {
    await page.selectOption('[name="typeFilter"]', 'photo');
    await page.click('.btn-filter');
    
    await page.waitForTimeout(500);
  });

  test('应该能够查看同步详情', async ({ page }) => {
    const historyItem = page.locator('.history-item').first();
    if (await historyItem.isVisible()) {
      await historyItem.click();
      
      await expect(page.locator('.history-detail-modal')).toBeVisible();
    }
  });

  test('应该能够清除历史记录', async ({ page }) => {
    await page.click('.btn-clear-history');
    
    await page.click('.confirm-dialog .btn-confirm');
    
    await expect(page.locator('.toast-success')).toBeVisible({ timeout: 5000 });
  });

  test('应该能够导出历史记录', async ({ page }) => {
    await page.click('.btn-export');
    
    await page.selectOption('[name="exportFormat"]', 'csv');
    await page.click('.btn-download');
    
    await page.waitForTimeout(1000);
  });
});

test.describe('同步冲突', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/login');
    await page.fill('[name="username"]', TEST_CREDENTIALS.username);
    await page.fill('[name="password"]', TEST_CREDENTIALS.password);
    await page.click('button[type="submit"]');
    await page.waitForURL('**/dashboard');
    await page.goto('/mobile/conflicts');
  });

  test('应该显示冲突列表', async ({ page }) => {
    await expect(page.locator('.conflict-list')).toBeVisible();
  });

  test('应该能够查看冲突详情', async ({ page }) => {
    const conflict = page.locator('.conflict-item').first();
    if (await conflict.isVisible()) {
      await conflict.click();
      
      await expect(page.locator('.conflict-detail-modal')).toBeVisible();
      await expect(page.locator('.local-version')).toBeVisible();
      await expect(page.locator('.remote-version')).toBeVisible();
    }
  });

  test('应该能够保留本地版本', async ({ page }) => {
    const conflict = page.locator('.conflict-item').first();
    if (await conflict.isVisible()) {
      await conflict.click();
      
      await page.click('.btn-keep-local');
      await page.click('.confirm-dialog .btn-confirm');
      
      await expect(page.locator('.toast-success')).toBeVisible({ timeout: 5000 });
    }
  });

  test('应该能够保留远程版本', async ({ page }) => {
    const conflict = page.locator('.conflict-item').first();
    if (await conflict.isVisible()) {
      await conflict.click();
      
      await page.click('.btn-keep-remote');
      await page.click('.confirm-dialog .btn-confirm');
      
      await expect(page.locator('.toast-success')).toBeVisible({ timeout: 5000 });
    }
  });

  test('应该能够合并冲突', async ({ page }) => {
    const conflict = page.locator('.conflict-item').first();
    if (await conflict.isVisible()) {
      await conflict.click();
      
      await page.click('.btn-merge');
      
      // 编辑合并内容
      await page.fill('[name="mergedContent"]', 'Merged content');
      
      await page.click('.btn-save-merge');
      await page.click('.confirm-dialog .btn-confirm');
      
      await expect(page.locator('.toast-success')).toBeVisible({ timeout: 5000 });
    }
  });

  test('应该能够忽略冲突', async ({ page }) => {
    const conflict = page.locator('.conflict-item').first();
    if (await conflict.isVisible()) {
      await conflict.click();
      
      await page.click('.btn-ignore');
      await page.click('.confirm-dialog .btn-confirm');
      
      await expect(page.locator('.toast-success')).toBeVisible({ timeout: 5000 });
    }
  });
});

test.describe('同步配额', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/login');
    await page.fill('[name="username"]', TEST_CREDENTIALS.username);
    await page.fill('[name="password"]', TEST_CREDENTIALS.password);
    await page.click('button[type="submit"]');
    await page.waitForURL('**/dashboard');
    await page.goto('/mobile/quota');
  });

  test('应该显示配额使用情况', async ({ page }) => {
    await expect(page.locator('.quota-overview')).toBeVisible();
  });

  test('应该显示月度配额', async ({ page }) => {
    await expect(page.locator('.monthly-quota')).toBeVisible();
    await expect(page.locator('.quota-used')).toBeVisible();
    await expect(page.locator('.quota-remaining')).toBeVisible();
  });

  test('应该能够设置配额警告', async ({ page }) => {
    await page.fill('[name="warningThreshold"]', '80');
    
    await page.click('.btn-save');
    
    await expect(page.locator('.toast-success')).toBeVisible({ timeout: 5000 });
  });
});

test.describe('移动端权限', () => {
  test('非管理员不应修改同步设置', async ({ page }) => {
    await page.goto('/login');
    await page.fill('[name="username"]', 'viewer');
    await page.fill('[name="password"]', 'viewer123');
    await page.click('button[type="submit"]');
    await page.waitForURL('**/dashboard');
    
    await page.goto('/mobile/settings');
    
    await expect(page.locator('.permission-denied, .error-page')).toBeVisible();
  });

  test('非管理员不应执行设备操作', async ({ page }) => {
    await page.goto('/login');
    await page.fill('[name="username"]', 'viewer');
    await page.fill('[name="password"]', 'viewer123');
    await page.click('button[type="submit"]');
    await page.waitForURL('**/dashboard');
    
    await page.goto('/mobile/devices');
    
    await expect(page.locator('.btn-remove')).not.toBeVisible();
  });

  test('操作员可以执行同步操作', async ({ page }) => {
    await page.goto('/login');
    await page.fill('[name="username"]', 'operator');
    await page.fill('[name="password"]', 'operator123');
    await page.click('button[type="submit"]');
    await page.waitForURL('**/dashboard');
    
    await page.goto('/mobile/photos');
    
    await expect(page.locator('.btn-sync-selected')).toBeVisible();
  });
});
