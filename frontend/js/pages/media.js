// AI-NAS Media Manager - Media Page
import { api } from '../api.js';
import { showToast, formatFileSize, getTaskBadgeColor, VirtualList } from '../utils.js';

export class MediaPage {
    constructor() {
        this.container = document.getElementById('page-media');
        this.mediaFiles = [];
        this.currentMediaId = null;
        this.selectedFiles = new Set();
        this.batchMode = false;
        this.mediaSkip = 0;
        this.mediaLimit = 50;
        this.hasMoreMedia = true;
        this.virtualList = null;
        this.useVirtualScroll = false;
    }

    async load(append = false) {
        if (!append) {
            this.mediaSkip = 0;
            this.mediaFiles = [];
            this.destroyVirtualScroll();
        }
        document.getElementById('media-loading').style.display = 'flex';
        document.getElementById('media-empty').style.display = 'none';

        try {
            const typeFilter = document.getElementById('media-type-filter').value;
            const files = await api.getMediaFiles({
                skip: this.mediaSkip,
                limit: this.mediaLimit,
                file_type: typeFilter || undefined
            });

            if (append) {
                this.mediaFiles = this.mediaFiles.concat(files);
            } else {
                this.mediaFiles = files;
            }
            this.hasMoreMedia = files.length === this.mediaLimit;
            document.getElementById('load-more-btn').style.display = this.hasMoreMedia ? 'inline-block' : 'none';
            this.renderGrid();
        } catch (e) {
            console.error('加载媒体失败:', e);
            showToast('加载媒体失败: ' + e.message, 'danger');
        } finally {
            document.getElementById('media-loading').style.display = 'none';
        }
    }

    loadMore() {
        this.mediaSkip += this.mediaLimit;
        this.load(true);
    }

    renderGrid() {
        const grid = document.getElementById('media-grid');
        if (this.mediaFiles.length === 0) {
            grid.innerHTML = '';
            document.getElementById('media-empty').style.display = 'block';
            return;
        }
        document.getElementById('media-empty').style.display = 'none';

        // 大数据量时启用虚拟滚动 (>100项)
        if (this.mediaFiles.length > 100 && !this.useVirtualScroll) {
            this.initVirtualScroll();
            return;
        }

        grid.innerHTML = this.mediaFiles.map(f => this.renderMediaItem(f)).join('');

        if (this.batchMode) {
            grid.classList.add('batch-mode');
            document.getElementById('batch-toolbar').style.display = 'flex';
        } else {
            grid.classList.remove('batch-mode');
            document.getElementById('batch-toolbar').style.display = 'none';
        }
    }
    
    renderMediaItem(f) {
        const selected = this.selectedFiles.has(f.id) ? 'selected' : '';
        const checked = this.selectedFiles.has(f.id) ? 'checked' : '';
        const clickHandler = this.batchMode ? `mediaPage.toggleSelect(${f.id})` : `mediaPage.showDetail(${f.id})`;
        const aiBadge = f.ai_processed ? '<span class="status-badge status-ai"><i class="fas fa-robot"></i></span>' : '';
        return `
            <div class="media-item ${selected}" data-id="${f.id}" onclick="${clickHandler}">
                <input type="checkbox" class="media-item-checkbox" ${checked} onclick="event.stopPropagation(); mediaPage.toggleSelect(${f.id})">
                <img src="/api/media/${f.id}/thumbnail?size=200" onerror="this.src='data:image/svg+xml,&lt;svg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 100 100%22&gt;&lt;rect fill=%22%23ddd%22 width=%22100%22 height=%22100%22/&gt;&lt;text x=%2250%22 y=%2250%22 text-anchor=%22middle%22 dy=%22.3em%22 fill=%22%23999%22&gt;No Image&lt;/text&gt;&lt;/svg&gt;'">
                <div class="media-item-overlay"><small>${f.file_name || ''}</small></div>
                ${aiBadge}
            </div>
        `;
    }

