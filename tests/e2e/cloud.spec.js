/**
 * 云存储界面 E2E 测试
 * 覆盖：云存储配置、同步管理、备份恢复
 */
const { test, expect } = require('@playwright/test');

// 测试配置
const TEST_CREDENTIALS = {
  username: 'admin',
  password: 'admin123'
};

test.describe('云存储概览', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/login');
    await page.fill('[name="username"]', TEST_CREDENTIALS.username);
    await page.fill('[name="password"]', TEST_CREDENTIALS.password);
    await page.click('button[type="submit"]');
    await page.waitForURL('**/dashboard');
  });

  test('应该显示云存储入口', async ({ page }) => {
    await page.goto('/dashboard');
    
    await expect(page.locator('.cloud-menu, .cloud-section')).toBeVisible();
  });

  test('应该显示存储统计', async ({ page }) => {
    await page.goto('/cloud');
    
    await expect(page.locator('.storage-stats')).toBeVisible();
    await expect(page.locator('.local-storage-info')).toBeVisible();
    await expect(page.locator('.cloud-storage-info')).toBeVisible();
  });

  test('应该显示同步状态', async ({ page }) => {
    await page.goto('/cloud');
    
    await expect(page.locator('.sync-status')).toBeVisible();
  });
});

test.describe('阿里云OSS配置', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/login');
    await page.fill('[name="username"]', TEST_CREDENTIALS.username);
    await page.fill('[name="password"]', TEST_CREDENTIALS.password);
    await page.click('button[type="submit"]');
    await page.waitForURL('**/dashboard');
    await page.goto('/cloud/settings/aliyun');
  });

  test('应该显示OSS配置表单', async ({ page }) => {
    await expect(page.locator('[name="accessKey"]')).toBeVisible();
    await expect(page.locator('[name="secretKey"]')).toBeVisible();
    await expect(page.locator('[name="bucket"]')).toBeVisible();
    await expect(page.locator('[name="endpoint"]')).toBeVisible();
  });

  test('应该能够配置阿里云OSS', async ({ page }) => {
    await page.fill('[name="accessKey"]', 'test_access_key');
    await page.fill('[name="secretKey"]', 'test_secret_key');
    await page.fill('[name="bucket"]', 'test-bucket');
    await page.fill('[name="endpoint"]', 'oss-cn-hangzhou.aliyuncs.com');
    
    await page.click('.btn-save');
    
    await expect(page.locator('.toast-success')).toBeVisible({ timeout: 5000 });
  });

  test('应该能够测试OSS连接', async ({ page }) => {
    await page.fill('[name="accessKey"]', 'test_access_key');
    await page.fill('[name="secretKey"]', 'test_secret_key');
    await page.fill('[name="bucket"]', 'test-bucket');
    
    await page.click('.btn-test-connection');
    
    await page.waitForSelector('.connection-success, .connection-failed', { timeout: 10000 });
  });

  test('应该能够断开OSS连接', async ({ page }) => {
    await page.click('.btn-disconnect');
    
    await page.click('.confirm-dialog .btn-confirm');
    
    await expect(page.locator('.toast-success')).toBeVisible({ timeout: 5000 });
  });
});

test.describe('腾讯云COS配置', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/login');
    await page.fill('[name="username"]', TEST_CREDENTIALS.username);
    await page.fill('[name="password"]', TEST_CREDENTIALS.password);
    await page.click('button[type="submit"]');
    await page.waitForURL('**/dashboard');
    await page.goto('/cloud/settings/tencent');
  });

  test('应该显示COS配置表单', async ({ page }) => {
    await expect(page.locator('[name="secretId"]')).toBeVisible();
    await expect(page.locator('[name="secretKey"]')).toBeVisible();
    await expect(page.locator('[name="bucket"]')).toBeVisible();
    await expect(page.locator('[name="region"]')).toBeVisible();
  });

  test('应该能够配置腾讯云COS', async ({ page }) => {
    await page.fill('[name="secretId"]', 'test_secret_id');
    await page.fill('[name="secretKey"]', 'test_secret_key');
    await page.fill('[name="bucket"]', 'test-bucket-123456');
    await page.fill('[name="region"]', 'ap-guangzhou');
    
    await page.click('.btn-save');
    
    await expect(page.locator('.toast-success')).toBeVisible({ timeout: 5000 });
  });

  test('应该能够测试COS连接', async ({ page }) => {
    await page.fill('[name="secretId"]', 'test_id');
    await page.fill('[name="secretKey"]', 'test_key');
    await page.fill('[name="bucket"]', 'test-bucket');
    
    await page.click('.btn-test-connection');
    
    await page.waitForSelector('.connection-success, .connection-failed', { timeout: 10000 });
  });
});

