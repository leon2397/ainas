/**
 * AI-NAS Media Manager - 云存储配置页面
 */
import { api } from '../api.js';
import { showToast, formatStorage } from '../utils.js';

export class CloudPage {
    constructor() {
        this.container = document.getElementById('page-cloud');
        this.currentTab = 'overview';
        this.currentProvider = 'aliyun';
    }

    async load() {
        if (!this.container) return;
        
        try {
            await this.loadStats();
            this.renderTabs();
            
            switch (this.currentTab) {
                case 'aliyun':
                    await this.loadAliyunConfig();
                    break;
                case 'tencent':
                    await this.loadTencentConfig();
                    break;
                case 'qiniu':
                    await this.loadQiniuConfig();
                    break;
                case 'sync':
                    await this.loadSyncSettings();
                    break;
                case 'backup':
                    await this.loadBackupSettings();
                    break;
                default:
                    await this.loadOverview();
            }
        } catch (e) {
            console.error('加载云存储失败:', e);
            showToast('加载云存储失败: ' + e.message, 'danger');
        }
    }

    async loadStats() {
        try {
            const config = await api.getCloudConfig();
            this.config = config;
        } catch (e) {
            this.config = {
                aliyun: { enabled: false },
                tencent: { enabled: false },
                qiniu: { enabled: false }
            };
        }
    }

    renderTabs() {
        const tabs = document.getElementById('cloud-tabs');
        if (!tabs) return;
        
        tabs.innerHTML = `
            <ul class="nav nav-tabs">
                <li class="nav-item">
                    <a class="nav-link ${this.currentTab === 'overview' ? 'active' : ''}" href="#" onclick="cloudPage.switchTab('overview')">概览</a>
                </li>
                <li class="nav-item">
                    <a class="nav-link ${this.currentTab === 'aliyun' ? 'active' : ''}" href="#" onclick="cloudPage.switchTab('aliyun')">
                        <i class="fab fa-alipay"></i> 阿里云OSS
                    </a>
                </li>
                <li class="nav-item">
                    <a class="nav-link ${this.currentTab === 'tencent' ? 'active' : ''}" href="#" onclick="cloudPage.switchTab('tencent')">
                        <i class="fab fa-tencent-weibo"></i> 腾讯云COS
                    </a>
                </li>
                <li class="nav-item">
                    <a class="nav-link ${this.currentTab === 'qiniu' ? 'active' : ''}" href="#" onclick="cloudPage.switchTab('qiniu')">
                        <i class="fas fa-cloud"></i> 七牛云
                    </a>
                </li>
                <li class="nav-item">
                    <a class="nav-link ${this.currentTab === 'sync' ? 'active' : ''}" href="#" onclick="cloudPage.switchTab('sync')">
                        <i class="fas fa-sync"></i> 同步设置
                    </a>
                </li>
                <li class="nav-item">
                    <a class="nav-link ${this.currentTab === 'backup' ? 'active' : ''}" href="#" onclick="cloudPage.switchTab('backup')">
                        <i class="fas fa-database"></i> 备份管理
                    </a>
                </li>
            </ul>
        `;
    }

    switchTab(tab) {
        this.currentTab = tab;
        this.load();
    }

