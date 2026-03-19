# 标准条款映射

本文列出 nearlink-sdr 各模块与 TXS-10002-2025 SparkLink SLE 标准条款的对应关系。

## 第 6 章 SLE 非连接模式物理层

| 条款 | 内容 | 实现模块 | 状态 |
|------|------|----------|------|
| 6.2.1.1 | GFSK 调制 | `phy.gfsk` | 完成 |
| 6.2.1.2 | PSK 调制 (BPSK/QPSK/8PSK) | `phy.psk` | 完成 |
| 6.3 | 帧结构 | `phy.frame` | 完成 |
| 6.4 | 物理层控制信息 | `phy.control_info` | 完成 |
| 6.5 | 同步信号 1/2 | `phy.sync_sequence` | 完成 |
| 6.6 | 同步信号 3/4 | `phy.sync_sequence` | 完成 |
| 6.7 | 导频 | `phy.pilot` | 完成 |
| 6.9 | CRC | `common.crc` | 完成 |
| 6.9.1.2 | 码块分割 (无 CRC) | `common.code_block_seg` | 完成 |
| 6.9.1.3 | 码块分割 (含 CRC) | `common.code_block_seg` | 完成 |
| 6.10.1 | Polar 编码 | `common.polar` | 完成 |
| 6.10.2 | 速率匹配 | `common.polar` | 完成 |
| 6.10.3 | 跳频 | `phy.freq_hopping` | 完成 |
| 6.10.4 | 加扰 | `common.scrambler` | 完成 |
| 6.10.5 | MCS | `common.mcs` | 完成 |
| 6.10.6 | 速率自适应 | `common.mcs` | 完成 |
| 6.11 | BCH 编码 | `common.bch` | 完成 |

## 第 8 章 SLE 非连接模式物理层过程

| 条款 | 内容 | 实现模块 | 状态 |
|------|------|----------|------|
| 8.1.2 | 频率管理 | `phy.freq_hopping` | 完成 |
| 8.3.5 | PRBS 序列 | `common.prbs` | 完成 |

## 附录 H 测试向量

| 测试向量 | 内容 | 验证状态 |
|----------|------|----------|
| TV101 | PRBS11 种子 -> 比特 -> CRC -> 加扰 | 完成, 全流程匹配 |

## 待实现条款

以下条款尚未实现, 按优先级排列:

- 6.8: 功率控制
- 6.3 帧类型完整的头部编码 (Polar 编码控制信息)
- 第 7 章: 连接模式物理层
- 第 9 章: MAC 层协议