test.describe('同步管理', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/login');
    await page.fill('[name="username"]', TEST_CREDENTIALS.username);
    await page.fill('[name="password"]', TEST_CREDENTIALS.password);
    await page.click('button[type="submit"]');
    await page.waitForURL('**/dashboard');
    await page.goto('/cloud/sync');
  });

  test('应该显示同步设置', async ({ page }) => {
    await expect(page.locator('.sync-settings')).toBeVisible();
  });

  test('应该能够设置同步方向', async ({ page }) => {
    await page.click('.sync-direction-option:has-text("双向同步")');
    
    await page.click('.btn-save');
    
    await expect(page.locator('.toast-success')).toBeVisible({ timeout: 5000 });
  });

  test('应该能够设置同步过滤规则', async ({ page }) => {
    await page.click('.btn-add-filter');
    
    await page.fill('[name="filterPattern"]', '*.tmp');
    await page.selectOption('[name="filterAction"]', 'exclude');
    
    await page.click('.btn-add');
    
    await expect(page.locator('.toast-success')).toBeVisible({ timeout: 5000 });
  });

  test('应该能够设置WiFi同步', async ({ page }) => {
    await page.check('[name="wifiOnly"]');
    
    await page.click('.btn-save');
    
    await expect(page.locator('.toast-success')).toBeVisible({ timeout: 5000 });
  });

  test('应该能够手动触发同步', async ({ page }) => {
    await page.click('.btn-sync-now');
    
    await expect(page.locator('.sync-progress')).toBeVisible();
    
    await page.waitForSelector('.sync-complete, .toast-success', { timeout: 120000 });
  });

  test('应该能够查看同步历史', async ({ page }) => {
    await page.click('.btn-sync-history');
    
    await expect(page.locator('.sync-history-list')).toBeVisible();
  });

  test('应该能够暂停/恢复同步', async ({ page }) => {
    const pauseButton = page.locator('.btn-pause-sync');
    if (await pauseButton.isVisible()) {
      await pauseButton.click();
      await expect(page.locator('.btn-resume-sync')).toBeVisible();
    }
  });
});

test.describe('备份管理', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/login');
    await page.fill('[name="username"]', TEST_CREDENTIALS.username);
    await page.fill('[name="password"]', TEST_CREDENTIALS.password);
    await page.click('button[type="submit"]');
    await page.waitForURL('**/dashboard');
    await page.goto('/cloud/backup');
  });

  test('应该显示备份列表', async ({ page }) => {
    await expect(page.locator('.backup-list')).toBeVisible();
  });

  test('应该能够创建备份', async ({ page }) => {
    await page.click('.btn-create-backup');
    
    await page.fill('[name="backupName"]', 'Test Backup ' + Date.now());
    await page.fill('[name="description"]', 'E2E test backup');
    
    // 选择备份内容
    await page.check('[name="includeMedia"]');
    await page.check('[name="includeAlbums"]');
    await page.check('[name="includeSettings"]');
    
    await page.click('.btn-start-backup');
    
    await page.waitForSelector('.backup-complete, .toast-success', { timeout: 180000 });
  });

  test('应该能够恢复备份', async ({ page }) => {
    const backup = page.locator('.backup-item').first();
    if (await backup.isVisible()) {
      await backup.click();
      
      await page.click('.btn-restore');
      
      await page.click('.confirm-dialog .btn-confirm');
      
      await expect(page.locator('.restore-progress')).toBeVisible();
    }
  });

  test('应该能够删除备份', async ({ page }) => {
    const backup = page.locator('.backup-item').first();
    if (await backup.isVisible()) {
      await backup.hover();
      await page.click('.backup-item:first-child .btn-delete');
      
      await page.click('.confirm-dialog .btn-confirm');
      
      await expect(page.locator('.toast-success')).toBeVisible({ timeout: 5000 });
    }
  });

  test('应该能够导出备份', async ({ page }) => {
    const backup = page.locator('.backup-item').first();
    if (await backup.isVisible()) {
      await backup.hover();
      await page.click('.backup-item:first-child .btn-export');
      
      await page.waitForTimeout(2000);
    }
  });

  test('应该能够设置自动备份', async ({ page }) => {
    await page.click('.btn-auto-backup-settings');
    
    await page.check('[name="enableAutoBackup"]');
    await page.selectOption('[name="backupFrequency"]', 'daily');
    await page.fill('[name="backupTime"]', '02:00');
    
    await page.click('.btn-save');
    
    await expect(page.locator('.toast-success')).toBeVisible({ timeout: 5000 });
  });

  test('应该能够查看备份详情', async ({ page }) => {
    const backup = page.locator('.backup-item').first();
    if (await backup.isVisible()) {
      await backup.click();
      
      await expect(page.locator('.backup-detail')).toBeVisible();
      await expect(page.locator('.backup-contents')).toBeVisible();
    }
  });
});

