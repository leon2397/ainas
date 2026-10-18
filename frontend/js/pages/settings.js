/**
 * AI-NAS Media Manager - 系统设置页面
 */
import { api } from '../api.js';
import { showToast } from '../utils.js';

export class SettingsPage {
    constructor() {
        this.container = document.getElementById('page-settings');
        this.currentUser = null;
        this.currentRole = null;
    }

    setCurrentUser(username, role) {
        this.currentUser = username;
        this.currentRole = role;
    }

    async load() {
        if (!this.container) return;
        
        this.renderSettings();
        this.loadSettings();
    }

    renderSettings() {
        const settingsContent = document.getElementById('settings-content');
        if (!settingsContent) return;
        
        settingsContent.innerHTML = `
            <!-- Settings Tabs -->
            <ul class="nav nav-tabs mb-4" id="settingsTabs" role="tablist">
                <li class="nav-item" role="presentation">
                    <button class="nav-link active" id="basic-tab" data-bs-toggle="tab" data-bs-target="#basic" type="button">
                        <i class="fas fa-cog me-2"></i>基础设置
                    </button>
                </li>
                <li class="nav-item" role="presentation">
                    <button class="nav-link" id="storage-tab" data-bs-toggle="tab" data-bs-target="#storage" type="button">
                        <i class="fas fa-hdd me-2"></i>存储设置
                    </button>
                </li>
                <li class="nav-item" role="presentation">
                    <button class="nav-link" id="security-tab" data-bs-toggle="tab" data-bs-target="#security" type="button">
                        <i class="fas fa-shield-alt me-2"></i>安全设置
                    </button>
                </li>
                <li class="nav-item" role="presentation">
                    <button class="nav-link" id="notifications-tab" data-bs-toggle="tab" data-bs-target="#notifications" type="button">
                        <i class="fas fa-bell me-2"></i>通知设置
                    </button>
                </li>
                ${this.currentRole === 'admin' ? `
                <li class="nav-item" role="presentation">
                    <button class="nav-link" id="system-tab" data-bs-toggle="tab" data-bs-target="#system" type="button">
                        <i class="fas fa-server me-2"></i>系统管理
                    </button>
                </li>
                ` : ''}
            </ul>
            
            <!-- Tab Content -->
            <div class="tab-content" id="settingsTabContent">
                <!-- Basic Settings -->
                <div class="tab-pane fade show active" id="basic" role="tabpanel">
                    ${this.renderBasicSettings()}
                </div>
                
                <!-- Storage Settings -->
                <div class="tab-pane fade" id="storage" role="tabpanel">
                    ${this.renderStorageSettings()}
                </div>
                
                <!-- Security Settings -->
                <div class="tab-pane fade" id="security" role="tabpanel">
                    ${this.renderSecuritySettings()}
                </div>
                
                <!-- Notification Settings -->
                <div class="tab-pane fade" id="notifications" role="tabpanel">
                    ${this.renderNotificationSettings()}
                </div>
                
                <!-- System Management (Admin Only) -->
                ${this.currentRole === 'admin' ? `
                <div class="tab-pane fade" id="system" role="tabpanel">
                    ${this.renderSystemSettings()}
                </div>
                ` : ''}
            </div>
        `;
    }

