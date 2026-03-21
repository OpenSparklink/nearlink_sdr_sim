# 标准条款映射

本文列出 nearlink-sdr 各模块与 TXS-10002-2025 SparkLink SLE 标准条款的对应关系。

## 第 6 章 SLE 非连接模式物理层

| 条款 | 内容 | 实现模块 | 状态 |
|------|------|----------|------|
| 6.2.1.1 | GFSK 调制 | `phy.gfsk` | 完成 |
| 6.2.1.2 | PSK 调制 (BPSK/QPSK/8PSK) | `phy.psk` | 完成 |
| 6.2.1.3 | 多音信号 | `phy.multitone` | 完成 |
| 6.2.1.4 | UWB 脉冲波形与芯片调制 | `phy.uwb_pulse` | 完成 |
| 6.3 | 帧结构 | `phy.frame` | 完成 |
| 6.4 | 物理层控制信息 | `phy.control_info` | 完成 |
| 6.5 | 同步信号 1/2 | `phy.sync_sequence` | 完成 |
| 6.5.1 | QoS 服务质量管理 (ARQ/HARQ/流控) | `mac.qos` | 完成 |
| 6.5.1-6.5.3 | 异步/同步数据链路传输规程 | `phy.data_link` | 完成 |
| 6.6 | 系统管理帧编解码 | `mac.smf` | 完成 |
| 6.6.3 | 系统管理帧发送调度 | `mac.smf_scheduler` | 完成 |
| 6.6 | 同步信号 3/4 | `phy.sync_sequence` | 完成 |
| 6.7 | 导频 | `phy.pilot` | 完成 |
| 6.7/6.8 | 窄带/UWB 测量链路传输参数与调度 | `phy.measurement_tx` | 完成 |
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
| 6.2.3.5 | 同步信号 5 (GFSK 安全随机) | `phy.sync_sequence` | 完成 |
| 6.2.3.6 | 同步信号 6 (BPSK 安全随机) | `phy.sync_sequence` | 完成 |
| 6.2.4 | 位置信息测量信号 | `phy.measurement` | 完成 |
| 6.3.6 | 半可靠组播反馈 | `phy.measurement_frame` | 完成 |
| 6.3.7-6.3.10 | 测量帧类型 1-4 | `phy.measurement_frame` | 完成 |
| 6.3.11 | 超宽带脉冲测量帧 | `phy.measurement_frame` | 完成 |

## 第 8 章 SLE 非连接模式物理层过程

| 条款 | 内容 | 实现模块 | 状态 |
|------|------|----------|------|
| 8.1.1 | 应用频段 | `phy.freq_hopping` | 完成 |
| 8.1.2 | 频率管理 | `phy.freq_hopping` | 完成 |
| 8.2.1 | 输出功率等级 | `phy.rf_compliance` | 完成 |
| 8.2.2 | 调制精度 (GFSK频偏/PSK EVM/频率容限/时钟) | `phy.rf_compliance` | 完成 |
| 8.2.3 | 无用发射 (GFSK杂散/PSK频谱模板) | `phy.rf_compliance` | 完成 |
| 8.3.1 | 接收灵敏度与最大输入电平 | `phy.rf_compliance` | 完成 |
| 8.3.2 | 接收机选择性 | `phy.rf_compliance` | 完成 |
| 8.3.3 | 接收机杂散发射 | `phy.rf_compliance` | 完成 |
| 8.3.4 | RSSI 测量精度 | `phy.rf_compliance` | 完成 |
| 8.3.5 | PRBS 序列 | `common.prbs` | 完成 |
| 8.4 | UWB 射频 (信道/频谱/NRMSE) | `phy.rf_compliance` | 完成 |

## 附录 H 测试向量

| 测试向量 | 内容 | 验证状态 |
|----------|------|----------|
| TV101 | PRBS11 种子 -> 比特 -> CRC -> 加扰 | 完成, 全流程匹配 |
| TV201 | FT2 MCS5 QPSK 基准链路 | 完成, pipeline 验证 |
| TV202 | FT2 MCS7 QPSK 多码块 | 完成, pipeline 验证 |
| TV203 | FT2 MCS7 测试向量 | 完成 |
| TV205 | FT2 MCS6 小载荷 | 完成, pipeline + loopback 验证 |
| TV206 | FT2 MCS6 大载荷 | 完成, pipeline 验证 |
| TV207 | FT2 测试向量 | 完成 |
| TV209 | FT2 MCS11 8PSK | 完成, pipeline + loopback 验证 |
| TV213 | FT2 测试向量 | 完成 |

## 第 6.10 章 物理层处理流水线

| 条款 | 内容 | 实现模块 | 状态 |
|------|------|----------|------|
| 6.10 | TX 发射流水线 | `phy.tx_pipeline` | 完成, FT1-4 全帧类型 |
| 6.10 | RX 接收流水线 | `phy.rx_pipeline` | 完成, FT1-4 全帧类型 |