test.describe('存储配额', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/login');
    await page.fill('[name="username"]', TEST_CREDENTIALS.username);
    await page.fill('[name="password"]', TEST_CREDENTIALS.password);
    await page.click('button[type="submit"]');
    await page.waitForURL('**/dashboard');
    await page.goto('/cloud/quota');
  });

  test('应该显示配额使用情况', async ({ page }) => {
    await expect(page.locator('.quota-overview')).toBeVisible();
    await expect(page.locator('.quota-chart')).toBeVisible();
  });

  test('应该显示配额统计', async ({ page }) => {
    await expect(page.locator('.local-quota')).toBeVisible();
    await expect(page.locator('.cloud-quota')).toBeVisible();
  });

  test('应该能够设置配额警告', async ({ page }) => {
    await page.fill('[name="warningThreshold"]', '80');
    
    await page.click('.btn-save');
    
    await expect(page.locator('.toast-success')).toBeVisible({ timeout: 5000 });
  });
});

test.describe('文件浏览', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/login');
    await page.fill('[name="username"]', TEST_CREDENTIALS.username);
    await page.fill('[name="password"]', TEST_CREDENTIALS.password);
    await page.click('button[type="submit"]');
    await page.waitForURL('**/dashboard');
    await page.goto('/cloud/files');
  });

  test('应该显示云端文件列表', async ({ page }) => {
    await expect(page.locator('.file-list')).toBeVisible();
  });

  test('应该能够切换视图模式', async ({ page }) => {
    await page.click('.view-toggle-grid');
    await expect(page.locator('.file-grid')).toBeVisible();
    
    await page.click('.view-toggle-list');
    await expect(page.locator('.file-list-view')).toBeVisible();
  });

  test('应该能够上传文件到云端', async ({ page }) => {
    await page.click('.btn-upload');
    
    await page.setInputFiles('input[type="file"]', './test-file.jpg');
    
    await page.waitForSelector('.upload-complete, .toast-success', { timeout: 60000 });
  });

  test('应该能够下载云端文件', async ({ page }) => {
    const file = page.locator('.file-item').first();
    if (await file.isVisible()) {
      await file.hover();
      await page.click('.file-item:first-child .btn-download');
      
      await page.waitForTimeout(2000);
    }
  });

  test('应该能够删除云端文件', async ({ page }) => {
    const file = page.locator('.file-item').first();
    if (await file.isVisible()) {
      await file.hover();
      await page.click('.file-item:first-child .btn-delete');
      
      await page.click('.confirm-dialog .btn-confirm');
      
      await expect(page.locator('.toast-success')).toBeVisible({ timeout: 5000 });
    }
  });

  test('应该能够复制文件到本地', async ({ page }) => {
    const file = page.locator('.file-item').first();
    if (await file.isVisible()) {
      await file.hover();
      await page.click('.file-item:first-child .btn-copy-local');
      
      await expect(page.locator('.toast-success')).toBeVisible({ timeout: 10000 });
    }
  });

  test('应该能够创建文件夹', async ({ page }) => {
    await page.click('.btn-new-folder');
    
    await page.fill('[name="folderName"]', 'Test Folder');
    await page.click('.btn-create');
    
    await expect(page.locator('.toast-success')).toBeVisible({ timeout: 5000 });
  });

  test('应该能够移动文件', async ({ page }) => {
    const file = page.locator('.file-item').first();
    if (await file.isVisible()) {
      await file.hover();
      await page.click('.file-item:first-child .btn-move');
      
      await page.click('.folder-tree .folder-item:nth-child(2)');
      await page.click('.btn-confirm-move');
      
      await expect(page.locator('.toast-success')).toBeVisible({ timeout: 5000 });
    }
  });
});

test.describe('云存储健康检查', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/login');
    await page.fill('[name="username"]', TEST_CREDENTIALS.username);
    await page.fill('[name="password"]', TEST_CREDENTIALS.password);
    await page.click('button[type="submit"]');
    await page.waitForURL('**/dashboard');
    await page.goto('/cloud/health');
  });

  test('应该显示健康状态', async ({ page }) => {
    await expect(page.locator('.health-status')).toBeVisible();
  });

  test('应该能够运行健康检查', async ({ page }) => {
    await page.click('.btn-run-health-check');
    
    await page.waitForSelector('.health-check-complete', { timeout: 30000 });
  });

  test('应该能够查看健康报告', async ({ page }) => {
    await page.click('.btn-health-report');
    
    await expect(page.locator('.health-report-modal')).toBeVisible();
  });
});

test.describe('云存储权限', () => {
  test('非管理员不应修改云存储配置', async ({ page }) => {
    await page.goto('/login');
    await page.fill('[name="username"]', 'viewer');
    await page.fill('[name="password"]', 'viewer123');
    await page.click('button[type="submit"]');
    await page.waitForURL('**/dashboard');
    
    await page.goto('/cloud/settings');
    
    await expect(page.locator('.permission-denied, .error-page')).toBeVisible();
  });

  test('非管理员不应执行云端操作', async ({ page }) => {
    await page.goto('/login');
    await page.fill('[name="username"]', 'viewer');
    await page.fill('[name="password"]', 'viewer123');
    await page.click('button[type="submit"]');
    await page.waitForURL('**/dashboard');
    
    await page.goto('/cloud/files');
    
    await expect(page.locator('.btn-upload')).not.toBeVisible();
    await expect(page.locator('.btn-delete')).not.toBeVisible();
  });
});