    initVirtualScroll() {
        const grid = document.getElementById('media-grid');
        grid.innerHTML = '';
        grid.style.position = 'relative';
        
        // 创建虚拟列表实例
        this.virtualList = new VirtualList(grid, {
            itemHeight: 200,
            itemWidth: 200,
            columns: 4,
            gap: 16
        });
        
        // 绑定渲染函数
        this.virtualList._createItemElement = (item, index) => {
            const div = document.createElement('div');
            div.className = 'media-item';
            div.innerHTML = `
                <img src="/api/media/${item.id}/thumbnail?size=200" onerror="this.src='data:image/svg+xml,&lt;svg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 100 100%22&gt;&lt;rect fill=%22%23ddd%22 width=%22100%22 height=%22100%22/&gt;&lt;text x=%2250%22 y=%2250%22 text-anchor=%22middle%22 dy=%22.3em%22 fill=%22%23999%22&gt;No Image&lt;/text&gt;&lt;/svg&gt;'">
                <div class="media-item-overlay"><small>${item.file_name || ''}</small></div>
                ${item.ai_processed ? '<span class="status-badge status-ai"><i class="fas fa-robot"></i></span>' : ''}
            `;
            div.onclick = () => this.showDetail(item.id);
            return div;
        };
        
        this.virtualList.setItems(this.mediaFiles);
        this.useVirtualScroll = true;
    }

    filterByType(type) {
        document.getElementById('media-type-filter').value = type;
        this.destroyVirtualScroll();
        this.load();
    }
    
    destroyVirtualScroll() {
        if (this.virtualList) {
            this.virtualList.destroy();
            this.virtualList = null;
        }
        this.useVirtualScroll = false;
        const grid = document.getElementById('media-grid');
        grid.style.position = '';
    }

    toggleBatchMode() {
        this.batchMode = !this.batchMode;
        this.selectedFiles.clear();
        this.updateSelectedCount();
        this.renderGrid();
    }

    exitBatchMode() {
        this.batchMode = false;
        this.selectedFiles.clear();
        this.updateSelectedCount();
        this.renderGrid();
    }

    toggleSelect(id) {
        if (this.selectedFiles.has(id)) {
            this.selectedFiles.delete(id);
        } else {
            this.selectedFiles.add(id);
        }
        this.updateSelectedCount();
        this.renderGrid();
    }

    selectAll() {
        this.mediaFiles.forEach(f => this.selectedFiles.add(f.id));
        this.updateSelectedCount();
        this.renderGrid();
    }

    updateSelectedCount() {
        document.getElementById('selected-count').textContent = this.selectedFiles.size;
        document.getElementById('batch-tag-count').textContent = this.selectedFiles.size;
    }

    async showDetail(id) {
        this.currentMediaId = id;
        try {
            let file = this.mediaFiles.find(f => f.id === id);
            if (!file) {
                file = await api.getMediaDetail(id);
            }

            document.getElementById('media-detail-title').textContent = file.file_name || '媒体详情';
            document.getElementById('media-detail-img').src = `/api/media/${id}/thumbnail?size=800`;
            document.getElementById('media-detail-name').textContent = file.file_name || '-';
            document.getElementById('media-detail-size').textContent = formatFileSize(file.file_size);
            document.getElementById('media-detail-date').textContent = file.taken_at || '-';
            document.getElementById('media-detail-ai').innerHTML = file.ai_processed
                ? '<span class="badge bg-success">已分析</span>'
                : '<span class="badge bg-secondary">未分析</span>';
            this.renderTags(file.tags || []);

            new bootstrap.Modal(document.getElementById('mediaDetailModal')).show();
        } catch (e) {
            showToast('加载详情失败: ' + e.message, 'danger');
        }
    }

    renderTags(tags) {
        const container = document.getElementById('media-detail-tags');
        container.innerHTML = tags.map(t => `
            <span class="tag tag-primary tag-editable">${t}
                <i class="fas fa-times tag-remove" onclick="mediaPage.removeTag('${t}')"></i>
            </span>
        `).join('');
    }

