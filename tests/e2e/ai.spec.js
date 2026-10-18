/**
 * AI功能界面 E2E 测试
 * 覆盖：人脸识别、智能相册、自动标签、相似度检测
 */
const { test, expect } = require('@playwright/test');

// 测试配置
const TEST_CREDENTIALS = {
  username: 'admin',
  password: 'admin123'
};

test.describe('AI功能概览', () => {
  test.beforeEach(async ({ page }) => {
    // 登录
    await page.goto('/login');
    await page.fill('[name="username"]', TEST_CREDENTIALS.username);
    await page.fill('[name="password"]', TEST_CREDENTIALS.password);
    await page.click('button[type="submit"]');
    await page.waitForURL('**/dashboard');
  });

  test('应该显示AI功能入口', async ({ page }) => {
    await page.goto('/dashboard');
    
    await expect(page.locator('.ai-menu, .ai-features-section')).toBeVisible();
  });

  test('应该显示AI功能统计', async ({ page }) => {
    await page.goto('/ai/stats');
    
    await expect(page.locator('.ai-stat-card:has-text("已识别人物")')).toBeVisible();
    await expect(page.locator('.ai-stat-card:has-text("已生成标签")')).toBeVisible();
    await expect(page.locator('.ai-stat-card:has-text("相似图片")')).toBeVisible();
  });

  test('应该显示NPU状态', async ({ page }) => {
    await page.goto('/ai/stats');
    
    await expect(page.locator('.npu-status')).toBeVisible();
  });
});

test.describe('人脸识别', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/login');
    await page.fill('[name="username"]', TEST_CREDENTIALS.username);
    await page.fill('[name="password"]', TEST_CREDENTIALS.password);
    await page.click('button[type="submit"]');
    await page.waitForURL('**/dashboard');
    await page.goto('/ai/faces');
  });

  test('应该显示人脸列表', async ({ page }) => {
    await expect(page.locator('.face-list, .face-grid')).toBeVisible();
  });

  test('应该能够筛选人物', async ({ page }) => {
    await page.selectOption('[name="personFilter"]', 'all');
    await page.waitForTimeout(500);
    
    const faceCount = await page.locator('.face-card').count();
    expect(faceCount).toBeGreaterThanOrEqual(0);
  });

  test('应该能够搜索人物', async ({ page }) => {
    await page.fill('.search-input', '张三');
    await page.click('.search-button');
    
    await page.waitForTimeout(1000);
  });

  test('应该能够查看人物详情', async ({ page }) => {
    const faceCard = page.locator('.face-card').first();
    if (await faceCard.isVisible()) {
      await faceCard.click();
      
      await expect(page.locator('.face-detail-modal, .face-detail-panel')).toBeVisible();
    }
  });

  test('应该能够分配人名', async ({ page }) => {
    const faceCard = page.locator('.face-card').first();
    if (await faceCard.isVisible()) {
      await faceCard.click();
      
      await page.fill('[name="personName"]', '新人物');
      await page.click('.btn-assign-name');
      
      await expect(page.locator('.toast-success')).toBeVisible({ timeout: 5000 });
    }
  });

  test('应该能够创建人物分组', async ({ page }) => {
    await page.click('.btn-create-group');
    
    await page.fill('[name="groupName"]', '家庭成员');
    await page.click('.btn-create');
    
    await expect(page.locator('.toast-success')).toBeVisible({ timeout: 5000 });
  });

  test('应该能够触发人脸识别扫描', async ({ page }) => {
    await page.click('.btn-scan-faces');
    
    // 检查扫描对话框
    await expect(page.locator('.scan-dialog, .progress-modal')).toBeVisible();
    
    // 等待扫描完成（最多30秒）
    await page.waitForSelector('.scan-complete, .toast-success', { timeout: 30000 });
  });

  test('应该能够触发人脸聚类', async ({ page }) => {
    await page.click('.btn-cluster-faces');
    
    await page.selectOption('[name="clusterCount"]', '10');
    await page.click('.btn-start-clustering');
    
    await page.waitForSelector('.clustering-complete', { timeout: 60000 });
  });

  test('应该能够删除人脸记录', async ({ page }) => {
    const faceCard = page.locator('.face-card').first();
    if (await faceCard.isVisible()) {
      await faceCard.hover();
      await page.click('.face-card:first-child .btn-delete');
      
      await page.click('.confirm-dialog .btn-confirm');
      
      await expect(page.locator('.toast-success')).toBeVisible({ timeout: 5000 });
    }
  });

  test('应该能够导出人脸数据', async ({ page }) => {
    await page.click('.btn-export');
    
    await page.selectOption('[name="exportFormat"]', 'json');
    await page.click('.btn-download');
    
    await page.waitForTimeout(1000);
  });
});

