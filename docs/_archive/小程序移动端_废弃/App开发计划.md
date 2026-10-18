# AI-NAS Media Manager - Android App 开发计划

> 📅 制定日期：2026-04-07
> 📝 制定人：梨子7 🍐
> 👤 确认人：橘子8 🍊
> 📱 平台：**Android Only** ✅
> 🛠️ 技术选型：Flutter

---

## 🎯 项目目标

开发一款 **AI-NAS 移动端 App**，提供比小程序更完整的 NAS 管理体验，支持：
- 照片/视频自动备份
- 离线浏览
- 后台同步
- 系统级推送
- 更流畅的交互体验

---

## 📊 技术选型分析

| 方案 | 优点 | 缺点 | 推荐度 |
|------|------|------|--------|
| **Flutter** | 一套代码双端、性能好、生态成熟 | 包体积稍大 | ⭐⭐⭐⭐⭐ |
| React Native | 生态丰富、JS开发者多 | 性能略逊、配置复杂 | ⭐⭐⭐⭐ |
| 原生开发 | 性能最佳 | 成本高、维护难 | ⭐⭐⭐ |
| UniApp | 开发快、成本低 | 性能一般、定制受限 | ⭐⭐⭐ |

**最终选择：Flutter 3.x（Android Only）**
- ✅ 专注 Android 端开发
- ✅ 无需 Apple 开发者账号（$99/年）
- ✅ 无需 Mac 电脑
- ✅ 审核更快、更灵活
- ✅ 接近原生性能
- ✅ 热重载开发效率高
- ✅ 丰富的 UI 组件库

---

## 📋 功能模块规划

### 核心功能（MVP - 3周）

| 模块 | 功能点 | 优先级 | 工作量 |
|------|--------|--------|--------|
| **登录认证** | JWT Token 管理、自动登录、Token刷新 | ⭐⭐⭐ | 2天 |
| **媒体浏览** | 照片/视频列表、缩略图、详情查看 | ⭐⭐⭐ | 3天 |
| **相册管理** | 相册列表、创建/编辑相册、照片添加 | ⭐⭐⭐ | 2天 |
| **自动备份** | 后台自动上传新照片、WiFi-only选项 | ⭐⭐⭐ | 3天 |
| **设备管理** | 查看NAS设备状态、存储空间 | ⭐⭐ | 1天 |
| **设置** | 服务器地址、备份设置、关于 | ⭐⭐ | 1天 |

### 增强功能（V2.0 - 2周）

| 模块 | 功能点 | 优先级 | 工作量 |
|------|--------|--------|--------|
| **离线模式** | 本地缓存、离线浏览已下载内容 | ⭐⭐⭐ | 3天 |
| **推送通知** | 新照片提醒、备份完成通知、存储告警 | ⭐⭐ | 2天 |
| **搜索** | 全局搜索照片/相册/标签 | ⭐⭐ | 2天 |
| **分享** | 生成分享链接、社交分享 | ⭐ | 1天 |
| **深色模式** | 系统跟随/手动切换 | ⭐ | 1天 |

### 高级功能（V3.0 - 2周）

| 模块 | 功能点 | 优先级 | 工作量 |
|------|--------|--------|--------|
| **AI 功能** | 智能分类、人脸识别、场景识别 | ⭐⭐ | 3天 |
| **视频编辑** | 剪辑、滤镜、配乐（简单编辑） | ⭐ | 2天 |
| **多设备同步** | 多NAS设备管理 | ⭐ | 2天 |
| **家庭共享** | 家庭成员管理、权限控制 | ⭐ | 2天 |

---

## 📅 开发时间表

### 第一阶段：MVP（3周）

```
Week 1: 项目搭建 + 登录 + 媒体浏览
├── Day 1-2: 项目初始化、依赖配置、主题设计
├── Day 3-4: 登录认证模块（JWT、Token管理）
└── Day 5-7: 媒体浏览（列表、网格、缩略图）

Week 2: 相册 + 自动备份
├── Day 8-9: 相册列表、创建/编辑
├── Day 10-12: 自动备份（后台任务、上传队列）
└── Day 13-14: 设备管理、设置页面

Week 3: 优化 + 测试 + 打包
├── Day 15-17: UI优化、动画、错误处理
├── Day 18-19: 功能测试、Bug修复
└── Day 20-21: 打包（Android APK / iOS IPA）
```

### 第二阶段：增强功能（2周）

```
Week 4: 离线 + 推送
├── Day 22-24: 本地数据库（SQLite）、缓存策略
├── Day 25-26: 离线浏览实现
└── Day 27-28: 推送通知（Firebase/极光）

Week 5: 搜索 + 分享 + 深色模式
├── Day 29-30: 全局搜索
├── Day 31: 分享功能
└── Day 32-35: 深色模式、UI优化、测试
```

