// AI-NAS Media Manager - Devices Page
import { api } from '../api.js';
import { showToast } from '../utils.js';

export class DevicesPage {
    constructor() {
        this.container = document.getElementById('page-devices');
    }

    async load() {
        try {
            const devices = await api.getDevices();
            this.render(devices);
        } catch (e) {
            console.error('加载设备失败:', e);
            showToast('加载设备失败: ' + e.message, 'danger');
        }
    }

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
                        <strong>${d.device_name || d.device_id}</strong>
                        <small class="text-muted ms-2">${d.ip_address || '-'}</small>
                    </div>
                    <div>
                        <button class="btn btn-sm btn-outline-primary" onclick="devicesPage.testDevice('${d.device_id}')">
                            <i class="fas fa-plug"></i> 测试
                        </button>
                        <button class="btn btn-sm btn-outline-danger" onclick="devicesPage.removeDevice('${d.device_id}')">
                            <i class="fas fa-trash"></i>
                        </button>
                    </div>
                </div>
                <div class="mt-2 small text-muted">
                    NPU: ${d.npu_type || '-'} | CPU: ${d.cpu_usage || 0}% | 存储: ${d.storage_usage || 0}%
                </div>
            </div>
        `).join('');
    }

    showAddModal() {
        document.getElementById('device-id').value = '';
        document.getElementById('device-name').value = '';
        document.getElementById('device-ip').value = '';
        document.getElementById('device-port').value = '8000';
        new bootstrap.Modal(document.getElementById('addDeviceModal')).show();
    }

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
            showToast('请填写设备ID和IP地址', 'warning');
            return;
        }

        try {
            await api.addDevice(device);
            bootstrap.Modal.getInstance(document.getElementById('addDeviceModal')).hide();
            showToast('设备添加成功', 'success');
            this.load();
        } catch (e) {
            showToast('添加失败: ' + e.message, 'danger');
        }
    }

    async testDevice(deviceId) {
        try {
            const res = await api.testDevice(deviceId);
            showToast(res.status === 'success' ? '设备连接正常' : '设备连接失败',
                res.status === 'success' ? 'success' : 'danger');
        } catch (e) {
            showToast('测试失败: ' + e.message, 'danger');
        }
    }

    async removeDevice(deviceId) {
        if (!confirm('确定要删除这个设备吗？')) return;
        try {
            await api.deleteDevice(deviceId);
            showToast('设备已删除', 'success');
            this.load();
        } catch (e) {
            showToast('删除失败: ' + e.message, 'danger');
        }
    }
}

export const devicesPage = new DevicesPage();
window.devicesPage = devicesPage;
