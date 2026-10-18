// AI-NAS Media Manager - Main Application
import { api } from './api.js';
import { showToast, roleLabels } from './utils.js';

// 页面懒加载映射 - 按需加载减少首屏 JS 体积
const pageLoaders = {
    dashboard: () => import('./pages/dashboard.js'),
    media: () => import('./pages/media.js'),
    albums: () => import('./pages/albums.js'),
    devices: () => import('./pages/devices.js'),
    tasks: () => import('./pages/tasks.js'),
    users: () => import('./pages/users.js'),
    settings: () => import('./pages/settings.js'),
    audit: () => import('./pages/audit.js'),
    ai: () => import('./pages/ai.js'),
    cloud: () => import('./pages/cloud.js'),
    mobile: () => import('./pages/mobile.js'),
    plugins: () => import('./pages/plugins.js'),
    enterprise: () => import('./pages/enterprise.js')
};

class App {
    constructor() {
        this.currentUser = null;
        this.currentRole = null;
        this.pages = {};
        this.loadedPages = new Set();
    }

    async loadPageModule(pageName) {
        if (this.loadedPages.has(pageName)) {
            return this.pages[pageName];
        }
        
        try {
            const loader = pageLoaders[pageName];
            if (!loader) {
                console.warn(`No loader for page: ${pageName}`);
                return null;
            }
            
            const module = await loader();
            // 页面模块同时导出类（XxxPage）与单例（xxxPage）。
            // 优先使用单例——它与模块内 window.xxxPage 指向同一对象。
            // （历史 bug：此处曾写 new module['xxxPage']()，对单例对象执行 new
            //   必然抛 "PageClass is not a constructor"，13 个页面全部加载失败，
            //   整个前端的动态数据渲染都是死的）
            const instanceKey = `${pageName}Page`;
            let page = module[instanceKey];
            if (!page || typeof page.load !== 'function') {
                const classKey = `${pageName.charAt(0).toUpperCase()}${pageName.slice(1)}Page`;
                const PageClass = module[classKey];
                page = PageClass ? new PageClass() : null;
            }
            if (!page) {
                console.warn(`Page module has no usable export: ${pageName}`);
                return null;
            }
            this.pages[pageName] = page;
            this.loadedPages.add(pageName);
            this.bindPageMethods(pageName, page);
            return page;
        } catch (e) {
            console.error(`Failed to load page ${pageName}:`, e);
            return null;
        }
    }

    /**
     * 将页面实例的公共方法暴露到 window，供 HTML 内联 onclick 调用。
     * 不覆盖已存在的全局绑定（app.js 底部的显式委托优先）。
     */
    bindPageMethods(pageName, page) {
        let proto = page.constructor.prototype;
        while (proto && proto !== Object.prototype) {
            for (const key of Object.getOwnPropertyNames(proto)) {
                if (key === 'constructor' || key.startsWith('_')) continue;
                const fn = page[key];
                if (typeof fn === 'function' && !(key in window)) {
                    window[key] = fn.bind(page);
                }
            }
            proto = Object.getPrototypeOf(proto);
        }
    }

    async init() {
        // Listen for auth logout events
        window.addEventListener('auth:logout', () => this.logout());

        // Setup login form
        document.getElementById('login-form').addEventListener('submit', (e) => this.handleLogin(e));

        // Setup tag input
        const tagInput = document.getElementById('new-tag-input');
        if (tagInput) {
            tagInput.addEventListener('keypress', (e) => {
                if (e.key === 'Enter') {
                    e.preventDefault();
                    if (this.pages.media && this.pages.media.addTag) {
                        this.pages.media.addTag(e.target.value.trim());
                    }
                }
            });
        }

        // Setup confidence slider
        const confidenceSlider = document.getElementById('confidence-threshold');
        if (confidenceSlider) {
            confidenceSlider.addEventListener('input', (e) => {
                const valueEl = document.getElementById('confidence-value');
                if (valueEl) valueEl.textContent = e.target.value;
            });
        }

        // Setup new album checkbox
        const newAlbumCheck = document.getElementById('create-new-album-check');
        if (newAlbumCheck) {
            newAlbumCheck.addEventListener('change', function() {
                const newAlbumInput = document.getElementById('new-album-input');
                if (newAlbumInput) {
                    newAlbumInput.style.display = this.checked ? 'block' : 'none';
                }
            });
        }

        // Check auth and init
        const savedToken = localStorage.getItem('token');
        if (savedToken) {
            try {
                await this.checkAuth();
                this.hideLogin();
                this.showPage('dashboard');
            } catch (e) {
                this.showLogin();
            }
        } else {
            this.showLogin();
        }
    }

