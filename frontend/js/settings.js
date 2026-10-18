/**
 * AI-NAS Media Manager - Settings Module
 * 设置模块
 */

const Settings = {
    // 加载设置
    load() {
        document.getElementById('current-username').textContent = Auth.currentUser || '-';
        document.getElementById('current-role').textContent = 
            Auth.roleLabels[Auth.currentRole] || Auth.currentRole || '-';
    },

    // 显示修改密码弹窗
    showChangePasswordModal() {
        document.getElementById('old-password').value = '';
        document.getElementById('new-password-change').value = '';
        document.getElementById('confirm-password').value = '';
        new bootstrap.Modal(document.getElementById('changePasswordModal')).show();
    },

    // 修改密码
    async changePassword() {
        const oldPassword = document.getElementById('old-password').value;
        const newPassword = document.getElementById('new-password-change').value;
        const confirmPassword = document.getElementById('confirm-password').value;

        if (!oldPassword || !newPassword) {
            Utils.showToast('请填写密码', 'warning');
            return;
        }

        if (newPassword !== confirmPassword) {
            Utils.showToast('两次输入的密码不一致', 'warning');
            return;
        }

        if (newPassword.length < 6) {
            Utils.showToast('新密码至少6位', 'warning');
            return;
        }

        try {
            await Auth.changePassword(oldPassword, newPassword);
            bootstrap.Modal.getInstance(document.getElementById('changePasswordModal')).hide();
            Utils.showToast('密码修改成功', 'success');

        } catch (e) {
            Utils.showToast('修改失败: ' + e.message, 'danger');
        }
    }
};

// 导出
window.Settings = Settings;
