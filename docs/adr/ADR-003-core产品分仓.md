# ADR-003: core/产品分仓策略

- **状态**：已接受
- **日期**：2026-10-18
- **决策者**：项目负责人

## 背景

多形态并行最大的风险是"每款产品各做一遍轮子"，历史上已因 4 份代码拷贝各自漂移造成大量重复维护。需要决定共享代码的组织方式。

## 决策

采用 **core/产品分仓**（非 Monorepo）：

```
D:\pro1\ainas\
├── ainas-core/    共享底座：auth / storage / ai-engine / media-pipeline / plugin-sdk
└── ainas-nas/     产品仓（即当前 D:\pro1\ainas 的代码），引用 core
```

- core 通过 git tag 分发：产品仓 `pip install git+<repo>@v1.2.0`，requirements 精确锁 `==`
- 暂不搭私有 PyPI，消费者超过 3 个再升级

## 分仓三铁律（防代码漂移）

1. 产品仓**禁止 vendor/copy core 源码**，只准 pinned 依赖引用；CI 加重复度检查
2. core 发 minor/patch 前，CI 必须触发下游产品仓跑契约测试
3. 产品仓升级 core = 一次显式 PR，必须带契约测试 + 冒烟结果
4. nightly：产品仓对 core 最新 rc 跑契约测试，破坏性变更在 rc 阶段暴露

## 理由

- 与用户既有工作习惯一致（分仓）
- token-relay-service 的鉴权能力沉入 core，作为统一鉴权组件，不独立成产品
- 分仓的代价（两次 PR、版本协调）由上述机制压低

## 后果

- 当前 `D:\pro1\ainas` 即 ainas-nas 产品仓本体，core 抽离在底座功能稳定后执行
- 若后续协调成本超过收益，可改回 Monorepo——本 ADR 即退路记录
- 契约测试套件需在 core 独立时同步建立