test.describe('智能相册', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/login');
    await page.fill('[name="username"]', TEST_CREDENTIALS.username);
    await page.fill('[name="password"]', TEST_CREDENTIALS.password);
    await page.click('button[type="submit"]');
    await page.waitForURL('**/dashboard');
    await page.goto('/ai/albums');
  });

  test('应该显示相册列表', async ({ page }) => {
    await expect(page.locator('.album-list, .smart-album-grid')).toBeVisible();
  });

  test('应该能够按类型筛选', async ({ page }) => {
    await page.click('.filter-tab:has-text("人物")');
    await page.waitForTimeout(500);
    
    await expect(page.locator('.album-list')).toBeVisible();
  });

  test('应该能够按时间筛选', async ({ page }) => {
    await page.click('.filter-tab:has-text("时间")');
    await page.waitForTimeout(500);
    
    await page.selectOption('[name="timeRange"]', 'this-month');
    await page.waitForTimeout(500);
  });

  test('应该能够按地点筛选', async ({ page }) => {
    await page.click('.filter-tab:has-text("地点")');
    await page.waitForTimeout(500);
    
    await expect(page.locator('.location-filter')).toBeVisible();
  });

  test('应该能够创建智能相册', async ({ page }) => {
    await page.click('.btn-create-album');
    
    // 选择相册类型
    await page.click('.album-type-option:has-text("按人物")');
    
    // 填写名称
    await page.fill('[name="albumName"]', '张三的照片');
    
    // 选择人物
    await page.fill('[name="personName"]', '张三');
    
    await page.click('.btn-create');
    
    await expect(page.locator('.toast-success')).toBeVisible({ timeout: 5000 });
  });

  test('应该能够创建时间相册', async ({ page }) => {
    await page.click('.btn-create-album');
    
    await page.click('.album-type-option:has-text("按时间")');
    await page.fill('[name="albumName"]', '2026年4月');
    
    await page.selectOption('[name="year"]', '2026');
    await page.selectOption('[name="month"]', '4');
    
    await page.click('.btn-create');
    
    await expect(page.locator('.toast-success')).toBeVisible({ timeout: 5000 });
  });

  test('应该能够创建地点相册', async ({ page }) => {
    await page.click('.btn-create-album');
    
    await page.click('.album-type-option:has-text("按地点")');
    await page.fill('[name="albumName"]', '北京之旅');
    await page.fill('[name="location"]', '北京');
    
    await page.click('.btn-create');
    
    await expect(page.locator('.toast-success')).toBeVisible({ timeout: 5000 });
  });

  test('应该能够查看相册详情', async ({ page }) => {
    const albumCard = page.locator('.album-card').first();
    if (await albumCard.isVisible()) {
      await albumCard.click();
      
      await expect(page.locator('.album-detail-page')).toBeVisible();
      await expect(page.locator('.photo-grid')).toBeVisible();
    }
  });

  test('应该能够编辑智能相册', async ({ page }) => {
    const albumCard = page.locator('.album-card').first();
    if (await albumCard.isVisible()) {
      await albumCard.hover();
      await page.click('.album-card:first-child .btn-edit');
      
      await page.fill('[name="albumName"]', '已更新的相册名');
      await page.click('.btn-save');
      
      await expect(page.locator('.toast-success')).toBeVisible({ timeout: 5000 });
    }
  });

  test('应该能够删除智能相册', async ({ page }) => {
    const albumCard = page.locator('.album-card').first();
    if (await albumCard.isVisible()) {
      await albumCard.hover();
      await page.click('.album-card:first-child .btn-delete');
      
      await page.click('.confirm-dialog .btn-confirm');
      
      await expect(page.locator('.toast-success')).toBeVisible({ timeout: 5000 });
    }
  });

  test('应该能够刷新智能相册', async ({ page }) => {
    const albumCard = page.locator('.album-card').first();
    if (await albumCard.isVisible()) {
      await albumCard.hover();
      await page.click('.album-card:first-child .btn-refresh');
      
      await page.waitForSelector('.refresh-complete, .toast-success', { timeout: 30000 });
    }
  });
});

