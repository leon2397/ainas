// AI-NAS Media Manager - Tasks Page
import { api } from '../api.js';
import { showToast, getTaskBadgeColor } from '../utils.js';

export class TasksPage {
    constructor() {
        this.container = document.getElementById('page-tasks');
    }

    async load() {
        try {
            const tasks = await api.getTasks({ limit: 50 });
            this.render(tasks);
        } catch (e) {
            console.error('加载任务失败:', e);
            showToast('加载任务失败: ' + e.message, 'danger');
        }
    }

    render(tasks) {
        const tbody = document.getElementById('tasks-table-body');
        if (!tasks || tasks.length === 0) {
            tbody.innerHTML = '<tr><td colspan="7" class="text-center text-muted">暂无任务</td></tr>';
            return;
        }

        tbody.innerHTML = tasks.map(t => `
            <tr>
                <td><small>${t.task_id ? t.task_id.substring(0, 8) : ''}...</small></td>
                <td>${t.task_type}</td>
                <td>${t.device_id || '-'}</td>
                <td><span class="badge bg-${getTaskBadgeColor(t.status)}">${t.status}</span></td>
                <td>
                    <div class="progress task-progress">
                        <div class="progress-bar" style="width: ${t.progress || 0}%"></div>
                    </div>
                    <small>${t.progress || 0}%</small>
                </td>
                <td><small>${t.created_at || '-'}</small></td>
                <td>
                    ${t.status === 'pending' || t.status === 'running'
                        ? `<button class="btn btn-sm btn-outline-danger" onclick="tasksPage.cancelTask('${t.task_id}')">取消</button>`
                        : '-'
                    }
                </td>
            </tr>
        `).join('');
    }

    async cancelTask(taskId) {
        try {
            await api.cancelTask(taskId);
            showToast('任务已取消', 'success');
            this.load();
        } catch (e) {
            showToast('取消失败: ' + e.message, 'danger');
        }
    }
}

export const tasksPage = new TasksPage();
window.tasksPage = tasksPage;