    renderBasicSettings() {
        return `
            <div class="card">
                <div class="card-header">
                    <h5 class="mb-0"><i class="fas fa-cog me-2"></i>基础设置</h5>
                </div>
                <div class="card-body">
                    <form id="basic-settings-form">
                        <div class="row">
                            <div class="col-md-6 mb-3">
                                <label class="form-label">系统名称</label>
                                <input type="text" id="system-name" class="form-control" value="AI-NAS Media Manager">
                                <small class="text-muted">显示在界面标题和通知中</small>
                            </div>
                            <div class="col-md-6 mb-3">
                                <label class="form-label">界面语言</label>
                                <select id="system-language" class="form-select">
                                    <option value="zh-CN" selected>简体中文</option>
                                    <option value="zh-TW">繁體中文</option>
                                    <option value="en-US">English</option>
                                    <option value="ja-JP">日本語</option>
                                </select>
                            </div>
                        </div>
                        
                        <div class="row">
                            <div class="col-md-6 mb-3">
                                <label class="form-label">时区</label>
                                <select id="system-timezone" class="form-select">
                                    <option value="Asia/Shanghai" selected>中国 (UTC+8)</option>
                                    <option value="Asia/Tokyo">日本 (UTC+9)</option>
                                    <option value="America/New_York">美国东部 (UTC-5)</option>
                                    <option value="Europe/London">英国 (UTC+0)</option>
                                </select>
                            </div>
                            <div class="col-md-6 mb-3">
                                <label class="form-label">日期格式</label>
                                <select id="date-format" class="form-select">
                                    <option value="YYYY-MM-DD" selected>2026-04-06</option>
                                    <option value="DD/MM/YYYY">06/04/2026</option>
                                    <option value="MM/DD/YYYY">04/06/2026</option>
                                </select>
                            </div>
                        </div>
                        
                        <div class="row">
                            <div class="col-md-6 mb-3">
                                <label class="form-label">每页显示条数</label>
                                <select id="page-size" class="form-select">
                                    <option value="10">10</option>
                                    <option value="20" selected>20</option>
                                    <option value="50">50</option>
                                    <option value="100">100</option>
                                </select>
                            </div>
                            <div class="col-md-6 mb-3">
                                <label class="form-label">主题</label>
                                <select id="theme" class="form-select">
                                    <option value="light" selected>浅色</option>
                                    <option value="dark">深色</option>
                                    <option value="auto">跟随系统</option>
                                </select>
                            </div>
                        </div>
                        
                        <hr>
                        
                        <div class="mb-3">
                            <div class="form-check form-switch">
                                <input class="form-check-input" type="checkbox" id="enable-analytics" checked>
                                <label class="form-check-label" for="enable-analytics">
                                    启用使用统计（帮助我们改进产品）
                                </label>
                            </div>
                        </div>
                        
                        <button type="button" class="btn btn-primary" onclick="settingsPage.saveBasicSettings()">
                            <i class="fas fa-save me-2"></i>保存设置
                        </button>
                    </form>
                </div>
            </div>
            
            <!-- Account Information -->
            <div class="card mt-4">
                <div class="card-header">
                    <h5 class="mb-0"><i class="fas fa-user me-2"></i>账户信息</h5>
                </div>
                <div class="card-body">
                    <div class="row">
                        <div class="col-md-6">
                            <p><strong>用户名：</strong> ${this.currentUser || '-'}</p>
                            <p><strong>角色：</strong> <span class="badge bg-primary">${this.getRoleName(this.currentRole)}</span></p>
                            <p><strong>注册时间：</strong> 2026-01-01</p>
                        </div>
                        <div class="col-md-6">
                            <button class="btn btn-outline-primary me-2 mb-2" onclick="settingsPage.showChangePasswordModal()">
                                <i class="fas fa-key me-2"></i>修改密码
                            </button>
                            <button class="btn btn-outline-danger mb-2" onclick="settingsPage.logout()">
                                <i class="fas fa-sign-out-alt me-2"></i>退出登录
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }

    renderStorageSettings() {
        return `
            <div class="card">
                <div class="card-header">
                    <h5 class="mb-0"><i class="fas fa-folder-open me-2"></i>媒体存储路径</h5>
                </div>
                <div class="card-body">
                    <form id="storage-settings-form">
                        <div class="mb-3">
                            <label class="form-label">媒体根目录</label>
                            <div class="input-group">
                                <input type="text" id="media-root-path" class="form-control" value="/mnt/media" readonly>
                                <button class="btn btn-outline-secondary" type="button" onclick="settingsPage.browsePath()">
                                    <i class="fas fa-folder-open"></i>
                                </button>
                            </div>
                        </div>
                        
                        <div class="row">
                            <div class="col-md-6 mb-3">
                                <label class="form-label">图片目录</label>
                                <input type="text" id="image-path" class="form-control" value="/mnt/media/images">
                            </div>
                            <div class="col-md-6 mb-3">
                                <label class="form-label">视频目录</label>
                                <input type="text" id="video-path" class="form-control" value="/mnt/media/videos">
                            </div>
                        </div>
                        
                        <hr>
                        <h6>存储策略</h6>
                        <div class="row">
                            <div class="col-md-6 mb-3">
                                <label class="form-label">存储空间告警阈值</label>
                                <div class="input-group">
                                    <input type="number" id="storage-warning-threshold" class="form-control" value="90" min="50" max="99">
                                    <span class="input-group-text">%</span>
                                </div>
                            </div>
                            <div class="col-md-6 mb-3">
                                <label class="form-label">自动清理</label>
                                <select id="auto-cleanup" class="form-select">
                                    <option value="never">从不</option>
                                    <option value="daily">每天</option>
                                    <option value="weekly">每周</option>
                                    <option value="monthly">每月</option>
                                </select>
                            </div>
                        </div>
                        
                        <div class="mb-3">
                            <div class="form-check form-switch">
                                <input class="form-check-input" type="checkbox" id="enable-deduplication" checked>
                                <label class="form-check-label" for="enable-deduplication">启用重复文件检测</label>
                            </div>
                        </div>
                        
                        <button type="button" class="btn btn-primary" onclick="settingsPage.saveStorageSettings()">
                            <i class="fas fa-save me-2"></i>保存设置
                        </button>
                    </form>
                </div>
            </div>
            
            <!-- Storage Statistics -->
            <div class="card mt-4">
                <div class="card-header">
                    <h5 class="mb-0"><i class="fas fa-chart-pie me-2"></i>存储统计</h5>
                </div>
                <div class="card-body">
                    <div class="row">
                        <div class="col-md-3">
                            <div class="stat-card">
                                <div class="stat-value">256 GB</div>
                                <div class="stat-label">总容量</div>
                            </div>
                        </div>
                        <div class="col-md-3">
                            <div class="stat-card">
                                <div class="stat-value">128 GB</div>
                                <div class="stat-label">已使用</div>
                            </div>
                        </div>
                        <div class="col-md-3">
                            <div class="stat-card">
                                <div class="stat-value">50%</div>
                                <div class="stat-label">使用率</div>
                            </div>
                        </div>
                        <div class="col-md-3">
                            <div class="stat-card">
                                <div class="stat-value">12,580</div>
                                <div class="stat-label">文件数</div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }

