/**
 * Enterprise Settings Page
 * V6.0 Phase 4: 企业增强 - SSO/多租户/审计分析
 */

(function() {
  'use strict';

  const EnterprisePage = {
    currentTab: 'sso',
    
    async init() {
      await this.loadPage();
      this.bindEvents();
    },
    
    async loadPage() {
      const container = document.getElementById('enterprise-content');
      if (!container) return;
      
      container.innerHTML = `
        <div class="enterprise-page">
          ${this.renderHeader()}
          ${this.renderTabs()}
          <div class="tab-content">
            <div id="tab-sso" class="tab-pane ${this.currentTab === 'sso' ? 'active' : ''}">
              ${await this.renderSSOTab()}
            </div>
            <div id="tab-tenants" class="tab-pane ${this.currentTab === 'tenants' ? 'active' : ''}">
              ${await this.renderTenantsTab()}
            </div>
            <div id="tab-audit" class="tab-pane ${this.currentTab === 'audit' ? 'active' : ''}">
              ${await this.renderAuditTab()}
            </div>
          </div>
        </div>
      `;
    },
    
    renderHeader() {
      return `
        <div class="enterprise-header">
          <div class="header-info">
            <h1>🏢 企业设置</h1>
            <p>管理 SSO 单点登录、多租户和审计分析</p>
          </div>
        </div>
      `;
    },
    
    renderTabs() {
      return `
        <ul class="nav nav-tabs enterprise-tabs">
          <li class="nav-item">
            <a class="nav-link ${this.currentTab === 'sso' ? 'active' : ''}" 
               data-tab="sso" href="#">
              <i class="fas fa-key"></i> SSO 单点登录
            </a>
          </li>
          <li class="nav-item">
            <a class="nav-link ${this.currentTab === 'tenants' ? 'active' : ''}" 
               data-tab="tenants" href="#">
              <i class="fas fa-building"></i> 多租户
            </a>
          </li>
          <li class="nav-item">
            <a class="nav-link ${this.currentTab === 'audit' ? 'active' : ''}" 
               data-tab="audit" href="#">
              <i class="fas fa-chart-bar"></i> 审计分析
            </a>
          </li>
        </ul>
      `;
    },
    
    async renderSSOTab() {
      let ssoStatus = { enabled: false, provider: null, status: 'not_configured' };
      
      try {
        ssoStatus = await api.get('/enterprise/sso/status');
      } catch (e) {
        console.error('Failed to load SSO status:', e);
      }
      
      return `
        <div class="tab-content-inner">
          <div class="card">
            <div class="card-header d-flex justify-content-between align-items-center">
              <h5 class="mb-0"><i class="fas fa-shield-alt me-2"></i>SSO 配置</h5>
              <div>
                ${ssoStatus.enabled 
                  ? '<span class="badge bg-success">已启用</span>'
                  : '<span class="badge bg-secondary">未启用</span>'
                }
              </div>
            </div>
            <div class="card-body">
              <div id="sso-config-form">
                <div class="mb-3">
                  <label class="form-label">SSO 提供商</label>
                  <select id="sso-provider" class="form-select">
                    <option value="">请选择...</option>
                    <option value="oidc">OpenID Connect (OIDC)</option>
                    <option value="azure_ad">Microsoft Azure AD</option>
                    <option value="ldap">LDAP / Active Directory</option>
                  </select>
                </div>
                
                <div id="oidc-config" class="sso-config-section" style="display:none">
                  <div class="mb-3">
                    <label class="form-label">客户端 ID (Client ID)</label>
                    <input type="text" id="sso-client-id" class="form-control" placeholder="应用程序客户端ID">
                  </div>
                  <div class="mb-3">
                    <label class="form-label">客户端密钥 (Client Secret)</label>
                    <input type="password" id="sso-client-secret" class="form-control" placeholder="应用程序客户端密钥">
                  </div>
                  <div class="mb-3">
                    <label class="form-label">授权服务器 (Authority)</label>
                    <input type="text" id="sso-authority" class="form-control" 
                           placeholder="https://login.microsoftonline.com/{tenant}/v2.0">
                  </div>
                  <div class="mb-3">
                    <label class="form-label">自动创建用户</label>
                    <div class="form-check form-switch">
                      <input class="form-check-input" type="checkbox" id="sso-auto-provision" checked>
                      <label class="form-check-label" for="sso-auto-provision">
                        首次登录时自动创建本地账户
                      </label>
                    </div>
                  </div>
                  <div class="mb-3">
                    <label class="form-label">默认角色</label>
                    <select id="sso-default-role" class="form-select">
                      <option value="viewer">访客</option>
                      <option value="editor">编辑者</option>
                      <option value="admin">管理员</option>
                    </select>
                  </div>
                </div>
                
                <div id="ldap-config" class="sso-config-section" style="display:none">
                  <div class="alert alert-info">
                    <i class="fas fa-info-circle me-2"></i>
                    LDAP 配置需要服务器端 python-ldap 库支持
                  </div>
                  <div class="mb-3">
                    <label class="form-label">LDAP 服务器</label>
                    <input type="text" id="ldap-server" class="form-control" placeholder="ldap://ldap.example.com:389">
                  </div>
                  <div class="mb-3">
                    <label class="form-label">管理员 DN</label>
                    <input type="text" id="ldap-bind-dn" class="form-control" placeholder="cn=admin,dc=example,dc=com">
                  </div>
                  <div class="mb-3">
                    <label class="form-label">管理员密码</label>
                    <input type="password" id="ldap-bind-password" class="form-control">
                  </div>
                  <div class="mb-3">
                    <label class="form-label">用户搜索基础 DN</label>
                    <input type="text" id="ldap-search-base" class="form-control" placeholder="ou=users,dc=example,dc=com">
                  </div>
                </div>
                
                <div class="mt-4">
                  <button type="button" class="btn btn-primary" onclick="enterprisePage.saveSSO()">
                    <i class="fas fa-save me-2"></i>保存配置
                  </button>
                  ${ssoStatus.enabled 
                    ? `<button type="button" class="btn btn-warning ms-2" onclick="enterprisePage.disableSSO()">
                         <i class="fas fa-ban me-2"></i>禁用 SSO
                       </button>`
                    : `<button type="button" class="btn btn-success ms-2" onclick="enterprisePage.enableSSO()">
                         <i class="fas fa-check me-2"></i>启用 SSO
                       </button>`
                  }
                </div>
              </div>
            </div>
          </div>
        </div>
      `;
    },
    
    async renderTenantsTab() {
      let tenants = { tenants: [], total: 0 };
      
      try {
        tenants = await api.get('/enterprise/tenants');
      } catch (e) {
        console.error('Failed to load tenants:', e);
      }
      
      return `
        <div class="tab-content-inner">
          <div class="card">
            <div class="card-header d-flex justify-content-between align-items-center">
              <h5 class="mb-0"><i class="fas fa-building me-2"></i>租户管理</h5>
              <button class="btn btn-sm btn-primary" onclick="enterprisePage.showCreateTenantModal()">
                <i class="fas fa-plus me-2"></i>创建租户
              </button>
            </div>
            <div class="card-body">
              ${tenants.total === 0 
                ? `<div class="text-center text-muted py-5">
                     <i class="fas fa-building fa-3x mb-3"></i>
                     <p>暂无租户</p>
                   </div>`
                : `<div class="table-responsive">
                     <table class="table table-hover">
                       <thead>
                         <tr>
                           <th>名称</th>
                           <th>标识</th>
                           <th>套餐</th>
                           <th>状态</th>
                           <th>创建时间</th>
                           <th>操作</th>
                         </tr>
                       </thead>
                       <tbody>
                         ${tenants.tenants.map(t => `
                           <tr>
                             <td>${t.name}</td>
                             <td><code>${t.slug}</code></td>
                             <td><span class="badge bg-info">${t.plan}</span></td>
                             <td><span class="badge ${t.status === 'active' ? 'bg-success' : 'bg-secondary'}">${t.status}</span></td>
                             <td>${new Date(t.created_at).toLocaleDateString()}</td>
                             <td>
                               <button class="btn btn-sm btn-outline-primary" onclick="enterprisePage.editTenant('${t.id}')">
                                 配置
                               </button>
                               <button class="btn btn-sm btn-outline-danger" onclick="enterprisePage.deleteTenant('${t.id}')">
                                 删除
                               </button>
                             </td>
                           </tr>
                         `).join('')}
                       </tbody>
                     </table>
                   </div>`
              }
            </div>
          </div>
        </div>
      `;
    },
    
    async renderAuditTab() {
      const today = new Date();
      const weekAgo = new Date(today.getTime() - 7 * 24 * 60 * 60 * 1000);
      
      return `
        <div class="tab-content-inner">
          <div class="card mb-4">
            <div class="card-header">
              <h5 class="mb-0"><i class="fas fa-chart-pie me-2"></i>审计摘要</h5>
            </div>
            <div class="card-body">
              <div class="row g-3 mb-4">
                <div class="col-md-3">
                  <label class="form-label">开始日期</label>
                  <input type="date" id="audit-start" class="form-control" 
                         value="${weekAgo.toISOString().split('T')[0]}">
                </div>
                <div class="col-md-3">
                  <label class="form-label">结束日期</label>
                  <input type="date" id="audit-end" class="form-control" 
                         value="${today.toISOString().split('T')[0]}">
                </div>
                <div class="col-md-3 align-self-end">
                  <button class="btn btn-primary" onclick="enterprisePage.loadAuditSummary()">
                    <i class="fas fa-search me-2"></i>查询
                  </button>
                </div>
              </div>
              
              <div id="audit-summary-content">
                <div class="text-center text-muted py-5">
                  <i class="fas fa-chart-bar fa-3x mb-3"></i>
                  <p>点击查询按钮加载审计数据</p>
                </div>
              </div>
            </div>
          </div>
          
          <div class="card mb-4">
            <div class="card-header">
              <h5 class="mb-0"><i class="fas fa-bell me-2"></i>安全告警</h5>
            </div>
            <div class="card-body">
              <div id="audit-alerts-content">
                <div class="text-center text-muted py-4">
                  暂无告警
                </div>
              </div>
            </div>
          </div>
          
          <div class="card">
            <div class="card-header d-flex justify-content-between align-items-center">
              <h5 class="mb-0"><i class="fas fa-file-alt me-2"></i>报表导出</h5>
              <button class="btn btn-sm btn-outline-primary" onclick="enterprisePage.exportReport()">
                <i class="fas fa-download me-2"></i>导出报表
              </button>
            </div>
            <div class="card-body">
              <p class="text-muted">生成并导出指定时间范围的审计报表 (JSON 或 CSV 格式)</p>
            </div>
          </div>
        </div>
      `;
    },
    
    bindEvents() {
      // Tab switching
      document.querySelectorAll('.enterprise-tabs .nav-link').forEach(link => {
        link.addEventListener('click', (e) => {
          e.preventDefault();
          const tab = e.target.closest('.nav-link').dataset.tab;
          this.switchTab(tab);
        });
      });
      
      // SSO provider change
      const ssoProvider = document.getElementById('sso-provider');
      if (ssoProvider) {
        ssoProvider.addEventListener('change', (e) => {
          this.showSSOConfig(e.target.value);
        });
      }
    },
    
    switchTab(tab) {
      this.currentTab = tab;
      
      document.querySelectorAll('.enterprise-tabs .nav-link').forEach(link => {
        link.classList.remove('active');
      });
      document.querySelector(`.enterprise-tabs .nav-link[data-tab="${tab}"]`)?.classList.add('active');
      
      document.querySelectorAll('.tab-pane').forEach(pane => {
        pane.classList.remove('active');
      });
      document.getElementById(`tab-${tab}`)?.classList.add('active');
    },
    
    showSSOConfig(provider) {
      document.querySelectorAll('.sso-config-section').forEach(el => {
        el.style.display = 'none';
      });
      
      if (provider === 'oidc' || provider === 'azure_ad') {
        document.getElementById('oidc-config').style.display = 'block';
      } else if (provider === 'ldap') {
        document.getElementById('ldap-config').style.display = 'block';
      }
    },
    
    async saveSSO() {
      const provider = document.getElementById('sso-provider')?.value;
      if (!provider) {
        showToast('请选择 SSO 提供商', 'error');
        return;
      }
      
      let config = { provider };
      
      if (provider === 'oidc' || provider === 'azure_ad') {
        config = {
          ...config,
          client_id: document.getElementById('sso-client-id')?.value,
          client_secret: document.getElementById('sso-client-secret')?.value,
          authority: document.getElementById('sso-authority')?.value,
          auto_provision: document.getElementById('sso-auto-provision')?.checked,
          default_role: document.getElementById('sso-default-role')?.value,
          scopes: ['openid', 'profile', 'email']
        };
      } else if (provider === 'ldap') {
        config = {
          ...config,
          server: document.getElementById('ldap-server')?.value,
          bind_dn: document.getElementById('ldap-bind-dn')?.value,
          bind_password: document.getElementById('ldap-bind-password')?.value,
          search_base: document.getElementById('ldap-search-base')?.value
        };
      }
      
      try {
        await api.post('/enterprise/sso/configure', config);
        showToast('SSO 配置已保存');
      } catch (e) {
        showToast('保存失败: ' + (e.message || '未知错误'), 'error');
      }
    },
    
    async enableSSO() {
      try {
        await api.post('/enterprise/sso/enable');
        showToast('SSO 已启用');
        this.loadPage();
      } catch (e) {
        showToast('启用失败', 'error');
      }
    },
    
    async disableSSO() {
      try {
        await api.post('/enterprise/sso/disable');
        showToast('SSO 已禁用');
        this.loadPage();
      } catch (e) {
        showToast('禁用失败', 'error');
      }
    },
    
    async loadAuditSummary() {
      const startDate = document.getElementById('audit-start')?.value;
      const endDate = document.getElementById('audit-end')?.value;
      
      if (!startDate || !endDate) {
        showToast('请选择日期范围', 'error');
        return;
      }
      
      try {
        const summary = await api.get(`/enterprise/audit/summary?start_date=${startDate}&end_date=${endDate}`);
        const alerts = await api.get(`/enterprise/audit/alerts?start_date=${startDate}&end_date=${endDate}`);
        
        this.renderAuditSummary(summary, alerts);
      } catch (e) {
        showToast('加载失败', 'error');
      }
    },
    
    renderAuditSummary(summary, alerts) {
      const container = document.getElementById('audit-summary-content');
      if (!container) return;
      
      container.innerHTML = `
        <div class="row mb-4">
          <div class="col-md-3">
            <div class="stat-box">
              <div class="stat-value">${summary.total_events || 0}</div>
              <div class="stat-label">总事件数</div>
            </div>
          </div>
          <div class="col-md-3">
            <div class="stat-box ${summary.error_rate > 0.05 ? 'warning' : ''}">
              <div class="stat-value">${((summary.error_rate || 0) * 100).toFixed(1)}%</div>
              <div class="stat-label">错误率</div>
            </div>
          </div>
          <div class="col-md-3">
            <div class="stat-box">
              <div class="stat-value">${summary.events_by_category ? Object.keys(summary.events_by_category).length : 0}</div>
              <div class="stat-label">事件类型</div>
            </div>
          </div>
          <div class="col-md-3">
            <div class="stat-box ${(alerts.total || 0) > 0 ? 'warning' : 'success'}">
              <div class="stat-value">${alerts.total || 0}</div>
              <div class="stat-label">安全告警</div>
            </div>
          </div>
        </div>
        
        <div class="row">
          <div class="col-md-6">
            <h6>按级别分布</h6>
            <div class="level-bars">
              ${Object.entries(summary.events_by_level || {}).map(([level, count]) => `
                <div class="level-bar-item">
                  <span class="level-label">${level}</span>
                  <div class="level-bar">
                    <div class="level-bar-fill level-${level.toLowerCase()}" 
                         style="width: ${(count / summary.total_events * 100).toFixed(1)}%"></div>
                  </div>
                  <span class="level-count">${count}</span>
                </div>
              `).join('')}
            </div>
          </div>
          <div class="col-md-6">
            <h6>Top 用户</h6>
            <ul class="list-group">
              ${(summary.top_users || []).slice(0, 5).map(u => `
                <li class="list-group-item d-flex justify-content-between align-items-center">
                  ${u.user}
                  <span class="badge bg-primary rounded-pill">${u.count}</span>
                </li>
              `).join('') || '<li class="list-group-item">暂无数据</li>'}
            </ul>
          </div>
        </div>
      `;
      
      // Render alerts
      const alertsContainer = document.getElementById('audit-alerts-content');
      if (alertsContainer && alerts.alerts && alerts.alerts.length > 0) {
        alertsContainer.innerHTML = alerts.alerts.map(a => `
          <div class="alert alert-${a.severity === 'HIGH' ? 'danger' : a.severity === 'MEDIUM' ? 'warning' : 'info'}">
            <div class="d-flex justify-content-between">
              <div>
                <strong>${a.type}</strong>: ${a.description}
              </div>
              <small>${new Date(a.timestamp).toLocaleString()}</small>
            </div>
          </div>
        `).join('');
      }
    },
    
    async exportReport() {
      const startDate = document.getElementById('audit-start')?.value;
      const endDate = document.getElementById('audit-end')?.value;
      
      if (!startDate || !endDate) {
        showToast('请先查询数据', 'error');
        return;
      }
      
      try {
        const report = await api.post('/enterprise/audit/report', {
          start_date: startDate,
          end_date: endDate,
          format: 'json'
        });
        
        const blob = new Blob([JSON.stringify(report, null, 2)], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `audit-report-${startDate}-${endDate}.json`;
        a.click();
        
        showToast('报表已导出');
      } catch (e) {
        showToast('导出失败', 'error');
      }
    },
    
    showCreateTenantModal() {
      const dialog = createDialog(`
        <h5>创建租户</h5>
        <form id="create-tenant-form">
          <div class="mb-3">
            <label class="form-label">租户名称</label>
            <input type="text" id="tenant-name" class="form-control" required>
          </div>
          <div class="mb-3">
            <label class="form-label">租户标识 (slug)</label>
            <input type="text" id="tenant-slug" class="form-control" required 
                   placeholder="唯一标识，用于URL">
          </div>
          <div class="mb-3">
            <label class="form-label">套餐</label>
            <select id="tenant-plan" class="form-select">
              <option value="free">免费版</option>
              <option value="basic">基础版</option>
              <option value="pro">专业版</option>
              <option value="enterprise">企业版</option>
            </select>
          </div>
          <div class="d-flex justify-content-end gap-2">
            <button type="button" class="btn btn-secondary" onclick="closeDialog()">取消</button>
            <button type="submit" class="btn btn-primary">创建</button>
          </div>
        </form>
      `);
      
      document.getElementById('create-tenant-form').addEventListener('submit', async (e) => {
        e.preventDefault();
        
        try {
          await api.post('/enterprise/tenants', {
            name: document.getElementById('tenant-name').value,
            slug: document.getElementById('tenant-slug').value,
            plan: document.getElementById('tenant-plan').value
          });
          
          showToast('租户创建成功');
          closeDialog();
          this.loadPage();
        } catch (e) {
          showToast('创建失败', 'error');
        }
      });
    },
    
    editTenant(tenantId) {
      showToast('租户配置功能开发中...', 'info');
    },
    
    async deleteTenant(tenantId) {
      if (!confirm('确定要删除此租户吗？')) return;
      
      try {
        await api.delete(`/enterprise/tenants/${tenantId}`);
        showToast('租户已删除');
        this.loadPage();
      } catch (e) {
        showToast('删除失败', 'error');
      }
    }
  };

  // Register page
  window.EnterprisePage = EnterprisePage;
  window.enterprisePage = EnterprisePage;

})();
