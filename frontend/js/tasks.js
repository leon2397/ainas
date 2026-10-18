/**
 * AI-NAS Media Manager - Tasks Module
 * 任务管理模块
 */

const Tasks = {
    // 加载任务列表
    async load() {
        try {
            const tasks = await API.get('/api/tasks/?limit=50');
            this.render(tasks);

        } catch (e) {
            console.error('加载任务失败:', e);
        }
    },

    // 渲染任务列表
    render(tasks) {
        const tbody = document.getElementById('tasks-table-body');

        if (!tasks || tasks.length === 0) {
            tbody.innerHTML = '<tr><td colspan="7" class="text-center text-muted">暂无任务</td></tr>';
            return;
        }

        tbody.innerHTML = tasks.map(t => `
            <tr>
                <td><small>${(t.task_id || '').substring(0, 8)}...</small></td>
                <td>${Utils.escapeHtml(t.task_type)}</td>
                <td>${t.device_id || '-'}</td>
                <td>
                    <span class="badge bg-${Utils.getTaskBadgeColor(t.status)}">${t.status}</span>
                </td>
                <td>
                    <div class="progress task-progress">
                        <div class="progress-bar" style="width: ${t.progress || 0}%"></div>
                    </div>
                    <small>${t.progress || 0}%</small>
                </td>
                <td><small>${t.created_at || '-'}</small></td>
                <td>
                    ${t.status === 'pending' || t.status === 'running' ?
                        `<button class="btn btn-sm btn-outline-danger" onclick="Tasks.cancel('${t.task_id}')">取消</button>` :
                        '-'}
                </td>
            </tr>
        `).join('');
    },

    // 取消任务
    async cancel(taskId) {
        try {
            await API.delete(`/api/tasks/${taskId}`);
            Utils.showToast('任务已取消', 'success');
            this.load();

        } catch (e) {
            Utils.showToast('取消失败: ' + e.message, 'danger');
        }
    }
};

// 导出
window.Tasks = Tasks;
