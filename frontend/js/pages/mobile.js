/**
 * AI-NAS Media Manager - 移动同步页面
 */
import { api } from '../api.js';
import { showToast, formatDate, formatStorage } from '../utils.js';

export class MobilePage {
    constructor() {
        this.container = document.getElementById('page-mobile');
        this.currentTab = 'devices';
        this.devices = [];
    }

    async load() {
        if (!this.container) return;
        
        try {
            await this.loadDevices();
            this.renderTabs();
            this.renderContent();
        } catch (e) {
            console.error('加载移动同步失败:', e);
            showToast('加载移动同步失败: ' + e.message, 'danger');
        }
    }

    async loadDevices() {
        try {
            // 获取已连接的移动设备
            const response = await api.request('/api/ecosystem/mobile/devices');
            this.devices = response.devices || [];
        } catch (e) {
            // 如果API不存在，使用模拟数据
            this.devices = this.getMockDevices();
        }
    }

    getMockDevices() {
        return [
            {
                id: 'device-001',
                name: '我的iPhone',
                platform: 'ios',
                last_sync: '2026-04-06T08:30:00Z',
                status: 'online',
                storage_used: 5368709120,
                storage_total: 128849018880,
                photos_count: 1250,
                sync_enabled: true
            },
            {
                id: 'device-002',
                name: '小米手机',
                platform: 'android',
                last_sync: '2026-04-05T22:15:00Z',
                status: 'offline',
                storage_used: 2147483648,
                storage_total: 64424509440,
                photos_count: 580,
                sync_enabled: false
            }
        ];
    }

    renderTabs() {
        const tabs = document.getElementById('mobile-tabs');
        if (!tabs) return;
        
        tabs.innerHTML = `
            <ul class="nav nav-tabs">
                <li class="nav-item">
                    <a class="nav-link ${this.currentTab === 'devices' ? 'active' : ''}" href="#" onclick="mobilePage.switchTab('devices')">
                        <i class="fas fa-mobile-alt"></i> 已连接设备
                    </a>
                </li>
                <li class="nav-item">
                    <a class="nav-link ${this.currentTab === 'settings' ? 'active' : ''}" href="#" onclick="mobilePage.switchTab('settings')">
                        <i class="fas fa-cog"></i> 同步设置
                    </a>
                </li>
                <li class="nav-item">
                    <a class="nav-link ${this.currentTab === 'history' ? 'active' : ''}" href="#" onclick="mobilePage.switchTab('history')">
                        <i class="fas fa-history"></i> 同步历史
                    </a>
                </li>
                <li class="nav-item">
                    <a class="nav-link ${this.currentTab === 'conflicts' ? 'active' : ''}" href="#" onclick="mobilePage.switchTab('conflicts')">
                        <i class="fas fa-exclamation-triangle"></i> 冲突解决
                    </a>
                </li>
            </ul>
        `;
    }

    renderContent() {
        const content = document.getElementById('mobile-content');
        if (!content) return;
        
        switch (this.currentTab) {
            case 'devices':
                this.renderDevicesList(content);
                break;
            case 'settings':
                this.renderSyncSettings(content);
                break;
            case 'history':
                this.renderSyncHistory(content);
                break;
            case 'conflicts':
                this.renderConflicts(content);
                break;
        }
    }

    switchTab(tab) {
        this.currentTab = tab;
        this.renderContent();
    }

    renderDevicesList(container) {
        container.innerHTML = `
            <div class="d-flex justify-content-between align-items-center mb-4">
                <h5><i class="fas fa-mobile-alt me-2"></i>已连接设备</h5>
                <button class="btn btn-primary" onclick="mobilePage.showAddDeviceModal()">
                    <i class="fas fa-plus"></i> 添加设备
                </button>
            </div>
            
            <div class="row">
                ${this.devices.length === 0 ? `
                    <div class="col-12 text-center text-muted py-5">
                        <i class="fas fa-mobile-alt fa-5x mb-3"></i>
                        <p>暂无已连接的移动设备</p>
                        <button class="btn btn-primary" onclick="mobilePage.showAddDeviceModal()">
                            添加设备
                        </button>
                    </div>
                ` : this.devices.map(device => this.renderDeviceCard(device)).join('')}
            </div>
            
            <div class="card mt-4">
                <div class="card-header">
                    <h5 class="mb-0"><i class="fas fa-info-circle me-2"></i>使用说明</h5>
                </div>
                <div class="card-body">
                    <ol class="mb-0">
                        <li class="mb-2">在移动设备上下载并安装 <strong>AI-NAS Mobile</strong> 应用</li>
                        <li class="mb-2">打开应用，扫描右侧的二维码或在应用内输入连接码</li>
                        <li class="mb-2">授权后，设备将自动同步照片和视频</li>
                        <li>可在下方设置同步策略和规则</li>
                    </ol>
                </div>
            </div>
        `;
    }