    async addTag(tag) {
        if (!tag || !this.currentMediaId) return;
        try {
            await api.addTag(this.currentMediaId, tag);
            const file = await api.getMediaDetail(this.currentMediaId);
            this.renderTags(file.tags || []);
            document.getElementById('new-tag-input').value = '';
            showToast('标签已添加', 'success');
        } catch (e) {
            showToast('添加标签失败: ' + e.message, 'danger');
        }
    }

    async removeTag(tag) {
        if (!this.currentMediaId) return;
        try {
            await api.removeTag(this.currentMediaId, tag);
            const file = await api.getMediaDetail(this.currentMediaId);
            this.renderTags(file.tags || []);
            showToast('标签已移除', 'success');
        } catch (e) {
            showToast('移除标签失败: ' + e.message, 'danger');
        }
    }

    async deleteCurrent() {
        if (!this.currentMediaId || !confirm('确定要删除这个文件吗？')) return;
        try {
            await api.deleteMedia(this.currentMediaId);
            bootstrap.Modal.getInstance(document.getElementById('mediaDetailModal')).hide();
            this.load();
            showToast('文件已删除', 'success');
        } catch (e) {
            showToast('删除失败: ' + e.message, 'danger');
        }
    }

    toggleAdvancedSearch() {
        const panel = document.getElementById('advanced-search-panel');
        panel.style.display = panel.style.display === 'none' ? 'block' : 'none';
    }

    async performAdvancedSearch() {
        const keyword = document.getElementById('adv-keyword').value;
        const fileType = document.getElementById('adv-file-type').value;
        const tags = document.getElementById('adv-tags').value.split(',').map(t => t.trim()).filter(t => t);
        const dateFrom = document.getElementById('adv-date-from').value;
        const dateTo = document.getElementById('adv-date-to').value;

        try {
            const res = await api.advancedSearch({
                keyword,
                file_type: fileType || null,
                tags: tags.length > 0 ? tags : null,
                date_from: dateFrom || null,
                date_to: dateTo || null,
                limit: 100
            });
            this.mediaFiles = res.results || [];
            this.hasMoreMedia = false;
            document.getElementById('load-more-btn').style.display = 'none';
            this.renderGrid();
            showToast(`找到 ${this.mediaFiles.length} 个结果`, 'info');
        } catch (e) {
            showToast('搜索失败: ' + e.message, 'danger');
        }
    }

    // Batch operations
    showBatchTagModal() {
        if (this.selectedFiles.size === 0) {
            showToast('请先选择文件', 'warning');
            return;
        }
        document.getElementById('batch-tags-input').value = '';
        new bootstrap.Modal(document.getElementById('batchTagModal')).show();
    }

    async batchAddTags() {
        const tags = document.getElementById('batch-tags-input').value.split(',').map(t => t.trim()).filter(t => t);
        if (tags.length === 0) {
            showToast('请输入标签', 'warning');
            return;
        }
        try {
            await api.batchAddTags(Array.from(this.selectedFiles), tags);
            bootstrap.Modal.getInstance(document.getElementById('batchTagModal')).hide();
            showToast(`已为 ${this.selectedFiles.size} 个文件添加标签`, 'success');
            this.exitBatchMode();
            this.load();
        } catch (e) {
            showToast('操作失败: ' + e.message, 'danger');
        }
    }

    async batchDelete() {
        if (this.selectedFiles.size === 0) return;
        if (!confirm(`确定要删除选中的 ${this.selectedFiles.size} 个文件吗？`)) return;
        try {
            await api.batchDelete(Array.from(this.selectedFiles));
            showToast(`已删除 ${this.selectedFiles.size} 个文件`, 'success');
            this.exitBatchMode();
            this.load();
        } catch (e) {
            showToast('删除失败: ' + e.message, 'danger');
        }
    }

    downloadCurrent() {
        if (!this.currentMediaId) return;
        showToast('下载功能开发中', 'info');
    }

    runAIClassify() {
        if (!this.currentMediaId) return;
        showToast('AI 分析任务已提交', 'info');
    }
}

export const mediaPage = new MediaPage();
window.mediaPage = mediaPage;
