# 系统架构

nearlink-sdr 是一个链路级仿真系统, 实现了 TXS-10002-2025 SparkLink SLE 标准定义的物理层处理链路。本文说明系统的整体结构和设计思路。

## 模块组织

系统分为四个子包:

```
nearlink_sdr/
├── common/      信道编码与底层算法
├── phy/         物理层信号处理
├── mac/         MAC 层协议
└── sim/         链路仿真入口
```

### common -- 信道编码

| 模块 | 功能 | 标准条款 |
|------|------|----------|
| `crc` | CRC12/24A/24B/32 校验 | 6.9 (6.10.1) |
| `bch` | BCH(31,26) / BCH(63,24) 编码 | 6.11 |
| `polar` | Polar 编码, SC 解码 | 6.10.1 |
| `code_block_seg` | 码块分割 | 6.9.1.2 / 6.9.1.3 |
| `m_sequence` | m31/m63 序列生成 | 6.11 |
| `scrambler` | 信道比特加扰 (Galois LFSR) | 6.10.4 |
| `mcs` | MCS 表与速率匹配 | 6.10.5 / 6.10.6 |
| `prbs` | PRBS11/PRBS17 伪随机序列 | 8.3.5 |

### phy -- 物理层

| 模块 | 功能 | 标准条款 |
|------|------|----------|
| `gfsk` | GFSK 调制/解调 | 6.2.1.1 |
| `psk` | BPSK/QPSK/8PSK, RRC 脉冲成型 | 6.2.1.2 |
| `preamble` | 前导码生成 | 6.4 |
| `sync_sequence` | 同步信号 1-6 | 6.5/6.6/6.2.3 |
| `pilot` | 导频符号插入与移除 | 6.7 |
| `frame` | 帧结构组装/解析 (类型 1-4) | 6.3 |
| `control_info` | A1-A7/B1-B5 物理层控制信息 | 6.4 |
| `tx_pipeline` | TX 发射流水线 | 6.10 |
| `rx_pipeline` | RX 接收流水线 | 6.10 |
| `channel` | AWGN/Rayleigh/Rician/多径信道, Jakes Doppler 衰落, 多用户干扰 | -- |
| `equalizer` | ZF/MMSE 均衡, LS 信道估计 | -- |
| `freq_hopping` | 跳频序列与频率管理 | 6.10.3/8.1.2 |
| `mac_interface` | MAC-PHY 适配层 | -- |
| `measurement` | 位置信息测量信号 | 6.2.4 |
| `measurement_frame` | 测量帧类型 1-4 与 UWB 脉冲帧 | 6.3.6-6.3.11 |
| `measurement_tx` | 窄带/UWB 测量链路参数与调度 | 6.7/6.8 |
| `uwb_pulse` | UWB 脉冲波形与芯片调制 | 6.2.1.4 |
| `multitone` | 多音信号生成 | 6.2.1.3 |
| `rf_compliance` | 射频合规参数校验 | 8.2-8.4 |
| `data_link` | 异步/同步数据链路传输规程 | 6.5.1-6.5.3 |
| `usrp` | USRP E310 硬件接口 | -- |

### mac -- MAC 层

| 模块 | 功能 | 标准条款 |
|------|------|----------|
| `frame` | 控制面/数据面/复用帧结构 | 7.3.2-7.3.4 |
| `broadcast` | 广播帧结构与子信息 | 7.1.4 |
| `signaling` | 信令注册与编解码 (112 个类型) | 7.3 |
| `link_control` | 全部链路控制信令 | 7.3.2 |
| `power_control` | 功率控制流程与信令 | 7.2.13 |
| `link_manager` | 链路管理状态机 | 7.1/7.2 |
| `access` | 接入流程管理 | 7.1.3 |
| `scheduler` | 时序调度器 | 6.3/6.6/7.2 |
| `security` | 配对信令 (16 个消息类型) | 9.2 |
| `crypto` | AES-CCM 加密与密钥派生 | 9.3/9.4 |
| `security_manager` | 安全流程集成 (配对 + 加密) | 9.2-9.4 |
| `qos` | QoS 服务质量管理 (ARQ/HARQ/流控/LQI) | 6.5 |
| `smf` | 系统管理帧编解码 | 6.6 |
| `smf_scheduler` | SMF 发送调度 | 6.6.3 |
| `uwb_measurement_security` | UWB 脉冲测量安全 | 9.5 |

### sim -- 仿真

`link_sim` 模块封装了端到端仿真流程, 分为十二个阶段:

