/**
 * Plugin Marketplace Page
 * V6.0 Phase 3: 插件体系前端
 */

(function() {
  'use strict';

  // Plugin data store
  const PluginStore = {
    plugins: [],
    loading: false,
    
    async load() {
      this.loading = true;
      try {
        const res = await api.get('/plugins/');
        this.plugins = res.plugins || [];
        this.render();
      } catch (err) {
        console.error('Failed to load plugins:', err);
        showToast('加载插件失败', 'error');
      } finally {
        this.loading = false;
      }
    },
    
    async enable(id) {
      try {
        await api.post(`/plugins/${id}/enable`);
        showToast('插件已启用');
        this.load();
      } catch (err) {
        showToast('启用失败', 'error');
      }
    },
    
    async disable(id) {
      try {
        await api.post(`/plugins/${id}/disable`);
        showToast('插件已禁用');
        this.load();
      } catch (err) {
        showToast('禁用失败', 'error');
      }
    },
    
    async uninstall(id) {
      if (!confirm('确定要卸载此插件吗？')) return;
      try {
        await api.delete(`/plugins/${id}`);
        showToast('插件已卸载');
        this.load();
      } catch (err) {
        showToast('卸载失败', 'error');
      }
    },
    
    async install(file) {
      const formData = new FormData();
      formData.append('file', file);
      
      try {
        await api.upload('/plugins/install', formData);
        showToast('插件安装成功');
        this.load();
      } catch (err) {
        showToast('安装失败', 'error');
      }
    },
    
    render() {
      const container = document.getElementById('plugin-content');
      if (!container) return;
      
      // Group plugins by type
      const builtin = this.plugins.filter(p => p.type === 'builtin');
      const installed = this.plugins.filter(p => p.type === 'installed');
      
      container.innerHTML = `
        <div class="plugin-page">
          ${this.renderHeader()}
          ${this.renderBuiltinPlugins(builtin)}
          ${this.renderInstalledPlugins(installed)}
          ${this.renderMarketplace()}
        </div>
      `;
      
      this.bindEvents();
    },
    
    renderHeader() {
      return `
        <div class="plugin-header">
          <div class="header-info">
            <h1>🧩 插件管理</h1>
            <p>扩展系统功能，支持第三方插件</p>
          </div>
          <div class="header-actions">
            <label class="btn btn-primary upload-btn">
              <input type="file" accept=".zip" id="plugin-upload" style="display:none" />
              📦 安装插件
            </label>
          </div>
        </div>
      `;
    },
    
    renderBuiltinPlugins(plugins) {
      if (plugins.length === 0) return '';
      
      return `
        <div class="plugin-section">
          <h2 class="section-title">📦 内置插件</h2>
          <div class="plugin-grid">
            ${plugins.map(p => this.renderPluginCard(p, true)).join('')}
          </div>
        </div>
      `;
    },
    
    renderInstalledPlugins(plugins) {
      if (plugins.length === 0) {
        return `
          <div class="plugin-section">
            <h2 class="section-title">📥 已安装插件</h2>
            <div class="empty-state">
              <span class="empty-icon">🧩</span>
              <p>暂无已安装的插件</p>
              <p class="empty-hint">上传插件 ZIP 包即可安装</p>
            </div>
          </div>
        `;
      }
      
      return `
        <div class="plugin-section">
          <h2 class="section-title">📥 已安装插件 (${plugins.length})</h2>
          <div class="plugin-grid">
            ${plugins.map(p => this.renderPluginCard(p, false)).join('')}
          </div>
        </div>
      `;
    },
    
    renderMarketplace() {
      return `
        <div class="plugin-section">
          <h2 class="section-title">🏪 插件市场</h2>
          <div class="market-grid" id="market-grid">
            <div class="loading">
              <span>加载推荐插件...</span>
            </div>
          </div>
        </div>
      `;
    },
    
    renderPluginCard(plugin, isBuiltin) {
      const manifest = plugin.manifest || {};
      const typeLabels = {
        'storage': { icon: '💾', text: '存储' },
        'ai': { icon: '🤖', text: 'AI' },
        'ui': { icon: '🎨', text: 'UI' },
        'tool': { icon: '🔧', text: '工具' },
        'integration': { icon: '🔗', text: '集成' }
      };
      const type = typeLabels[manifest.plugin_type] || { icon: '📦', text: '插件' };
      
      return `
        <div class="plugin-card ${plugin.enabled ? 'enabled' : ''}" data-id="${plugin.id}">
          <div class="plugin-card-header">
            <span class="plugin-icon">${type.icon}</span>
            <span class="plugin-type-badge">${type.text}</span>
            ${plugin.enabled ? '<span class="status-badge enabled">已启用</span>' : '<span class="status-badge disabled">未启用</span>'}
          </div>
          <div class="plugin-card-body">
            <h3 class="plugin-name">${manifest.name || plugin.name}</h3>
            <p class="plugin-desc">${manifest.description || '暂无描述'}</p>
            <div class="plugin-meta">
              <span class="plugin-author">${manifest.author || '未知作者'}</span>
              <span class="plugin-version">v${manifest.version || '1.0.0'}</span>
            </div>
          </div>
          <div class="plugin-card-footer">
            ${!isBuiltin ? `
              ${plugin.enabled ? `
                <button class="btn btn-sm btn-warning" data-action="disable" data-id="${plugin.id}">禁用</button>
              ` : `
                <button class="btn btn-sm btn-success" data-action="enable" data-id="${plugin.id}">启用</button>
              `}
              <button class="btn btn-sm btn-danger" data-action="uninstall" data-id="${plugin.id}">卸载</button>
              <button class="btn btn-sm btn-default" data-action="config" data-id="${plugin.id}">配置</button>
            ` : `
              <button class="btn btn-sm ${plugin.enabled ? 'btn-warning' : 'btn-success'}" data-action="toggle" data-id="${plugin.id}">
                ${plugin.enabled ? '禁用' : '启用'}
              </button>
            `}
          </div>
        </div>
      `;
    },
    
    bindEvents() {
      // Upload button
      const uploadInput = document.getElementById('plugin-upload');
      if (uploadInput) {
        uploadInput.addEventListener('change', async (e) => {
          const file = e.target.files[0];
          if (file) {
            await this.install(file);
            e.target.value = '';
          }
        });
      }
      
      // Action buttons
      document.querySelectorAll('[data-action]').forEach(btn => {
        btn.addEventListener('click', async (e) => {
          const action = e.target.dataset.action;
          const id = e.target.dataset.id;
          
          switch (action) {
            case 'enable':
              await this.enable(id);
              break;
            case 'disable':
              await this.disable(id);
              break;
            case 'toggle':
              const plugin = this.plugins.find(p => p.id === id);
              if (plugin.enabled) {
                await this.disable(id);
              } else {
                await this.enable(id);
              }
              break;
            case 'uninstall':
              await this.uninstall(id);
              break;
            case 'config':
              this.showConfigDialog(id);
              break;
          }
        });
      });
      
      // Load marketplace
      this.loadMarketplace();
    },
    
    async loadMarketplace() {
      try {
        const res = await api.get('/plugins/market/featured');
        const container = document.getElementById('market-grid');
        if (container && res.featured) {
          container.innerHTML = res.featured.map(p => `
            <div class="market-item">
              <div class="market-icon">${this.getTypeIcon(p.type)}</div>
              <div class="market-info">
                <h4>${p.name}</h4>
                <p>${p.description}</p>
                <div class="market-meta">
                  <span class="market-rating">⭐ ${p.rating}</span>
                  <span class="market-downloads">📥 ${p.downloads}</span>
                </div>
              </div>
              <button class="btn btn-sm btn-primary" disabled>即将推出</button>
            </div>
          `).join('');
        }
      } catch (err) {
        console.error('Failed to load marketplace:', err);
      }
    },
    
    getTypeIcon(type) {
      const icons = {
        'storage': '💾',
        'ai': '🤖',
        'ui': '🎨',
        'tool': '🔧',
        'integration': '🔗'
      };
      return icons[type] || '📦';
    },
    
    showConfigDialog(pluginId) {
      const plugin = this.plugins.find(p => p.id === pluginId);
      if (!plugin) return;
      
      const manifest = plugin.manifest || {};
      const config = plugin.config || {};
      const schema = manifest.config_schema || {};
      const properties = schema.properties || {};
      
      let formHtml = '';
      for (const [key, prop] of Object.entries(properties)) {
        const value = config[key] || prop.default || '';
        formHtml += `
          <div class="form-group">
            <label>${prop.title}</label>
            ${prop.format === 'password' 
              ? `<input type="password" name="${key}" value="${value}" placeholder="${prop.description || ''}" />`
              : `<input type="text" name="${key}" value="${value}" placeholder="${prop.description || ''}" />`
            }
            ${prop.description ? `<small>${prop.description}</small>` : ''}
          </div>
        `;
      }
      
      const dialog = createDialog(`
        <h2>配置 ${manifest.name}</h2>
        <form id="plugin-config-form">
          ${formHtml}
          <div class="form-actions">
            <button type="button" class="btn btn-default" onclick="closeDialog()">取消</button>
            <button type="submit" class="btn btn-primary">保存</button>
          </div>
        </form>
      `);
      
      document.getElementById('plugin-config-form').addEventListener('submit', async (e) => {
        e.preventDefault();
        const formData = new FormData(e.target);
        const newConfig = {};
        formData.forEach((value, key) => {
          newConfig[key] = value;
        });
        
        try {
          await api.post(`/plugins/${pluginId}/config`, { config: newConfig });
          showToast('配置已保存');
          closeDialog();
          this.load();
        } catch (err) {
          showToast('保存失败', 'error');
        }
      });
    }
  };

  // Register page
  window.Pages = window.Pages || {};
  window.Pages.plugins = PluginStore;

})();
