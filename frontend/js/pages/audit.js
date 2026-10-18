/**
 * AI-NAS Media Manager - 审计日志页面
 */
import { api } from '../api.js';
import { showToast, formatDate, getLogLevelBadge } from '../utils.js';

export class AuditPage {
    constructor() {
        this.container = document.getElementById('page-audit');
        this.logs = [];
        this.currentPage = 1;
        this.pageSize = 20;
        this.filters = {
            level: '',
            category: '',
            username: '',
            startDate: '',
            endDate: '',
            keyword: ''
        };
    }

    async load() {
        // 如果容器不存在，跳过
        if (!this.container) return;
        
        try {
            await this.loadLogs();
            this.renderStats();
        } catch (e) {
            console.error('加载审计日志失败:', e);
            showToast('加载审计日志失败: ' + e.message, 'danger');
        }
    }

    async loadLogs() {
        const params = new URLSearchParams();
        params.append('skip', (this.currentPage - 1) * this.pageSize);
        params.append('limit', this.pageSize);
        
        if (this.filters.level) params.append('level', this.filters.level);
        if (this.filters.category) params.append('category', this.filters.category);
        if (this.filters.username) params.append('username', this.filters.username);
        
        const response = await api.request(`/api/system/audit/logs?${params.toString()}`);
        this.logs = response.logs || [];
        this.total = response.total || 0;
        
        this.render();
        this.renderPagination();
    }

