# AI-NAS Media Manager - ARM 设备真机测试计划

> 📅 创建日期：2026-04-08
> 📝 制定人：香蕉3 🍌
> 🎯 目标：完成 Phase 1 真机测试，验证生产就绪状态

---

## 📋 测试环境

| 项目 | 内容 |
|------|------|
| **设备型号** | Jetson Nano |
| **IP 地址** | 192.168.1.123 |
| **用户名** | nvidia |
| **密码** | nvidia |
| **架构** | aarch64 (ARM64) |
| **Python** | 3.8 |
| **服务端口** | 9999 |

---

## ✅ 已完成测试（2026-04-07）

| 测试项 | 结果 | 说明 |
|--------|------|------|
| 服务启动 | ✅ 通过 | arm_server.py 正常启动 |
| 端口配置 | ✅ 修复 | 改为 9999 避免冲突 |
| 依赖安装 | ✅ 通过 | requirements_arm.txt 安装成功 |
| 日志路径 | ✅ 修复 | 改为 ./logs 避免权限问题 |

---

## 📝 待测试清单

### Part 1: 基础连通性测试（5分钟）

```bash
# 1.1 SSH 登录
ssh nvidia@192.168.1.123
# 密码: nvidia

# 1.2 检查服务状态
curl http://localhost:9999/health

# 1.3 检查系统资源
free -h
df -h
```

**预期结果：**
- health 返回 `{"status": "healthy", ...}`
- 内存剩余 > 500MB
- 磁盘剩余 > 5GB

---

### Part 2: API 功能测试（15分钟）

```bash
# 2.1 健康检查
curl http://192.168.1.123:9999/health

# 2.2 设备信息
curl http://192.168.1.123:9999/api/device/info

# 2.3 NPU 状态
curl http://192.168.1.123:9999/api/ai/accelerator/status

# 2.4 可用加速器列表
curl http://192.168.1.123:9999/api/ai/accelerator/available

# 2.5 系统状态
curl http://192.168.1.123:9999/api/monitor/status
```

**预期结果：**
- 所有 API 返回 JSON 格式
- NPU 状态显示 `cuda` 或 `cpu`（Jetson 支持 CUDA）

---

### Part 3: 媒体扫描测试（20分钟）

```bash
# 3.1 创建测试目录
mkdir -p ~/test_media/photos
mkdir -p ~/test_media/videos

# 3.2 下载测试图片（如果没有）
# 可从 Windows 复制或下载样本图片

# 3.3 触发媒体扫描
curl -X POST http://192.168.1.123:9999/api/media/scan \
  -H "Content-Type: application/json" \
  -d '{"path": "/home/nvidia/test_media/photos"}'

# 3.4 查看扫描结果
curl http://192.168.1.123:9999/api/media/list

# 3.5 查看扫描任务状态
curl http://192.168.1.123:9999/api/tasks
```

**预期结果：**
- 扫描任务创建成功
- 媒体列表返回扫描到的文件
- 任务状态显示完成

---

### Part 4: AI 分类测试（20分钟）

```bash
# 4.1 检查 AI 引擎状态
curl http://192.168.1.123:9999/api/ai/status

# 4.2 单张图片分类测试
curl -X POST http://192.168.1.123:9999/api/ai/classify \
  -H "Content-Type: application/json" \
  -d '{"media_id": 1}'

# 4.3 批量分类测试
curl -X POST http://192.168.1.123:9999/api/actions/batch/ai \
  -H "Content-Type: application/json" \
  -d '{"media_ids": [1, 2, 3]}'

# 4.4 查看分类结果
curl http://192.168.1.123:9999/api/media/1
```

**预期结果：**
- AI 分类返回标签（如 "cat", "outdoor", "nature"）
- 批量分类任务正常执行
- 结果保存到数据库

---

### Part 5: 缩略图生成测试（10分钟）

```bash
# 5.1 触发缩略图生成
curl -X POST http://192.168.1.123:9999/api/media/thumbnail \
  -H "Content-Type: application/json" \
  -d '{"media_id": 1}'

# 5.2 检查缩略图文件
ls -la ~/ai-nas/arm/.thumbnails/

# 5.3 获取缩略图
curl http://192.168.1.123:9999/api/media/1/thumbnail --output thumb.jpg
```

