// AI-NAS Media Manager - Users Page
import { api } from '../api.js';
import { showToast, getRoleBadgeColor, roleLabels } from '../utils.js';

export class UsersPage {
    constructor() {
        this.container = document.getElementById('page-users');
        this.currentUser = null;
        this.currentRole = null;
    }

    setCurrentUser(user, role) {
        this.currentUser = user;
        this.currentRole = role;
    }

    async load() {
        if (this.currentRole !== 'admin') {
            this.container.innerHTML = '<div class="alert alert-warning">需要管理员权限</div>';
            return;
        }
        try {
            const users = await api.getUsers();
            this.render(users);
        } catch (e) {
            console.error('加载用户失败:', e);
            document.getElementById('users-table-body').innerHTML =
                '<tr><td colspan="4" class="text-center text-danger">加载失败</td></tr>';
        }
    }

    render(users) {
        const tbody = document.getElementById('users-table-body');
        if (!users || users.length === 0) {
            tbody.innerHTML = '<tr><td colspan="4" class="text-center text-muted">暂无用户</td></tr>';
            return;
        }

        tbody.innerHTML = users.map(u => {
            const isCurrent = u.username === this.currentUser ? '<span class="badge bg-info ms-2">当前</span>' : '';
            const roleBadge = `<span class="badge bg-${getRoleBadgeColor(u.role)}">${roleLabels[u.role] || u.role}</span>`;
            const statusBadge = `<span class="badge bg-${u.disabled ? 'warning' : 'success'}">${u.disabled ? '已禁用' : '正常'}</span>`;

            let actions = '<span class="text-muted small">系统用户</span>';
            if (u.username !== 'admin') {
                actions = `
                    <select class="form-select form-select-sm d-inline-block" style="width:80px;" onchange="usersPage.changeRole('${u.username}', this.value)">
                        <option value="viewer" ${u.role === 'viewer' ? 'selected' : ''}>访客</option>
                        <option value="editor" ${u.role === 'editor' ? 'selected' : ''}>编辑者</option>
                        <option value="admin" ${u.role === 'admin' ? 'selected' : ''}>管理员</option>
                    </select>
                    <button class="btn btn-sm btn-outline-${u.disabled ? 'success' : 'warning'} ms-1" onclick="usersPage.toggleUser('${u.username}', ${!u.disabled})">
                        ${u.disabled ? '启用' : '禁用'}
                    </button>
                    <button class="btn btn-sm btn-outline-danger ms-1" onclick="usersPage.deleteUser('${u.username}')">
                        <i class="fas fa-trash"></i>
                    </button>
                `;
            }

            return `
                <tr>
                    <td>${u.username}${isCurrent}</td>
                    <td>${roleBadge}</td>
                    <td>${statusBadge}</td>
                    <td>${actions}</td>
                </tr>
            `;
        }).join('');
    }

    showCreateModal() {
        document.getElementById('new-username').value = '';
        document.getElementById('new-password').value = '';
        document.getElementById('new-user-role').value = 'viewer';
        new bootstrap.Modal(document.getElementById('createUserModal')).show();
    }

    async create() {
        const username = document.getElementById('new-username').value;
        const password = document.getElementById('new-password').value;
        const role = document.getElementById('new-user-role').value;

        if (!username || !password) {
            showToast('请填写用户名和密码', 'warning');
            return;
        }
        if (password.length < 6) {
            showToast('密码至少6位', 'warning');
            return;
        }

        try {
            await api.createUser({ username, password, role });
            bootstrap.Modal.getInstance(document.getElementById('createUserModal')).hide();
            showToast('用户创建成功', 'success');
            this.load();
        } catch (e) {
            showToast('创建失败: ' + e.message, 'danger');
        }
    }

    async changeRole(username, role) {
        try {
            await api.changeUserRole(username, role);
            showToast('角色已更新', 'success');
            this.load();
        } catch (e) {
            showToast('更新失败: ' + e.message, 'danger');
        }
    }

    async toggleUser(username, disabled) {
        try {
            await api.toggleUser(username, disabled);
            showToast(disabled ? '用户已禁用' : '用户已启用', 'success');
            this.load();
        } catch (e) {
            showToast('操作失败: ' + e.message, 'danger');
        }
    }

    async deleteUser(username) {
        if (!confirm(`确定要删除用户 "${username}" 吗？`)) return;
        try {
            await api.deleteUser(username);
            showToast('用户已删除', 'success');
            this.load();
        } catch (e) {
            showToast('删除失败: ' + e.message, 'danger');
        }
    }
}

export const usersPage = new UsersPage();
window.usersPage = usersPage;
