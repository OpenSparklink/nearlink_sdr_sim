# 系统架构

nearlink-sdr 是一个链路级仿真系统, 实现了 TXS-10002-2025 SparkLink SLE 标准定义的物理层处理链路。本文说明系统的整体结构和设计思路。

## 模块组织

系统分为四个子包:

```
nearlink_sdr/
├── common/      信道编码与底层算法
├── phy/         物理层信号处理
├── mac/         MAC 层协议 (规划中)
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
| `sync_sequence` | 同步信号 1-4 | 6.5 / 6.6 |
| `pilot` | 导频符号插入与移除 | 6.7 |
| `frame` | 帧结构组装/解析 (类型 1-4) | 6.3 |
| `control_info` | A1-A7/B1-B5 物理层控制信息 | 6.4 |
| `tx_pipeline` | TX 发射流水线 | 6.10 |
| `rx_pipeline` | RX 接收流水线 | 6.10 |
| `channel` | AWGN/Rayleigh/Rician/多径信道模型 | -- |
| `equalizer` | ZF/MMSE 均衡, LS 信道估计 | -- |
| `freq_hopping` | 跳频序列与频率管理 | 6.10.3 / 8.1.2 |
| `usrp` | USRP E310 硬件接口 | -- |

### sim -- 仿真

`link_sim` 模块封装了端到端仿真流程, 分为六个阶段:

| 阶段 | 内容 | 函数 |
|------|------|------|
| Phase 1 | 无编码 GFSK/PSK BER | `sim_gfsk_link`, `sim_psk_link` |
| Phase 2 | Polar 编码 BER/FER | `sim_polar_coded_psk_link` |
| Phase 3 | 帧级仿真 | `sim_frame_link` |
| Phase 4 | 多径信道 + 均衡器 | `sim_multipath_coded_link` |
| Phase 5 | 跳频仿真 | `sim_hopping_link` |
| Phase 6 | 全链路 Pipeline 仿真 | `sim_pipeline_link` |
| Phase 7 | 多径信道 + 频偏 Pipeline 仿真 | `sim_pipeline_channel_link` |

每个阶段的仿真函数可独立调用, 也可通过 `run_phaseN_simulation()` 批量执行。

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
