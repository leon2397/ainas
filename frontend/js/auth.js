/**
 * AI-NAS Media Manager - Authentication Module
 * 认证模块：登录、登出、权限检查
 */

const Auth = {
    // 当前用户信息
    currentUser: null,
    currentRole: null,
    token: null,

    // 角色标签
    roleLabels: {
        admin: '管理员',
        editor: '编辑者',
        viewer: '访客'
    },

    // 初始化
    init() {
        this.token = localStorage.getItem('token');
        this.currentUser = localStorage.getItem('username');
        this.currentRole = localStorage.getItem('role');
    },

    // 检查是否已登录
    isLoggedIn() {
        return !!this.token;
    },

    // 检查是否是管理员
    isAdmin() {
        return this.currentRole === 'admin';
    },

    // 检查是否是编辑者或以上
    canEdit() {
        return this.currentRole === 'admin' || this.currentRole === 'editor';
    },

    // 登录
    async login(username, password) {
        const formData = new FormData();
        formData.append('username', username);
        formData.append('password', password);

        const res = await fetch('/api/auth/login', {
            method: 'POST',
            body: formData
        });

        if (!res.ok) {
            const err = await res.json().catch(() => ({}));
            throw new Error(err.detail || '登录失败');
        }

        const data = await res.json();
        
        // 保存认证信息
        this.token = data.access_token;
        this.currentUser = data.username;
        this.currentRole = data.role;

        localStorage.setItem('token', this.token);
        localStorage.setItem('username', this.currentUser);
        localStorage.setItem('role', this.currentRole);

        return data;
    },

    // 登出
    logout() {
        this.token = null;
        this.currentUser = null;
        this.currentRole = null;

        localStorage.removeItem('token');
        localStorage.removeItem('username');
        localStorage.removeItem('role');

        // 显示登录页面
        App.showLogin();
    },

    // 检查认证状态
    async checkAuth() {
        if (!this.token) {
            return false;
        }

        try {
            const user = await API.get('/api/auth/me');
            this.currentUser = user.username;
            this.currentRole = user.role;
            this.applyPermissions();
            return true;
        } catch (e) {
            return false;
        }
    },

    // 应用权限控制
    applyPermissions() {
        const navDevices = document.getElementById('nav-devices');
        const navTasks = document.getElementById('nav-tasks');
        const navUsers = document.getElementById('nav-users');
        const navSettings = document.getElementById('nav-settings');

        // viewer 权限：隐藏设备/任务/设置
        if (this.currentRole === 'viewer') {
            if (navDevices) navDevices.style.display = 'none';
            if (navTasks) navTasks.style.display = 'none';
            if (navSettings) navSettings.style.display = 'none';
        } else {
            if (navDevices) navDevices.style.display = 'block';
            if (navTasks) navTasks.style.display = 'block';
            if (navSettings) navSettings.style.display = 'block';
        }

        // 用户管理仅 admin 可见
        if (navUsers) {
            navUsers.style.display = this.isAdmin() ? 'block' : 'none';
        }
    },

    // 修改密码
    async changePassword(oldPassword, newPassword) {
        return API.post('/api/auth/change-password', {
            old_password: oldPassword,
            new_password: newPassword
        });
    }
};

// 初始化
Auth.init();

// 导出
window.Auth = Auth;
