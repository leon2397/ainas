// AI-NAS Media Manager - API Module

class APIModule {
    constructor() {
        this.authToken = localStorage.getItem('token') || null;
        this.etagCache = new Map(); // ETag 缓存
    }

    setToken(token) {
        this.authToken = token;
        if (token) {
            localStorage.setItem('token', token);
        } else {
            localStorage.removeItem('token');
        }
    }

    clearToken() {
        this.authToken = null;
        localStorage.removeItem('token');
        localStorage.removeItem('username');
        localStorage.removeItem('role');
        this.etagCache.clear();
    }

    // 请求重试 - 网络不稳定时自动重试
    async requestWithRetry(endpoint, options = {}, maxRetries = 3) {
        let lastError;
        
        for (let attempt = 0; attempt < maxRetries; attempt++) {
            try {
                const headers = { 'Content-Type': 'application/json', ...options.headers };
                if (this.authToken) {
                    headers['Authorization'] = 'Bearer ' + this.authToken;
                }

                // 添加 ETag 条件请求
                const cachedEtag = this.etagCache.get(endpoint);
                if (cachedEtag && !options.method) {
                    headers['If-None-Match'] = cachedEtag;
                }

                const res = await fetch(endpoint, { ...options, headers });
                
                // 保存 ETag 用于下次请求
                const etag = res.headers.get('ETag');
                if (etag) {
                    this.etagCache.set(endpoint, etag);
                }

                // 304 Not Modified - 使用缓存
                if (res.status === 304) {
                    return { fromCache: true, data: null };
                }
                
                if (res.status === 401) {
                    this.clearToken();
                    window.dispatchEvent(new CustomEvent('auth:logout'));
                    throw new Error('未授权，请重新登录');
                }
                
                if (!res.ok) {
                    const err = await res.json().catch(() => ({}));
                    throw new Error(err.detail || '请求失败');
                }
                
                if (res.status === 204) return null;
                return res.json();
            } catch (e) {
                lastError = e;
                // 网络错误可以重试 (fetch 抛出的错误)
                if (attempt < maxRetries - 1) {
                    await new Promise(resolve => setTimeout(resolve, 1000 * (attempt + 1)));
                }
            }
        }
        
        throw lastError;
    }

    // 兼容旧 API
    async request(endpoint, options = {}) {
        return this.requestWithRetry(endpoint, options, 1); // 默认不重试
    }

    // Auth APIs
    async login(username, password) {
        const formData = new FormData();
        formData.append('username', username);
        formData.append('password', password);
        
        const res = await fetch('/api/auth/login', { method: 'POST', body: formData });
        if (!res.ok) {
            const err = await res.json().catch(() => ({}));
            throw new Error(err.detail || '登录失败');
        }
        const data = await res.json();
        this.setToken(data.access_token);
        return data;
    }

    async getCurrentUser() {
        return this.request('/api/auth/me');
    }

    async getUsers() {
        return this.request('/api/auth/users');
    }

    async createUser(userData) {
        return this.request('/api/auth/users', { method: 'POST', body: JSON.stringify(userData) });
    }

    async changeUserRole(username, role) {
        return this.request(`/api/auth/users/${username}/role`, { method: 'PATCH', body: JSON.stringify({ role }) });
    }

    async toggleUser(username, disabled) {
        return this.request(`/api/auth/users/${username}/toggle`, { method: 'PATCH', body: JSON.stringify({ disabled }) });
    }

    async deleteUser(username) {
        return this.request(`/api/auth/users/${username}`, { method: 'DELETE' });
    }

    async changePassword(oldPassword, newPassword) {
        return this.request('/api/auth/change-password', { 
            method: 'POST', 
            body: JSON.stringify({ old_password: oldPassword, new_password: newPassword }) 
        });
    }

    // Media APIs
    async getMediaFiles(params = {}) {
        const query = new URLSearchParams();
        if (params.skip !== undefined) query.append('skip', params.skip);
        if (params.limit !== undefined) query.append('limit', params.limit);
        if (params.file_type) query.append('file_type', params.file_type);
        if (params.device_id) query.append('device_id', params.device_id);
        return this.request(`/api/media/?${query.toString()}`);
    }

    async getMediaDetail(fileId) {
        return this.request(`/api/media/${fileId}`);
    }

