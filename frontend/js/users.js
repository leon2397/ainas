/**
 * AI-NAS Media Manager - Users Module
 * 用户管理模块（仅管理员）
 */

const Users = {
    // 加载用户列表
    async load() {
        if (!Auth.isAdmin()) {
            document.getElementById('page-users').innerHTML = 
                '<div class="alert alert-warning">需要管理员权限</div>';
            return;
        }

        try {
            const users = await API.get('/api/auth/users');
            this.render(users);

        } catch (e) {
            console.error('加载用户失败:', e);
            document.getElementById('users-table-body').innerHTML = 
                '<tr><td colspan="4" class="text-center text-danger">加载失败</td></tr>';
        }
    },

    // 渲染用户列表
    render(users) {
        const tbody = document.getElementById('users-table-body');

        if (!users || users.length === 0) {
            tbody.innerHTML = '<tr><td colspan="4" class="text-center text-muted">暂无用户</td></tr>';
            return;
        }

        tbody.innerHTML = users.map(u => {
            const isCurrent = u.username === Auth.currentUser;
            const roleBadge = `<span class="badge bg-${Utils.getRoleBadgeColor(u.role)}">${Auth.roleLabels[u.role] || u.role}</span>`;
            const statusBadge = `<span class="badge bg-${u.disabled ? 'warning' : 'success'}">${u.disabled ? '已禁用' : '正常'}</span>`;

            let actions = '<span class="text-muted small">系统用户</span>';
            if (u.username !== 'admin') {
                actions = `
                    <select class="form-select form-select-sm d-inline-block" style="width:80px;" 
                            onchange="Users.changeRole('${u.username}', this.value)">
                        <option value="viewer" ${u.role === 'viewer' ? 'selected' : ''}>访客</option>
                        <option value="editor" ${u.role === 'editor' ? 'selected' : ''}>编辑者</option>
                        <option value="admin" ${u.role === 'admin' ? 'selected' : ''}>管理员</option>
                    </select>
                    <button class="btn btn-sm btn-outline-${u.disabled ? 'success' : 'warning'} ms-1" 
                            onclick="Users.toggle('${u.username}', ${!u.disabled})">
                        ${u.disabled ? '启用' : '禁用'}
                    </button>
                    <button class="btn btn-sm btn-outline-danger ms-1" 
                            onclick="Users.delete('${u.username}')">
                        <i class="fas fa-trash"></i>
                    </button>
                `;
            }

            return `
                <tr>
                    <td>
                        ${Utils.escapeHtml(u.username)}
                        ${isCurrent ? '<span class="badge bg-info ms-2">当前</span>' : ''}
                    </td>
                    <td>${roleBadge}</td>
                    <td>${statusBadge}</td>
                    <td>${actions}</td>
                </tr>
            `;
        }).join('');
    },

    // 显示创建用户弹窗
    showCreateModal() {
        document.getElementById('new-username').value = '';
        document.getElementById('new-password').value = '';
        document.getElementById('new-user-role').value = 'viewer';
        new bootstrap.Modal(document.getElementById('createUserModal')).show();
    },

    // 创建用户
    async create() {
        const username = document.getElementById('new-username').value;
        const password = document.getElementById('new-password').value;
        const role = document.getElementById('new-user-role').value;

        if (!username || !password) {
            Utils.showToast('请填写用户名和密码', 'warning');
            return;
        }

        if (password.length < 6) {
            Utils.showToast('密码至少6位', 'warning');
            return;
        }

        try {
            await API.post('/api/auth/users', { username, password, role });
            bootstrap.Modal.getInstance(document.getElementById('createUserModal')).hide();
            Utils.showToast('用户创建成功', 'success');
            this.load();

        } catch (e) {
            Utils.showToast('创建失败: ' + e.message, 'danger');
        }
    },

    // 修改用户角色
    async changeRole(username, role) {
        try {
            await API.patch(`/api/auth/users/${username}/role`, { role });
            Utils.showToast('角色已更新', 'success');
            this.load();

        } catch (e) {
            Utils.showToast('更新失败: ' + e.message, 'danger');
        }
    },

    // 启用/禁用用户
    async toggle(username, disabled) {
        try {
            await API.patch(`/api/auth/users/${username}/toggle`, { disabled });
            Utils.showToast(disabled ? '用户已禁用' : '用户已启用', 'success');
            this.load();

        } catch (e) {
            Utils.showToast('操作失败: ' + e.message, 'danger');
        }
    },

    // 删除用户
    async delete(username) {
        if (!confirm(`确定要删除用户 "${username}" 吗？`)) return;

        try {
            await API.delete(`/api/auth/users/${username}`);
            Utils.showToast('用户已删除', 'success');
            this.load();

        } catch (e) {
            Utils.showToast('删除失败: ' + e.message, 'danger');
        }
    }
};

// 导出
window.Users = Users;