### 第三阶段：高级功能（2周）

```
Week 6-7: AI + 视频 + 多设备
├── AI功能集成
├── 视频编辑基础
├── 多设备管理
└── 家庭共享
```

---

## 🏗️ 技术架构

### 项目结构

```
ainas_app/
├── android/              # Android 原生配置
├── ios/                  # iOS 原生配置
├── lib/
│   ├── main.dart         # 应用入口
│   ├── app.dart          # 应用配置
│   ├── config/           # 配置常量
│   │   ├── api.dart      # API地址
│   │   ├── theme.dart    # 主题配置
│   │   └── constants.dart # 常量
│   ├── models/           # 数据模型
│   │   ├── media.dart    # 媒体文件
│   │   ├── album.dart    # 相册
│   │   ├── user.dart     # 用户
│   │   └── device.dart   # 设备
│   ├── services/         # 业务服务
│   │   ├── api_service.dart      # HTTP客户端
│   │   ├── auth_service.dart     # 认证服务
│   │   ├── media_service.dart    # 媒体服务
│   │   ├── backup_service.dart   # 备份服务
│   │   └── storage_service.dart  # 本地存储
│   ├── providers/        # 状态管理（Riverpod）
│   │   ├── auth_provider.dart
│   │   ├── media_provider.dart
│   │   └── backup_provider.dart
│   ├── screens/          # 页面
│   │   ├── splash/       # 启动页
│   │   ├── login/        # 登录
│   │   ├── home/         # 首页
│   │   ├── media/        # 媒体浏览
│   │   ├── album/        # 相册
│   │   ├── backup/       # 备份设置
│   │   ├── device/       # 设备管理
│   │   └── settings/     # 设置
│   ├── widgets/          # 公共组件
│   │   ├── common/       # 通用组件
│   │   ├── media/        # 媒体相关
│   │   └── loading/      # 加载状态
│   └── utils/            # 工具函数
│       ├── date_util.dart
│       ├── file_util.dart
│       └── validators.dart
├── assets/               # 静态资源
│   ├── images/
│   ├── icons/
│   └── fonts/
├── test/                 # 单元测试
└── pubspec.yaml          # 依赖配置
```

### 依赖库选择

| 功能 | 库名 | 说明 |
|------|------|------|
| 状态管理 | `flutter_riverpod` | 响应式状态管理 |
| HTTP请求 | `dio` | 强大的HTTP客户端 |
| 本地存储 | `hive` | 高性能NoSQL数据库 |
| 图片加载 | `cached_network_image` | 网络图片缓存 |
| 图片选择 | `image_picker` | 相册/相机选择 |
| 权限管理 | `permission_handler` | 权限申请 |
| 后台任务 | `workmanager` | 定时/后台任务 |
| 推送通知 | `firebase_messaging` | FCM推送 |
| 视频播放 | `video_player` | 视频播放 |
| 本地通知 | `flutter_local_notifications` | 本地通知 |
| 路径管理 | `path_provider` | 文件路径 |
| 设备信息 | `device_info_plus` | 设备信息 |

---

## 🎨 UI/UX 设计规范

### 设计原则

1. **简洁直观** - 减少认知负担
2. **快速响应** - 操作反馈即时
3. **一致性** - 统一的设计语言
4. **可访问性** - 支持大屏/小屏/无障碍

### 色彩方案

```dart
// 主色调
const primaryColor = Color(0xFF6366F1);      // 靛蓝
const primaryLight = Color(0xFF818CF8);      // 浅靛蓝
const primaryDark = Color(0xFF4F46E5);       // 深靛蓝

// 辅助色
const successColor = Color(0xFF10B981);      // 绿色
const warningColor = Color(0xFFF59E0B);      // 橙色
const errorColor = Color(0xFFEF4444);        // 红色
const infoColor = Color(0xFF3B82F6);         // 蓝色

// 中性色
const backgroundColor = Color(0xFFF9FAFB);   // 背景
const surfaceColor = Colors.white;           // 卡片
const textPrimary = Color(0xFF111827);       // 主文字
const textSecondary = Color(0xFF6B7280);     // 次要文字
```

### 页面结构

```
┌─────────────────────────────────┐
│  Status Bar                     │
├─────────────────────────────────┤
│  App Bar (标题 + 操作按钮)       │
├─────────────────────────────────┤
│                                 │
│         Body Content            │
│         (可滚动内容区)           │
│                                 │
├─────────────────────────────────┤
│  Bottom Navigation Bar          │
│  (首页 | 相册 | 备份 | 设置)     │
└─────────────────────────────────┘
```

