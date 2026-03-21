# 设计说明

本章节从协议总览到各子系统逐层深入，解释 SparkLink SLE 标准的设计原理与项目的实现方式。

```{toctree}
:maxdepth: 2

overview
principles
physical-layer
mac-layer
security
data-flow
architecture
standard-mapping
```

## 阅读顺序建议

1. [协议总览](overview.md) — 频段、帧结构、协议栈全貌
2. [物理层原理](principles.md) — Polar 编码、PSK/GFSK 调制、信道模型等核心算法的数学推导
3. [物理层实现](physical-layer.md) — 调制解调、帧结构、同步、导频
4. [MAC 层](mac-layer.md) — 链路管理、信令、安全流程、QoS
5. [安全子系统](security.md) — 配对、加密、密钥分发
6. [端到端数据流](data-flow.md) — TX→信道→RX 的完整处理链
7. [系统架构](architecture.md) — 模块划分与依赖关系
8. [标准对标](standard-mapping.md) — 代码实现与 TXS-10002-2025 条款的映射