    render() {
        const tbody = document.getElementById('audit-table-body');
        if (!tbody) return;
        
        if (this.logs.length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="6" class="text-center text-muted py-4">
                        暂无审计日志
                    </td>
                </tr>
            `;
            return;
        }
        
        tbody.innerHTML = this.logs.map(log => `
            <tr class="audit-row" data-id="${log.id}">
                <td>
                    <span class="text-muted small">${formatDate(log.timestamp)}</span>
                </td>
                <td>
                    ${getLogLevelBadge(log.level)}
                </td>
                <td>
                    <span class="badge bg-secondary">${log.category}</span>
                </td>
                <td>
                    <span class="text-primary">${log.username || 'System'}</span>
                </td>
                <td>
                    <span class="text-truncate d-inline-block" style="max-width: 300px;" title="${log.action}">
                        ${log.action}
                    </span>
                </td>
                <td>
                    <button class="btn btn-sm btn-outline-info" onclick="auditPage.showDetail(${log.id})">
                        <i class="fas fa-eye"></i>
                    </button>
                </td>
            </tr>
        `).join('');
    }

    renderStats() {
        // 渲染统计数据
        const statsContainer = document.getElementById('audit-stats');
        if (!statsContainer) return;
        
        // 统计各级别日志数量
        const stats = {
            total: this.total,
            info: this.logs.filter(l => l.level === 'INFO').length,
            warning: this.logs.filter(l => l.level === 'WARNING').length,
            error: this.logs.filter(l => l.level === 'ERROR').length
        };
        
        statsContainer.innerHTML = `
            <div class="row">
                <div class="col-md-3">
                    <div class="stat-card">
                        <div class="stat-value">${stats.total}</div>
                        <div class="stat-label">总日志数</div>
                    </div>
                </div>
                <div class="col-md-3">
                    <div class="stat-card stat-info">
                        <div class="stat-value">${stats.info}</div>
                        <div class="stat-label">信息级</div>
                    </div>
                </div>
                <div class="col-md-3">
                    <div class="stat-card stat-warning">
                        <div class="stat-value">${stats.warning}</div>
                        <div class="stat-label">警告级</div>
                    </div>
                </div>
                <div class="col-md-3">
                    <div class="stat-card stat-danger">
                        <div class="stat-value">${stats.error}</div>
                        <div class="stat-label">错误级</div>
                    </div>
                </div>
            </div>
        `;
    }

    renderPagination() {
        const container = document.getElementById('audit-pagination');
        if (!container) return;
        
        const totalPages = Math.ceil(this.total / this.pageSize);
        
        if (totalPages <= 1) {
            container.innerHTML = '';
            return;
        }
        
        let html = '<ul class="pagination justify-content-center">';
        
        // 上一页
        html += `<li class="page-item ${this.currentPage === 1 ? 'disabled' : ''}">
            <a class="page-link" href="#" onclick="auditPage.goToPage(${this.currentPage - 1})">上一页</a>
        </li>`;
        
        // 页码
        for (let i = 1; i <= totalPages; i++) {
            if (i === 1 || i === totalPages || (i >= this.currentPage - 2 && i <= this.currentPage + 2)) {
                html += `<li class="page-item ${i === this.currentPage ? 'active' : ''}">
                    <a class="page-link" href="#" onclick="auditPage.goToPage(${i})">${i}</a>
                </li>`;
            } else if (i === this.currentPage - 3 || i === this.currentPage + 3) {
                html += `<li class="page-item disabled"><span class="page-link">...</span></li>`;
            }
        }
        
        // 下一页
        html += `<li class="page-item ${this.currentPage === totalPages ? 'disabled' : ''}">
            <a class="page-link" href="#" onclick="auditPage.goToPage(${this.currentPage + 1})">下一页</a>
        </li>`;
        
        html += '</ul>';
        container.innerHTML = html;
    }

    goToPage(page) {
        this.currentPage = page;
        this.loadLogs();
    }

    applyFilters() {
        this.filters.level = document.getElementById('filter-level')?.value || '';
        this.filters.category = document.getElementById('filter-category')?.value || '';
        this.filters.username = document.getElementById('filter-username')?.value || '';
        this.filters.startDate = document.getElementById('filter-start-date')?.value || '';
        this.filters.endDate = document.getElementById('filter-end-date')?.value || '';
        
        this.currentPage = 1;
        this.loadLogs();
    }

    resetFilters() {
        document.getElementById('filter-level').value = '';
        document.getElementById('filter-category').value = '';
        document.getElementById('filter-username').value = '';
        document.getElementById('filter-start-date').value = '';
        document.getElementById('filter-end-date').value = '';
        
        this.filters = {
            level: '',
            category: '',
            username: '',
            startDate: '',
            endDate: '',
            keyword: ''
        };
        
        this.currentPage = 1;
        this.loadLogs();
    }

    showDetail(logId) {
        const log = this.logs.find(l => l.id === logId);
        if (!log) return;
        
        const modal = document.getElementById('audit-detail-modal');
        if (!modal) return;
        
        document.getElementById('detail-timestamp').textContent = formatDate(log.timestamp);
        document.getElementById('detail-level').innerHTML = getLogLevelBadge(log.level);
        document.getElementById('detail-category').textContent = log.category;
        document.getElementById('detail-username').textContent = log.username || 'System';
        document.getElementById('detail-action').textContent = log.action;
        document.getElementById('detail-ip').textContent = log.ip_address || '-';
        document.getElementById('detail-user-agent').textContent = log.user_agent || '-';
        document.getElementById('detail-request').textContent = JSON.stringify(log.request_data || {}, null, 2);
        document.getElementById('detail-response').textContent = JSON.stringify(log.response_data || {}, null, 2);
        
        new bootstrap.Modal(modal).show();
    }

    async exportLogs(format = 'json') {
        try {
            showToast('正在导出日志...', 'info');
            
            const params = new URLSearchParams();
            params.append('format', format);
            if (this.filters.level) params.append('level', this.filters.level);
            if (this.filters.category) params.append('category', this.filters.category);
            
            const response = await api.request(`/api/system/audit/export?${params.toString()}`);
            
            // 下载文件
            const blob = new Blob([response.data], { type: format === 'csv' ? 'text/csv' : 'application/json' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `audit_logs_${new Date().toISOString().split('T')[0]}.${format}`;
            a.click();
            URL.revokeObjectURL(url);
            
            showToast('导出成功', 'success');
        } catch (e) {
            console.error('导出失败:', e);
            showToast('导出失败: ' + e.message, 'danger');
        }
    }
}

export const auditPage = new AuditPage();
window.auditPage = auditPage;