    async searchMedia(keyword, fileType, limit = 100) {
        const query = new URLSearchParams({ keyword, limit });
        if (fileType) query.append('file_type', fileType);
        return this.request(`/api/media/search/?${query.toString()}`);
    }

    async advancedSearch(searchParams) {
        return this.request('/api/media/search/advanced', { 
            method: 'POST', 
            body: JSON.stringify(searchParams) 
        });
    }

    async addTag(fileId, tag) {
        return this.request('/api/media/add-tag', { 
            method: 'POST', 
            body: JSON.stringify({ file_id: fileId, tag }) 
        });
    }

    async removeTag(fileId, tag) {
        return this.request('/api/media/remove-tag', { 
            method: 'POST', 
            body: JSON.stringify({ file_id: fileId, tag }) 
        });
    }

    async deleteMedia(fileId) {
        return this.request(`/api/media/${fileId}`, { method: 'DELETE' });
    }

    async getMediaCounts() {
        return this.request('/api/media/count/by-type');
    }

    // Album APIs
    async getAlbums(sort = 'name_asc') {
        return this.request(`/api/albums/?sort=${sort}`);
    }

    async getAlbumDetail(albumId) {
        return this.request(`/api/albums/${albumId}`);
    }

    async getAlbumFiles(albumId) {
        return this.request(`/api/albums/${albumId}/files`);
    }

    async createAlbum(name, albumType = 'custom') {
        return this.request('/api/albums/', { 
            method: 'POST', 
            body: JSON.stringify({ name, album_type: albumType }) 
        });
    }

    async addFilesToAlbum(albumId, fileIds) {
        return this.request('/api/albums/add-files', { 
            method: 'POST', 
            body: JSON.stringify({ album_id: albumId, file_ids: fileIds }) 
        });
    }

    async deleteAlbum(albumId) {
        return this.request(`/api/albums/${albumId}`, { method: 'DELETE' });
    }

    // Device APIs
    async getDevices() {
        return this.request('/api/devices/');
    }

    async getOnlineDevices() {
        return this.request('/api/devices/online');
    }

    async getDeviceDetail(deviceId) {
        return this.request(`/api/devices/${deviceId}`);
    }

    async getDeviceInfo(deviceId) {
        return this.request(`/api/devices/${deviceId}/info`);
    }

    async addDevice(deviceData) {
        return this.request('/api/devices/add', { method: 'POST', body: JSON.stringify(deviceData) });
    }

    async testDevice(deviceId) {
        return this.request(`/api/devices/${deviceId}/test`);
    }

    async deleteDevice(deviceId) {
        return this.request(`/api/devices/${deviceId}`, { method: 'DELETE' });
    }

    // Task APIs
    async getTasks(params = {}) {
        const query = new URLSearchParams();
        if (params.status) query.append('status', params.status);
        if (params.limit) query.append('limit', params.limit);
        return this.request(`/api/tasks/?${query.toString()}`);
    }

    async getTaskDetail(taskId) {
        return this.request(`/api/tasks/${taskId}`);
    }

    // 扫描服务器媒体目录（增量索引入库）
    async scanMedia(path, recursive = true) {
        return this.request('/api/actions/scan', {
            method: 'POST',
            body: JSON.stringify({ path, recursive })
        });
    }

    async cancelTask(taskId) {
        return this.request(`/api/tasks/${taskId}`, { method: 'DELETE' });
    }

    // Batch Actions
    async batchAddTags(fileIds, tags) {
        return this.request('/api/actions/batch/add-tags', { 
            method: 'POST', 
            body: JSON.stringify({ file_ids: fileIds, tags }) 
        });
    }

    async batchDelete(fileIds) {
        return this.request('/api/actions/batch/delete', { 
            method: 'POST', 
            body: JSON.stringify({ file_ids: fileIds }) 
        });
    }

    async batchAddToAlbum(fileIds, albumId) {
        return this.request('/api/actions/batch/add-to-album', { 
            method: 'POST', 
            body: JSON.stringify({ file_ids: fileIds, album_id: albumId }) 
        });
    }

    // System
    async healthCheck() {
        return this.request('/health');
    }

    async getStatus() {
        return this.request('/status');
    }