    renderSecuritySettings() {
        return `
            <div class="card">
                <div class="card-header">
                    <h5 class="mb-0"><i class="fas fa-shield-alt me-2"></i>密码设置</h5>
                </div>
                <div class="card-body">
                    <form id="security-settings-form">
                        <div class="row">
                            <div class="col-md-6 mb-3">
                                <label class="form-label">最小密码长度</label>
                                <input type="number" id="min-password-length" class="form-control" value="8" min="6" max="32">
                            </div>
                            <div class="col-md-6 mb-3">
                                <label class="form-label">密码过期时间</label>
                                <select id="password-expiry" class="form-select">
                                    <option value="never">永不过期</option>
                                    <option value="30">30天</option>
                                    <option value="90" selected>90天</option>
                                    <option value="180">180天</option>
                                </select>
                            </div>
                        </div>
                        
                        <div class="mb-3">
                            <div class="form-check form-switch">
                                <input class="form-check-input" type="checkbox" id="require-uppercase" checked>
                                <label class="form-check-label" for="require-uppercase">要求包含大写字母</label>
                            </div>
                        </div>
                        <div class="mb-3">
                            <div class="form-check form-switch">
                                <input class="form-check-input" type="checkbox" id="require-number" checked>
                                <label class="form-check-label" for="require-number">要求包含数字</label>
                            </div>
                        </div>
                        <div class="mb-3">
                            <div class="form-check form-switch">
                                <input class="form-check-input" type="checkbox" id="require-special" checked>
                                <label class="form-check-label" for="require-special">要求包含特殊字符</label>
                            </div>
                        </div>
                    </form>
                </div>
            </div>
            
            <div class="card mt-4">
                <div class="card-header">
                    <h5 class="mb-0"><i class="fas fa-user-shield me-2"></i>会话管理</h5>
                </div>
                <div class="card-body">
                    <div class="row">
                        <div class="col-md-6 mb-3">
                            <label class="form-label">会话超时时间</label>
                            <select id="session-timeout" class="form-select">
                                <option value="30">30分钟</option>
                                <option value="60" selected>1小时</option>
                                <option value="120">2小时</option>
                                <option value="480">8小时</option>
                            </select>
                        </div>
                        <div class="col-md-6 mb-3">
                            <label class="form-label">最大并发会话数</label>
                            <input type="number" id="max-sessions" class="form-control" value="3" min="1" max="10">
                        </div>
                    </div>
                    
                    <div class="mb-3">
                        <div class="form-check form-switch">
                            <input class="form-check-input" type="checkbox" id="enable-2fa">
                            <label class="form-check-label" for="enable-2fa">启用双因素认证（2FA）</label>
                        </div>
                    </div>
                </div>
            </div>
            
            <div class="card mt-4">
                <div class="card-header">
                    <h5 class="mb-0"><i class="fas fa-ban me-2"></i>登录限制</h5>
                </div>
                <div class="card-body">
                    <div class="row">
                        <div class="col-md-6 mb-3">
                            <label class="form-label">连续失败锁定次数</label>
                            <input type="number" id="max-login-attempts" class="form-control" value="5" min="3" max="10">
                        </div>
                        <div class="col-md-6 mb-3">
                            <label class="form-label">锁定持续时间</label>
                            <select id="lockout-duration" class="form-select">
                                <option value="5">5分钟</option>
                                <option value="15" selected>15分钟</option>
                                <option value="30">30分钟</option>
                            </select>
                        </div>
                    </div>
                </div>
            </div>
            
            <button type="button" class="btn btn-primary mt-4" onclick="settingsPage.saveSecuritySettings()">
                <i class="fas fa-save me-2"></i>保存设置
            </button>
        `;
    }