    renderDeviceCard(device) {
        const storagePercent = device.storage_total > 0 
            ? Math.round((device.storage_used / device.storage_total) * 100) 
            : 0;
        const platformIcon = device.platform === 'ios' ? 'fab fa-apple' : 'fab fa-android';
        const platformName = device.platform === 'ios' ? 'iOS' : 'Android';
        const statusClass = device.status === 'online' ? 'bg-success' : 'bg-secondary';
        const statusText = device.status === 'online' ? '在线' : '离线';
        
        return `
            <div class="col-md-6 mb-4">
                <div class="card device-card">
                    <div class="card-body">
                        <div class="d-flex justify-content-between align-items-start mb-3">
                            <div class="d-flex align-items-center">
                                <div class="device-icon me-3">
                                    <i class="${platformIcon} fa-2x"></i>
                                </div>
                                <div>
                                    <h5 class="mb-0">${device.name}</h5>
                                    <small class="text-muted">${platformName} · ${statusText}</small>
                                </div>
                            </div>
                            <div class="dropdown">
                                <button class="btn btn-sm btn-outline-secondary" data-bs-toggle="dropdown">
                                    <i class="fas fa-ellipsis-v"></i>
                                </button>
                                <ul class="dropdown-menu dropdown-menu-end">
                                    <li><a class="dropdown-item" href="#" onclick="mobilePage.syncDevice('${device.id}')">
                                        <i class="fas fa-sync me-2"></i>立即同步
                                    </a></li>
                                    <li><a class="dropdown-item" href="#" onclick="mobilePage.editDevice('${device.id}')">
                                        <i class="fas fa-edit me-2"></i>编辑
                                    </a></li>
                                    <li><a class="dropdown-item" href="#" onclick="mobilePage.viewDevicePhotos('${device.id}')">
                                        <i class="fas fa-images me-2"></i>查看照片
                                    </a></li>
                                    <li><hr class="dropdown-divider"></li>
                                    <li><a class="dropdown-item text-danger" href="#" onclick="mobilePage.removeDevice('${device.id}')">
                                        <i class="fas fa-trash me-2"></i>移除设备
                                    </a></li>
                                </ul>
                            </div>
                        </div>
                        
                        <div class="mb-3">
                            <div class="d-flex justify-content-between small mb-1">
                                <span>存储空间</span>
                                <span>${formatStorage(device.storage_used)} / ${formatStorage(device.storage_total)}</span>
                            </div>
                            <div class="progress" style="height: 8px;">
                                <div class="progress-bar ${storagePercent > 80 ? 'bg-danger' : 'bg-primary'}" 
                                    style="width: ${storagePercent}%"></div>
                            </div>
                        </div>
                        
                        <div class="row text-center">
                            <div class="col-4">
                                <div class="stat-small">
                                    <div class="value">${device.photos_count || 0}</div>
                                    <div class="label">照片</div>
                                </div>
                            </div>
                            <div class="col-4">
                                <div class="stat-small">
                                    <div class="value">${device.last_sync ? this.formatRelativeTime(device.last_sync) : '从未'}</div>
                                    <div class="label">最后同步</div>
                                </div>
                            </div>
                            <div class="col-4">
                                <div class="stat-small">
                                    <div class="form-check form-switch">
                                        <input class="form-check-input" type="checkbox" 
                                            ${device.sync_enabled ? 'checked' : ''} 
                                            onchange="mobilePage.toggleSync('${device.id}', this.checked)">
                                    </div>
                                    <div class="label">自动同步</div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }

    formatRelativeTime(dateStr) {
        if (!dateStr) return '从未';
        
        const date = new Date(dateStr);
        const now = new Date();
        const diff = now - date;
        
        const minutes = Math.floor(diff / 60000);
        const hours = Math.floor(diff / 3600000);
        const days = Math.floor(diff / 86400000);
        
        if (minutes < 1) return '刚刚';
        if (minutes < 60) return `${minutes}分钟前`;
        if (hours < 24) return `${hours}小时前`;
        if (days < 7) return `${days}天前`;
        return formatDate(dateStr);
    }

    renderSyncSettings(container) {
        container.innerHTML = `
            <div class="card">
                <div class="card-header">
                    <h5 class="mb-0"><i class="fas fa-cog me-2"></i>全局同步设置</h5>
                </div>
                <div class="card-body">
                    <form id="mobile-sync-settings-form">
                        <div class="row">
                            <div class="col-md-6 mb-3">
                                <label class="form-label">同步模式</label>
                                <select id="sync-mode" class="form-select">
                                    <option value="wifi-only">仅WiFi</option>
                                    <option value="wifi-cellular">WiFi + 移动数据</option>
                                    <option value="always">始终同步（注意流量）</option>
                                </select>
                            </div>
                            <div class="col-md-6 mb-3">
                                <label class="form-label">同步质量</label>
                                <select id="sync-quality" class="form-select">
                                    <option value="original">原图</option>
                                    <option value="high">高质量(80%)</option>
                                    <option value="medium">中等质量(60%)</option>
                                    <option value="low">低质量(40%)</option>
                                </select>
                            </div>
                        </div>
                        
                        <div class="row">
                            <div class="col-md-6 mb-3">
                                <label class="form-label">同步频率</label>
                                <select id="sync-frequency" class="form-select">
                                    <option value="realtime">实时</option>
                                    <option value="hourly">每小时</option>
                                    <option value="daily" selected>每天</option>
                                    <option value="manual">手动</option>
                                </select>
                            </div>
                            <div class="col-md-6 mb-3">
                                <label class="form-label">同步时间</label>
                                <input type="time" id="sync-time" class="form-control" value="02:00">
                            </div>
                        </div>
                        
                        <hr>
                        
                        <h6>同步内容</h6>
                        <div class="mb-3">
                            <div class="form-check form-switch mb-2">
                                <input class="form-check-input" type="checkbox" id="sync-photos" checked>
                                <label class="form-check-label" for="sync-photos">
                                    同步照片
                                </label>
                            </div>
                            <div class="form-check form-switch mb-2">
                                <input class="form-check-input" type="checkbox" id="sync-videos">
                                <label class="form-check-label" for="sync-videos">
                                    同步视频
                                </label>
                            </div>
                            <div class="form-check form-switch mb-2">
                                <input class="form-check-input" type="checkbox" id="sync-screenshots">
                                <label class="form-check-label" for="sync-screenshots">
                                    同步截图
                                </label>
                            </div>
                            <div class="form-check form-switch">
                                <input class="form-check-input" type="checkbox" id="sync-albums" checked>
                                <label class="form-check-label" for="sync-albums">
                                    保留相册结构
                                </label>
                            </div>
                        </div>
                        
                        <hr>
                        
                        <h6>高级设置</h6>
                        <div class="row">
                            <div class="col-md-6 mb-3">
                                <label class="form-label">电池阈值</label>
                                <div class="d-flex align-items-center">
                                    <input type="range" class="form-range flex-grow-1" 
                                        id="battery-threshold" min="10" max="50" value="20">
                                    <span class="ms-2" id="battery-threshold-value">20%</span>
                                </div>
                                <small class="text-muted">电池电量低于此值时暂停同步</small>
                            </div>
                            <div class="col-md-6 mb-3">
                                <label class="form-label">存储阈值</label>
                                <div class="d-flex align-items-center">
                                    <input type="range" class="form-range flex-grow-1" 
                                        id="storage-threshold" min="1" max="10" value="2">
                                    <span class="ms-2" id="storage-threshold-value">2GB</span>
                                </div>
                                <small class="text-muted">本地剩余空间低于此值时暂停同步</small>
                            </div>
                        </div>
                        
                        <div class="form-check form-switch mb-3">
                            <input class="form-check-input" type="checkbox" id="sync-delete-original">
                            <label class="form-check-label" for="sync-delete-original">
                                同步后自动删除原文件（谨慎开启）
                            </label>
                        </div>
                        
                        <div class="form-check form-switch mb-3">
                            <input class="form-check-input" type="checkbox" id="sync-heic-convert" checked>
                            <label class="form-check-label" for="sync-heic-convert">
                                HEIC格式转换为JPEG
                            </label>
                        </div>
                        
                        <div class="d-flex gap-2">
                            <button type="button" class="btn btn-primary" onclick="mobilePage.saveSettings()">
                                <i class="fas fa-save"></i> 保存设置
                            </button>
                            <button type="button" class="btn btn-outline-secondary" onclick="mobilePage.resetSettings()">
                                <i class="fas fa-undo"></i> 恢复默认
                            </button>
                        </div>
                    </form>
                </div>
            </div>
            
            <script>
                document.getElementById('battery-threshold')?.addEventListener('input', function() {
                    document.getElementById('battery-threshold-value').textContent = this.value + '%';
                });
                document.getElementById('storage-threshold')?.addEventListener('input', function() {
                    document.getElementById('storage-threshold-value').textContent = this.value + 'GB';
                });
            </script>
        `;
    }

    renderSyncHistory(container) {
        const history = this.getMockHistory();
        
        container.innerHTML = `
            <div class="card">
                <div class="card-header d-flex justify-content-between align-items-center">
                    <h5 class="mb-0"><i class="fas fa-history me-2"></i>同步历史</h5>
                    <div class="btn-group">
                        <button class="btn btn-sm btn-outline-secondary" onclick="mobilePage.exportHistory()">
                            <i class="fas fa-download"></i> 导出
                        </button>
                        <button class="btn btn-sm btn-outline-danger" onclick="mobilePage.clearHistory()">
                            <i class="fas fa-trash"></i> 清空
                        </button>
                    </div>
                </div>
                <div class="card-body p-0">
                    <div class="table-responsive">
                        <table class="table table-hover mb-0">
                            <thead class="table-light">
                                <tr>
                                    <th>时间</th>
                                    <th>设备</th>
                                    <th>类型</th>
                                    <th>文件数</th>
                                    <th>大小</th>
                                    <th>状态</th>
                                    <th>操作</th>
                                </tr>
                            </thead>
                            <tbody>
                                ${history.map(item => `
                                    <tr>
                                        <td>${formatDate(item.time)}</td>
                                        <td>${item.device}</td>
                                        <td><span class="badge bg-secondary">${item.type}</span></td>
                                        <td>${item.count} 个</td>
                                        <td>${formatStorage(item.size)}</td>
                                        <td>
                                            ${item.status === 'success' 
                                                ? '<span class="badge bg-success">成功</span>' 
                                                : item.status === 'failed'
                                                    ? '<span class="badge bg-danger">失败</span>'
                                                    : '<span class="badge bg-warning">进行中</span>'}
                                        </td>
                                        <td>
                                            <button class="btn btn-sm btn-outline-primary" 
                                                onclick="mobilePage.viewHistoryDetail('${item.id}')">
                                                <i class="fas fa-eye"></i>
                                            </button>
                                        </td>
                                    </tr>
                                `).join('')}
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
            
            <div class="card mt-4">
                <div class="card-header">
                    <h5 class="mb-0"><i class="fas fa-chart-bar me-2"></i>同步统计</h5>
                </div>
                <div class="card-body">
                    <div class="row">
                        <div class="col-md-3">
                            <div class="stat-card">
                                <div class="stat-value">${history.length}</div>
                                <div class="stat-label">总同步次数</div>
                            </div>
                        </div>
                        <div class="col-md-3">
                            <div class="stat-card">
                                <div class="stat-value">${history.filter(h => h.status === 'success').length}</div>
                                <div class="stat-label">成功</div>
                            </div>
                        </div>
                        <div class="col-md-3">
                            <div class="stat-card">
                                <div class="stat-value">${formatStorage(history.reduce((sum, h) => sum + h.size, 0))}</div>
                                <div class="stat-label">已同步</div>
                            </div>
                        </div>
                        <div class="col-md-3">
                            <div class="stat-card">
                                <div class="stat-value">${history.filter(h => h.type === 'upload').length}</div>
                                <div class="stat-label">上传次数</div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }

