// AI-NAS Media Manager - Utilities

export const roleLabels = {
    admin: '管理员',
    editor: '编辑者',
    viewer: '访客'
};

export function formatFileSize(bytes) {
    if (!bytes) return '-';
    const units = ['B', 'KB', 'MB', 'GB'];
    let i = 0;
    while (bytes >= 1024 && i < units.length - 1) {
        bytes /= 1024;
        i++;
    }
    return bytes.toFixed(1) + ' ' + units[i];
}

export function getTaskBadgeColor(status) {
    const colors = {
        pending: 'secondary',
        running: 'primary',
        success: 'success',
        failed: 'danger'
    };
    return colors[status] || 'secondary';
}

export function getRoleBadgeColor(role) {
    const colors = {
        admin: 'danger',
        editor: 'primary',
        viewer: 'secondary'
    };
    return colors[role] || 'secondary';
}

export function showToast(message, type = 'info') {
    const container = document.getElementById('toast-container');
    if (!container) return;
    
    const id = 'toast-' + Date.now();
    const bgClass = {
        success: 'bg-success',
        danger: 'bg-danger',
        warning: 'bg-warning',
        info: 'bg-info'
    }[type] || 'bg-info';
    
    const toast = document.createElement('div');
    toast.id = id;
    toast.className = 'toast align-items-center text-white ' + bgClass + ' border-0';
    toast.setAttribute('role', 'alert');
    toast.innerHTML = `<div class="d-flex"><div class="toast-body">${message}</div><button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button></div>`;
    
    container.appendChild(toast);
    const bsToast = new bootstrap.Toast(toast, { delay: 3000 });
    bsToast.show();
    toast.addEventListener('hidden.bs.toast', () => toast.remove());
}

export function formatDate(dateStr) {
    if (!dateStr) return '-';
    const date = new Date(dateStr);
    return date.toLocaleString('zh-CN');
}

// 防抖 - 多次触发只执行最后一次
export function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// 节流 - 限制执行频率
export function throttle(func, limit) {
    let inThrottle;
    return function(...args) {
        if (!inThrottle) {
            func.apply(this, args);
            inThrottle = true;
            setTimeout(() => inThrottle = false, limit);
        }
    };
}

// 请求重试 - 网络不稳定时自动重试
export async function fetchWithRetry(url, options = {}, maxRetries = 3, baseDelay = 1000) {
    let lastError;
    
    for (let attempt = 0; attempt < maxRetries; attempt++) {
        try {
            const response = await fetch(url, options);
            if (!response.ok) {
                // 4xx 错误不重试
                if (response.status < 500) {
                    const err = await response.json().catch(() => ({}));
                    throw new Error(err.detail || `HTTP ${response.status}`);
                }
                // 5xx 可以重试
                lastError = new Error(`Server error: ${response.status}`);
            } else {
                return response;
            }
        } catch (e) {
            lastError = e;
            // 网络错误可以重试
            if (!e.message.includes('Server error')) {
                console.warn(`Network error, retrying (${attempt + 1}/${maxRetries})...`);
            }
        }
        
        // 等待后重试，指数退避
        if (attempt < maxRetries - 1) {
            const delay = baseDelay * Math.pow(2, attempt);
            await new Promise(resolve => setTimeout(resolve, delay));
        }
    }
    
    throw lastError;
}

// 审计日志相关工具函数
export function getLogLevelBadge(level) {
    const badges = {
        DEBUG: '<span class="badge bg-secondary">DEBUG</span>',
        INFO: '<span class="badge bg-info">INFO</span>',
        WARNING: '<span class="badge bg-warning text-dark">WARNING</span>',
        ERROR: '<span class="badge bg-danger">ERROR</span>',
        CRITICAL: '<span class="badge bg-dark">CRITICAL</span>'
    };
    return badges[level] || '<span class="badge bg-secondary">UNKNOWN</span>';
}

export function getCategoryLabel(category) {
    const labels = {
        AUTH: '认证',
        USER: '用户',
        MEDIA: '媒体',
        ALBUM: '相册',
        DEVICE: '设备',
        SYSTEM: '系统',
        CONFIG: '配置',
        SECURITY: '安全',
        ADMIN: '管理'
    };
    return labels[category] || category;
}

// 权限检查工具函数
export function hasPermission(userRole, permission) {
    const permissions = {
        admin: ['*'],
        editor: ['media:read', 'media:write', 'album:read', 'album:write', 'device:read'],
        viewer: ['media:read', 'album:read']
    };
    const userPerms = permissions[userRole] || [];
    return userPerms.includes('*') || userPerms.includes(permission);
}