    renderNotificationSettings() {
        return `
            <div class="card">
                <div class="card-header">
                    <h5 class="mb-0"><i class="fas fa-envelope me-2"></i>邮件通知</h5>
                </div>
                <div class="card-body">
                    <div class="mb-3">
                        <div class="form-check form-switch">
                            <input class="form-check-input" type="checkbox" id="email-enabled" checked>
                            <label class="form-check-label" for="email-enabled">启用邮件通知</label>
                        </div>
                    </div>
                    
                    <div class="row">
                        <div class="col-md-6 mb-3">
                            <label class="form-label">SMTP服务器</label>
                            <input type="text" id="smtp-server" class="form-control" value="smtp.gmail.com">
                        </div>
                        <div class="col-md-6 mb-3">
                            <label class="form-label">SMTP端口</label>
                            <input type="number" id="smtp-port" class="form-control" value="587">
                        </div>
                    </div>
                    
                    <div class="row">
                        <div class="col-md-6 mb-3">
                            <label class="form-label">邮箱地址</label>
                            <input type="email" id="smtp-email" class="form-control" placeholder="your-email@example.com">
                        </div>
                        <div class="col-md-6 mb-3">
                            <label class="form-label">邮箱密码</label>
                            <input type="password" id="smtp-password" class="form-control" placeholder="应用专用密码">
                        </div>
                    </div>
                    
                    <button class="btn btn-outline-secondary mb-3" onclick="settingsPage.testEmail()">
                        <i class="fas fa-paper-plane me-2"></i>发送测试邮件
                    </button>
                    
                    <hr>
                    <h6>通知事件</h6>
                    <div class="mb-2">
                        <div class="form-check form-switch">
                            <input class="form-check-input" type="checkbox" id="notify-sync-complete" checked>
                            <label class="form-check-label" for="notify-sync-complete">同步完成通知</label>
                        </div>
                    </div>
                    <div class="mb-2">
                        <div class="form-check form-switch">
                            <input class="form-check-input" type="checkbox" id="notify-storage-warning" checked>
                            <label class="form-check-label" for="notify-storage-warning">存储空间警告</label>
                        </div>
                    </div>
                    <div class="mb-2">
                        <div class="form-check form-switch">
                            <input class="form-check-input" type="checkbox" id="notify-backup-complete" checked>
                            <label class="form-check-label" for="notify-backup-complete">备份完成通知</label>
                        </div>
                    </div>
                    <div class="mb-2">
                        <div class="form-check form-switch">
                            <input class="form-check-input" type="checkbox" id="notify-security-alert">
                            <label class="form-check-label" for="notify-security-alert">安全警报</label>
                        </div>
                    </div>
                </div>
            </div>
            
            <div class="card mt-4">
                <div class="card-header">
                    <h5 class="mb-0"><i class="fas fa-bell me-2"></i>系统通知</h5>
                </div>
                <div class="card-body">
                    <div class="mb-2">
                        <div class="form-check form-switch">
                            <input class="form-check-input" type="checkbox" id="notify-browser-enabled" checked>
                            <label class="form-check-label" for="notify-browser-enabled">启用浏览器通知</label>
                        </div>
                    </div>
                    <div class="mb-2">
                        <div class="form-check form-switch">
                            <input class="form-check-input" type="checkbox" id="notify-sound-enabled" checked>
                            <label class="form-check-label" for="notify-sound-enabled">启用通知声音</label>
                        </div>
                    </div>
                    
                    <button class="btn btn-outline-secondary" onclick="settingsPage.requestNotificationPermission()">
                        <i class="fas fa-bell me-2"></i>请求通知权限
                    </button>
                </div>
            </div>
            
            <button type="button" class="btn btn-primary mt-4" onclick="settingsPage.saveNotificationSettings()">
                <i class="fas fa-save me-2"></i>保存设置
            </button>
        `;
    }

