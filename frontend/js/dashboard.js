/**
 * AI-NAS Media Manager - Dashboard Module
 * 仪表盘模块
 */

const Dashboard = {
    // 加载仪表盘数据
    async load() {
        try {
            // 并行加载统计数据
            const [counts, albums, devices, tasks] = await Promise.all([
                API.get('/api/media/count/by-type').catch(() => ({ images: 0, videos: 0 })),
                API.get('/api/albums/').catch(() => []),
                API.get('/api/devices/online').catch(() => []),
                API.get('/api/tasks/?limit=5').catch(() => [])
            ]);

            // 更新统计卡片
            document.getElementById('stat-images').textContent = counts.images || 0;
            document.getElementById('stat-videos').textContent = counts.videos || 0;
            document.getElementById('stat-albums').textContent = albums.length || 0;
            document.getElementById('stat-devices').textContent = devices.length || 0;

            // 渲染最近任务
            this.renderRecentTasks(tasks);

            // 渲染设备状态
            this.renderDeviceStatus(devices);

        } catch (e) {
            console.error('加载仪表盘失败:', e);
            Utils.showToast('加载仪表盘数据失败', 'danger');
        }
    },

    // 渲染最近任务
    renderRecentTasks(tasks) {
        const container = document.getElementById('recent-tasks');
        
        if (!tasks || tasks.length === 0) {
            container.innerHTML = '<div class="text-muted text-center py-3">暂无任务</div>';
            return;
        }

        container.innerHTML = tasks.map(t => `
            <div class="d-flex justify-content-between align-items-center py-2 border-bottom">
                <div>
                    <span class="badge bg-${Utils.getTaskBadgeColor(t.status)} me-2">${t.status}</span>
                    <small>${Utils.escapeHtml(t.task_type)}</small>
                </div>
                <small class="text-muted">${t.created_at || '-'}</small>
            </div>
        `).join('');
    },

    // 渲染设备状态
    renderDeviceStatus(devices) {
        const container = document.getElementById('device-status-list');
        
        if (!devices || devices.length === 0) {
            container.innerHTML = '<div class="text-muted text-center py-3">暂无在线设备</div>';
            return;
        }

        container.innerHTML = devices.map(d => `
            <div class="d-flex justify-content-between align-items-center py-2">
                <div>
                    <span class="device-status online me-2"></span>
                    ${Utils.escapeHtml(d.device_name || d.device_id)}
                </div>
                <small class="text-muted">CPU: ${d.cpu_usage || 0}%</small>
            </div>
        `).join('');
    }
};

// 导出
window.Dashboard = Dashboard;