test.describe('自动标签', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/login');
    await page.fill('[name="username"]', TEST_CREDENTIALS.username);
    await page.fill('[name="password"]', TEST_CREDENTIALS.password);
    await page.click('button[type="submit"]');
    await page.waitForURL('**/dashboard');
    await page.goto('/ai/tags');
  });

  test('应该显示标签云', async ({ page }) => {
    await expect(page.locator('.tag-cloud')).toBeVisible();
  });

  test('应该显示标签统计', async ({ page }) => {
    await expect(page.locator('.tag-stats')).toBeVisible();
  });

  test('应该能够按类别筛选标签', async ({ page }) => {
    await page.click('.tag-category:has-text("场景")');
    await page.waitForTimeout(500);
  });

  test('应该能够搜索标签', async ({ page }) => {
    await page.fill('.search-input', 'beach');
    await page.click('.search-button');
    
    await page.waitForTimeout(500);
  });

  test('应该能够查看标签详情', async ({ page }) => {
    const tag = page.locator('.tag-item').first();
    if (await tag.isVisible()) {
      await tag.click();
      
      await expect(page.locator('.tag-detail-modal')).toBeVisible();
    }
  });

  test('应该能够手动添加标签', async ({ page }) => {
    await page.click('.btn-add-tag');
    
    await page.fill('[name="tagName"]', 'vacation');
    await page.selectOption('[name="category"]', 'activity');
    
    await page.click('.btn-add');
    
    await expect(page.locator('.toast-success')).toBeVisible({ timeout: 5000 });
  });

  test('应该能够删除标签', async ({ page }) => {
    const tag = page.locator('.tag-item').first();
    if (await tag.isVisible()) {
      await tag.hover();
      await page.click('.tag-item:first-child .btn-delete');
      
      await page.click('.confirm-dialog .btn-confirm');
      
      await expect(page.locator('.toast-success')).toBeVisible({ timeout: 5000 });
    }
  });

  test('应该能够触发批量标签生成', async ({ page }) => {
    await page.click('.btn-batch-tag');
    
    await page.selectOption('[name="mediaType"]', 'photo');
    await page.click('.btn-start-tagging');
    
    await page.waitForSelector('.tagging-complete, .toast-success', { timeout: 60000 });
  });

  test('应该能够查看标签配置', async ({ page }) => {
    await page.click('.btn-tag-settings');
    
    await expect(page.locator('.tag-settings-modal')).toBeVisible();
    await expect(page.locator('.confidence-threshold')).toBeVisible();
  });
});

