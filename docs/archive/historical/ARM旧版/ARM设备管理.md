# AI-NAS Media Manager - ARM 设备管理

> 📅 创建日期：2026-04-08
> 👑 梨子7 与 橘子8 开启
> 🎯 目标：管理多个 ARM 设备，实现分布式媒体处理

---

## 📊 当前已注册设备

| 设备ID | 设备名称 | IP 地址 | 端口 | NPU 类型 | 状态 | 注册时间 |
|--------|----------|---------|------|----------|------|----------|
| jetson-nano-001 | Jetson Nano | 192.168.1.123 | 9999 | jetson-nano | ✅ 在线 | 2026-04-08 |

---

## 🖥️ 设备详细信息

### 设备 1: Jetson Nano (jetson-nano-001)

| 项目 | 内容 |
|------|------|
| **设备型号** | Jetson Nano |
| **架构** | aarch64 (ARM64) |
| **IP 地址** | 192.168.1.123 |
| **服务端口** | 9999 |
| **用户名** | nvidia |
| **密码** | nvidia |
| **Python** | 3.8 |
| **CPU 核心数** | 6 |
| **总内存** | 6.7 GB |
| **可用内存** | 1.9 GB (2026-04-08 测试) |
| **存储路径** | /nas |

#### 服务状态
| 服务 | 状态 | 启动命令 |
|------|------|----------|
| arm_server.py | ✅ 运行中 | `python arm_server.py` |
| systemd 服务 | ✅ 已配置 | `sudo systemctl start ai-nas-arm` |

#### 已验证功能
- ✅ 健康检查 (`/health`)
- ✅ 设备信息 (`/device/info`)
- ✅ AI 分类 (`/api/ai/classify`)
- ✅ 媒体扫描 (`/api/media/scan`)
- ✅ Windows 联调测试通过

#### 部署文件
| 文件 | 路径 | 说明 |
|------|------|------|
| 服务入口 | `arm/arm_server.py` | 主服务文件 |
| 配置文件 | `arm/config.yaml` | 设备配置 |
| 依赖文件 | `arm/requirements_arm.txt` | Python 依赖 |
| systemd | `arm/ai-nas-arm.service` | 系统服务 |
| 部署脚本 | `arm/setup.sh` | 一键部署 |

---

## 🔧 设备管理操作

### 添加新设备

**方式 1: API 手动添加**
```powershell
$body = @{
    device_id = "设备ID"
    device_name = "设备名称"
    ip = "IP地址"
    port = 9999
    username = ""
    password = ""
    npu_type = "jetson-nano"  # 或 rk3588, bm1688, cpu
    ai_plugin = "cpu"
    storage_plugin = "local"
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://localhost:8000/api/devices/add" -Method POST -Body $body -ContentType "application/json"
```

**方式 2: 设备自动注册**
ARM 设备启动时会自动向 Windows 主控端注册，需配置 `config/devices.yaml`。

### 查看设备列表
```powershell
Invoke-RestMethod -Uri "http://localhost:8000/api/devices/" | ConvertTo-Json
```

### 测试设备连接
```powershell
Invoke-RestMethod -Uri "http://localhost:8000/api/devices/{device_id}/test" -Method POST | ConvertTo-Json
```

### 删除设备
```powershell
Invoke-RestMethod -Uri "http://localhost:8000/api/devices/{device_id}" -Method DELETE
```

---

## 🚀 ARM 设备部署指南

### 前置条件
- ARM 设备已联网
- Python 3.8+ 已安装
- pip 已安装

### 一键部署
```bash
# 1. 复制 arm/ 目录到设备
scp -r arm/ nvidia@192.168.1.123:~/ai-nas/

# 2. SSH 登录设备
ssh nvidia@192.168.1.123

# 3. 执行部署脚本
cd ~/ai-nas/arm
chmod +x setup.sh
./setup.sh

# 4. 启动服务
python arm_server.py
# 或使用 systemd
sudo systemctl start ai-nas-arm
```

### 手动部署
```bash
# 1. 安装依赖
pip install -r requirements_arm.txt

# 2. 创建必要目录
mkdir -p logs data/thumbnails

# 3. 修改配置
vim config.yaml  # 设置端口、存储路径等

# 4. 启动服务
python arm_server.py
```

---

## 🔗 设备与 Windows 主控端联调

### 启动顺序
1. **先启动 ARM 设备端**：`python arm_server.py`
2. **再启动 Windows 主控端**：`python main.py`
3. **添加设备**：调用 `/api/devices/add` 或等待自动发现

### 验证联调
```powershell
# 1. 检查 Windows 主控端
Invoke-RestMethod -Uri "http://localhost:8000/api/monitor/status"

# 2. 检查 ARM 设备端
Invoke-RestMethod -Uri "http://192.168.1.123:9999/health"

# 3. 测试设备连接
Invoke-RestMethod -Uri "http://localhost:8000/api/devices/jetson-nano-001/test" -Method POST

# 4. 查看设备信息
Invoke-RestMethod -Uri "http://localhost:8000/api/devices/jetson-nano-001/info"
```

---

## 📊 支持的 NPU 类型

| NPU 类型 | 设备型号 | AI 引擎 | 说明 |
|----------|----------|---------|------|
| `jetson-nano` | Jetson Nano | CUDA | NVIDIA Jetson 系列 |
| `rk3588` | RK3588 | RKNN | 瑞芯微 NPU |
| `bm1688` | BM1688 | TPU | 比特大陆 NPU |
| `cpu` | 通用 | CPU | 纯 CPU 后备 |

---

## ⚠️ 已知问题与解决方案

| 问题 | 原因 | 解决方案 |
|------|------|----------|
| 端口冲突 | 8000/8080 被占用 | 改用 9999 端口 |
| 日志权限 | /var/log 需要 sudo | 改用 ./logs 目录 |
| uvloop 缺失 | ARM 不支持 uvloop | 使用 requirements_arm.txt |
| typing_extensions 版本 | 版本过旧 | 升级到 4.13.2+ |
| venv 路径硬编码 | Junction 链接问题 | 使用 `python -m pip` 安装 |

---

## 📁 相关文档

| 文档 | 路径 | 说明 |
|------|------|------|
| 部署指南 | `arm/DEPLOY.md` | 详细部署步骤 |
| 测试计划 | `docs/ARM真机测试计划.md` | 测试用例 |
| 配置说明 | `arm/config.yaml` | 设备配置 |

---

## 📝 维护日志

| 日期 | 操作 | 结果 |
|------|------|------|
| 2026-04-08 | Jetson Nano 真机测试 | ✅ 通过 |
| 2026-04-08 | Windows 联调测试 | ✅ 通过 |
| 2026-04-08 | 设备注册 | ✅ jetson-nano-001 已添加 |

---

*🍌 香蕉3 维护 | 2026-04-08*