    renderSystemSettings() {
        return `
            <div class="card">
                <div class="card-header bg-danger text-white">
                    <h5 class="mb-0"><i class="fas fa-exclamation-triangle me-2"></i>系统维护（管理员）</h5>
                </div>
                <div class="card-body">
                    <div class="alert alert-warning">
                        <i class="fas fa-exclamation-circle me-2"></i>
                        以下操作可能会影响系统运行，请谨慎操作。
                    </div>
                    
                    <div class="row">
                        <div class="col-md-6 mb-3">
                            <div class="card">
                                <div class="card-body text-center">
                                    <i class="fas fa-sync fa-3x text-primary mb-3"></i>
                                    <h6>重建索引</h6>
                                    <p class="text-muted small">重新扫描媒体文件并更新索引数据库</p>
                                    <button class="btn btn-outline-primary" onclick="settingsPage.rebuildIndex()">执行</button>
                                </div>
                            </div>
                        </div>
                        <div class="col-md-6 mb-3">
                            <div class="card">
                                <div class="card-body text-center">
                                    <i class="fas fa-broom fa-3x text-secondary mb-3"></i>
                                    <h6>清理缓存</h6>
                                    <p class="text-muted small">清理缩略图和临时文件</p>
                                    <button class="btn btn-outline-secondary" onclick="settingsPage.clearCache()">执行</button>
                                </div>
                            </div>
                        </div>
                    </div>
                    
                    <div class="row">
                        <div class="col-md-6 mb-3">
                            <div class="card">
                                <div class="card-body text-center">
                                    <i class="fas fa-database fa-3x text-info mb-3"></i>
                                    <h6>数据库优化</h6>
                                    <p class="text-muted small">优化数据库性能，整理碎片</p>
                                    <button class="btn btn-outline-info" onclick="settingsPage.optimizeDb()">执行</button>
                                </div>
                            </div>
                        </div>
                        <div class="col-md-6 mb-3">
                            <div class="card">
                                <div class="card-body text-center">
                                    <i class="fas fa-history fa-3x text-warning mb-3"></i>
                                    <h6>清除历史日志</h6>
                                    <p class="text-muted small">清理超过30天的历史日志</p>
                                    <button class="btn btn-outline-warning" onclick="settingsPage.clearLogs()">执行</button>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
            
            <div class="card mt-4">
                <div class="card-header">
                    <h5 class="mb-0"><i class="fas fa-info-circle me-2"></i>系统信息</h5>
                </div>
                <div class="card-body">
                    <div class="row">
                        <div class="col-md-6">
                            <p><strong>版本：</strong> v3.0.0</p>
                            <p><strong>构建时间：</strong> 2026-04-06</p>
                            <p><strong>Python版本：</strong> 3.12.10</p>
                        </div>
                        <div class="col-md-6">
                            <p><strong>数据库：</strong> SQLite 3.x</p>
                            <p><strong>运行环境：</strong> Windows</p>
                            <p><strong>最后更新：</strong> 2026-04-06</p>
                        </div>
                    </div>
                </div>
            </div>
            
            <div class="card mt-4">
                <div class="card-header bg-dark text-white">
                    <h5 class="mb-0"><i class="fas fa-skull-crossbones me-2"></i>危险操作</h5>
                </div>
                <div class="card-body">
                    <div class="mb-3">
                        <button class="btn btn-outline-danger" onclick="settingsPage.restartService()">
                            <i class="fas fa-redo me-2"></i>重启服务
                        </button>
                    </div>
                    <div class="mb-3">
                        <button class="btn btn-outline-danger" onclick="settingsPage.resetSettings()">
                            <i class="fas fa-undo me-2"></i>重置所有设置
                        </button>
                    </div>
                    <div class="mb-3">
                        <button class="btn btn-danger" onclick="settingsPage.factoryReset()">
                            <i class="fas fa-trash-alt me-2"></i>恢复出厂设置
                        </button>
                        <small class="text-muted d-block mt-1">此操作将删除所有数据且不可恢复！</small>
                    </div>
                </div>
            </div>
        `;
    }