    async handleLogin(e) {
        e.preventDefault();
        const username = document.getElementById('login-username').value;
        const password = document.getElementById('login-password').value;
        const errorDiv = document.getElementById('login-error');
        const loginBtn = document.getElementById('login-btn');
        const loginText = document.getElementById('login-text');
        const loginSpinner = document.getElementById('login-spinner');

        loginBtn.disabled = true;
        loginText.textContent = '登录中...';
        loginSpinner.style.display = 'inline-block';
        errorDiv.style.display = 'none';

        try {
            const data = await api.login(username, password);
            this.currentUser = data.username;
            this.currentRole = data.role;
            this.applyRolePermissions();
            this.hideLogin();
            
            // 登录后加载设置和用户页面
            const settingsPage = await this.loadPageModule('settings');
            if (settingsPage && settingsPage.setCurrentUser) {
                settingsPage.setCurrentUser(this.currentUser, this.currentRole);
            }
            
            this.showPage('dashboard');
            showToast('登录成功', 'success');
        } catch (err) {
            errorDiv.textContent = err.message;
            errorDiv.style.display = 'block';
        } finally {
            loginBtn.disabled = false;
            loginText.textContent = '登录';
            loginSpinner.style.display = 'none';
        }
    }

    async checkAuth() {
        try {
            const user = await api.getCurrentUser();
            this.currentUser = user.username;
            this.currentRole = user.role;
            this.applyRolePermissions();
            
            // 懒加载设置和用户页面
            const usersPage = await this.loadPageModule('users');
            if (usersPage && usersPage.setCurrentUser) {
                usersPage.setCurrentUser(this.currentUser, this.currentRole);
            }
            const settingsPage = await this.loadPageModule('settings');
            if (settingsPage && settingsPage.setCurrentUser) {
                settingsPage.setCurrentUser(this.currentUser, this.currentRole);
            }
            return true;
        } catch (e) {
            this.showLogin();
            return false;
        }
    }

    logout() {
        api.clearToken();
        this.currentUser = null;
        this.currentRole = null;
        this.showLogin();
    }

    showLogin() {
        document.getElementById('login-overlay').style.display = 'flex';
        document.getElementById('login-error').style.display = 'none';
    }

    hideLogin() {
        document.getElementById('login-overlay').style.display = 'none';
    }

    applyRolePermissions() {
        if (this.currentRole === 'viewer') {
            document.getElementById('nav-devices').style.display = 'none';
            document.getElementById('nav-tasks').style.display = 'none';
            document.getElementById('nav-settings').style.display = 'none';
        } else {
            document.getElementById('nav-devices').style.display = 'block';
            document.getElementById('nav-tasks').style.display = 'block';
            document.getElementById('nav-settings').style.display = 'block';
        }

        if (this.currentRole === 'admin') {
            document.getElementById('nav-users').style.display = 'block';
            document.getElementById('nav-audit').style.display = 'block';  // 审计日志
        } else {
            document.getElementById('nav-users').style.display = 'none';
            document.getElementById('nav-audit').style.display = 'none';  // 审计日志
        }
    }