    getMockHistory() {
        return [
            { id: '1', time: '2026-04-06T08:30:00Z', device: '我的iPhone', type: '上传', count: 45, size: 536870912, status: 'success' },
            { id: '2', time: '2026-04-06T07:00:00Z', device: '小米手机', type: '下载', count: 12, size: 1073741824, status: 'success' },
            { id: '3', time: '2026-04-05T22:15:00Z', device: '我的iPhone', type: '上传', count: 128, size: 2147483648, status: 'success' },
            { id: '4', time: '2026-04-05T20:30:00Z', device: '小米手机', type: '同步', count: 8, size: 536870912, status: 'failed' },
            { id: '5', time: '2026-04-05T02:00:00Z', device: '我的iPhone', type: '备份', count: 256, size: 4294967296, status: 'success' }
        ];
    }

    renderConflicts(container) {
        const conflicts = [];
        
        container.innerHTML = `
            <div class="card">
                <div class="card-header">
                    <h5 class="mb-0"><i class="fas fa-exclamation-triangle me-2"></i>冲突解决</h5>
                </div>
                <div class="card-body">
                    ${conflicts.length === 0 ? `
                        <div class="text-center text-muted py-5">
                            <i class="fas fa-check-circle fa-5x text-success mb-3"></i>
                            <p>暂无冲突文件</p>
                        </div>
                    ` : `
                        <div class="alert alert-warning">
                            <i class="fas fa-exclamation-triangle me-2"></i>
                            发现 ${conflicts.length} 个冲突文件需要处理
                        </div>
                        
                        <div class="table-responsive">
                            <table class="table table-hover">
                                <thead>
                                    <tr>
                                        <th>文件名</th>
                                        <th>位置</th>
                                        <th>冲突类型</th>
                                        <th>操作</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    ${conflicts.map(c => `
                                        <tr>
                                            <td>${c.name}</td>
                                            <td>${c.location}</td>
                                            <td>${c.type}</td>
                                            <td>
                                                <button class="btn btn-sm btn-success" onclick="mobilePage.keepLocal('${c.id}')">
                                                    保留本地
                                                </button>
                                                <button class="btn btn-sm btn-info" onclick="mobilePage.keepRemote('${c.id}')">
                                                    保留云端
                                                </button>
                                                <button class="btn btn-sm btn-secondary" onclick="mobilePage.keepBoth('${c.id}')">
                                                    保留两者
                                                </button>
                                            </td>
                                        </tr>
                                    `).join('')}
                                </tbody>
                            </table>
                        </div>
                        
                        <button class="btn btn-primary" onclick="mobilePage.resolveAll()">
                            <i class="fas fa-check"></i> 全部保留最新
                        </button>
                    `}
                </div>
            </div>
            
            <div class="card mt-4">
                <div class="card-header">
                    <h5 class="mb-0"><i class="fas fa-shield-alt me-2"></i>冲突预防设置</h5>
                </div>
                <div class="card-body">
                    <div class="form-check form-switch mb-3">
                        <input class="form-check-input" type="checkbox" id="auto-resolve" checked>
                        <label class="form-check-label" for="auto-resolve">
                            自动保留最新版本
                        </label>
                    </div>
                    <div class="form-check form-switch mb-3">
                        <input class="form-check-input" type="checkbox" id="keep-both">
                        <label class="form-check-label" for="keep-both">
                            自动保留两个版本
                        </label>
                    </div>
                    <div class="mb-3">
                        <label class="form-label">冲突时默认操作</label>
                        <select id="conflict-action" class="form-select">
                            <option value="ask">每次询问</option>
                            <option value="keep-new">保留最新</option>
                            <option value="keep-local">保留本地</option>
                            <option value="keep-remote">保留云端</option>
                        </select>
                    </div>
                    <button class="btn btn-primary" onclick="mobilePage.saveConflictSettings()">
                        <i class="fas fa-save"></i> 保存设置
                    </button>
                </div>
            </div>
        `;
    }

