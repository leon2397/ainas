/**
 * AI-NAS Media Manager - Devices Module
 * 设备管理模块
 */

const Devices = {
    // 加载设备列表
    async load() {
        try {
            const devices = await API.get('/api/devices/');
            this.render(devices);

        } catch (e) {
            console.error('加载设备失败:', e);
        }
    },

    // 渲染设备列表
    render(devices) {
        const container = document.getElementById('devices-list');

        if (!devices || devices.length === 0) {
            container.innerHTML = `
                <div class="text-center text-muted py-5">
                    <i class="fas fa-microchip fa-3x mb-3"></i>
                    <p>暂无设备</p>
                </div>
            `;
            return;
        }

        container.innerHTML = devices.map(d => `
            <div class="device-card">
                <div class="d-flex justify-content-between align-items-center">
                    <div>
                        <span class="device-status ${d.status === 'online' ? 'online' : 'offline'}"></span>
                        <strong>${Utils.escapeHtml(d.device_name || d.device_id)}</strong>
                        <small class="text-muted ms-2">${d.ip_address || '-'}</small>
                    </div>
                    <div>
                        <button class="btn btn-sm btn-outline-primary" onclick="Devices.test('${d.device_id}')">
                            <i class="fas fa-plug"></i> 测试
                        </button>
                        <button class="btn btn-sm btn-outline-danger" onclick="Devices.remove('${d.device_id}')">
                            <i class="fas fa-trash"></i>
                        </button>
                    </div>
                </div>
                <div class="mt-2 small text-muted">
                    NPU: ${d.npu_type || '-'} | 
                    CPU: ${d.cpu_usage || 0}% | 
                    存储: ${d.storage_usage || 0}%
                </div>
            </div>
        `).join('');
    },

    // 显示添加设备弹窗
    showAddModal() {
        document.getElementById('device-id').value = '';
        document.getElementById('device-name').value = '';
        document.getElementById('device-ip').value = '';
        document.getElementById('device-port').value = '8000';
        new bootstrap.Modal(document.getElementById('addDeviceModal')).show();
    },

    // 添加设备
    async add() {
        const device = {
            device_id: document.getElementById('device-id').value,
            device_name: document.getElementById('device-name').value,
            ip: document.getElementById('device-ip').value,
            port: parseInt(document.getElementById('device-port').value) || 8000,
            npu_type: document.getElementById('device-npu').value,
            ai_plugin: 'default',
            storage_plugin: 'default'
        };

        if (!device.device_id || !device.ip) {
            Utils.showToast('请填写设备ID和IP地址', 'warning');
            return;
        }

        try {
            await API.post('/api/devices/add', device);
            bootstrap.Modal.getInstance(document.getElementById('addDeviceModal')).hide();
            Utils.showToast('设备添加成功', 'success');
            this.load();

        } catch (e) {
            Utils.showToast('添加失败: ' + e.message, 'danger');
        }
    },

    // 测试设备连接
    async test(deviceId) {
        try {
            const res = await API.get(`/api/devices/${deviceId}/test`);
            Utils.showToast(
                res.status === 'success' ? '设备连接正常' : '设备连接失败',
                res.status === 'success' ? 'success' : 'danger'
            );

        } catch (e) {
            Utils.showToast('测试失败: ' + e.message, 'danger');
        }
    },

    // 删除设备
    async remove(deviceId) {
        if (!confirm('确定要删除这个设备吗？')) return;

        try {
            await API.delete(`/api/devices/${deviceId}`);
            Utils.showToast('设备已删除', 'success');
            this.load();

        } catch (e) {
            Utils.showToast('删除失败: ' + e.message, 'danger');
        }
    }
};

// 导出
window.Devices = Devices;
