/**
 * AI-NAS Media Manager - Media Module
 * 媒体库模块
 */

const Media = {
    // 状态
    files: [],
    currentId: null,
    selected: new Set(),
    batchMode: false,
    skip: 0,
    limit: 50,
    hasMore: true,

    // 加载媒体列表
    async load(append = false) {
        if (!append) {
            this.skip = 0;
            this.files = [];
        }

        document.getElementById('media-loading').style.display = 'flex';
        document.getElementById('media-empty').style.display = 'none';

        try {
            const typeFilter = document.getElementById('media-type-filter')?.value || '';
            let url = `/api/media/?skip=${this.skip}&limit=${this.limit}`;
            if (typeFilter) url += `&file_type=${typeFilter}`;

            const files = await API.get(url);

            if (append) {
                this.files = this.files.concat(files);
            } else {
                this.files = files;
            }

            this.hasMore = files.length === this.limit;
            document.getElementById('load-more-btn').style.display = 
                this.hasMore ? 'inline-block' : 'none';

            this.render();

        } catch (e) {
            console.error('加载媒体失败:', e);
            Utils.showToast('加载媒体失败: ' + e.message, 'danger');
        } finally {
            document.getElementById('media-loading').style.display = 'none';
        }
    },

    // 加载更多
    loadMore() {
        this.skip += this.limit;
        this.load(true);
    },

    // 渲染媒体网格
    render() {
        const grid = document.getElementById('media-grid');

        if (this.files.length === 0) {
            grid.innerHTML = '';
            document.getElementById('media-empty').style.display = 'block';
            return;
        }

        document.getElementById('media-empty').style.display = 'none';

        grid.innerHTML = this.files.map(f => {
            const selected = this.selected.has(f.id) ? 'selected' : '';
            const checked = this.selected.has(f.id) ? 'checked' : '';
            const clickHandler = this.batchMode ? 
                `Media.toggleSelect(${f.id})` : 
                `Media.showDetail(${f.id})`;
            const aiBadge = f.ai_processed ? 
                '<span class="status-badge status-ai"><i class="fas fa-robot"></i></span>' : '';

            return `
                <div class="media-item ${selected}" data-id="${f.id}" onclick="${clickHandler}">
                    <input type="checkbox" class="media-item-checkbox" ${checked} 
                           onclick="event.stopPropagation(); Media.toggleSelect(${f.id})">
                    <img src="/api/media/${f.id}/thumbnail?size=200" 
                         onerror="this.src='data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 100 100%22><rect fill=%22%23ddd%22 width=%22100%22 height=%22100%22/></svg>'">
                    <div class="media-item-overlay">
                        <small>${Utils.escapeHtml(f.file_name || '')}</small>
                    </div>
                    ${aiBadge}
                </div>
            `;
        }).join('');

        // 批量模式样式
        if (this.batchMode) {
            grid.classList.add('batch-mode');
            document.getElementById('batch-toolbar').style.display = 'flex';
        } else {
            grid.classList.remove('batch-mode');
            document.getElementById('batch-toolbar').style.display = 'none';
        }
    },

    // 筛选类型
    filterType(type) {
        const filter = document.getElementById('media-type-filter');
        if (filter) filter.value = type;
        this.load();
    },

    // 切换批量模式
    toggleBatchMode() {
        this.batchMode = !this.batchMode;
        this.selected.clear();
        this.updateSelectedCount();
        this.render();
    },

    // 退出批量模式
    exitBatchMode() {
        this.batchMode = false;
        this.selected.clear();
        this.updateSelectedCount();
        this.render();
    },

    // 切换选择
    toggleSelect(id) {
        if (this.selected.has(id)) {
            this.selected.delete(id);
        } else {
            this.selected.add(id);
        }
        this.updateSelectedCount();
        this.render();
    },

    // 全选当前页
    selectAll() {
        this.files.forEach(f => this.selected.add(f.id));
        this.updateSelectedCount();
        this.render();
    },

    // 更新选中数量
    updateSelectedCount() {
        const count = this.selected.size;
        document.getElementById('selected-count').textContent = count;
        const batchCount = document.getElementById('batch-tag-count');
        if (batchCount) batchCount.textContent = count;
    },

    // 显示媒体详情
    async showDetail(id) {
        this.currentId = id;
        const file = this.files.find(f => f.id === id) || await API.get(`/api/media/${id}`);

        document.getElementById('media-detail-title').textContent = file.file_name || '媒体详情';
        document.getElementById('media-detail-img').src = `/api/media/${id}/thumbnail?size=800`;
        document.getElementById('media-detail-name').textContent = file.file_name || '-';
        document.getElementById('media-detail-size').textContent = Utils.formatFileSize(file.file_size);
        document.getElementById('media-detail-date').textContent = file.taken_at || '-';

        document.getElementById('media-detail-ai').innerHTML = file.ai_processed ?
            '<span class="badge bg-success">已分析</span>' :
            '<span class="badge bg-secondary">未分析</span>';

        this.renderTags(file.tags || []);

        new bootstrap.Modal(document.getElementById('mediaDetailModal')).show();
    },

    // 渲染标签
    renderTags(tags) {
        const container = document.getElementById('media-detail-tags');
        container.innerHTML = tags.map(t => `
            <span class="tag tag-primary tag-editable">
                ${Utils.escapeHtml(t)}
                <i class="fas fa-times tag-remove" onclick="Media.removeTag('${Utils.escapeHtml(t)}')"></i>
            </span>
        `).join('');
    },

    // 添加标签
    async addTag(tag) {
        if (!tag || !this.currentId) return;

        try {
            await API.post('/api/media/add-tag', {
                file_id: this.currentId,
                tag: tag
            });

            const file = await API.get(`/api/media/${this.currentId}`);
            this.renderTags(file.tags || []);
            document.getElementById('new-tag-input').value = '';
            Utils.showToast('标签已添加', 'success');

        } catch (e) {
            Utils.showToast('添加标签失败: ' + e.message, 'danger');
        }
    },

    // 移除标签
    async removeTag(tag) {
        if (!this.currentId) return;

        try {
            await API.post('/api/media/remove-tag', {
                file_id: this.currentId,
                tag: tag
            });

            const file = await API.get(`/api/media/${this.currentId}`);
            this.renderTags(file.tags || []);
            Utils.showToast('标签已移除', 'success');

        } catch (e) {
            Utils.showToast('移除标签失败: ' + e.message, 'danger');
        }
    },

    // 删除当前媒体
    async deleteCurrent() {
        if (!this.currentId || !confirm('确定要删除这个文件吗？')) return;

        try {
            await API.delete(`/api/media/${this.currentId}`);
            bootstrap.Modal.getInstance(document.getElementById('mediaDetailModal')).hide();
            this.load();
            Utils.showToast('文件已删除', 'success');

        } catch (e) {
            Utils.showToast('删除失败: ' + e.message, 'danger');
        }
    },

    // 批量删除
    async batchDelete() {
        if (this.selected.size === 0) return;
        if (!confirm(`确定要删除选中的 ${this.selected.size} 个文件吗？`)) return;

        try {
            await API.post('/api/actions/batch/delete', {
                file_ids: Array.from(this.selected)
            });

            Utils.showToast(`已删除 ${this.selected.size} 个文件`, 'success');
            this.exitBatchMode();
            this.load();

        } catch (e) {
            Utils.showToast('删除失败: ' + e.message, 'danger');
        }
    },

    // 批量添加标签
    async batchAddTags(tags) {
        if (this.selected.size === 0 || tags.length === 0) return;

        try {
            await API.post('/api/actions/batch/add-tags', {
                file_ids: Array.from(this.selected),
                tags: tags
            });

            Utils.showToast(`已为 ${this.selected.size} 个文件添加标签`, 'success');
            this.exitBatchMode();
            this.load();

        } catch (e) {
            Utils.showToast('操作失败: ' + e.message, 'danger');
        }
    },

    // 显示添加到相册弹窗
    showAddToAlbumModal() {
        if (this.selected.size === 0) {
            Utils.showToast('请先选择文件', 'warning');
            return;
        }
        // 更新选中数量
        const countEl = document.getElementById('batch-album-count');
        if (countEl) countEl.textContent = this.selected.size;
        // 加载相册列表
        Albums.loadForSelect();
        new bootstrap.Modal(document.getElementById('addToAlbumModal')).show();
    },

    // 批量添加到相册
    async batchAddToAlbum() {
        const albumId = document.getElementById('target-album-id').value;
        if (!albumId) {
            Utils.showToast('请选择相册', 'warning');
            return;
        }

        try {
            await API.post('/api/actions/batch/add-to-album', {
                file_ids: Array.from(this.selected),
                album_id: parseInt(albumId)
            });

            Utils.showToast(`已添加 ${this.selected.size} 个文件到相册`, 'success');
            bootstrap.Modal.getInstance(document.getElementById('addToAlbumModal')).hide();
            this.exitBatchMode();
            this.load();

        } catch (e) {
            Utils.showToast('操作失败: ' + e.message, 'danger');
        }
    },

    // 高级搜索
    async advancedSearch(params) {
        try {
            const res = await API.post('/api/media/search/advanced', {
                ...params,
                limit: 100
            });

            this.files = res.results || [];
            this.hasMore = false;
            document.getElementById('load-more-btn').style.display = 'none';
            this.render();

            Utils.showToast(`找到 ${this.files.length} 个结果`, 'info');

        } catch (e) {
            Utils.showToast('搜索失败: ' + e.message, 'danger');
        }
    }
};

// 导出
window.Media = Media;
