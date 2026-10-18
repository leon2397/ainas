// AI-NAS Media Manager - Dashboard Page
import { api } from '../api.js';
import { showToast, getTaskBadgeColor } from '../utils.js';

export class DashboardPage {
    constructor() {
        this.container = document.getElementById('page-dashboard');
    }

    async load() {
        try {
            const counts = await api.getMediaCounts();
            document.getElementById('stat-images').textContent = counts.images || 0;
            document.getElementById('stat-videos').textContent = counts.videos || 0;

            const albums = await api.getAlbums();
            document.getElementById('stat-albums').textContent = albums.length || 0;

            const devices = await api.getOnlineDevices();
            document.getElementById('stat-devices').textContent = devices.length || 0;

            // 加载最近任务
            const tasks = await api.getTasks({ limit: 5 });
            this.renderRecentTasks(tasks);

            // 加载设备状态
            this.renderDeviceStatus(devices);

        } catch (e) {
            console.error('加载仪表盘数据失败:', e);
        } finally {
            this.startAutoRefresh();
        }
    }

    /**
     * 启动自动刷新（30 秒轮询 + 切回标签页立即刷新）。
     * 修复“页面长时间开着，扫描/上传完成后数据不更新”的问题。
     */
    startAutoRefresh() {
        this.stopAutoRefresh();
        this._refreshTimer = setInterval(() => this.load(), 30000);
        this._visibilityHandler = () => {
            if (!document.hidden) this.load();
        };
        document.addEventListener('visibilitychange', this._visibilityHandler);
    }

    /** 离开仪表盘时停止刷新，避免定时器叠加 */
    stopAutoRefresh() {
        if (this._refreshTimer) {
            clearInterval(this._refreshTimer);
            this._refreshTimer = null;
        }
        if (this._visibilityHandler) {
            document.removeEventListener('visibilitychange', this._visibilityHandler);
            this._visibilityHandler = null;
        }
    }

    renderRecentTasks(tasks) {
        const container = document.getElementById('recent-tasks');
        if (!container) return;
        if (!tasks || tasks.length === 0) {
            container.innerHTML = '<div class="text-muted text-center py-3">暂无最近任务</div>';
            return;
        }
        container.innerHTML = tasks.map(t => `
            <div class="d-flex justify-content-between align-items-center py-2 border-bottom">
                <div>
                    <span class="badge bg-${getTaskBadgeColor(t.status)} me-2">${t.status}</span>
                    <small>${t.task_type}</small>
                </div>
                <small class="text-muted">${t.created_at || '-'}</small>
            </div>
        `).join('');
    }

    renderDeviceStatus(devices) {
        const container = document.getElementById('device-status-list');
        if (!container) return;
        if (!devices || devices.length === 0) {
            container.innerHTML = '<div class="text-muted text-center py-3">暂无在线设备</div>';
            return;
        }
        container.innerHTML = devices.map(d => `
            <div class="d-flex justify-content-between align-items-center py-2">
                <div>
                    <span class="device-status online me-2"></span>
                    ${d.device_name || d.device_id}
                </div>
                <small class="text-muted">CPU: ${d.cpu_usage || 0}%</small>
            </div>
        `).join('');
    }

    async showUploadModal() {
        // 加载设备列表
        try {
            const devices = await api.getOnlineDevices();
            const select = document.getElementById('upload-device-id');
            select.innerHTML = '<option value="default">默认设备</option>' +
                devices.map(d => `<option value="${d.device_id}">${d.device_name || d.device_id}</option>`).join('');
        } catch (e) {
            console.error('加载设备列表失败:', e);
        }

        const modal = new bootstrap.Modal(document.getElementById('uploadModal'));
        modal.show();
    }

    async uploadFiles() {
        const fileInput = document.getElementById('upload-file-input');
        const deviceId = document.getElementById('upload-device-id').value;
        const files = fileInput.files;

        if (!files || files.length === 0) {
            showToast('请选择要上传的文件', 'warning');
            return;
        }

        const progressBar = document.getElementById('upload-progress');
        const statusText = document.getElementById('upload-status');

        progressBar.style.width = '0%';
        statusText.textContent = '准备上传...';

        for (let i = 0; i < files.length; i++) {
            const file = files[i];
            const percent = Math.round((i / files.length) * 100);
            progressBar.style.width = percent + '%';
            statusText.textContent = `正在上传: ${file.name}`;

            try {
                await api.upload(file, deviceId, (progress) => {
                    progressBar.style.width = (percent + progress / files.length) + '%';
                    progressBar.textContent = percent + '%';
                });
                showToast(`${file.name} 上传成功`, 'success');
            } catch (e) {
                showToast(`${file.name} 上传失败: ${e.message}`, 'danger');
            }
        }

        statusText.textContent = '上传完成';
        progressBar.style.width = '100%';

        // 刷新统计
        setTimeout(() => {
            bootstrap.Modal.getInstance(document.getElementById('uploadModal')).hide();
            this.load();
        }, 1000);
    }
}

export const dashboardPage = new DashboardPage();
window.dashboardPage = dashboardPage;