# AI-NAS V7.0 ECS 部署指南

## 部署方式

由于网络/工具限制，采用**手动部署**方式。

## 前置条件

- ECS 已安装 Python 3.9+
- 已有 V6.0.3 运行环境
- 已备份现有数据

## 部署步骤

### 1. 备份现有部署

```bash
sudo systemctl stop ai-nas
cd /root/ai-nas
sudo tar -czf /tmp/ai-nas-v6-backup-$(date +%Y%m%d).tar.gz backend/ frontend/ config/ deploy/ .env
```

### 2. 上传 V7.0 代码

将本地 `D:\project\NAS\AI-NAS-V7.0.0` 打包上传到 ECS `/root/ai-nas-v7/`:

**方式 A - SCP (推荐)**:
```bash
# 在本地 PowerShell 执行
scp -r D:/project/NAS/AI-NAS-V7.0.0/* root@120.77.249.3:/root/ai-nas-v7/
```

**方式 B - 压缩包上传**:
1. 本地打包: 压缩 `AI-NAS-V7.0.0` 目录
2. 上传到 ECS `/tmp/`
3. ECS 解压: `tar -xzf ai-nas-v7.tar.gz -C /root/ai-nas-v7/`

### 3. 执行安装

```bash
cd /root/ai-nas-v7
sudo bash deploy/install.sh
```

安装脚本会自动：
- 检测架构 (x86_64/aarch64)
- 创建虚拟环境
- 安装依赖
- 初始化数据库
- 注册 systemd 服务
- 启动服务

### 4. 验证部署

```bash
# 检查服务状态
sudo systemctl status ai-nas

# 健康检查
curl http://localhost:8000/health

# 查看日志
sudo journalctl -u ai-nas -f
```

## 目录结构

安装完成后：
```
/opt/ai-nas/           # 安装目录
├── backend/           # 后端代码 (含 modules/)
├── frontend/          # 前端静态文件
├── config/            # 配置文件
├── venv/              # Python 虚拟环境
└── .env               # 环境变量

/data/ai-nas/          # 数据目录
├── media/             # 媒体文件
├── thumbnails/        # 缩略图
├── cache/             # 缓存
├── logs/              # 日志
└── backup/            # 备份
```

## 关键变更 (V6.0.3 → V7.0)

| 变更 | 说明 |
|------|------|
| 模块化架构 | 新增 `backend/modules/` 8个模块 |
| 日志系统 | 统一使用 loguru |
| 异常处理 | 结构化异常类 |
| 部署脚本 | 全新 install/update/uninstall/rollback |

## 回滚方案

如果部署失败：

```bash
# 停止新服务
sudo systemctl stop ai-nas

# 恢复备份
cd /root/ai-nas
sudo rm -rf backend/ frontend/ config/ deploy/
sudo tar -xzf /tmp/ai-nas-v6-backup-XXXX.tar.gz

# 重启原服务
sudo systemctl start ai-nas
```

## 注意事项

1. **端口冲突**: 确保 8000 端口未被占用
2. **防火墙**: 开放 8000 端口 (或配置 nginx 反向代理)
3. **数据迁移**: V6.0.3 数据库兼容 V7.0
4. **Python 版本**: 需要 3.9+

## 联系支持

部署问题请检查日志：
```bash
sudo journalctl -u ai-nas -n 100 --no-pager
```
