# AINAS API 文档

> 版本：v1.0.0 | 更新日期：2026-10-18
> **运行时为准**：本文是人工维护的参考；接口如有变动，以运行中的 `/openapi.json` 与 `/docs`（Swagger UI）输出为准。
> 当前规模：197 个 API 路径（101 GET + 96 POST）。

---

# AI-NAS Media Manager - API 文档

## 基础信息

- **Base URL**: `http://localhost:8000`
- **WebSocket**: `ws://localhost:8000/ws`
- **API 文档**: `http://localhost:8000/docs`

## 通用响应格式

```json
// 成功
{
  "id": 1,
  "file_path": "/path/to/file.jpg",
  "status": "success"
}

// 错误
{
  "error": "错误信息"
}

// 列表
[
  {"id": 1, "name": "item1"},
  {"id": 2, "name": "item2"}
]
```

---

## 媒体文件 API `/api/media`

### 列出媒体文件
```
GET /api/media/
```
参数:
- `skip`: int, 跳过数量 (默认 0)
- `limit`: int, 返回数量 (默认 50, 最大 500)
- `file_type`: string, 过滤类型 (image/video)
- `device_id`: string, 设备ID

### 获取媒体详情
```
GET /api/media/{file_id}
```

### 搜索媒体
```
GET /api/media/search/?keyword=关键词
```
参数:
- `keyword`: string, 搜索关键词
- `file_type`: string, 可选过滤
- `limit`: int, 最大返回数

### 按日期获取
```
GET /api/media/date/{year}?month=月份
```

### 上传媒体
```
POST /api/media/upload
```
参数:
- `file`: 文件 (form-data)
- `device_id`: string

### 更新标签
```
POST /api/media/update-tags
```
Body:
```json
{
  "file_id": 1,
  "tags": ["风景", "户外", "日落"]
}
```

### 删除媒体
```
DELETE /api/media/{file_id}
```

---

## 相册 API `/api/albums`

### 列出相册
```
GET /api/albums/?album_type=类型
```
类型: person/scene/date/custom

### 获取相册详情
```
GET /api/albums/{album_id}
```

### 获取相册文件
```
GET /api/albums/{album_id}/files
```

### 创建相册
```
POST /api/albums/
```
Body:
```json
{
  "name": "我的相册",
  "album_type": "custom"
}
```

### 添加文件到相册
```
POST /api/albums/add-files
```
Body:
```json
{
  "album_id": 1,
  "file_ids": [1, 2, 3]
}
```

### 删除相册
```
DELETE /api/albums/{album_id}
```

---

## 设备 API `/api/devices`

### 列出设备
```
GET /api/devices/
```

### 获取在线设备
```
GET /api/devices/online
```

### 获取设备详情
```
GET /api/devices/{device_id}
```

### 获取设备信息 (实时)
```
GET /api/devices/{device_id}/info
```

### 添加设备
```
POST /api/devices/add
```
Body:
```json
{
  "device_id": "arm-01",
  "device_name": "BM1688 NAS",
  "ip": "192.168.1.100",
  "port": 8000,
  "npu_type": "bm1688"
}
```

### 设备心跳
```
POST /api/devices/heartbeat?device_id=xxx&cpu_usage=30&npu_usage=50
```

### 删除设备
```
DELETE /api/devices/{device_id}
```

### 测试连接
```
POST /api/devices/{device_id}/test
```

---

## 任务 API `/api/tasks`

### 列出任务
```
GET /api/tasks/?status=pending&limit=50
```
状态: pending/running/success/failed

### 获取任务详情
```
GET /api/tasks/{task_id}
```

### 提交任务结果
```
POST /api/tasks/{task_id}/result
```
Body:
```json
{
  "status": "success",
  "result": {"processed": 100}
}
```

### 更新任务进度
```
POST /api/tasks/{task_id}/progress?progress=50
```

### 取消任务
```
DELETE /api/tasks/{task_id}
```

---

## 操作 API `/api/actions`

### 扫描媒体
```
POST /api/actions/scan
```
Body:
```json
{
  "path": "C:\\Users\\Pictures",
  "recursive": true
}
```

### AI 分类
```
POST /api/actions/classify
```
Body:
```json
{
  "file_id": null,
  "device_id": null,
  "force": false
}
```

### 人脸检测
```
POST /api/actions/classify/face?file_id=1
```

### 去重
```
POST /api/actions/dedup
```
Body:
```json
{
  "scope_path": null,
  "threshold": 0.85,
  "method": "hash"
}
```

### 去重统计
```
GET /api/actions/dedup/stats
```

---

## 设备发现 API `/api/discovery`

### 列出发现的设备
```
GET /api/discovery/devices
```

### 列出在线设备
```
GET /api/discovery/devices/online
```

### 注册设备
```
POST /api/discovery/devices/{device_id}/register
```

### 启动发现服务
```
POST /api/discovery/start
```

### 停止发现服务
```
POST /api/discovery/stop
```

---

## WebSocket `/ws`

### 连接
```javascript
const ws = new WebSocket('ws://localhost:8000/ws');
```

### 订阅
```json
{"type": "subscribe", "channel": "all"}
```

### 接收消息

任务更新:
```json
{
  "type": "task_update",
  "data": {
    "task_id": "xxx",
    "status": "running",
    "progress": 50
  }
}
```

设备状态:
```json
{
  "type": "device_status",
  "data": {
    "device_id": "arm-01",
    "status": "online",
    "cpu_usage": 30
  }
}
```

媒体更新:
```json
{
  "type": "media_update",
  "data": {
    "action": "add",
    "file": {"id": 1, "name": "xxx"}
  }
}
```

---

## 系统 API

### 健康检查
```
GET /health
```

### 系统状态
```
GET /status
```

### 根路由
```
GET /
```
