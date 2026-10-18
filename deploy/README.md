# AI-NAS V7.0 部署脚本

本目录包含 AI-NAS V7.0 的自动化部署脚本，支持传统部署方式（pip + venv + systemd）。

## 脚本说明

| 脚本 | 用途 | 使用方式 |
|------|------|---------|
| `install.sh` | 一键安装 | `sudo bash install.sh` |
| `update.sh` | 升级 + 自动回滚 | `sudo bash update.sh <pkg.tar.gz>` |
| `rollback.sh` | 手动回滚 | `sudo bash rollback.sh [backup_path]` |
| `uninstall.sh` | 卸载 | `sudo bash uninstall.sh` |
| `check-health.sh` | 健康检查 | `bash check-health.sh` |

## 安装流程

```bash
# 1. 下载或复制 AI-NAS V7.0 代码到服务器
# 2. 进入 deploy 目录
cd /path/to/AI-NAS-V7.0.0/deploy

# 3. 执行安装
sudo bash install.sh
```

安装完成后：
- 安装目录：`/opt/ai-nas/`
- 数据目录：`/data/ai-nas/`
- 服务名称：`ai-nas`
- 默认端口：`8000`

## 管理命令

```bash
# 启动服务
sudo systemctl start ai-nas

# 停止服务
sudo systemctl stop ai-nas

# 重启服务
sudo systemctl restart ai-nas

# 查看日志
sudo journalctl -u ai-nas -f

# 查看状态
sudo systemctl status ai-nas
```

## 升级流程

```bash
# 1. 打包新版本
cd /path/to/AI-NAS-V7.0.0
tar -czf ai-nas-v7.0.1.tar.gz backend/ frontend/ migrations/

# 2. 上传到服务器并执行升级
sudo bash deploy/update.sh ai-nas-v7.0.1.tar.gz
```

升级失败会自动回滚。

## 环境变量

可通过环境变量自定义安装：

```bash
INSTALL_DIR=/opt/ai-nas-custom \
DATA_DIR=/data/ai-nas-custom \
PORT=8080 \
sudo bash install.sh
```

## 支持的系统

- Ubuntu 20.04+
- Debian 11+
- CentOS 8+
- 群晖 DSM 7.0+
- 其他支持 systemd 的 Linux 发行版

## 架构支持

- x86_64 (Intel/AMD)
- aarch64 (ARM 64位，如树莓派 4、Jetson)
- armv7l (ARM 32位，部分功能受限)
