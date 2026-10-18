const { test, expect } = require('@playwright/test');

test.use({
  baseURL: 'http://localhost:8000',
  headless: true,
});

/**
 * 文件上传 E2E 测试
 */
test.describe('文件上传', () => {
  
  test.beforeEach(async ({ page }) => {
    // 每个测试前登录
    await page.goto('/');
    await page.fill('input[name="username"]', 'admin');
    await page.fill('input[name="password"]', 'admin123');
    await page.click('button[type="submit"]');
    await page.waitForURL('**/dashboard**');
    
    // 导航到媒体页面
    await page.click('text=媒体库');
    await page.waitForSelector('.media-grid, .media-list');
  });

  test('上传单张图片', async ({ page }) => {
    // 点击上传按钮
    await page.click('text=上传文件');
    
    // 选择文件
    const input = page.locator('input[type="file"]');
    await input.setInputFiles({
      name: 'test-image.jpg',
      mimeType: 'image/jpeg',
      buffer: Buffer.from('fake-image-data')
    });
    
    // 等待上传完成
    await expect(page.locator('text=上传成功')).toBeVisible({ timeout: 10000 });
    
    // 验证文件出现在列表中
    await expect(page.locator('text=test-image')).toBeVisible();
  });

  test('上传多张图片', async ({ page }) => {
    await page.click('text=上传文件');
    
    const input = page.locator('input[type="file"]');
    await input.setInputFiles([
      { name: 'image1.jpg', mimeType: 'image/jpeg', buffer: Buffer.from('data1') },
      { name: 'image2.jpg', mimeType: 'image/jpeg', buffer: Buffer.from('data2') },
      { name: 'image3.jpg', mimeType: 'image/jpeg', buffer: Buffer.from('data3') }
    ]);
    
    // 等待所有上传完成
    await expect(page.locator('text=3个文件上传成功')).toBeVisible({ timeout: 15000 });
  });

  test('上传视频文件', async ({ page }) => {
    await page.click('text=上传文件');
    
    const input = page.locator('input[type="file"]');
    await input.setInputFiles({
      name: 'test-video.mp4',
      mimeType: 'video/mp4',
      buffer: Buffer.from('fake-video-data')
    });
    
    // 验证视频类型识别
    await expect(page.locator('.video-icon, [data-type="video"]')).toBeVisible({ timeout: 10000 });
  });

  test('上传进度显示', async ({ page }) => {
    await page.click('text=上传文件');
    
    // 上传大文件
    const input = page.locator('input[type="file"]');
    await input.setInputFiles({
      name: 'large-image.jpg',
      mimeType: 'image/jpeg',
      buffer: Buffer.alloc(1024 * 1024) // 1MB
    });
    
    // 验证进度条显示
    await expect(page.locator('.progress-bar, .upload-progress')).toBeVisible();
  });

  test('取消上传', async ({ page }) => {
    await page.click('text=上传文件');
    
    const input = page.locator('input[type="file"]');
    await input.setInputFiles({
      name: 'cancel-test.jpg',
      mimeType: 'image/jpeg',
      buffer: Buffer.alloc(10 * 1024 * 1024) // 10MB
    });
    
    // 点击取消
    await page.click('text=取消');
    
    // 验证上传已取消
    await expect(page.locator('text=已取消')).toBeVisible();
  });

  test('拖拽上传', async ({ page }) => {
    // 找到上传区域
    const dropZone = page.locator('.upload-zone, .drop-zone');
    
    // 模拟拖拽
    await dropZone.evaluate((el, data) => {
      const event = new DragEvent('drop', {
        dataTransfer: {
          files: [new File([data], 'drag-image.jpg', { type: 'image/jpeg' })]
        }
      });
      el.dispatchEvent(event);
    }, 'fake-image-data');
    
    // 验证上传开始
    await expect(page.locator('.uploading, .progress')).toBeVisible();
  });

  test('上传后显示缩略图', async ({ page }) => {
    await page.click('text=上传文件');
    
    const input = page.locator('input[type="file"]');
    await input.setInputFiles({
      name: 'thumbnail-test.jpg',
      mimeType: 'image/jpeg',
      buffer: Buffer.from('fake-image-data')
    });
    
    // 等待缩略图生成
    await expect(page.locator('img.thumbnail, .media-thumb img')).toBeVisible({ timeout: 15000 });
  });
});
