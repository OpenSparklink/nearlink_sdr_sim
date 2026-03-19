# Changelog

本项目遵循 TXS-10002-2025 SparkLink SLE 标准, 分阶段构建链路级仿真与硬件对接系统。

## Phase 6 — USRP E310 硬件接口层 (153eed4)

- 新增 `phy/usrp.py`: USRP E310 硬件接口封装
  - `USRPConfig`: 设备配置管理, E310 参数范围校验, SLE 信道-频率映射
  - `MockUSRP` / `MockStreamer`: 无硬件环境下的完整 UHD API 仿真
  - `USRPDevice`: 设备初始化、频率调谐、增益/采样率运行时管理
  - `TXStream`: 单帧发射与连续发射流接口
  - `RXStream`: 定量接收与连续接收模式
  - `SLETransceiver`: 帧级收发 Pipeline, 支持跳频发射/接收
- 新增 78 个测试, 全量 409 测试通过

## Phase 5 — 跳频序列与频率管理 (f337c40)

- 新增 `phy/freq_hopping.py`: 标准 6.10.3 / 8.1.2
  - 射频信道/物理信道映射, 三频段 (2.4/5.1/5.8 GHz) 频率表管理
  - 标准伪随机数生成器 (6.10.3.2)
  - 数据链路/系统管理帧/测量链路跳频 (6.10.3.3-6.10.3.5)
  - 多带宽 (1/2/4 MHz) 频率过滤, 屏蔽信道管理
- 新增 `sim/link_sim.py` Phase 5 跳频仿真
- 新增 66 个测试, 全量 331 测试通过

## Phase 4 — 多径信道模型与均衡器 (4f57a9f)

- 新增 `phy/channel.py`: AWGN / Rayleigh / Rician / 多径频率选择性信道
- 新增 `phy/equalizer.py`: ZF/MMSE 频域均衡, MMSE 时域 Wiener 均衡, 1-tap 均衡, LS 信道估计
- 新增 `sim/link_sim.py` Phase 4 信道仿真 (7 种配置)
- 新增 44 个测试, 全量 265 测试通过

## Phase 3 — 帧结构与导频 (e4eeaf5)

- 新增 `phy/pilot.py`: 导频符号生成与插入/移除 (标准 6.7)
- 新增 `phy/frame.py`: 帧结构组装/解析 (标准 6.3), 支持帧类型 1-4
- 新增 `sim/link_sim.py` Phase 3 帧级仿真
- 新增 39 个测试, 全量 221 测试通过

## Phase 2 — Polar 编解码与码块分割 (a59ec3f)

- 新增 `common/polar.py`: Polar 编码器, SC 解码器, LLR 模式 (标准 6.10.1)
- 新增 `common/code_block_seg.py`: 码块分割 (标准 6.10.2)
- 新增 `sim/link_sim.py` Phase 2 编码链路仿真
- 新增 75 个测试, 全量 182 测试通过

## Phase 1 — PHY 基础模块 (7b50936)

- 新增 `common/crc.py`: CRC12/CRC24A/CRC24B/CRC32 (标准 6.9)
- 新增 `common/m_sequence.py`: m31/m63 序列生成
- 新增 `common/bch.py`: BCH(31,26) / BCH(63,24) 编码 (标准 6.11)
- 新增 `phy/gfsk.py`: GFSK 调制/解调 (标准 6.2.1.1)
- 新增 `phy/psk.py`: BPSK/QPSK/8PSK 调制/解调, RRC 脉冲成型 (标准 6.2.1.2)
- 新增 `phy/preamble.py`: 前导码生成 (标准 6.4)
- 新增 `phy/sync_sequence.py`: 同步信号 1-4 (标准 6.5/6.6)
- 新增 `sim/link_sim.py` Phase 1 无编码链路仿真
- 107 个测试通过