| 阶段 | 内容 | 函数 |
|------|------|------|
| Phase 1 | 无编码 GFSK/PSK BER | `sim_gfsk_link`, `sim_psk_link` |
| Phase 2 | Polar 编码 BER/FER | `sim_polar_coded_psk_link` |
| Phase 3 | 帧级仿真 | `sim_frame_link` |
| Phase 4 | 多径信道 + 均衡器 | `sim_channel_eq_link` |
| Phase 5 | 跳频仿真 | `sim_hopping_link` |
| Phase 6 | 全链路 Pipeline 仿真 | `sim_pipeline_link` |
| Phase 7 | 多径信道 + 频偏 Pipeline | `sim_pipeline_channel_link` |
| Phase 8 | 均衡器集成 Pipeline | (run_phase8_simulation) |
| Phase 9 | MAC 帧级端到端仿真 | `sim_mac_signaling_link`, `sim_mac_data_link`, `sim_mac_mux_link` |
| Phase 10 | 多链路调度仿真 | `sim_multi_link`, `sim_access_scheduled_link`, `sim_event_group_timing`, `sim_superframe_capacity` |
| Phase 11 | 安全通信端到端仿真 | `sim_secure_link`, `sim_encrypted_vs_plain`, `sim_pairing_signaling_phy` |
| Phase 12 | AMC / HARQ / 跳频多径 | `sim_amc_throughput`, `sim_harq_link`, `sim_hopping_multipath_link` |
| Phase 13 | QoS ARQ / AMC 自适应 / 流控 | `sim_qos_arq_link`, `sim_qos_amc_adaptive`, `sim_qos_flow_control` |
| Phase 14 | 双节点端到端仿真 | `sim_dual_node_link`, `sim_dual_node_secure_link`, `sim_dual_node_mcs_adapt` |
| Phase 15 | SleNode 集成仿真 | `sim_node_hopping_link`, `sim_node_access_flow`, `sim_node_channel_sweep`, `sim_node_power_adapt`, `sim_node_measurement` |
| Phase 16 | 多用户干扰 + Doppler 时变信道 | `sim_doppler_link`, `sim_multi_user_interference`, `sim_sir_sweep`, `sim_doppler_multipath_link` |

每个阶段的仿真函数可独立调用, 也可通过 `run_phaseN_simulation()` 批量执行。

### node -- 节点实体

`node` 模块提供顶层 `SleNode` 类, 将所有 MAC/PHY 组件整合为统一的收发接口:

| 类 | 职责 |
|-----|------|
| `NodeConfig` | 节点参数配置 (地址、角色、帧类型、MCS、带宽、加密等) |
| `SleNode` | 节点主体, 管理完整链路生命周期 |
| `NodeCallback` | 事件回调接口 (状态变迁、连接、断开) |
| `TxResult` / `RxResult` | 发射/接收结果数据 |

`SleNode` 内部组件关系:

```
SleNode
├── LinkManager      链路状态机 (IDLE → BROADCASTING/SCANNING → CONNECTED → DISCONNECTED)
├── QosManager       QoS 管理 (ARQ + HARQ + 流控 + 质量跟踪 + 发送队列)
├── PairingManager   配对流程驱动 (ECDH 密钥交换)
├── FrameCryptoContext  帧级加密上下文 (AES-CCM)
├── FreqHopping      跳频序列管理
├── PowerController  功率控制
├── ScheduleManager  时序调度
├── ChannelModel     信道模型 (仿真模式)
├── AccessManager    接入流程管理
├── SMFScheduler     系统管理帧调度 (可选)
└── TxConfig         发射参数 (帧类型 + MCS + 导频 + 加扰)
```

## 信号处理链路

SparkLink SLE 的发射处理链路 (`tx_chain`):

```
信息比特
  → CRC 附加
  → 码块分割 (segment_without_crc / segment_with_crc)
  → Polar 编码 (FT2/3/4) 或直通 (FT1)
  → 比特加扰
  → 调制 (GFSK / BPSK / QPSK / 8PSK)
  → 导频插入 (FT2/3/4)
  → 帧组装 (前导 + 同步 + 控制信息 + 数据)
  → 脉冲成型 (RRC)
  → 上变频 / 发射
```

接收链路 (`rx_chain`) 是上述过程的逆操作:

```
接收 IQ
  → 帧同步 (前导检测 + 同步序列相关)
  → 头部解码 (解加扰 → Polar 解码 → CRC 校验)
  → 导频移除
  → 解调 (软 LLR / 硬判决)
  → Polar 解码 (FT2/3/4) 或直通 (FT1)
  → 解加扰
  → CRC 校验
  → 数据比特输出
```

## 帧类型

标准定义了四种帧类型:

| 帧类型 | 调制方式 | 编码 | 控制信息 | 同步信号 | 用途 |
|--------|----------|------|----------|----------|------|
| 1 | GFSK | 无 (BCH) | A 组 (20 bit + CRC12) | sync_signal_1 | 广播/发现 |
| 2 | PSK | Polar(64,K) | A 组 (28 bit + CRC12) | sync_signal_2 | 数据 (有连接) |
| 3 | PSK | Polar(256,K) | B 组 (27 bit + CRC24B) | sync_signal_3 | 数据 (有连接) |
| 4 | PSK | Polar(256,K) | B 组 (27 bit + CRC24B) | sync_signal_4 | 数据 (有连接) |

关键差异:

- **FT1** 使用 GFSK 调制, 不经 Polar 编码, 头部通过 BCH 编码。`mcs_index=8` 表示非编码直通。
- **FT2** 使用 PSK 调制, Polar(64,K) 头部编码, `segment_without_crc` 码块分割。
- **FT3/FT4** 使用 PSK 调制, Polar(256,K) 头部编码, `segment_with_crc` 码块分割 (每段额外附加 CRC)。B 组控制信息 CRC 种子为 `0x555555 ^ LLID`。

## 硬件对接

`phy.usrp` 模块封装了 USRP E310 (Xilinx Zynq-7020 + AD9361) 的收发接口。在无硬件环境下, `MockUSRP` 提供完整的 UHD API 仿真, 使得收发流程可以离线调试。