## 待实现条款

以下条款尚未完全实现, 不影响核心 SLE 通信:

- 多用户干扰/Doppler 时变信道仿真

## 第 7 章 MAC 层

### 7.1 广播与链路管理

| 条款 | 内容 | 实现模块 | 状态 |
|------|------|----------|------|
| 7.1.3 | 接入流程 | `mac.access` | 完成 |
| 7.1.4 | 广播帧结构 | `mac.broadcast` | 完成 |
| 7.1.4.1-7 | 广播帧子信息 (资源配置/接入) | `mac.broadcast` | 完成 |
| 7.1.4.3/8/9 | 广播帧子信息 (扩展) | `mac.broadcast` | 完成 |
| 7.1.4.10 | 非链接态窄带跳频测量配置 | `mac.broadcast` | 完成 |
| 7.1.4.11 | 非链接态超宽带脉冲测量配置 | `mac.broadcast` | 完成 |
| 7.1.5 | 广播帧过滤 | `mac.broadcast` | 完成 |
| 7.1.6 | 接入白名单 | `mac.access` | 完成 |
| 7.1.7 | 广播帧控制交互 (角色协商/非链接态广播) | `mac.access` | 完成 |
| 7.1/7.2 | 链路管理状态机 | `mac.link_manager` | 完成 |

### 7.2 链路管理流程

| 条款 | 内容 | 实现模块 | 状态 |
|------|------|----------|------|
| 7.2.1 | 收发间隔参数更新 | `mac.link_manager` | 完成 |
| 7.2.2 | 多级收发间隔参数更新 | `mac.link_control` | 完成 |
| 7.2.3 | 加密/密钥更新流程 | `mac.security_manager` | 完成 |
| 7.2.4 | 特性交互 | `mac.link_manager` | 完成 |
| 7.2.5 | 版本交互 | `mac.link_manager` | 完成 |
| 7.2.6 | 数据长度更新 | `mac.link_manager` | 完成 |
| 7.2.7 | 信道质量上报配置 | `mac.link_manager` | 完成 |
| 7.2.8 | 跳频表更新 | `mac.link_manager` | 完成 |
| 7.2.9 | 跳频地图更新 | `mac.link_manager` | 完成 |
| 7.2.10 | 最少可用信道 | `mac.link_manager` | 完成 |
| 7.2.11 | CRC 切换 | `mac.link_manager` | 完成 |
| 7.2.12 | 物理层更新 | `mac.link_manager` | 完成 |
| 7.2.13 | 功率控制流程 | `mac.power_control` | 完成 |
| 7.2.14 | 休眠与唤醒 | `mac.link_manager` | 完成 |
| 7.2.15 | 角色切换 | `mac.link_manager` | 完成 |
| 7.2.16 | PING 流程 | `mac.link_manager` | 完成 |
| 7.2.17 | 链路断开 | `mac.link_manager` | 完成 |
| 7.2.18 | 异步链路参数更新 | `mac.link_manager` | 完成 |
| 7.2.19 | 同步等时链路管理 | `mac.link_manager` | 完成 |
| 7.2.20 | 广播链路管理 | `mac.link_manager` | 完成 |
| 7.2.21 | 系统管理帧链路管理 | `mac.link_manager` | 完成 |
| 7.2.22 | 异步组播链路管理 | `mac.link_manager` | 完成 |
| 7.2.23 | 窄带跳频测量 | `mac.link_manager` | 完成 |
| 7.2.24 | 超宽带脉冲测量与感知 | `mac.link_manager` | 完成 |
| 7.2.25 | 窄带跳频感知 | `mac.link_manager` | 完成 |

### 7.2 功率控制

| 条款 | 内容 | 实现模块 | 状态 |
|------|------|----------|------|
| 7.2.13 | 功率控制流程 | `mac.power_control` | 完成 |
| 7.3.2.27 | PowerControlRequest 信令 | `mac.power_control` | 完成 |
| 7.3.2.28 | PowerControlResponse 信令 | `mac.power_control` | 完成 |
| 7.3.2.29 | PowerChangeIndication 信令 | `mac.power_control` | 完成 |

### 7.3 帧结构与信令

| 条款 | 内容 | 实现模块 | 状态 |
|------|------|----------|------|
| 7.3.2 | 控制面帧结构 | `mac.frame` | 完成 |
| 7.3.3 | 数据面帧结构 | `mac.frame` | 完成 |
| 7.3.4 | 复用帧 | `mac.frame` | 完成 |
| 7.3 | 信令注册与编解码 | `mac.signaling` | 完成 |

### 7.3.2 链路控制信令 (112 个类型)

