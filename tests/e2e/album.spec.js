const { test, expect } = require('@playwright/test');

test.use({
  baseURL: 'http://localhost:8000',
  headless: true,
});

/**
 * 相册管理 E2E 测试
 */
test.describe('相册管理', () => {
  
  test.beforeEach(async ({ page }) => {
    // 登录
    await page.goto('/');
    await page.fill('input[name="username"]', 'admin');
    await page.fill('input[name="password"]', 'admin123');
    await page.click('button[type="submit"]');
    await page.waitForURL('**/dashboard**');
    
    // 导航到相册页面
    await page.click('text=相册');
    await page.waitForSelector('.album-grid, .album-list');
  });

  test('创建自定义相册', async ({ page }) => {
    // 点击创建相册
    await page.click('text=创建相册');
    
    // 填写相册信息
    await page.fill('input[name="album_name"]', '我的旅行相册');
    await page.fill('textarea[name="description"]', '记录美好的旅行时光');
    
    // 选择相册类型
    await page.selectOption('select[name="album_type"]', 'custom');
    
    // 提交
    await page.click('button[type="submit"]');
    
    // 验证创建成功
    await expect(page.locator('text=相册创建成功')).toBeVisible();
    await expect(page.locator('text=我的旅行相册')).toBeVisible();
  });

  test('查看相册详情', async ({ page }) => {
    // 假设有一个相册存在
    await page.click('.album-item:first-child, .album-card:first-child');
    
    // 验证详情页显示
    await expect(page.locator('.album-detail')).toBeVisible();
    await expect(page.locator('.album-photos')).toBeVisible();
  });

  test('添加照片到相册', async ({ page }) => {
    // 进入相册详情
    await page.click('.album-item:first-child');
    
    // 点击添加照片
    await page.click('text=添加照片');
    
    // 选择照片（假设有照片可选）
    await page.click('.photo-select:first-child');
    await page.click('.photo-select:nth-child(2)');
    
    // 确认添加
    await page.click('text=确认添加');
    
    // 验证添加成功
    await expect(page.locator('text=照片添加成功')).toBeVisible();
  });

  test('从相册移除照片', async ({ page }) => {
    await page.click('.album-item:first-child');
    
    // 选择照片
    await page.hover('.album-photo:first-child');
    await page.click('.remove-photo-btn');
    
    // 确认移除
    await page.click('text=确认');
    
    // 验证移除成功
    await expect(page.locator('text=照片已移除')).toBeVisible();
  });

  test('编辑相册信息', async ({ page }) => {
    await page.click('.album-item:first-child');
    
    // 点击编辑
    await page.click('text=编辑');
    
    // 修改名称
    await page.fill('input[name="album_name"]', '修改后的相册名');
    
    // 保存
    await page.click('text=保存');
    
    // 验证修改成功
    await expect(page.locator('text=相册信息已更新')).toBeVisible();
    await expect(page.locator('text=修改后的相册名')).toBeVisible();
  });

  test('删除相册', async ({ page }) => {
    // 先创建一个测试相册
    await page.click('text=创建相册');
    await page.fill('input[name="album_name"]', '待删除相册');
    await page.click('button[type="submit"]');
    await expect(page.locator('text=相册创建成功')).toBeVisible();
    
    // 找到并删除
    await page.click('.album-item:has-text("待删除相册") .delete-btn');
    
    // 确认删除
    await page.click('text=确认删除');
    
    // 验证删除成功
    await expect(page.locator('text=相册已删除')).toBeVisible();
    await expect(page.locator('text=待删除相册')).not.toBeVisible();
  });

  test('相册排序', async ({ page }) => {
    // 创建多个相册
    for (let i = 1; i <= 3; i++) {
      await page.click('text=创建相册');
      await page.fill('input[name="album_name"]', `相册${i}`);
      await page.click('button[type="submit"]');
      await page.waitForTimeout(500);
    }
    
    // 点击排序按钮
    await page.click('text=排序');
    await page.selectOption('select[name="sort_by"]', 'name');
    await page.selectOption('select[name="sort_order"]', 'asc');
    
    // 验证排序结果
    const albumNames = await page.$$eval('.album-item .album-name', els => 
      els.map(el => el.textContent)
    );
    
    // 验证按名称排序
    expect(albumNames).toEqual([...albumNames].sort());
  });

  test('AI自动相册', async ({ page }) => {
    // 等待AI分类完成
    await page.waitForTimeout(2000);
    
    // 检查是否有AI生成的相册
    const aiAlbums = await page.locator('.album-item[data-type="ai"]').count();
    
    if (aiAlbums > 0) {
      // 点击AI相册
      await page.click('.album-item[data-type="ai"]:first-child');
      
      // 验证AI相册详情
      await expect(page.locator('.ai-album-badge')).toBeVisible();
    }
  });

  test('相册分享', async ({ page }) => {
    await page.click('.album-item:first-child');
    
    // 点击分享
    await page.click('text=分享');
    
    // 生成分享链接
    await page.click('text=生成分享链接');
    
    // 验证分享链接生成
    await expect(page.locator('.share-link')).toBeVisible();
    
    // 复制链接
    await page.click('text=复制链接');
    await expect(page.locator('text=链接已复制')).toBeVisible();
  });
});