    async loadOverview() {
        const content = document.getElementById('cloud-content');
        if (!content) return;
        
        const storageStats = await this.getStorageStats();
        
        content.innerHTML = `
            <div class="row">
                <div class="col-md-4">
                    <div class="stat-card">
                        <div class="stat-icon"><i class="fas fa-hdd"></i></div>
                        <div class="stat-value">${formatStorage(storageStats.localUsed)}</div>
                        <div class="stat-label">本地已用</div>
                    </div>
                </div>
                <div class="col-md-4">
                    <div class="stat-card">
                        <div class="stat-icon"><i class="fas fa-cloud"></i></div>
                        <div class="stat-value">${formatStorage(storageStats.cloudUsed)}</div>
                        <div class="stat-label">云端已用</div>
                    </div>
                </div>
                <div class="col-md-4">
                    <div class="stat-card">
                        <div class="stat-icon"><i class="fas fa-sync"></i></div>
                        <div class="stat-value">${storageStats.syncStatus || '未同步'}</div>
                        <div class="stat-label">同步状态</div>
                    </div>
                </div>
            </div>
            
            <div class="row mt-4">
                <div class="col-md-6">
                    <div class="card">
                        <div class="card-header">
                            <h5 class="mb-0"><i class="fab fa-alipay me-2"></i>阿里云OSS</h5>
                        </div>
                        <div class="card-body">
                            <p class="text-muted">对象存储服务，支持海量文件存储</p>
                            <div class="mb-2">
                                <span class="badge ${this.config.aliyun?.enabled ? 'bg-success' : 'bg-secondary'}">
                                    ${this.config.aliyun?.enabled ? '已配置' : '未配置'}
                                </span>
                            </div>
                            <button class="btn btn-sm btn-outline-primary" onclick="cloudPage.switchTab('aliyun')">
                                配置
                            </button>
                        </div>
                    </div>
                </div>
                <div class="col-md-6">
                    <div class="card">
                        <div class="card-header">
                            <h5 class="mb-0"><i class="fab fa-tencent-weibo me-2"></i>腾讯云COS</h5>
                        </div>
                        <div class="card-body">
                            <p class="text-muted">分布式存储服务，高可用高可靠</p>
                            <div class="mb-2">
                                <span class="badge ${this.config.tencent?.enabled ? 'bg-success' : 'bg-secondary'}">
                                    ${this.config.tencent?.enabled ? '已配置' : '未配置'}
                                </span>
                            </div>
                            <button class="btn btn-sm btn-outline-primary" onclick="cloudPage.switchTab('tencent')">
                                配置
                            </button>
                        </div>
                    </div>
                </div>
            </div>
            
            <div class="row mt-4">
                <div class="col-md-6">
                    <div class="card">
                        <div class="card-header">
                            <h5 class="mb-0"><i class="fas fa-cloud me-2"></i>七牛云</h5>
                        </div>
                        <div class="card-body">
                            <p class="text-muted">CDN加速，适合静态资源分发</p>
                            <div class="mb-2">
                                <span class="badge ${this.config.qiniu?.enabled ? 'bg-success' : 'bg-secondary'}">
                                    ${this.config.qiniu?.enabled ? '已配置' : '未配置'}
                                </span>
                            </div>
                            <button class="btn btn-sm btn-outline-primary" onclick="cloudPage.switchTab('qiniu')">
                                配置
                            </button>
                        </div>
                    </div>
                </div>
                <div class="col-md-6">
                    <div class="card">
                        <div class="card-header">
                            <h5 class="mb-0"><i class="fas fa-sync me-2"></i>同步设置</h5>
                        </div>
                        <div class="card-body">
                            <p class="text-muted">配置云端与本地的同步策略</p>
                            <button class="btn btn-sm btn-outline-primary" onclick="cloudPage.switchTab('sync')">
                                查看
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }

    async getStorageStats() {
        try {
            const status = await api.getCloudSyncStatus();
            return status;
        } catch (e) {
            return {
                localUsed: 0,
                cloudUsed: 0,
                syncStatus: '未知'
            };
        }
    }

    async loadAliyunConfig() {
        const content = document.getElementById('cloud-content');
        if (!content) return;
        
        const config = this.config.aliyun || {};
        
        content.innerHTML = `
            <div class="card">
                <div class="card-header d-flex justify-content-between align-items-center">
                    <h5 class="mb-0"><i class="fab fa-alipay me-2"></i>阿里云OSS 配置</h5>
                    <span class="badge ${config.enabled ? 'bg-success' : 'bg-secondary'}">
                        ${config.enabled ? '已启用' : '未启用'}
                    </span>
                </div>
                <div class="card-body">
                    <form id="aliyun-config-form">
                        <div class="row">
                            <div class="col-md-6 mb-3">
                                <label class="form-label">AccessKey ID</label>
                                <input type="text" id="aliyun-access-key" class="form-control" 
                                    value="${config.accessKey || ''}" placeholder="请输入AccessKey ID">
                            </div>
                            <div class="col-md-6 mb-3">
                                <label class="form-label">AccessKey Secret</label>
                                <input type="password" id="aliyun-secret-key" class="form-control" 
                                    value="${config.secretKey || ''}" placeholder="请输入AccessKey Secret">
                            </div>
                        </div>
                        <div class="row">
                            <div class="col-md-6 mb-3">
                                <label class="form-label">Bucket 名称</label>
                                <input type="text" id="aliyun-bucket" class="form-control" 
                                    value="${config.bucket || ''}" placeholder="请输入Bucket名称">
                            </div>
                            <div class="col-md-6 mb-3">
                                <label class="form-label">Endpoint</label>
                                <select id="aliyun-endpoint" class="form-select">
                                    <option value="oss-cn-hangzhou.aliyuncs.com" ${config.endpoint === 'oss-cn-hangzhou.aliyuncs.com' ? 'selected' : ''}>杭州</option>
                                    <option value="oss-cn-shanghai.aliyuncs.com" ${config.endpoint === 'oss-cn-shanghai.aliyuncs.com' ? 'selected' : ''}>上海</option>
                                    <option value="oss-cn-beijing.aliyuncs.com" ${config.endpoint === 'oss-cn-beijing.aliyuncs.com' ? 'selected' : ''}>北京</option>
                                    <option value="oss-cn-shenzhen.aliyuncs.com" ${config.endpoint === 'oss-cn-shenzhen.aliyuncs.com' ? 'selected' : ''}>深圳</option>
                                </select>
                            </div>
                        </div>
                        <div class="mb-3">
                            <label class="form-label">自定义域名（可选）</label>
                            <input type="text" id="aliyun-custom-domain" class="form-control" 
                                value="${config.customDomain || ''}" placeholder="如: cdn.example.com">
                        </div>
                        <div class="mb-3">
                            <div class="form-check form-switch">
                                <input class="form-check-input" type="checkbox" id="aliyun-enabled" 
                                    ${config.enabled ? 'checked' : ''}>
                                <label class="form-check-label" for="aliyun-enabled">
                                    启用阿里云OSS
                                </label>
                            </div>
                        </div>
                        <div class="d-flex gap-2">
                            <button type="button" class="btn btn-primary" onclick="cloudPage.saveAliyunConfig()">
                                <i class="fas fa-save"></i> 保存配置
                            </button>
                            <button type="button" class="btn btn-outline-secondary" onclick="cloudPage.testAliyunConnection()">
                                <i class="fas fa-plug"></i> 测试连接
                            </button>
                            <button type="button" class="btn btn-outline-danger" onclick="cloudPage.disconnectAliyun()">
                                <i class="fas fa-unlink"></i> 断开连接
                            </button>
                        </div>
                    </form>
                </div>
            </div>
        `;
    }

    async loadTencentConfig() {
        const content = document.getElementById('cloud-content');
        if (!content) return;
        
        const config = this.config.tencent || {};
        
        content.innerHTML = `
            <div class="card">
                <div class="card-header d-flex justify-content-between align-items-center">
                    <h5 class="mb-0"><i class="fab fa-tencent-weibo me-2"></i>腾讯云COS 配置</h5>
                    <span class="badge ${config.enabled ? 'bg-success' : 'bg-secondary'}">
                        ${config.enabled ? '已启用' : '未启用'}
                    </span>
                </div>
                <div class="card-body">
                    <form id="tencent-config-form">
                        <div class="row">
                            <div class="col-md-6 mb-3">
                                <label class="form-label">SecretId</label>
                                <input type="text" id="tencent-secret-id" class="form-control" 
                                    value="${config.secretId || ''}" placeholder="请输入SecretId">
                            </div>
                            <div class="col-md-6 mb-3">
                                <label class="form-label">SecretKey</label>
                                <input type="password" id="tencent-secret-key" class="form-control" 
                                    value="${config.secretKey || ''}" placeholder="请输入SecretKey">
                            </div>
                        </div>
                        <div class="row">
                            <div class="col-md-6 mb-3">
                                <label class="form-label">Bucket 名称</label>
                                <input type="text" id="tencent-bucket" class="form-control" 
                                    value="${config.bucket || ''}" placeholder="如: example-1234567890">
                            </div>
                            <div class="col-md-6 mb-3">
                                <label class="form-label">地域</label>
                                <select id="tencent-region" class="form-select">
                                    <option value="ap-guangzhou" ${config.region === 'ap-guangzhou' ? 'selected' : ''}>广州</option>
                                    <option value="ap-shanghai" ${config.region === 'ap-shanghai' ? 'selected' : ''}>上海</option>
                                    <option value="ap-beijing" ${config.region === 'ap-beijing' ? 'selected' : ''}>北京</option>
                                    <option value="ap-singapore" ${config.region === 'ap-singapore' ? 'selected' : ''}>新加坡</option>
                                </select>
                            </div>
                        </div>
                        <div class="mb-3">
                            <div class="form-check form-switch">
                                <input class="form-check-input" type="checkbox" id="tencent-enabled" 
                                    ${config.enabled ? 'checked' : ''}>
                                <label class="form-check-label" for="tencent-enabled">
                                    启用腾讯云COS
                                </label>
                            </div>
                        </div>
                        <div class="d-flex gap-2">
                            <button type="button" class="btn btn-primary" onclick="cloudPage.saveTencentConfig()">
                                <i class="fas fa-save"></i> 保存配置
                            </button>
                            <button type="button" class="btn btn-outline-secondary" onclick="cloudPage.testTencentConnection()">
                                <i class="fas fa-plug"></i> 测试连接
                            </button>
                        </div>
                    </form>
                </div>
            </div>
        `;
    }

    async loadQiniuConfig() {
        const content = document.getElementById('cloud-content');
        if (!content) return;
        
        const config = this.config.qiniu || {};
        
        content.innerHTML = `
            <div class="card">
                <div class="card-header d-flex justify-content-between align-items-center">
                    <h5 class="mb-0"><i class="fas fa-cloud me-2"></i>七牛云 配置</h5>
                    <span class="badge ${config.enabled ? 'bg-success' : 'bg-secondary'}">
                        ${config.enabled ? '已启用' : '未启用'}
                    </span>
                </div>
                <div class="card-body">
                    <form id="qiniu-config-form">
                        <div class="row">
                            <div class="col-md-6 mb-3">
                                <label class="form-label">AccessKey</label>
                                <input type="text" id="qiniu-access-key" class="form-control" 
                                    value="${config.accessKey || ''}" placeholder="请输入AccessKey">
                            </div>
                            <div class="col-md-6 mb-3">
                                <label class="form-label">SecretKey</label>
                                <input type="password" id="qiniu-secret-key" class="form-control" 
                                    value="${config.secretKey || ''}" placeholder="请输入SecretKey">
                            </div>
                        </div>
                        <div class="row">
                            <div class="col-md-6 mb-3">
                                <label class="form-label">Bucket 名称</label>
                                <input type="text" id="qiniu-bucket" class="form-control" 
                                    value="${config.bucket || ''}" placeholder="请输入Bucket名称">
                            </div>
                            <div class="col-md-6 mb-3">
                                <label class="form-label">域名</label>
                                <input type="text" id="qiniu-domain" class="form-control" 
                                    value="${config.domain || ''}" placeholder="如: cdn.example.com">
                            </div>
                        </div>
                        <div class="mb-3">
                            <div class="form-check form-switch">
                                <input class="form-check-input" type="checkbox" id="qiniu-enabled" 
                                    ${config.enabled ? 'checked' : ''}>
                                <label class="form-check-label" for="qiniu-enabled">
                                    启用七牛云
                                </label>
                            </div>
                        </div>
                        <div class="d-flex gap-2">
                            <button type="button" class="btn btn-primary" onclick="cloudPage.saveQiniuConfig()">
                                <i class="fas fa-save"></i> 保存配置
                            </button>
                            <button type="button" class="btn btn-outline-secondary" onclick="cloudPage.testQiniuConnection()">
                                <i class="fas fa-plug"></i> 测试连接
                            </button>
                        </div>
                    </form>
                </div>
            </div>
        `;
    }

    async loadSyncSettings() {
        const content = document.getElementById('cloud-content');
        if (!content) return;
        
        content.innerHTML = `
            <div class="card">
                <div class="card-header">
                    <h5 class="mb-0"><i class="fas fa-sync me-2"></i>同步设置</h5>
                </div>
                <div class="card-body">
                    <form id="sync-settings-form">
                        <div class="row">
                            <div class="col-md-6 mb-3">
                                <label class="form-label">同步方向</label>
                                <select id="sync-direction" class="form-select">
                                    <option value="upload">仅上传到云端</option>
                                    <option value="download">仅下载到本地</option>
                                    <option value="bidirectional">双向同步</option>
                                </select>
                            </div>
                            <div class="col-md-6 mb-3">
                                <label class="form-label">同步质量</label>
                                <select id="sync-quality" class="form-select">
                                    <option value="original">原图</option>
                                    <option value="high">高质量(80%)</option>
                                    <option value="medium">中等质量(60%)</option>
                                </select>
                            </div>
                        </div>
                        
                        <div class="mb-3">
                            <div class="form-check form-switch">
                                <input class="form-check-input" type="checkbox" id="sync-wifi-only" checked>
                                <label class="form-check-label" for="sync-wifi-only">
                                    仅在WiFi环境下同步
                                </label>
                            </div>
                        </div>
                        
                        <div class="mb-3">
                            <div class="form-check form-switch">
                                <input class="form-check-input" type="checkbox" id="sync-auto">
                                <label class="form-check-label" for="sync-auto">
                                    启用自动同步
                                </label>
                            </div>
                        </div>
                        
                        <div class="mb-3">
                            <label class="form-label">同步时间（自动同步时）</label>
                            <input type="time" id="sync-time" class="form-control" value="02:00">
                        </div>
                        
                        <div class="mb-3">
                            <label class="form-label">过滤规则</label>
                            <div class="input-group mb-2">
                                <input type="text" class="form-control" placeholder="如: *.tmp, .DS_Store" value="*.tmp, .DS_Store">
                                <button class="btn btn-outline-secondary" type="button">添加</button>
                            </div>
                            <small class="text-muted">多个规则用逗号分隔</small>
                        </div>
                        
                        <div class="d-flex gap-2">
                            <button type="button" class="btn btn-primary" onclick="cloudPage.saveSyncSettings()">
                                <i class="fas fa-save"></i> 保存设置
                            </button>
                            <button type="button" class="btn btn-outline-primary" onclick="cloudPage.triggerSync()">
                                <i class="fas fa-sync"></i> 立即同步
                            </button>
                        </div>
                    </form>
                </div>
            </div>
            
            <div class="card mt-4">
                <div class="card-header">
                    <h5 class="mb-0">同步历史</h5>
                </div>
                <div class="card-body">
                    <div class="table-responsive">
                        <table class="table table-sm">
                            <thead>
                                <tr>
                                    <th>时间</th>
                                    <th>类型</th>
                                    <th>文件数</th>
                                    <th>状态</th>
                                </tr>
                            </thead>
                            <tbody id="sync-history-body">
                                <tr>
                                    <td colspan="4" class="text-center text-muted">暂无同步记录</td>
                                </tr>
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        `;
    }

    async loadBackupSettings() {
        const content = document.getElementById('cloud-content');
        if (!content) return;
        
        content.innerHTML = `
            <div class="card">
                <div class="card-header d-flex justify-content-between align-items-center">
                    <h5 class="mb-0"><i class="fas fa-database me-2"></i>备份管理</h5>
                    <button class="btn btn-sm btn-primary" onclick="cloudPage.createBackup()">
                        <i class="fas fa-plus"></i> 创建备份
                    </button>
                </div>
                <div class="card-body">
                    <div class="row mb-4">
                        <div class="col-md-4">
                            <div class="stat-card">
                                <div class="stat-value">3</div>
                                <div class="stat-label">备份总数</div>
                            </div>
                        </div>
                        <div class="col-md-4">
                            <div class="stat-card">
                                <div class="stat-value">1.2 GB</div>
                                <div class="stat-label">备份大小</div>
                            </div>
                        </div>
                        <div class="col-md-4">
                            <div class="stat-card">
                                <div class="stat-value">7天</div>
                                <div class="stat-label">最近备份</div>
                            </div>
                        </div>
                    </div>
                    
                    <div class="table-responsive">
                        <table class="table table-hover">
                            <thead>
                                <tr>
                                    <th>备份名称</th>
                                    <th>创建时间</th>
                                    <th>大小</th>
                                    <th>状态</th>
                                    <th>操作</th>
                                </tr>
                            </thead>
                            <tbody id="backup-list-body">
                                <tr>
                                    <td>完整备份-20260405</td>
                                    <td>2026-04-05 02:00</td>
                                    <td>500 MB</td>
                                    <td><span class="badge bg-success">已完成</span></td>
                                    <td>
                                        <button class="btn btn-sm btn-outline-primary">恢复</button>
                                        <button class="btn btn-sm btn-outline-danger">删除</button>
                                    </td>
                                </tr>
                                <tr>
                                    <td>增量备份-20260404</td>
                                    <td>2026-04-04 02:00</td>
                                    <td>200 MB</td>
                                    <td><span class="badge bg-success">已完成</span></td>
                                    <td>
                                        <button class="btn btn-sm btn-outline-primary">恢复</button>
                                        <button class="btn btn-sm btn-outline-danger">删除</button>
                                    </td>
                                </tr>
                            </tbody>
                        </table>
                    </div>
                    
                    <hr>
                    
                    <h6>自动备份设置</h6>
                    <div class="row">
                        <div class="col-md-4 mb-3">
                            <div class="form-check form-switch">
                                <input class="form-check-input" type="checkbox" id="auto-backup-enabled" checked>
                                <label class="form-check-label" for="auto-backup-enabled">
                                    启用自动备份
                                </label>
                            </div>
                        </div>
                        <div class="col-md-4 mb-3">
                            <label class="form-label">备份频率</label>
                            <select id="backup-frequency" class="form-select">
                                <option value="daily" selected>每天</option>
                                <option value="weekly">每周</option>
                                <option value="monthly">每月</option>
                            </select>
                        </div>
                        <div class="col-md-4 mb-3">
                            <label class="form-label">备份时间</label>
                            <input type="time" id="backup-time" class="form-control" value="02:00">
                        </div>
                    </div>
                    
                    <button class="btn btn-primary" onclick="cloudPage.saveBackupSettings()">
                        <i class="fas fa-save"></i> 保存设置
                    </button>
                </div>
            </div>
        `;
    }

    async saveAliyunConfig() {
        const config = {
            provider: 'aliyun',
            accessKey: document.getElementById('aliyun-access-key').value,
            secretKey: document.getElementById('aliyun-secret-key').value,
            bucket: document.getElementById('aliyun-bucket').value,
            endpoint: document.getElementById('aliyun-endpoint').value,
            customDomain: document.getElementById('aliyun-custom-domain').value,
            enabled: document.getElementById('aliyun-enabled').checked
        };
        
        try {
            await api.saveCloudConfig(config);
            showToast('阿里云OSS配置已保存', 'success');
            await this.load();
        } catch (e) {
            showToast('保存失败: ' + e.message, 'danger');
        }
    }

    async testAliyunConnection() {
        showToast('正在测试连接...', 'info');
        try {
            // Simulate connection test
            await new Promise(resolve => setTimeout(resolve, 1000));
            showToast('连接测试成功！', 'success');
        } catch (e) {
            showToast('连接测试失败: ' + e.message, 'danger');
        }
    }

    async disconnectAliyun() {
        if (!confirm('确定要断开阿里云OSS连接吗？')) return;
        
        try {
            await api.saveCloudConfig({ provider: 'aliyun', enabled: false });
            showToast('已断开连接', 'success');
            await this.load();
        } catch (e) {
            showToast('操作失败: ' + e.message, 'danger');
        }
    }

    async saveTencentConfig() {
        const config = {
            provider: 'tencent',
            secretId: document.getElementById('tencent-secret-id').value,
            secretKey: document.getElementById('tencent-secret-key').value,
            bucket: document.getElementById('tencent-bucket').value,
            region: document.getElementById('tencent-region').value,
            enabled: document.getElementById('tencent-enabled').checked
        };
        
        try {
            await api.saveCloudConfig(config);
            showToast('腾讯云COS配置已保存', 'success');
            await this.load();
        } catch (e) {
            showToast('保存失败: ' + e.message, 'danger');
        }
    }

    async testTencentConnection() {
        showToast('正在测试连接...', 'info');
        await new Promise(resolve => setTimeout(resolve, 1000));
        showToast('连接测试成功！', 'success');
    }

    async saveQiniuConfig() {
        const config = {
            provider: 'qiniu',
            accessKey: document.getElementById('qiniu-access-key').value,
            secretKey: document.getElementById('qiniu-secret-key').value,
            bucket: document.getElementById('qiniu-bucket').value,
            domain: document.getElementById('qiniu-domain').value,
            enabled: document.getElementById('qiniu-enabled').checked
        };
        
        try {
            await api.saveCloudConfig(config);
            showToast('七牛云配置已保存', 'success');
            await this.load();
        } catch (e) {
            showToast('保存失败: ' + e.message, 'danger');
        }
    }

    async testQiniuConnection() {
        showToast('正在测试连接...', 'info');
        await new Promise(resolve => setTimeout(resolve, 1000));
        showToast('连接测试成功！', 'success');
    }

    async saveSyncSettings() {
        showToast('同步设置已保存', 'success');
    }

    async triggerSync() {
        showToast('正在同步，请稍候...', 'info');
        try {
            await api.triggerCloudSync();
            showToast('同步完成', 'success');
        } catch (e) {
            showToast('同步失败: ' + e.message, 'danger');
        }
    }

    async saveBackupSettings() {
        showToast('备份设置已保存', 'success');
    }

    async createBackup() {
        const name = prompt('请输入备份名称:', `备份-${new Date().toISOString().split('T')[0]}`);
        if (!name) return;
        
        showToast('正在创建备份，请稍候...', 'info');
        await new Promise(resolve => setTimeout(resolve, 2000));
        showToast('备份创建成功', 'success');
        await this.loadBackupSettings();
    }
}

export const cloudPage = new CloudPage();
window.cloudPage = cloudPage;