    showPage(pageName) {
        // Hide all pages
        document.querySelectorAll('.page').forEach(p => p.style.display = 'none');

        // Show selected page
        const pageEl = document.getElementById('page-' + pageName);
        if (pageEl) pageEl.style.display = 'block';

        // Update sidebar active state
        document.querySelectorAll('.sidebar-nav-item').forEach(item => {
            item.classList.remove('active');
            if (item.dataset.page === pageName) item.classList.add('active');
        });

        // Lazy load page and call load()
        this.loadPageModule(pageName).then(page => {
            if (page && page.load) {
                page.load();
            }
        });

        // 离开仪表盘时停止其自动刷新，避免定时器叠加
        if (pageName !== 'dashboard' && window.dashboardPage) {
            window.dashboardPage.stopAutoRefresh();
        }

        // Close mobile sidebar
        if (window.innerWidth <= 767) {
            this.closeSidebar();
        }
    }

    // Mobile sidebar
    toggleSidebar() {
        document.getElementById('sidebar').classList.toggle('open');
        document.getElementById('sidebar-overlay').classList.toggle('show');
    }

    closeSidebar() {
        document.getElementById('sidebar').classList.remove('open');
        document.getElementById('sidebar-overlay').classList.remove('show');
    }
}

// Global functions for HTML onclick handlers
window.showPage = (page) => app.showPage(page);
window.logout = () => app.logout();
window.toggleSidebar = () => app.toggleSidebar();
window.closeSidebar = () => app.closeSidebar();

/**
 * 页面方法委托工厂：按需加载页面模块后调用其方法。
 * 历史上这些处理器直接引用 mediaPage/albumsPage 等单例，但 app.js
 * 从未 import 它们——每次点击都是 ReferenceError。统一走
 * loadPageModule 懒加载，模块未加载过时会自动加载。
 */
function onPage(page, method) {
    return (...args) => app.loadPageModule(page).then(p => p && p[method](...args));
}

// Filter media type from dashboard
window.filterMediaType = (type) => {
    app.showPage('media');
    app.loadPageModule('media').then(p => p && p.filterByType(type));
};

// Media page functions
window.toggleBatchMode = onPage('media', 'toggleBatchMode');
window.exitBatchMode = onPage('media', 'exitBatchMode');
window.selectAllVisible = onPage('media', 'selectAll');
window.loadMoreMedia = onPage('media', 'loadMore');
window.toggleAdvancedSearch = onPage('media', 'toggleAdvancedSearch');
window.toggleScanPanel = onPage('media', 'toggleScanPanel');
window.performAdvancedSearch = onPage('media', 'performAdvancedSearch');
window.showBatchTagModal = onPage('media', 'showBatchTagModal');
window.batchAddTags = onPage('media', 'batchAddTags');
window.batchDelete = onPage('media', 'batchDelete');
window.deleteCurrentMedia = onPage('media', 'deleteCurrent');
window.downloadMedia = onPage('media', 'downloadCurrent');
window.runAIClassify = onPage('media', 'runAIClassify');
window.showAddToAlbumModal = async () => {
    const media = await app.loadPageModule('media');
    const albums = await app.loadPageModule('albums');
    albums.showAddToAlbumModal(media.selectedFiles);
};

// Album page functions
window.loadAlbums = onPage('albums', 'load');
window.showCreateAlbumModal = onPage('albums', 'showCreateModal');
window.createAlbum = onPage('albums', 'create');
window.addToAlbum = async () => {
    const media = await app.loadPageModule('media');
    const albums = await app.loadPageModule('albums');
    const success = await albums.addToAlbum(media.selectedFiles);
    if (success) {
        media.exitBatchMode();
    }
};

// Device page functions
window.loadDevices = onPage('devices', 'load');
window.showAddDeviceModal = onPage('devices', 'showAddModal');
window.addDevice = onPage('devices', 'add');

// Task page functions
window.loadTasks = onPage('tasks', 'load');

// User page functions
window.loadUsers = onPage('users', 'load');
window.showCreateUserModal = onPage('users', 'showCreateModal');
window.createUser = onPage('users', 'create');

// Settings page functions
window.loadSettings = onPage('settings', 'load');
window.showChangePasswordModal = onPage('settings', 'showChangePasswordModal');
window.changePassword = onPage('settings', 'changePassword');

// Initialize app
const app = new App();
window.app = app;

document.addEventListener('DOMContentLoaded', () => app.init());