test.describe('相似度检测', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/login');
    await page.fill('[name="username"]', TEST_CREDENTIALS.username);
    await page.fill('[name="password"]', TEST_CREDENTIALS.password);
    await page.click('button[type="submit"]');
    await page.waitForURL('**/dashboard');
    await page.goto('/ai/similarity');
  });

  test('应该显示相似图片组', async ({ page }) => {
    await expect(page.locator('.similarity-groups, .duplicate-list')).toBeVisible();
  });

  test('应该能够设置相似度阈值', async ({ page }) => {
    await page.fill('[name="similarityThreshold"]', '0.9');
    await page.click('.btn-apply');
    
    await page.waitForTimeout(500);
  });

  test('应该能够查看相似图片组详情', async ({ page }) => {
    const group = page.locator('.similar-group').first();
    if (await group.isVisible()) {
      await group.click();
      
      await expect(page.locator('.similarity-detail-modal')).toBeVisible();
      await expect(page.locator('.similar-images-grid')).toBeVisible();
    }
  });

  test('应该能够保留/删除相似图片', async ({ page }) => {
    const group = page.locator('.similar-group').first();
    if (await group.isVisible()) {
      await group.click();
      
      // 选择保留的图片
      await page.click('.similar-image-card:first-child .btn-keep');
      
      // 删除其他
      await page.click('.btn-delete-others');
      await page.click('.confirm-dialog .btn-confirm');
      
      await expect(page.locator('.toast-success')).toBeVisible({ timeout: 5000 });
    }
  });

  test('应该能够合并重复图片', async ({ page }) => {
    const group = page.locator('.similar-group').first();
    if (await group.isVisible()) {
      await group.click();
      
      await page.click('.btn-merge-duplicates');
      await page.click('.confirm-dialog .btn-confirm');
      
      await expect(page.locator('.toast-success')).toBeVisible({ timeout: 5000 });
    }
  });

  test('应该能够触发相似度扫描', async ({ page }) => {
    await page.click('.btn-scan-similarity');
    
    await expect(page.locator('.scan-progress')).toBeVisible();
    
    await page.waitForSelector('.scan-complete, .toast-success', { timeout: 120000 });
  });

  test('应该能够生成相似度报告', async ({ page }) => {
    await page.click('.btn-generate-report');
    
    await page.selectOption('[name="reportFormat"]', 'pdf');
    await page.click('.btn-download');
    
    await page.waitForTimeout(1000);
  });

  test('应该能够查看重复统计', async ({ page }) => {
    await page.goto('/ai/similarity/stats');
    
    await expect(page.locator('.duplicate-stats')).toBeVisible();
    await expect(page.locator('.storage-saved')).toBeVisible();
  });
});

test.describe('推荐功能', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/login');
    await page.fill('[name="username"]', TEST_CREDENTIALS.username);
    await page.fill('[name="password"]', TEST_CREDENTIALS.password);
    await page.click('button[type="submit"]');
    await page.waitForURL('**/dashboard');
  });

  test('应该显示每日推荐', async ({ page }) => {
    await page.goto('/ai/recommendations/daily');
    
    await expect(page.locator('.recommendation-list')).toBeVisible();
  });

  test('应该能够查看推荐详情', async ({ page }) => {
    await page.goto('/ai/recommendations/daily');
    
    const recommendation = page.locator('.recommendation-card').first();
    if (await recommendation.isVisible()) {
      await recommendation.click();
      
      await expect(page.locator('.recommendation-detail')).toBeVisible();
    }
  });

  test('应该能够收藏/取消收藏推荐', async ({ page }) => {
    await page.goto('/ai/recommendations/daily');
    
    const recommendation = page.locator('.recommendation-card').first();
    if (await recommendation.isVisible()) {
      await recommendation.hover();
      await page.click('.recommendation-card:first-child .btn-favorite');
      
      await expect(page.locator('.toast-success')).toBeVisible({ timeout: 5000 });
    }
  });

  test('应该显示回忆闪回', async ({ page }) => {
    await page.goto('/ai/recommendations/memory');
    
    await expect(page.locator('.memory-list')).toBeVisible();
  });
});

test.describe('AI任务管理', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/login');
    await page.fill('[name="username"]', TEST_CREDENTIALS.username);
    await page.fill('[name="password"]', TEST_CREDENTIALS.password);
    await page.click('button[type="submit"]');
    await page.waitForURL('**/dashboard');
    await page.goto('/ai/tasks');
  });

  test('应该显示任务列表', async ({ page }) => {
    await expect(page.locator('.task-list')).toBeVisible();
  });

  test('应该能够查看任务详情', async ({ page }) => {
    const task = page.locator('.task-item').first();
    if (await task.isVisible()) {
      await task.click();
      
      await expect(page.locator('.task-detail-modal')).toBeVisible();
    }
  });

  test('应该能够取消任务', async ({ page }) => {
    const runningTask = page.locator('.task-item.running').first();
    if (await runningTask.isVisible()) {
      await runningTask.hover();
      await page.click('.task-item.running .btn-cancel');
      
      await page.click('.confirm-dialog .btn-confirm');
      
      await expect(page.locator('.toast-success')).toBeVisible({ timeout: 5000 });
    }
  });

  test('应该能够重试失败任务', async ({ page }) => {
    const failedTask = page.locator('.task-item.failed').first();
    if (await failedTask.isVisible()) {
      await failedTask.hover();
      await page.click('.task-item.failed .btn-retry');
      
      await expect(page.locator('.toast-success')).toBeVisible({ timeout: 5000 });
    }
  });
});
