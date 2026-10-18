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
            const PageClass = module[`${pageName}Page`];
            this.pages[pageName] = new PageClass();
            this.loadedPages.add(pageName);
            return this.pages[pageName];
        } catch (e) {
            console.error(`Failed to load page ${pageName}:`, e);
            return null;
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

// Filter media type from dashboard
window.filterMediaType = (type) => {
    mediaPage.filterByType(type);
    app.showPage('media');
};

// Media page functions
window.toggleBatchMode = () => mediaPage.toggleBatchMode();
window.exitBatchMode = () => mediaPage.exitBatchMode();
window.selectAllVisible = () => mediaPage.selectAll();
window.loadMoreMedia = () => mediaPage.loadMore();
window.toggleAdvancedSearch = () => mediaPage.toggleAdvancedSearch();
window.toggleScanPanel = () => mediaPage.toggleScanPanel();
window.performAdvancedSearch = () => mediaPage.performAdvancedSearch();
window.showBatchTagModal = () => mediaPage.showBatchTagModal();
window.batchAddTags = () => mediaPage.batchAddTags();
window.batchDelete = () => mediaPage.batchDelete();
window.deleteCurrentMedia = () => mediaPage.deleteCurrent();
window.downloadMedia = () => mediaPage.downloadCurrent();
window.runAIClassify = () => mediaPage.runAIClassify();
window.showAddToAlbumModal = () => albumsPage.showAddToAlbumModal(mediaPage.selectedFiles);

// Album page functions
window.loadAlbums = () => albumsPage.load();
window.showCreateAlbumModal = () => albumsPage.showCreateModal();
window.createAlbum = () => albumsPage.create();
window.addToAlbum = async () => {
    const success = await albumsPage.addToAlbum(mediaPage.selectedFiles);
    if (success) {
        mediaPage.exitBatchMode();
    }
};

// Device page functions
window.loadDevices = () => devicesPage.load();
window.showAddDeviceModal = () => devicesPage.showAddModal();
window.addDevice = () => devicesPage.add();

// Task page functions
window.loadTasks = () => tasksPage.load();

// User page functions
window.loadUsers = () => usersPage.load();
window.showCreateUserModal = () => usersPage.showCreateModal();
window.createUser = () => usersPage.create();

// Settings page functions
window.loadSettings = () => settingsPage.load();
window.showChangePasswordModal = () => settingsPage.showChangePasswordModal();
window.changePassword = () => settingsPage.changePassword();

// Initialize app
const app = new App();
window.app = app;

document.addEventListener('DOMContentLoaded', () => app.init());
