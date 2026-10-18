# AINAS 文档中心

> **产品定位**：隐私优先的本地 AI NAS 媒体管理系统
> **当前版本**：v1.0.0（2026-10-18 重建基线，基于 V7.0.0 生产验证版）
> **文档原则**：与代码同仓、随版本快照、内容可追溯

---

## 快速导航

| 你是谁 | 先读什么 |
|--------|----------|
| 新用户，想 5 分钟跑起来 | [QUICKSTART.md](./QUICKSTART.md) |
| 日常使用（浏览/扫描/上传） | [USER_GUIDE.md](./USER_GUIDE.md) |
| 管理员（用户/设置/审计） | [ADMIN_GUIDE.md](./ADMIN_GUIDE.md) |
| 部署到服务器/NAS | [DEPLOYMENT.md](./DEPLOYMENT.md) |
| 开发/二次开发 | [DEVELOPMENT.md](./DEVELOPMENT.md) |
| 调接口 | [API.md](./API.md) 或运行中的 `/docs`（Swagger UI） |
| 出问题了 | [TROUBLESHOOTING.md](./TROUBLESHOOTING.md) |

## 文档结构

```
docs/
├── README.md            ← 你在这里（文档中心导航）
├── QUICKSTART.md        ← 5 分钟运行（本地/Docker 双路径，已实测）
├── USER_GUIDE.md        ← 用户手册：媒体库、扫描接入、上传、相册
├── ADMIN_GUIDE.md       ← 管理员手册：账号、权限、设置、审计日志
├── DEPLOYMENT.md        ← 部署运维：Docker / Linux 一键安装 / K8s
├── ARCHITECTURE.md      ← 架构总览：模块划分、数据流、技术选型
├── DEVELOPMENT.md       ← 开发指南：模块铁律、规范、测试
├── API.md               ← API 参考（以 /openapi.json 运行时输出为准）
├── TROUBLESHOOTING.md   ← 故障排查 + 已知问题 + 历史 BUG 记录
├── adr/                 ← 架构决策记录（为什么这么决定）
│   ├── ADR-001-基底选择.md
│   ├── ADR-002-产品范围收缩.md
│   └── ADR-003-core产品分仓.md
└── archive/             ← 历史归档（V3–V7 时代文档，原样保留，仅供追溯）
```

版本历史见根目录 [CHANGELOG.md](../CHANGELOG.md)。

## 关于 archive/

`archive/` 保存 V3.0–V7.0 开发时期的全部文档（路线图、阶段报告、测试报告、废弃的小程序/ARM 方案等）。它们是**历史资料**，描述的是过去某个时间点的状态，**不代表产品现状**——描述现状请以上方各文档为准。

## 文档维护规则

1. **代码改了，文档同 PR 改**——防止再次出现"文档说谎"（V7 时代曾出现默认密码、NAS_PATH 等文档与代码不符）
2. **不确定时以运行中的 `/openapi.json` 和实际代码为准**，文档描述实现，不反向
3. 每个版本发布时更新根目录 `CHANGELOG.md`，本文档中心的版本号同步刷新