**预期结果：**
- 缩略图文件生成成功
- 文件大小合理（10-100KB）
- 可正常下载查看

---

### Part 6: 与 Windows 主控端联调测试（15分钟）

**前提：Windows 端服务已启动（端口 8000）**

```bash
# 6.1 在 Windows 端检查设备发现
curl http://localhost:8000/api/devices/

# 6.2 检查 ARM 设备是否出现在设备列表
# 预期返回包含 192.168.1.123 的设备信息

# 6.3 测试心跳监控
# 等待 30 秒后再次查询设备状态
curl http://localhost:8000/api/devices/

# 6.4 测试任务分发（从 Windows 端下发任务到 ARM）
curl -X POST http://localhost:8000/api/tasks \
  -H "Content-Type: application/json" \
  -d '{"type": "scan", "device_id": "arm-192.168.1.123", "params": {"path": "/home/nvidia/test_media"}}'
```

**预期结果：**
- Windows 端能发现 ARM 设备
- 设备状态显示 "online"
- 任务能下发到 ARM 执行

---

### Part 7: 性能压力测试（15分钟）

```bash
# 7.1 CPU 压力测试
stress --cpu 4 --timeout 60 &
# 观察服务响应时间
curl -w "%{time_total}\n" http://192.168.1.123:9999/health

# 7.2 内存使用监控
watch -n 5 free -h

# 7.3 并发请求测试
for i in {1..10}; do
  curl http://192.168.1.123:9999/api/media/list &
done
wait

# 7.4 长时间运行测试
# 让服务运行 1 小时后检查是否有内存泄漏
```

**预期结果：**
- CPU 压力下响应时间 < 2秒
- 内存使用稳定，无持续增长
- 并发请求全部成功

---

## 📊 测试检查表

| # | 测试项 | 预期结果 | 实际结果 | 状态 |
|---|--------|----------|----------|------|
| 1 | SSH 登录 | 成功 | | ☐ |
| 2 | 服务健康检查 | 200 OK | | ☐ |
| 3 | API 响应 | JSON 格式 | | ☐ |
| 4 | 媒体扫描 | 识别文件 | | ☐ |
| 5 | AI 分类 | 返回标签 | | ☐ |
| 6 | 缩略图生成 | 文件生成 | | ☐ |
| 7 | 设备发现 | Windows 可见 | | ☐ |
| 8 | 心跳监控 | 状态更新 | | ☐ |
| 9 | 任务分发 | 远程执行 | | ☐ |
| 10 | CPU 压力 | 响应正常 | | ☐ |
| 11 | 内存稳定 | 无泄漏 | | ☐ |
| 12 | 并发请求 | 全部成功 | | ☐ |

---

## 🐛 已知问题（2026-04-07 修复）

| # | 问题 | 解决方案 | 状态 |
|---|------|----------|------|
| 1 | uvicorn[standard] 需要 uvloop | 改用 uvicorn>=0.23.0 | ✅ |
| 2 | exceptiongroup 缺失 | 添加到 packages | ✅ |
| 3 | typing_extensions 版本过旧 | 升级到 4.13.2 | ✅ |
| 4 | /var/log 需要 sudo | 改用 ./logs | ✅ |
| 5 | FileHandler 不支持 maxBytes | 改用 RotatingFileHandler | ✅ |
| 6 | 端口 8000/8001/8080 冲突 | 默认端口改为 9999 | ✅ |

---

## 📁 相关文件

| 文件 | 路径 | 说明 |
|------|------|------|
| ARM 服务 | arm/arm_server.py | 主服务文件 |
| ARM 配置 | arm/config.yaml | 设备配置 |
| ARM 依赖 | arm/requirements_arm.txt | Python 依赖 |
| 部署指南 | arm/DEPLOY.md | 详细部署步骤 |

---

## 🚀 测试完成后

测试全部通过后：
1. 更新备忘录 Phase 1 状态为 ✅ 完成
2. 标记 V6.0.3 为生产就绪版本
3. 准备正式发布 V7.0（或直接发布 V6.0.3 正式版）

---

*🍌 香蕉3 为 橘子8 准备 | 2026-04-08*
