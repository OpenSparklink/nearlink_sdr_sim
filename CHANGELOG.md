# Changelog

本项目的所有重要变更都记录在此文件中。

格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/),
版本号遵循 [语义化版本](https://semver.org/lang/zh-CN/)。

## [Unreleased]

### Added

- `mac/scheduler.py`: 新增时序调度器模块 (标准 6.3/6.6/7.2)
  - SlotCounter: 30 bit 系统时隙计数器 (Tsys=125μs)
  - EventTimingParams: 事件组计时参数
  - TimeSlice: 超帧内时间片配置
  - Superframe: 超帧管理 (链路注册/冲突检测/活动区间)
  - EventGroupScheduler: 事件组调度 (TX/RX 窗口计算)
  - ScheduleManager: 综合调度管理器 (SMF + 事件组 + 收发间隔)
  - MultiLevelInterval: 31 级多级收发间隔
- `tests/test_scheduler.py`: 62 个调度器测试
- `mac/access.py`: 新增接入流程管理模块 (标准 7.1.3)
  - negotiate_gt_role: GT 角色协商逻辑
  - BroadcasterAccessManager: 广播方接入管理 (阶段 a/c)
  - InitiatorAccessManager: 接入发起方管理 (阶段 b/d)
  - run_access_procedure: 端到端接入流程仿真
- `tests/test_access.py`: 24 个接入流程测试
- `phy/measurement_frame.py`: 新增测量帧结构组装模块 (标准 6.3.6-6.3.11)
  - build_nack_feedback: 半可靠组播 NACK 反馈序列 (6.3.6)
  - equalization_guard: 均衡保护序列 (6.3.7)
  - build_measurement_frame_1: 测量帧类型 1 组装, 先发/后发节点 (6.3.7)
  - build_measurement_frame_2: 测量帧类型 2 (纯测量信号) (6.3.8)
  - build_measurement_frame_3: 测量帧类型 3, 位置测量初始化 (6.3.9)
  - build_measurement_frame_4: 测量帧类型 4, UWB 初始化同步 (6.3.10)
  - build_uwb_sync_field / build_uwb_measurement_field / build_uwb_pulse_measurement_frame:
    超宽带脉冲测量帧 (6.3.11)
- `tests/test_measurement_frame.py`: 34 个测量帧结构测试
- `docs/how-to/sdr-deployment.md`: SDR E310 部署规划与 MAC 层基础设施分析
- `mac/security.py`: 新增配对信令模块 (标准 9.2)
  - 16 个配对消息类型 (0x0133-0x0149): PairingInitiate, PairingRequest,
    PairingResponse, PairingConfirm, PairingInitialInfo, TNodeConfirmCode,
    RaMessage, RbMessage, GNodeConfirmCodeWithRandom, TNodeConfirmCodeWithRandom,
    GNodeConfirmCode, GNodeDHKeyVerify, TNodeDHKeyVerify, PairingFailure,
    RgMessage, RtMessage
- `mac/signaling.py`: 注册表扩展至 128 个信令类型 (新增 16 个配对信令)
- `mac/broadcast.py`: 新增 3 个广播帧子信息结构
  - TransportIndicationInfo (7.1.4.3): 传输指示信息, 支持 2.4GHz/5GHz 跳频地图
  - NonLinkedBroadcastLinkInfo (7.1.4.8): 非链接态广播链路信息
  - QueryRequestFilterInfo (7.1.4.9): 查询请求过滤信息
- `tests/test_security.py`: 52 个配对信令测试
- `tests/test_broadcast.py`: 18 个广播子信息结构测试
- `mac/crypto.py`: 新增安全子系统加密模块 (标准 9.3/9.4)
  - KDF 密钥派生函数 (AES-CMAC, HMAC-SM3 预留)
  - AES-CCM 认证加密/解密
  - CCM Nonce 构建 (异步/同步链路, 其他链路)
  - 初始化向量计算 (FT1-FT4)
  - 会话密钥派生 (SK/EnK/InK)
  - 链路密钥和 DH Key 验证码密钥派生
  - 确认码/数字比较码/混淆算法
  - 组播密钥管理 (GK/GSK/GEnK/GInK)
  - 隐私管理 (可解析随机标识生成/验证)
- `tests/test_crypto.py`: 54 个加密模块测试
- `phy/sync_sequence.py`: 新增同步信号 5/6 (标准 6.2.3.5/6.2.3.6)
  - 安全随机函数序列生成 (6.10.7, KDF-AES-CMAC 256 位)
  - sync_signal_5: GFSK 安全随机同步序列, 收发分离
  - sync_signal_6: 无相位旋转 BPSK 安全随机同步序列
- `phy/measurement.py`: 新增位置信息测量信号模块 (标准 6.2.4)
  - measurement_signal_1: 四种安全类型单音测量信号 (6.2.4.1)
  - measurement_signal_2: 多音测量信号波形生成 (6.2.4.2)
  - antenna_pair_order_sequential / antenna_pair_order_random: 天线对排序 (6.2.4.3)
- `tests/test_sync_sequence.py`: 11 个同步信号 5/6 测试
- `tests/test_measurement.py`: 36 个测量信号测试

## [0.24.0] - 2025-07-15

### Added

- `mac/link_control.py`: 新增 57 个链路控制信令类型 (0x0035-0x0070)
  - Channel5GStatusIndication / HopMap5GUpdate / BroadcastHopMap5GUpdate: 5G 信道与跳频管理
  - MultiIntervalUpdateRequest/Response/Indication: 多间隔更新
  - SystemTimeIndication: 系统时间指示
  - AsyncMulticastLinkSetup / AsyncMulticastParamExchange* / AsyncMulticastParamUpdate*: 异步组播链路管理
  - NarrowbandMeasCap*/FreqTable*/MeasConfig/MeasReport/MeasAction: 窄带跳频测量
  - CoordinateRequest/Report/Config: 坐标管理
  - NarrowbandDelayRequest/Response: 窄带时延
  - AsyncTTLinkSetup: 异步 TT 链路建链
  - UWBMeasCap*/Config/ConfigFeedback/Report: UWB 脉冲测量
  - UWBSensingCap*/Config/ConfigFeedback/Report/Action: UWB 感知
  - ResourceReservation/Terminate: 资源预留
  - NarrowbandSensing*/ProxySensing*/SensingCap*/SensingConfig*: 窄带感知
  - SensingDeviceStatusReport: 感知设备状态
  - NarrowbandMeasConfigUpdate*: 窄带测量配置更新
  - UWBSensingProcess*/UWBProxySensing*/UWBMeasAction: UWB 扩展感知
- `mac/signaling.py`: 注册表扩展至 112 个信令类型
- `tests/test_link_control_ext.py`: 新增 114 个往返测试覆盖全部新信令

### Fixed

- `ResourceReservation`: 修复重复 unpack 方法, 修正 BYTE_LENGTH 为 13

## [0.23.0] - 2025-07-15

### Added

- `mac/link_control.py`: 新增 14 个链路控制信令类型 (0x0020-0x002E)
  - AsyncLinkParamRequest/Response: 链接态异步链路参数更新
  - IsochronousLinkSetup: 同步等时链路建链指示 (56B, 40 字段位域编码)
  - IsochronousParamExchangeRequest/Response: 同步等时参数交互 (52B)
  - IsochronousParamUpdateRequest/Indication: 同步等时参数更新
  - BroadcastLinkSetup: 链接态广播链路建立 (44B, 含 80-bit 跳频地图)
  - BroadcastLinkParamUpdate: 广播链路参数更新 (32B)
  - BroadcastHopMapUpdate: 广播链路跳频地图更新 (14B)
  - SMFParamUpdateRequest/Indication: 系统管理帧参数更新
  - SMFTimeSlotUpdateRequest/Response: 系统管理帧时间片更新
- `mac/signaling.py`: 注册表扩展至 55 个信令类型
- `tests/test_link_control_ext.py`: 新增 20+ 往返测试覆盖所有新信令

## [0.22.0] - 2025-07-15

### Added

- `sim/link_sim.py` Phase 9: MAC 帧级端到端仿真
  - `sim_mac_signaling_link`: 信令帧经 PHY 全链路的解码成功率仿真
  - `sim_mac_data_link`: 异步数据帧多载荷大小的字节级 BER 和 FER 仿真
  - `sim_mac_mux_link`: 控制+数据复用帧的端到端完整性仿真
  - `run_phase9_simulation`: 综合仿真入口, 含三子图输出
  - 三个仿真函数均支持 Rayleigh/Rician/多径信道、载波频偏和 ZF/MMSE 均衡器
  - `_channel_impair`: 信道损伤统一辅助函数
- `tests/test_link_sim_mac.py`: 13 个仿真测试覆盖高 SNR 正确性、返回值结构、
  统计单调性、Rayleigh+MMSE 信道场景和频偏退化验证

### Changed

- `sim/link_sim.py` `__main__` 入口重构为 dispatch 字典, 支持 phase1-phase9

## [0.21.0] - 2025-07-15

### Added

- `phy/mac_interface.py`: MAC-PHY 集成适配层
  - `bytes_to_bits` / `bits_to_bytes`: MAC 字节流与 PHY 比特数组互转
  - `mac_to_iq` / `iq_to_mac`: MAC 帧到 IQ 信号的发射/接收适配
  - `signaling_to_iq` / `iq_to_signaling`: 信令消息直接转 IQ 信号
  - `roundtrip_signaling` / `roundtrip_data`: 端到端回环验证工具
- `tests/test_mac_phy_integration.py`: 15 个集成测试覆盖比特转换、IQ 发射、
  回环验证、信令与数据帧全链路

## [0.20.0] - 2025-07-14

### Added

- `mac/link_manager.py`: 链路管理状态机实现 (标准 7.1/7.2)
  - 状态: IDLE / BROADCASTING / SCANNING / ACCESSING / CONNECTED / DISCONNECTED
  - G/T 节点角色协商与切换 (7.1.7.1, 7.2.15)
  - 事件驱动架构，支持广播、发现、接入、信令收发、断开全流程
  - 监督超时检测、参数更新、回调接口
- `tests/test_link_manager.py`: 27 个测试用例覆盖状态转换、接入流程、控制面信令、
  角色切换、断开流程和完整生命周期

## [0.19.0] - 2025-07-14

### Added

- `mac/link_control.py`: 新增 22 类控制面信令编解码, 覆盖安全流程、信道管理、PHY 更新、
  角色切换、PING、超时更新、广播/组播断开等 (标准 7.3.2.6-7.3.2.63)
- `mac/signaling.py`: 信令注册表从 17 扩展至 41 条目
- `tests/test_link_control_ext.py`: 新增 28 个信令 roundtrip 和注册表测试

### Fixed

- `mac/link_control.py`: 修正 IntervalUpdateRequest DATA_TYPE_INDEX 从 0x0001 → 0x0000,
  IntervalUpdateResponse 重命名为 IntervalUpdateIndication (0x0002),
  新建正确的 IntervalUpdateResponse (0x0001, 1 字节)
- `mac/link_control.py`: 修正 AsyncMulticastReconfig BYTE_LENGTH 从 31 → 30,
  修正 struct unpack 偏移对齐
- `mac/link_control.py`: 修正 AsyncUnicastUpdate pack 输出与标准 15 字节一致

## [0.18.0] - 2025-07-14

### Added

- `mac/broadcast.py`: 广播帧编解码实现 (标准 7.1.4), 含 BroadcastFrame、
  ExtAdvResourceConfig、DiscoveryAccessResourceConfig、AccessBasicInfo、
  AccessRequestInfo、AccessResponseInfo、SystemMgmtFrameInfo 等 7 个数据类
- `tests/test_broadcast.py`: 广播帧 20 个测试用例

## [0.17.0] - 2026-03-20

### Added

- `docs/explanation/principles.md`: 物理层原理讲解, 含 Polar 编码/SC 解码、PSK/GFSK 调制、信道模型、均衡器、CRC、码块分割、加扰等数学推导
- `docs/conf.py`: LaTeX/PDF 输出配置, 使用 XeLaTeX + HarmonyOS Sans SC 字体
- `docs/how-to/build-docs.md`: PDF 构建说明
- MyST 数学公式扩展 (dollarmath, amsmath)

## [0.16.0] - 2026-03-20

### Added

- `sim/link_sim.py`: Phase 8 多帧类型 + 信道 + 均衡器综合仿真
- FT1/FT2/FT3/FT4 在 AWGN 和 Rayleigh+MMSE 下的 BER/FER 对比
- CLI: `uv run python -m nearlink_sdr.sim.link_sim phase8`

## [0.15.0] - 2026-03-20

### Added

- `phy/channel.py`: `last_taps` 属性, `apply_fading` 缓存信道系数供均衡器复用
- `sim/link_sim.py`: `sim_pipeline_channel_link()` 支持 `eq_method` 参数 (none/zf/mmse)
- 平坦衰落 (Rayleigh/Rician) 采用 `equalize_1tap`, 多径采用 `equalize_mmse_freq`
- Rayleigh + MMSE 均衡: BER 从 ~16% 错误地板降至 0 (5dB 即收敛)

### Fixed

- 修复 `sim_pipeline_channel_link` 中均衡器使用独立随机信道系数的问题

## [0.14.0] - 2026-03-20

### Changed

- `common/polar.py`: 可靠性序列 `lru_cache` 缓存, SC 解码 `_f`/`_g` 内联, 编码器向量化蝶形运算
- `phy/psk.py`: RRC 滤波器 `lru_cache` 缓存, 避免重复计算
- Pipeline 仿真速度提升 37% (3.05ms → 1.68ms/frame)

## [0.13.0] - 2026-03-20

### Added

- `sim/link_sim.py`: 多径信道 + 频率偏移 Pipeline 仿真 (Phase 7)
- `sim_pipeline_channel_link()`: 支持 AWGN/Rayleigh/Rician 信道 + 载波频偏
- `run_phase7_simulation()`: 6 种信道配置的 BER/FER 曲线生成

## [0.12.0] - 2026-03-20

### Added

- `sim/link_sim.py`: 全链路 Pipeline 仿真 (Phase 6), 使用 `tx_chain`/`rx_chain` 端到端 BER/FER 仿真
- `sim_pipeline_link()`: 支持 FT1(GFSK)/FT2(QPSK)/FT3(QPSK)/FT4(BPSK) 全帧类型
- `run_phase6_simulation()`: 5 种 MCS/帧类型配置的 BER/FER 曲线生成

### Fixed

- FT3/4 仿真中 `m_seq_index` 误传 PID 导致 `KeyError`, 修正为 0-5 范围

## [0.11.0] - 2026-03-20

### Added

- TX/RX Pipeline 全面支持 FT1(GFSK 无 Polar)/FT3(Polar 256 + segment_with_crc)/FT4 帧类型
- `test_ft_pipeline.py`: FT1(5)/FT3(4)/FT4(4)/帧同步(2) 共 15 个测试
- 帧同步支持 FT3(`sync_signal_3`) 和 FT4(`sync_signal_4`)

### Fixed

- `gfsk.py`: 解调器末尾不完整符号导致 off-by-one, 改用向上取整
- `rx_pipeline.py`: FT3/4 头部使用 CRC24B(非 CRC12), 修正 `k_info` 计算
- `rx_pipeline.py`: FT3/4 payload 解码后剥离 Polar 前端补零

## [0.10.0] - 2026-03-20

### Added

- TV202(MCS7 多码块)/TV205(MCS6)/TV206(MCS6 大载荷)/TV209(MCS11 8PSK) 全链路 pipeline 测试
- RX roundtrip + loopback 测试覆盖 TV202/205/206/209

### Fixed

- `frame.py`: 8PSK 解调缺失, 添加星座点逆映射
- `frame.py`: 8PSK 调制比特数非 3 倍数时自动补零对齐
- `frame.py`: `_bits_to_symbols_count` 添加 8PSK 支持 (3 bits/symbol)

## [0.9.0] - 2026-03-19

### Added

- `phy/rx_pipeline.py`: 完整 RX 接收流水线, 支持帧同步、头部解码、载荷解码
- `rx_chain()`: IQ 信号到数据比特的完整解码链路
- `decode_head()` / `decode_payload()` / `frame_sync()` 子函数
- 14 个 RX pipeline 测试

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

[Unreleased]: https://github.com/user/nearlink-sdr/compare/v0.14.0...HEAD
[0.14.0]: https://github.com/user/nearlink-sdr/compare/v0.13.0...v0.14.0
[0.13.0]: https://github.com/user/nearlink-sdr/compare/v0.12.0...v0.13.0
[0.12.0]: https://github.com/user/nearlink-sdr/compare/v0.11.0...v0.12.0
[0.11.0]: https://github.com/user/nearlink-sdr/compare/v0.10.0...v0.11.0
[0.10.0]: https://github.com/user/nearlink-sdr/compare/v0.9.0...v0.10.0
[0.9.0]: https://github.com/user/nearlink-sdr/compare/v0.8.0...v0.9.0
[0.8.0]: https://github.com/user/nearlink-sdr/compare/v0.7.0...v0.8.0
[0.7.0]: https://github.com/user/nearlink-sdr/compare/v0.6.0...v0.7.0
[0.6.0]: https://github.com/user/nearlink-sdr/compare/v0.5.0...v0.6.0
[0.5.0]: https://github.com/user/nearlink-sdr/compare/v0.4.0...v0.5.0
[0.4.0]: https://github.com/user/nearlink-sdr/compare/v0.3.0...v0.4.0
[0.3.0]: https://github.com/user/nearlink-sdr/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/user/nearlink-sdr/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/user/nearlink-sdr/releases/tag/v0.1.0
