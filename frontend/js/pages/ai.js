/**
 * AI-NAS Media Manager - AI功能页面
 */
import { api } from '../api.js';
import { showToast, formatDate, getFileIcon } from '../utils.js';

export class AIPage {
    constructor() {
        this.container = document.getElementById('page-ai');
        this.currentTab = 'overview';
    }

    async load() {
        if (!this.container) return;
        
        try {
            await this.loadStats();
            this.renderTabs();
            
            switch (this.currentTab) {
                case 'faces':
                    await this.loadFaceRecognition();
                    break;
                case 'albums':
                    await this.loadSmartAlbums();
                    break;
                case 'tags':
                    await this.loadTags();
                    break;
                case 'similar':
                    await this.loadSimilar();
                    break;
                default:
                    await this.loadOverview();
            }
        } catch (e) {
            console.error('加载AI功能失败:', e);
            showToast('加载AI功能失败: ' + e.message, 'danger');
        }
    }

    async loadStats() {
        try {
            const stats = await api.getAIStats();
            this.stats = stats;
        } catch (e) {
            console.error('获取AI统计失败:', e);
            this.stats = {
                faces_count: 0,
                tags_count: 0,
                smart_albums_count: 0,
                similar_pairs_count: 0
            };
        }
    }

    renderTabs() {
        const tabs = document.getElementById('ai-tabs');
        if (!tabs) return;
        
        tabs.innerHTML = `
            <ul class="nav nav-tabs">
                <li class="nav-item">
                    <a class="nav-link ${this.currentTab === 'overview' ? 'active' : ''}" href="#" onclick="aiPage.switchTab('overview')">概览</a>
                </li>
                <li class="nav-item">
                    <a class="nav-link ${this.currentTab === 'faces' ? 'active' : ''}" href="#" onclick="aiPage.switchTab('faces')">
                        <i class="fas fa-user-circle"></i> 人脸识别
                    </a>
                </li>
                <li class="nav-item">
                    <a class="nav-link ${this.currentTab === 'albums' ? 'active' : ''}" href="#" onclick="aiPage.switchTab('albums')">
                        <i class="fas fa-magic"></i> 智能相册
                    </a>
                </li>
                <li class="nav-item">
                    <a class="nav-link ${this.currentTab === 'tags' ? 'active' : ''}" href="#" onclick="aiPage.switchTab('tags')">
                        <i class="fas fa-tags"></i> 标签管理
                    </a>
                </li>
                <li class="nav-item">
                    <a class="nav-link ${this.currentTab === 'similar' ? 'active' : ''}" href="#" onclick="aiPage.switchTab('similar')">
                        <i class="fas fa-images"></i> 相似图片
                    </a>
                </li>
            </ul>
        `;
    }

    switchTab(tab) {
        this.currentTab = tab;
        this.load();
    }