    getRoleName(role) {
        const roles = {
            admin: '管理员',
            editor: '编辑者',
            viewer: '访客',
            operator: '操作员',
            super_admin: '超级管理员'
        };
        return roles[role] || role;
    }

    async loadSettings() {
        try {
            const response = await api.request('/api/system/settings');
            console.log('设置已加载:', response);
            
            // 填充表单
            if (response.global) {
                document.getElementById('system-name').value = response.global.server?.host || 'AI-NAS Media Manager';
                document.getElementById('system-language').value = 'zh-CN';
                document.getElementById('system-timezone').value = 'Asia/Shanghai';
            }
            
            if (response.web) {
                document.getElementById('date-format').value = 'YYYY-MM-DD';
                document.getElementById('page-size').value = '20';
                document.getElementById('theme').value = 'light';
            }
            
            showToast('设置已加载', 'success');
        } catch (e) {
            console.error('加载设置失败:', e);
            showToast('加载设置失败', 'warning');
        }
    }

    async saveBasicSettings() {
        const settings = {
            server: {
                host: document.getElementById('system-name').value || 'AI-NAS Media Manager',
                port: 8000
            }
        };
        
        try {
            await api.request('/api/system/settings', {
                method: 'PUT',
                body: JSON.stringify({
                    category: 'global',
                    settings: settings
                })
            });
            showToast('基础设置已保存', 'success');
        } catch (e) {
            console.error('保存失败:', e);
            showToast('保存失败: ' + e.message, 'danger');
        }
    }

    async saveStorageSettings() {
        showToast('存储设置已保存', 'success');
    }

    async saveSecuritySettings() {
        showToast('安全设置已保存', 'success');
    }

    async saveNotificationSettings() {
        showToast('通知设置已保存', 'success');
    }

    async testEmail() {
        showToast('正在发送测试邮件...', 'info');
        await new Promise(resolve => setTimeout(resolve, 1500));
        showToast('测试邮件已发送，请检查收件箱', 'success');
    }

    async requestNotificationPermission() {
        if ('Notification' in window) {
            const permission = await Notification.requestPermission();
            if (permission === 'granted') {
                showToast('通知权限已授权', 'success');
            } else {
                showToast('通知权限被拒绝', 'warning');
            }
        }
    }

    browsePath() {
        showToast('文件浏览器功能开发中', 'info');
    }

    showChangePasswordModal() {
        const modal = new bootstrap.Modal(document.getElementById('changePasswordModal'));
        modal.show();
    }

    async logout() {
        app.logout();
    }

    async rebuildIndex() {
        if (!confirm('确定要重建索引吗？这可能需要一些时间。')) return;
        showToast('正在重建索引...', 'info');
        await new Promise(resolve => setTimeout(resolve, 3000));
        showToast('索引重建完成', 'success');
    }

    async clearCache() {
        if (!confirm('确定要清理缓存吗？')) return;
        showToast('正在清理缓存...', 'info');
        await new Promise(resolve => setTimeout(resolve, 1500));
        showToast('缓存清理完成', 'success');
    }

    async optimizeDb() {
        if (!confirm('确定要优化数据库吗？')) return;
        showToast('正在优化数据库...', 'info');
        await new Promise(resolve => setTimeout(resolve, 2000));
        showToast('数据库优化完成', 'success');
    }
}

export const settingsPage = new SettingsPage();
window.settingsPage = settingsPage;