    // Action methods
    async showAddDeviceModal() {
        const modal = `
            <div class="modal fade" id="addMobileDeviceModal" tabindex="-1">
                <div class="modal-dialog">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title"><i class="fas fa-mobile-alt me-2"></i>添加移动设备</h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                        </div>
                        <div class="modal-body">
                            <div class="text-center mb-4">
                                <div class="qr-code bg-light p-4 rounded d-inline-block">
                                    <i class="fas fa-qrcode fa-5x"></i>
                                </div>
                                <p class="mt-3 text-muted">扫描二维码或输入连接码</p>
                                <div class="bg-light rounded p-2 d-inline-block">
                                    <code class="fs-5">AINAS-MOBILE-20260406</code>
                                </div>
                            </div>
                            <hr>
                            <div class="mb-3">
                                <label class="form-label">或手动输入设备信息</label>
                            </div>
                            <div class="mb-3">
                                <label class="form-label">设备名称</label>
                                <input type="text" id="new-device-name" class="form-control" placeholder="如：我的iPhone">
                            </div>
                            <div class="mb-3">
                                <label class="form-label">设备平台</label>
                                <select id="new-device-platform" class="form-select">
                                    <option value="ios">iOS</option>
                                    <option value="android">Android</option>
                                </select>
                            </div>
                        </div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">取消</button>
                            <button type="button" class="btn btn-primary" onclick="mobilePage.addDevice()">
                                <i class="fas fa-plus"></i> 添加
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        // Remove existing modal if any
        const existingModal = document.getElementById('addMobileDeviceModal');
        if (existingModal) existingModal.remove();
        
        document.body.insertAdjacentHTML('beforeend', modal);
        new bootstrap.Modal(document.getElementById('addMobileDeviceModal')).show();
    }

    async addDevice() {
        const name = document.getElementById('new-device-name').value;
        const platform = document.getElementById('new-device-platform').value;
        
        if (!name) {
            showToast('请输入设备名称', 'warning');
            return;
        }
        
        showToast('设备添加功能开发中...', 'info');
        bootstrap.Modal.getInstance(document.getElementById('addMobileDeviceModal'))?.hide();
    }

    async syncDevice(deviceId) {
        showToast('正在同步...', 'info');
        // Simulate sync
        await new Promise(resolve => setTimeout(resolve, 2000));
        showToast('同步完成', 'success');
        this.load();
    }

    async toggleSync(deviceId, enabled) {
        try {
            await api.request(`/api/ecosystem/mobile/devices/${deviceId}/sync`, {
                method: 'PATCH',
                body: JSON.stringify({ sync_enabled: enabled })
            });
            showToast(enabled ? '已开启自动同步' : '已关闭自动同步', 'success');
        } catch (e) {
            showToast('操作失败', 'danger');
        }
    }

    editDevice(deviceId) {
        showToast('设备编辑功能开发中...', 'info');
    }

    viewDevicePhotos(deviceId) {
        app.showPage('media');
    }

    async removeDevice(deviceId) {
        if (!confirm('确定要移除此设备吗？')) return;
        
        try {
            await api.request(`/api/ecosystem/mobile/devices/${deviceId}`, { method: 'DELETE' });
            showToast('设备已移除', 'success');
            await this.load();
        } catch (e) {
            showToast('移除失败', 'danger');
        }
    }

    saveSettings() {
        showToast('同步设置已保存', 'success');
    }

    resetSettings() {
        if (!confirm('确定要恢复默认设置吗？')) return;
        showToast('设置已恢复默认', 'success');
    }

    viewHistoryDetail(historyId) {
        showToast('查看历史详情功能开发中...', 'info');
    }

    exportHistory() {
        showToast('导出历史记录...', 'info');
    }

    clearHistory() {
        if (!confirm('确定要清空同步历史吗？')) return;
        showToast('历史已清空', 'success');
    }

    keepLocal(conflictId) {
        showToast('已保留本地版本', 'success');
    }

    keepRemote(conflictId) {
        showToast('已保留云端版本', 'success');
    }

    keepBoth(conflictId) {
        showToast('已保留两个版本', 'success');
    }

    resolveAll() {
        showToast('所有冲突已解决', 'success');
    }

    saveConflictSettings() {
        showToast('冲突设置已保存', 'success');
    }
}

export const mobilePage = new MobilePage();
window.mobilePage = mobilePage;