---

## 🔌 API 对接

### 认证相关

```dart
// 登录
POST /api/auth/login
Body: { "username": "", "password": "" }
Response: { "access_token": "", "token_type": "bearer" }

// Token刷新
POST /api/auth/refresh
Headers: Authorization: Bearer {token}
Response: { "access_token": "", "token_type": "bearer" }
```

### 媒体相关

```dart
// 获取媒体列表
GET /api/media?skip=0&limit=50&type=image
Headers: Authorization: Bearer {token}

// 获取缩略图
GET /api/media/{id}/thumbnail

// 上传文件
POST /api/media/upload
Body: multipart/form-data
```

### 相册相关

```dart
// 获取相册列表
GET /api/albums

// 创建相册
POST /api/albums
Body: { "name": "", "description": "" }

// 添加照片到相册
POST /api/albums/{id}/media
Body: { "media_ids": [] }
```

---

## 📱 发布计划

### Android 发布

| 阶段 | 时间 | 内容 |
|------|------|------|
| 内测 | Week 3 | 生成 APK，内部测试 |
| 公测 | Week 5 | 上架 Google Play Beta |
| 正式 | Week 6 | 上架 Google Play、华为、小米等 |

---

## ✅ Android Only 优势

| 对比项 | Android Only | iOS + Android |
|--------|--------------|---------------|
| **开发成本** | ¥20,000-30,000 | ¥35,000-50,000 |
| **开发周期** | 3周 MVP | 5周 MVP |
| **开发者账号** | $25（一次性） | $99/年 + $25 |
| **审核时间** | 1-3天 | 1-2周 |
| **上架渠道** | 华为/小米/应用宝等 | 仅 App Store |
| **后台限制** | 较宽松 | 严格限制 |
| **自动备份** | 可实现 | 受限 |

---

## 💰 成本估算

### 开发成本

| 项目 | 费用 | 说明 |
|------|------|------|
| 开发人员 | ¥15,000-30,000 | 3周 MVP 开发 |
| UI设计 | ¥3,000-5,000 | 界面设计 |
| 测试 | ¥2,000-3,000 | 功能测试 |
| **总计** | **¥20,000-38,000** | MVP阶段 |

### 运营成本（年）

| 项目 | 费用 | 说明 |
|------|------|------|
| Google Play | $25 | 一次性（可选）|
| 推送服务 | ¥0-5,000 | 极光/FCM |
| 云存储 | ¥0-2,000 | 热更新、统计 |
| **总计** | **¥1,000-10,000** | |

---

## ⚠️ 风险与应对

| 风险 | 影响 | 应对措施 |
|------|------|----------|
| Flutter版本升级 | 中 | 锁定版本，定期升级 |
| iOS审核被拒 | 中 | 提前阅读审核指南 |
| 后台任务限制 | 高 | 使用系统推荐方案，做好降级 |
| 大文件上传超时 | 中 | 分片上传、断点续传 |
| 不同Android厂商差异 | 中 | 充分测试主流机型 |

---

## ✅ 里程碑

| 里程碑 | 时间 | 交付物 |
|--------|------|--------|
| M1 | Week 1 结束 | 项目框架 + 登录 + 媒体列表 |
| M2 | Week 2 结束 | 相册 + 自动备份功能完成 |
| M3 | Week 3 结束 | **MVP发布**（Android APK） |
| M4 | Week 5 结束 | 增强功能完成，公测版 |
| M5 | Week 7 结束 | **V1.0正式发布** |

---

## 📝 待确认事项

### ✅ 已确认
- [x] **只做 Android 端**

### ⏳ 待确认

1. **发布方式？**
   - [ ] 仅内部使用（APK直接安装）
   - [ ] 上架应用商店（华为/小米/应用宝）
   - [ ] 两者都做

2. **推送服务选择？**
   - [ ] Firebase（免费，需翻墙）
   - [ ] 极光推送（国内稳定，免费额度）
   - [ ] 不需要推送

3. **预算范围？**
   - [ ] 精简版（¥20,000）- 仅MVP核心功能
   - [ ] 标准版（¥30,000）- MVP + 增强功能
   - [ ] 完整版（¥40,000+）- 全部功能

4. **是否需要我立即开始开发？**
   - [ ] 是，准备环境开始 Week 1
   - [ ] 否，先确认其他事项

---

## 🚀 下一步行动

1. **确认开发范围** - 回答上述待确认事项
2. **准备开发环境** - 安装 Flutter SDK
3. **设计 UI 原型** - 确定界面风格
4. **开始开发** - Week 1 任务

---

*计划制定：梨子7 🍐*
*2026-04-07*