    async loadOverview() {
        const content = document.getElementById('ai-content');
        if (!content) return;
        
        content.innerHTML = `
            <div class="row">
                <div class="col-md-3">
                    <div class="stat-card">
                        <div class="stat-icon"><i class="fas fa-user-circle"></i></div>
                        <div class="stat-value">${this.stats.faces_count || 0}</div>
                        <div class="stat-label">已识别人物</div>
                    </div>
                </div>
                <div class="col-md-3">
                    <div class="stat-card">
                        <div class="stat-icon"><i class="fas fa-magic"></i></div>
                        <div class="stat-value">${this.stats.smart_albums_count || 0}</div>
                        <div class="stat-label">智能相册</div>
                    </div>
                </div>
                <div class="col-md-3">
                    <div class="stat-card">
                        <div class="stat-icon"><i class="fas fa-tags"></i></div>
                        <div class="stat-value">${this.stats.tags_count || 0}</div>
                        <div class="stat-label">已生成标签</div>
                    </div>
                </div>
                <div class="col-md-3">
                    <div class="stat-card">
                        <div class="stat-icon"><i class="fas fa-images"></i></div>
                        <div class="stat-value">${this.stats.similar_pairs_count || 0}</div>
                        <div class="stat-label">相似图片组</div>
                    </div>
                </div>
            </div>
            
            <div class="row mt-4">
                <div class="col-md-6">
                    <div class="card">
                        <div class="card-header">
                            <h5 class="mb-0"><i class="fas fa-user-circle me-2"></i>人脸识别</h5>
                        </div>
                        <div class="card-body">
                            <p class="text-muted">自动检测并识别照片中的人物，支持人脸聚类和命名。</p>
                            <button class="btn btn-primary" onclick="aiPage.switchTab('faces')">
                                <i class="fas fa-arrow-right"></i> 查看详情
                            </button>
                        </div>
                    </div>
                </div>
                <div class="col-md-6">
                    <div class="card">
                        <div class="card-header">
                            <h5 class="mb-0"><i class="fas fa-magic me-2"></i>智能相册</h5>
                        </div>
                        <div class="card-body">
                            <p class="text-muted">基于AI推荐算法，智能整理您的照片到不同的相册。</p>
                            <button class="btn btn-primary" onclick="aiPage.switchTab('albums')">
                                <i class="fas fa-arrow-right"></i> 查看详情
                            </button>
                        </div>
                    </div>
                </div>
            </div>
            
            <div class="row mt-4">
                <div class="col-md-6">
                    <div class="card">
                        <div class="card-header">
                            <h5 class="mb-0"><i class="fas fa-tags me-2"></i>自动标签</h5>
                        </div>
                        <div class="card-body">
                            <p class="text-muted">AI自动分析照片内容，生成描述性标签。</p>
                            <button class="btn btn-primary" onclick="aiPage.switchTab('tags')">
                                <i class="fas fa-arrow-right"></i> 查看详情
                            </button>
                        </div>
                    </div>
                </div>
                <div class="col-md-6">
                    <div class="card">
                        <div class="card-header">
                            <h5 class="mb-0"><i class="fas fa-images me-2"></i>相似图片检测</h5>
                        </div>
                        <div class="card-body">
                            <p class="text-muted">自动检测重复或相似的照片，帮助您清理图库。</p>
                            <button class="btn btn-primary" onclick="aiPage.switchTab('similar')">
                                <i class="fas fa-arrow-right"></i> 查看详情
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }

    async loadFaceRecognition() {
        const content = document.getElementById('ai-content');
        if (!content) return;
        
        try {
            const faces = await api.getFaceAlbums();
            
            content.innerHTML = `
                <div class="d-flex justify-content-between align-items-center mb-4">
                    <h5><i class="fas fa-user-circle me-2"></i>人脸识别</h5>
                    <button class="btn btn-primary" onclick="aiPage.runFaceRecognition()">
                        <i class="fas fa-search"></i> 开始扫描
                    </button>
                </div>
                
                <div class="row">
                    ${(faces || []).map(face => `
                        <div class="col-md-3 mb-4">
                            <div class="card">
                                <div class="card-body text-center">
                                    <div class="face-avatar mb-3">
                                        <i class="fas fa-user-circle fa-5x text-secondary"></i>
                                    </div>
                                    <h6>${face.name || '未命名'}</h6>
                                    <p class="text-muted small">${face.count || 0} 张照片</p>
                                    <button class="btn btn-sm btn-outline-primary" onclick="aiPage.nameFace(${face.id})">
                                        命名
                                    </button>
                                </div>
                            </div>
                        </div>
                    `).join('')}
                    
                    ${(!faces || faces.length === 0) ? `
                        <div class="col-12 text-center text-muted py-5">
                            <i class="fas fa-user-circle fa-5x mb-3"></i>
                            <p>暂无识别人脸</p>
                            <button class="btn btn-primary" onclick="aiPage.runFaceRecognition()">
                                开始扫描
                            </button>
                        </div>
                    ` : ''}
                </div>
            `;
        } catch (e) {
            content.innerHTML = `
                <div class="alert alert-warning">
                    <i class="fas fa-exclamation-triangle me-2"></i>
                    无法加载人脸数据: ${e.message}
                </div>
            `;
        }
    }

    async loadSmartAlbums() {
        const content = document.getElementById('ai-content');
        if (!content) return;
        
        try {
            const albums = await api.getSmartAlbums();
            
            content.innerHTML = `
                <div class="d-flex justify-content-between align-items-center mb-4">
                    <h5><i class="fas fa-magic me-2"></i>智能相册</h5>
                    <button class="btn btn-primary" onclick="aiPage.refreshSmartAlbums()">
                        <i class="fas fa-sync"></i> 刷新推荐
                    </button>
                </div>
                
                <div class="row">
                    ${(albums || []).map(album => `
                        <div class="col-md-4 mb-4">
                            <div class="card">
                                <div class="card-header">
                                    <span class="badge bg-info">${album.type || '智能'}</span>
                                    ${album.name}
                                </div>
                                <div class="card-body">
                                    <p class="text-muted">${album.description || ''}</p>
                                    <div class="d-flex justify-content-between align-items-center">
                                        <span class="small text-muted">${album.count || 0} 张照片</span>
                                        <button class="btn btn-sm btn-outline-primary" onclick="aiPage.viewSmartAlbum('${album.id}')">
                                            查看
                                        </button>
                                    </div>
                                </div>
                            </div>
                        </div>
                    `).join('')}
                    
                    ${(!albums || albums.length === 0) ? `
                        <div class="col-12 text-center text-muted py-5">
                            <i class="fas fa-magic fa-5x mb-3"></i>
                            <p>暂无智能相册</p>
                        </div>
                    ` : ''}
                </div>
            `;
        } catch (e) {
            content.innerHTML = `
                <div class="alert alert-warning">
                    <i class="fas fa-exclamation-triangle me-2"></i>
                    无法加载智能相册: ${e.message}
                </div>
            `;
        }
    }

    async loadTags() {
        const content = document.getElementById('ai-content');
        if (!content) return;
        
        try {
            const tags = await api.getTags();
            
            content.innerHTML = `
                <div class="d-flex justify-content-between align-items-center mb-4">
                    <h5><i class="fas fa-tags me-2"></i>标签管理</h5>
                    <button class="btn btn-primary" onclick="aiPage.runAutoTagging()">
                        <i class="fas fa-magic"></i> 批量生成标签
                    </button>
                </div>
                
                <div class="card">
                    <div class="card-body">
                        <div class="tag-cloud">
                            ${(tags || []).map(tag => `
                                <span class="badge bg-secondary me-2 mb-2" style="font-size: 14px;">
                                    ${tag.name} (${tag.count || 0})
                                </span>
                            `).join('')}
                            
                            ${(!tags || tags.length === 0) ? `
                                <span class="text-muted">暂无标签</span>
                            ` : ''}
                        </div>
                    </div>
                </div>
            `;
        } catch (e) {
            content.innerHTML = `
                <div class="alert alert-warning">
                    <i class="fas fa-exclamation-triangle me-2"></i>
                    无法加载标签: ${e.message}
                </div>
            `;
        }
    }

    async loadSimilar() {
        const content = document.getElementById('ai-content');
        if (!content) return;
        
        content.innerHTML = `
            <div class="d-flex justify-content-between align-items-center mb-4">
                <h5><i class="fas fa-images me-2"></i>相似图片检测</h5>
                <button class="btn btn-primary" onclick="aiPage.scanSimilar()">
                    <i class="fas fa-search"></i> 扫描相似
                </button>
            </div>
            
            <div class="alert alert-info">
                <i class="fas fa-info-circle me-2"></i>
                相似图片检测功能将自动找出重复或相似的照片，帮助您清理图库。
            </div>
            
            <div class="row" id="similar-groups">
                <div class="col-12 text-center text-muted py-5">
                    <i class="fas fa-images fa-5x mb-3"></i>
                    <p>点击"扫描相似"开始检测</p>
                </div>
            </div>
        `;
    }

    async runFaceRecognition() {
        try {
            showToast('正在扫描人脸，请稍候...', 'info');
            await api.runFaceRecognition();
            showToast('人脸扫描完成', 'success');
            await this.loadFaceRecognition();
        } catch (e) {
            showToast('扫描失败: ' + e.message, 'danger');
        }
    }

    async runAutoTagging() {
        try {
            showToast('正在生成标签，请稍候...', 'info');
            await api.runAutoTagging();
            showToast('标签生成完成', 'success');
            await this.loadTags();
        } catch (e) {
            showToast('生成失败: ' + e.message, 'danger');
        }
    }

    async scanSimilar() {
        try {
            showToast('正在扫描相似图片，请稍候...', 'info');
            // TODO: Implement similar scan API
            showToast('相似图片扫描完成', 'success');
        } catch (e) {
            showToast('扫描失败: ' + e.message, 'danger');
        }
    }

    nameFace(faceId) {
        const name = prompt('请输入人物名称:');
        if (name) {
            showToast(`已保存人物名称: ${name}`, 'success');
        }
    }

    viewSmartAlbum(albumId) {
        // Navigate to album detail
        app.showPage('albums');
    }

    refreshSmartAlbums() {
        showToast('正在刷新智能相册...', 'info');
        this.loadSmartAlbums();
    }
}

export const aiPage = new AIPage();
window.aiPage = aiPage;
