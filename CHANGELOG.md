# Changelog

本项目的所有重要变更都记录在此文件中。

格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/),
版本号遵循 [语义化版本](https://semver.org/lang/zh-CN/)。

## [Unreleased]

## [0.8.0] - 2026-03-19

### Added

- `common/prbs.py`: PRBS11 (x^11+x^2+1) / PRBS17 (x^17+x^3+1) 发生器, 对标标准 8.3.5
- TV101 端到端验证: PRBS11 -> HeadBits -> CRC12 -> 加扰 -> txHeadW, 全流程匹配附录 H
- 24 个新增测试

### Fixed

- `common/scrambler.py`: 由右移 Fibonacci LFSR 改为左移 Galois LFSR, 输出从 MSB (bit6), 反馈异或到 bit0 和 bit4 (mask=0x11), 经 TV101 测试向量端到端验证

## [0.7.0] - 2026-03-19

### Added

- `common/scrambler.py`: 7bit LFSR 信道比特加扰, 多项式 x^7+x^4+1, 周期 127, 广播种子/数据链路种子生成, 对标标准 6.10.4
- `common/mcs.py`: MCS 表 (MCS0-MCS12, BPSK/QPSK/8PSK) 与速率匹配表 1/2, `RateConfig` 工厂方法, 对标标准 6.10.5 / 6.10.6
- `phy/control_info.py`: 物理层控制信息 A1-A7 (帧类型 1/2, CRC12) 和 B1-B5 (帧类型 3/4, CRC24B+LLID 异或), 对标标准 6.4
- 109 个新增测试

## [0.6.0] - 2026-03-19

### Added

- `phy/usrp.py`: USRP E310 硬件接口封装, 含 `USRPConfig`/`MockUSRP`/`USRPDevice`/`TXStream`/`RXStream`/`SLETransceiver`
- 78 个新增测试

### Changed

- 引入 ruff 代码检查, 添加 `AGENTS.md` 工程规范

## [0.5.0] - 2026-03-19

### Added

- `phy/freq_hopping.py`: 射频信道/物理信道映射, 三频段频率表, 伪随机跳频序列, 多带宽过滤与屏蔽信道管理, 对标标准 6.10.3 / 8.1.2
- `sim/link_sim.py` Phase 5 跳频仿真
- 66 个新增测试

## [0.4.0] - 2026-03-19

### Added

- `phy/channel.py`: AWGN / Rayleigh / Rician / 多径频率选择性信道模型
- `phy/equalizer.py`: ZF/MMSE 频域均衡, MMSE 时域 Wiener 均衡, 1-tap 均衡, LS 信道估计
- `sim/link_sim.py` Phase 4 信道仿真 (7 种配置)
- 44 个新增测试

## [0.3.0] - 2026-03-19

### Added

- `phy/pilot.py`: 导频符号生成与插入/移除, 对标标准 6.7
- `phy/frame.py`: 帧结构组装/解析, 支持帧类型 1-4, 对标标准 6.3
- `sim/link_sim.py` Phase 3 帧级仿真
- 39 个新增测试

## [0.2.0] - 2026-03-19

### Added

- `common/polar.py`: Polar 编码器, SC 解码器, LLR 模式, 对标标准 6.10.1
- `common/code_block_seg.py`: 码块分割, 对标标准 6.10.2
- `sim/link_sim.py` Phase 2 编码链路仿真
- 75 个新增测试

## [0.1.0] - 2026-03-19

### Added

- `common/crc.py`: CRC12/CRC24A/CRC24B/CRC32, 对标标准 6.9
- `common/m_sequence.py`: m31/m63 序列生成
- `common/bch.py`: BCH(31,26) / BCH(63,24) 编码, 对标标准 6.11
- `phy/gfsk.py`: GFSK 调制/解调, 对标标准 6.2.1.1
- `phy/psk.py`: BPSK/QPSK/8PSK 调制/解调, RRC 脉冲成型, 对标标准 6.2.1.2
- `phy/preamble.py`: 前导码生成, 对标标准 6.4
- `phy/sync_sequence.py`: 同步信号 1-4, 对标标准 6.5/6.6
- `sim/link_sim.py` Phase 1 无编码链路仿真
- 107 个测试

[Unreleased]: https://github.com/user/nearlink-sdr/compare/v0.8.0...HEAD
[0.8.0]: https://github.com/user/nearlink-sdr/compare/v0.7.0...v0.8.0
[0.7.0]: https://github.com/user/nearlink-sdr/compare/v0.6.0...v0.7.0
[0.6.0]: https://github.com/user/nearlink-sdr/compare/v0.5.0...v0.6.0
[0.5.0]: https://github.com/user/nearlink-sdr/compare/v0.4.0...v0.5.0
[0.4.0]: https://github.com/user/nearlink-sdr/compare/v0.3.0...v0.4.0
[0.3.0]: https://github.com/user/nearlink-sdr/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/user/nearlink-sdr/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/user/nearlink-sdr/releases/tag/v0.1.0