| 条款范围 | 内容 | 实现模块 | 状态 |
|----------|------|----------|------|
| 7.3.2.2-2.5 | 收发间隔更新 | `mac.link_control` | 完成 |
| 7.3.2.6-2.11 | 安全流程 | `mac.link_control` | 完成 |
| 7.3.2.14 | 未知特性反馈 | `mac.link_control` | 完成 |
| 7.3.2.19-2.22 | 信道管理 | `mac.link_control` | 完成 |
| 7.3.2.25-2.26 | PHY 更新 | `mac.link_control` | 完成 |
| 7.3.2.33-2.34 | 异步链路参数重配置 | `mac.link_control` | 完成 |
| 7.3.2.35-2.36 | 异步链路参数更新 | `mac.link_control` | 完成 |
| 7.3.2.37-2.41 | 同步等时链路 | `mac.link_control` | 完成 |
| 7.3.2.42-2.44 | 广播链路 | `mac.link_control` | 完成 |
| 7.3.2.45 | 广播链路断开 | `mac.link_control` | 完成 |
| 7.3.2.46-2.49 | 系统管理帧 | `mac.link_control` | 完成 |
| 7.3.2.50 | 5G 信道状态/跳频地图 | `mac.link_control` | 完成 |
| 7.3.2.51-2.55 | 角色切换/PING/时间偏移 | `mac.link_control` | 完成 |
| 7.3.2.56-2.58 | 多间隔更新 | `mac.link_control` | 完成 |
| 7.3.2.59 | 系统时间指示 | `mac.link_control` | 完成 |
| 7.3.2.60-2.65 | 异步组播链路管理 | `mac.link_control` | 完成 |
| 7.3.2.62-2.63 | 超时更新/组播断开 | `mac.link_control` | 完成 |
| 7.3.2.66-2.73 | 窄带跳频测量 | `mac.link_control` | 完成 |
| 7.3.2.74-2.76 | 坐标管理 | `mac.link_control` | 完成 |
| 7.3.2.77-2.78 | 窄带时延 | `mac.link_control` | 完成 |
| 7.3.2.79 | 异步 TT 链路建链 | `mac.link_control` | 完成 |
| 7.3.2.80-2.84 | UWB 脉冲测量 | `mac.link_control` | 完成 |
| 7.3.2.85-2.90 | UWB 感知 | `mac.link_control` | 完成 |
| 7.3.2.91-2.92 | 资源预留 | `mac.link_control` | 完成 |
| 7.3.2.93-2.107 | 窄带感知 | `mac.link_control` | 完成 |
| 7.3.2.108-2.114 | 配置更新与 UWB 扩展感知 | `mac.link_control` | 完成 |

### 第 9 章 安全子系统

| 条款 | 内容 | 实现模块 | 状态 |
|------|------|----------|------|
| 9.2 | 配对信令 (16 个消息类型) | `mac.security` | 完成 |
| 9.3 | 密钥派生 (KDF/CMAC/AES) | `mac.crypto` | 完成 |
| 9.3.2 | 组播安全信令 | `mac.security` | 完成 |
| 9.3.3 | 安全信息分发 (IRK/地址) | `mac.security` | 完成 |
| 9.4 | AES-CCM 帧加密 | `mac.crypto` | 完成 |
| 9.5 | UWB 脉冲测量安全 | `phy.uwb_measurement_security` | 完成 |
| 9.2-9.4 | 安全流程集成 (配对+加密) | `mac.security_manager` | 完成 |

### 时序调度

| 内容 | 实现模块 | 状态 |
|------|----------|------|
| 时序调度器 (6.3/6.6/7.2) | `mac.scheduler` | 完成 |
| 接入流程管理 (7.1.3) | `mac.access` | 完成 |

### 仿真与集成

| 内容 | 实现模块 | 状态 |
|------|----------|------|
| MAC-PHY 集成适配层 | `phy.mac_interface` | 完成 |
| 全链路 Pipeline 仿真 (Phase 1-8) | `sim.link_sim` | 完成 |
| MAC 帧级端到端仿真 (Phase 9) | `sim.link_sim` | 完成 |
| 多链路调度仿真 (Phase 10) | `sim.link_sim` | 完成 |
| 接入→配对→加密端到端仿真 (Phase 11) | `sim.link_sim` | 完成 |
| AMC + HARQ + 跳频多径仿真 (Phase 12) | `sim.link_sim` | 完成 |
| QoS ARQ / AMC 自适应 / 流控仿真 (Phase 13) | `sim.link_sim` | 完成 |
| SLE 节点实体 (统一收发接口) | `node` | 完成 |
| SleNode 集成仿真 (Phase 15) | `sim.link_sim` | 完成 |
| USRP 环回仿真引擎 | `sim.usrp_sim` | 完成 |

### 一致性测试

| 章节 | 内容 | 测试模块 | 状态 |
|------|------|----------|------|
| 10-11 | 协议一致性测试 (FT1-FT4/控制面/流程) | `tests/conformance/test_protocol.py` | 完成 |
| 12 | 射频一致性测试 (TX/RX/UWB) | `tests/conformance/test_rf.py` | 完成 |
| 13 | 安全一致性测试 (配对/加密/隐私/UWB) | `tests/conformance/test_security.py` | 完成 |
