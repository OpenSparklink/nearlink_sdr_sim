# 技术参考

本节列出项目全部公开模块的接口文档, 内容从源代码注释自动生成。

## 通用模块 (`common`)

| 模块 | 功能 |
|------|------|
| {py:mod}`nearlink_sdr.common.crc` | CRC 校验 |
| {py:mod}`nearlink_sdr.common.m_sequence` | m 序列生成 |
| {py:mod}`nearlink_sdr.common.bch` | BCH 编码 |
| {py:mod}`nearlink_sdr.common.polar` | Polar 编解码 |
| {py:mod}`nearlink_sdr.common.code_block_seg` | 码块分割 |
| {py:mod}`nearlink_sdr.common.scrambler` | 信道比特加扰 |
| {py:mod}`nearlink_sdr.common.mcs` | MCS 与速率匹配 |
| {py:mod}`nearlink_sdr.common.prbs` | PRBS 伪随机序列 |

## 物理层模块 (`phy`)

| 模块 | 功能 |
|------|------|
| {py:mod}`nearlink_sdr.phy.gfsk` | GFSK 调制/解调 |
| {py:mod}`nearlink_sdr.phy.psk` | PSK 调制/解调 |
| {py:mod}`nearlink_sdr.phy.preamble` | 前导码 |
| {py:mod}`nearlink_sdr.phy.sync_sequence` | 同步信号 |
| {py:mod}`nearlink_sdr.phy.pilot` | 导频 |
| {py:mod}`nearlink_sdr.phy.frame` | 帧结构 |
| {py:mod}`nearlink_sdr.phy.control_info` | 控制信息 |
| {py:mod}`nearlink_sdr.phy.tx_pipeline` | TX 发射流水线 |
| {py:mod}`nearlink_sdr.phy.rx_pipeline` | RX 接收流水线 |
| {py:mod}`nearlink_sdr.phy.channel` | 信道模型 |
| {py:mod}`nearlink_sdr.phy.equalizer` | 均衡器 |
| {py:mod}`nearlink_sdr.phy.freq_hopping` | 跳频 |
| {py:mod}`nearlink_sdr.phy.mac_interface` | MAC-PHY 适配层 |
| {py:mod}`nearlink_sdr.phy.measurement` | 位置信息测量信号 |
| {py:mod}`nearlink_sdr.phy.measurement_frame` | 测量帧 |
| {py:mod}`nearlink_sdr.phy.usrp` | USRP 接口 |

## MAC 层模块 (`mac`)

| 模块 | 功能 |
|------|------|
| {py:mod}`nearlink_sdr.mac.frame` | 控制面/数据面/复用帧 |
| {py:mod}`nearlink_sdr.mac.broadcast` | 广播帧 |
| {py:mod}`nearlink_sdr.mac.signaling` | 信令注册与编解码 |
| {py:mod}`nearlink_sdr.mac.link_control` | 链路控制信令 |
| {py:mod}`nearlink_sdr.mac.power_control` | 功率控制 |
| {py:mod}`nearlink_sdr.mac.link_manager` | 链路管理状态机 |
| {py:mod}`nearlink_sdr.mac.access` | 接入流程 |
| {py:mod}`nearlink_sdr.mac.scheduler` | 时序调度器 |
| {py:mod}`nearlink_sdr.mac.security` | 配对信令 |
| {py:mod}`nearlink_sdr.mac.crypto` | 加密与密钥派生 |
| {py:mod}`nearlink_sdr.mac.security_manager` | 安全流程集成 |
| {py:mod}`nearlink_sdr.mac.qos` | QoS 服务质量管理 |

## 仿真模块 (`sim`)

| 模块 | 功能 |
|------|------|
| {py:mod}`nearlink_sdr.sim.link_sim` | 链路仿真 |

## 完整 API 文档

```{toctree}
:maxdepth: 2

/apidocs/nearlink_sdr/nearlink_sdr
```
