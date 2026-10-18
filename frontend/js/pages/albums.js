// AI-NAS Media Manager - Albums Page
import { api } from '../api.js';
import { showToast, VirtualList } from '../utils.js';

export class AlbumsPage {
    constructor() {
        this.container = document.getElementById('page-albums');
        this.currentAlbumId = null;
        this.albums = [];
        this.virtualList = null;
    }

    async load() {
        const sort = document.getElementById('album-sort').value;
        try {
            const albums = await api.getAlbums(sort);
            this.render(albums);
        } catch (e) {
            console.error('加载相册失败:', e);
            showToast('加载相册失败: ' + e.message, 'danger');
        }
    }

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

        this.albums = albums;
        
        // 大数据量时启用虚拟滚动 (>100项)
        if (albums.length > 100) {
            this.initVirtualScroll(grid);
            return;
        }

        grid.innerHTML = albums.map(a => `
            <div class="col-md-3 col-sm-4 col-6 mb-3">
                <div class="album-card card" onclick="albumsPage.openAlbum(${a.id})">
                    <div class="album-cover bg-light d-flex align-items-center justify-content-center">
                        <i class="fas fa-folder fa-2x text-muted"></i>
                    </div>
                    <div class="p-2">
                        <div class="fw-bold text-truncate">${a.album_name}</div>
                        <small class="text-muted">${a.file_count || 0} 项</small>
                    </div>
                </div>
            </div>
        `).join('');
    }
    
    initVirtualScroll(grid) {
        grid.innerHTML = '';
        grid.style.position = 'relative';
        
        this.virtualList = new VirtualList(grid, {
            itemHeight: 200,
            itemWidth: 200,
            columns: 4,
            gap: 16
        });
        
        this.virtualList._createItemElement = (item, index) => {
            const div = document.createElement('div');
            div.className = 'col-md-3 col-sm-4 col-6 mb-3';
            div.innerHTML = `
                <div class="album-card card" onclick="albumsPage.openAlbum(${item.id})">
                    <div class="album-cover bg-light d-flex align-items-center justify-content-center">
                        <i class="fas fa-folder fa-2x text-muted"></i>
                    </div>
                    <div class="p-2">
                        <div class="fw-bold text-truncate">${item.album_name}</div>
                        <small class="text-muted">${item.file_count || 0} 项</small>
                    </div>
                </div>
            `;
            return div;
        };
        
        this.virtualList.setItems(this.albums);
    }

    openAlbum(id) {
        this.currentAlbumId = id;
        showToast('相册详情功能开发中', 'info');
    }

    showCreateModal() {
        document.getElementById('album-name').value = '';
        document.getElementById('album-type').value = 'custom';
        new bootstrap.Modal(document.getElementById('createAlbumModal')).show();
    }

    async create() {
        const name = document.getElementById('album-name').value;
        const type = document.getElementById('album-type').value;
        if (!name) {
            showToast('请输入相册名称', 'warning');
            return;
        }
        try {
            await api.createAlbum(name, type);
            bootstrap.Modal.getInstance(document.getElementById('createAlbumModal')).hide();
            showToast('相册创建成功', 'success');
            this.load();
        } catch (e) {
            showToast('创建失败: ' + e.message, 'danger');
        }
    }

    async loadForSelect() {
        const select = document.getElementById('target-album-id');
        try {
            const albums = await api.getAlbums();
            select.innerHTML = '<option value="">选择相册...</option>' +
                albums.map(a => `<option value="${a.id}">${a.album_name} (${a.file_count || 0})</option>`).join('');
        } catch (e) {
            select.innerHTML = '<option value="">加载失败</option>';
        }
    }

    showAddToAlbumModal(selectedFiles) {
        if (selectedFiles.size === 0) {
            showToast('请先选择文件', 'warning');
            return;
        }
        this.loadForSelect();
        document.getElementById('create-new-album-check').checked = false;
        document.getElementById('new-album-input').style.display = 'none';
        new bootstrap.Modal(document.getElementById('addToAlbumModal')).show();
    }

    async addToAlbum(selectedFiles) {
        const createNew = document.getElementById('create-new-album-check').checked;
        const newAlbumName = document.getElementById('new-album-name').value;
        let albumId = document.getElementById('target-album-id').value;

        try {
            if (createNew && newAlbumName) {
                const newAlbum = await api.createAlbum(newAlbumName, 'custom');
                albumId = newAlbum.id;
            }
            if (!albumId) {
                showToast('请选择或创建相册', 'warning');
                return;
            }
            await api.batchAddToAlbum(Array.from(selectedFiles), parseInt(albumId));
            bootstrap.Modal.getInstance(document.getElementById('addToAlbumModal')).hide();
            showToast(`已添加 ${selectedFiles.size} 个文件到相册`, 'success');
            return true;
        } catch (e) {
            showToast('操作失败: ' + e.message, 'danger');
            return false;
        }
    }
}

export const albumsPage = new AlbumsPage();
window.albumsPage = albumsPage;