// ============================================
// 虚拟列表 - 大数据量渲染优化
// ============================================
export class VirtualList {
    constructor(container, options = {}) {
        this.container = container;
        this.itemHeight = options.itemHeight || 200;
        this.itemWidth = options.itemWidth || 200;
        this.columns = options.columns || 4;
        this.gap = options.gap || 16;
        this.items = [];
        this.renderedItems = new Set();
        
        this.scrollTop = 0;
        this.containerHeight = 0;
        
        this._onScroll = this._onScroll.bind(this);
        this._onResize = this._onResize.bind(this);
        
        container.addEventListener('scroll', this._onScroll);
        window.addEventListener('resize', this._onResize);
        
        this.updateDimensions();
    }
    
    updateDimensions() {
        const rect = this.container.getBoundingClientRect();
        this.containerHeight = rect.height;
        this._calculateRows();
    }
    
    _calculateRows() {
        const containerWidth = this.container.getBoundingClientRect().width;
        const columns = Math.max(1, Math.floor((containerWidth + this.gap) / (this.itemWidth + this.gap)));
        this.columns = columns;
        this.rowHeight = this.itemHeight + this.gap;
        this.totalRows = Math.ceil(this.items.length / this.columns);
        this.totalHeight = this.totalRows * this.rowHeight;
        
        // 设置容器高度
        this.container.style.height = this.totalHeight + 'px';
    }
    
    setItems(items) {
        this.items = items;
        this.renderedItems.clear();
        this._calculateRows();
        this.render();
    }
    
    _onScroll() {
        this.scrollTop = this.container.scrollTop;
        this.render();
    }
    
    _onResize() {
        this.updateDimensions();
        this.render();
    }
    
    _getVisibleRange() {
        const startRow = Math.floor(this.scrollTop / this.rowHeight);
        const visibleRows = Math.ceil(this.containerHeight / this.rowHeight);
        const bufferRows = 2; // 上下各多渲染2行
        return {
            startRow: Math.max(0, startRow - bufferRows),
            endRow: Math.min(this.totalRows, startRow + visibleRows + bufferRows)
        };
    }
    
    render() {
        const { startRow, endRow } = this._getVisibleRange();
        
        // 清除不再可见的元素
        const visibleIndices = new Set();
        for (let row = startRow; row < endRow; row++) {
            for (let col = 0; col < this.columns; col++) {
                const index = row * this.columns + col;
                if (index < this.items.length) {
                    visibleIndices.add(index);
                }
            }
        }
        
        // 移除不再可见的
        this.renderedItems.forEach(idx => {
            if (!visibleIndices.has(idx)) {
                const el = document.getElementById(`virtual-item-${idx}`);
                if (el) el.remove();
                this.renderedItems.delete(idx);
            }
        });
        
        // 渲染可见项
        visibleIndices.forEach(idx => {
            if (!this.renderedItems.has(idx)) {
                const row = Math.floor(idx / this.columns);
                const col = idx % this.columns;
                const top = row * this.rowHeight;
                const left = col * (this.itemWidth + this.gap);
                
                const item = this.items[idx];
                const el = this._createItemElement(item, idx);
                el.style.position = 'absolute';
                el.style.top = top + 'px';
                el.style.left = left + 'px';
                el.style.width = this.itemWidth + 'px';
                el.id = `virtual-item-${idx}`;
                
                this.container.appendChild(el);
                this.renderedItems.add(idx);
            }
        });
    }
    
    _createItemElement(item, index) {
        // 由子类或外部提供具体实现
        throw new Error('必须实现 _createItemElement 方法');
    }
    
    destroy() {
        this.container.removeEventListener('scroll', this._onScroll);
        window.removeEventListener('resize', this._onResize);
        this.container.innerHTML = '';
    }
}

// 文件类型图标
export function getFileIcon(fileType) {
    const icons = {
        image: 'fa-image',
        video: 'fa-video',
        audio: 'fa-music',
        document: 'fa-file-alt',
        archive: 'fa-file-archive'
    };
    return icons[fileType] || 'fa-file';
}

// 存储格式化
export function formatStorage(bytes) {
    if (!bytes) return '0 B';
    const units = ['B', 'KB', 'MB', 'GB', 'TB'];
    let i = 0;
    while (bytes >= 1024 && i < units.length - 1) {
        bytes /= 1024;
        i++;
    }
    return `${bytes.toFixed(2)} ${units[i]}`;
}