    // Audit APIs
    async getAuditLogs(params = {}) {
        const query = new URLSearchParams();
        if (params.skip !== undefined) query.append('skip', params.skip);
        if (params.limit !== undefined) query.append('limit', params.limit);
        if (params.level) query.append('level', params.level);
        if (params.category) query.append('category', params.category);
        if (params.username) query.append('username', params.username);
        if (params.start_date) query.append('start_date', params.start_date);
        if (params.end_date) query.append('end_date', params.end_date);
        return this.request(`/api/system/audit/logs?${query.toString()}`);
    }

    async getAuditLogDetail(logId) {
        return this.request(`/api/system/audit/logs/${logId}`);
    }

    async getAuditStats() {
        return this.request('/api/system/audit/stats');
    }

    async exportAuditLogs(params = {}) {
        return this.request(`/api/system/audit/export?format=${params.format || 'json'}`);
    }

    async clearAuditLogs() {
        return this.request('/api/system/audit/clear', { method: 'DELETE' });
    }

    // ── 媒体上传（XHR 支持上传进度回调；fetch 无法监听 upload 进度）──
    async upload(file, deviceId, onProgress) {
        return new Promise((resolve, reject) => {
            const formData = new FormData();
            formData.append('file', file);
            const url = `/api/media/upload?device_id=${encodeURIComponent(deviceId || 'default')}`;
            const xhr = new XMLHttpRequest();
            xhr.open('POST', url);
            if (this.authToken) xhr.setRequestHeader('Authorization', 'Bearer ' + this.authToken);
            xhr.upload.onprogress = (e) => {
                if (e.lengthComputable && typeof onProgress === 'function') {
                    onProgress(Math.round((e.loaded / e.total) * 100));
                }
            };
            xhr.onload = () => {
                if (xhr.status >= 200 && xhr.status < 300) {
                    try { resolve(JSON.parse(xhr.responseText)); }
                    catch (e) { resolve(xhr.responseText); }
                } else {
                    let msg = '上传失败 (' + xhr.status + ')';
                    try { msg = (JSON.parse(xhr.responseText).detail) || msg; } catch (e) {}
                    reject(new Error(msg));
                }
            };
            xhr.onerror = () => reject(new Error('网络错误，上传失败'));
            xhr.send(formData);
        });
    }

    // AI APIs
    async getAIStats() {
        return this.request('/api/ai/stats');
    }

    async runFaceRecognition(mediaIds = []) {
        return this.request('/api/ai/faces/detect', {
            method: 'POST',
            body: JSON.stringify({ media_ids: mediaIds })
        });
    }

    async getFaceAlbums() {
        // 后端 GET /api/ai/faces 返回 { faces:[...], total, total_faces }
        const data = await this.request('/api/ai/faces');
        return (data && data.faces) || [];
    }

    async getSmartAlbums() {
        // 后端 GET /api/ai/smart-albums 返回 { albums:[...], total }
        const data = await this.request('/api/ai/smart-albums');
        return (data && data.albums) || [];
    }

    async getSimilarPhotos(mediaId, threshold = 0.8) {
        // 后端 GET /api/ai/similar 返回相似图组 { groups:[...], total }（mediaId 仅用于前端上下文，后端返回全部分组）
        const data = await this.request(`/api/ai/similar?threshold=${threshold}`);
        return (data && data.groups) || [];
    }

    async runAutoTagging(mediaIds = []) {
        return this.request('/api/ai/tags/generate', {
            method: 'POST',
            body: JSON.stringify({ media_ids: mediaIds })
        });
    }

    async getTags() {
        return this.request('/api/ai/tags');
    }

    // Cloud Storage APIs
    async getCloudConfig() {
        return this.request('/api/cloud/config');
    }

    async saveCloudConfig(config) {
        return this.request('/api/cloud/config', {
            method: 'POST',
            body: JSON.stringify(config)
        });
    }

    async getCloudSyncStatus() {
        // 后端对应 GET /api/cloud/status
        return this.request('/api/cloud/status');
    }

    async triggerCloudSync() {
        // 后端对应 POST /api/cloud/backup（无 file_ids 时备份全部）
        return this.request('/api/cloud/backup', { method: 'POST' });
    }
}

export const api = new APIModule();
export default api;

// 暴露到 window，便于控制台调试与未来的内联事件调用
window.api = api;
