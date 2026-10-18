/**
 * AI-NAS Media Manager - Albums Module
 * 相册模块
 */

const Albums = {
    currentId: null,

    // 加载相册列表
    async load() {
        const sort = document.getElementById('album-sort')?.value || 'name_asc';

        try {
            const albums = await API.get(`/api/albums/?sort=${sort}`);
            this.render(albums);

        } catch (e) {
            console.error('加载相册失败:', e);
        }
    },

    // 渲染相册列表
    render(albums) {
        const grid = document.getElementById('albums-grid');

        if (!albums || albums.length === 0) {
            grid.innerHTML = `
                <div class="text-center text-muted py-5 w-100">
                    <i class="fas fa-folder-open fa-3x mb-3"></i>
                    <p>暂无相册</p>
                </div>
            `;
            return;
        }

        grid.innerHTML = albums.map(a => `
            <div class="col-md-3 col-sm-4 col-6 mb-3">
                <div class="album-card card" onclick="Albums.open(${a.id})">
                    <div class="album-cover bg-light d-flex align-items-center justify-content-center">
                        <i class="fas fa-folder fa-2x text-muted"></i>
                    </div>
                    <div class="p-2">
                        <div class="fw-bold text-truncate">${Utils.escapeHtml(a.album_name)}</div>
                        <small class="text-muted">${a.file_count || 0} 项</small>
                    </div>
                </div>
            </div>
        `).join('');
    },

    // 创建相册
    async create(name, type = 'custom') {
        try {
            await API.post('/api/albums/', {
                name: name,
                album_type: type
            });

            Utils.showToast('相册创建成功', 'success');
            this.load();

        } catch (e) {
            Utils.showToast('创建失败: ' + e.message, 'danger');
        }
    },

    // 打开相册
    open(id) {
        this.currentId = id;
        // TODO: 实现相册详情页面
        Utils.showToast('相册详情功能开发中', 'info');
    },

    // 加载相册选择列表（用于添加文件到相册）
    async loadForSelect() {
        const select = document.getElementById('target-album-id');

        try {
            const albums = await API.get('/api/albums/');
            select.innerHTML = '<option value="">选择相册...</option>' +
                albums.map(a => `<option value="${a.id}">${Utils.escapeHtml(a.album_name)} (${a.file_count || 0})</option>`).join('');

        } catch (e) {
            select.innerHTML = '<option value="">加载失败</option>';
        }
    },

    // 添加文件到相册
    async addFiles(albumId, fileIds) {
        try {
            await API.post('/api/actions/batch/add-to-album', {
                file_ids: fileIds,
                album_id: albumId
            });

            Utils.showToast(`已添加 ${fileIds.length} 个文件到相册`, 'success');
            return true;

        } catch (e) {
            Utils.showToast('操作失败: ' + e.message, 'danger');
            return false;
        }
    }
};

// 导出
window.Albums = Albums;
