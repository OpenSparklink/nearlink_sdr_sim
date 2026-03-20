# Changelog

本项目的所有重要变更都记录在此文件中。

格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/),
版本号遵循 [语义化版本](https://semver.org/lang/zh-CN/)。

## [Unreleased]

### Added

- 系统管理帧编解码模块 (`mac/smf.py`) -- 标准 6.6
  - SMFHeader: 分段指示 + 信令编号
  - ScheduleSignaling: 调度信令 (生效时隙/间隔/帧类型/带宽/频点表)
  - LinkSignaling: 链路信令 (逻辑链路标识/时间资源条目)
  - OffsetSignaling: 偏移信令 (逻辑链路/偏移量/单位)
  - SystemManagementFrame: 完整帧组装解析与分段重组
- 非链接态窄带跳频测量信息配置 (`mac/broadcast.py`) -- 标准 7.1.4.10
  - NarrowbandMeasurementConfig: 41 个字段, 含可变长跳频信道位图
- 非链接态超宽带脉冲测量信息配置 (`mac/broadcast.py`) -- 标准 7.1.4.11
  - UWBPulseMeasurementConfig: 38 个字段, 含可变长频点列表
- 系统管理帧与测量配置测试 (`tests/test_smf.py`)
  - 44 个测试覆盖全部 pack/unpack 环回、边界值、分段重组

- 覆盖率补充测试 (`tests/test_coverage_gaps.py`)
  - 67 个测试覆盖 20+ 模块的未覆盖分支/边界条件
  - 涵盖 scrambler、link_control、link_manager、frame、access、broadcast、
    security_manager、mac_interface、psk、tx/rx_pipeline、polar、scheduler 等
  - 总体覆盖率 91%, 核心模块覆盖率 97%+
- E310 硬件验证脚本 (`scripts/hw_verify.py`)
  - 6 步验证流程: 设备初始化 → 频率/信道 → 增益 → IQ 环回 → PHY 帧环回 → 跳频
  - 支持 `--mock` 模式和 `--addr` 真实设备, 25/25 测试项
- PHY 回环测试脚本 (`scripts/phy_loopback.py`)
  - 多帧类型 (FT2/FT3/FT4) × 多 MCS 全链路 BER/FER 统计
  - 经 SLETransceiver + LoopbackBuffer 完整收发链路
- FT3/FT4 多码块回环测试 (`TestMultiBlockLoopback` in `test_ft_pipeline.py`)
  - 32 字节载荷触发双码块分割场景的全链路闭环验证

- `secure_random_256()` 安全随机函数 (标准 6.10.7), 基于 KDF 生成 256-bit 安全序列
- `sync_sequence.py` 重构: 同步信号 5/6 改用 `crypto.secure_random_256` 公共 API
- `link_manager.py` 新增休眠/唤醒状态机 (标准 7.2.14)
  - DORMANT / WAKING 状态, ENTER_DORMANT / WAKE_UP / WAKE_COMPLETE 事件
  - `is_dormant` 属性, `on_dormant_enter` / `on_wake_complete` 回调
- USRP 环回仿真引擎 (`sim/usrp_sim.py`)
  - `LoopbackBuffer`: TX→RX 环回缓冲区, 支持信道模型注入
  - `USRPLoopbackSim`: 端到端仿真器, 集成 PHY/MAC 全链路
  - 支持 IQ 级、PHY 帧级、MAC 数据帧级、信令级环回
  - 跳频序列环回与批量帧仿真
- MockUSRP/MockStreamer 增加 loopback 模式, TX 发射数据可直接送入 RX
- `TxResult` 新增 `mac_bytes` 字段, 便于接收端确定解码长度
- 33 项 USRP 仿真测试覆盖全链路 (FT1-FT4、SleNode 双节点、信令环回)
- `get_polar_decoder()` 缓存工厂函数, 消除重复创建 PolarDecoder 的开销

### Fixed

- **FT3/FT4 多码块载荷解码** (`rx_pipeline.py decode_payload`)
  - `segment_with_crc` 多码块场景下, 每块附带 per-segment CRC24B
  - 旧代码直接取拼接后末尾 b_len 比特, 包含了 per-segment CRC 而非原始数据
  - 修复为逐块剥离 per-segment CRC24B 并正确处理末块前端补零对齐

### Changed

- Polar SC 解码器引入 SSC 优化
  - 预计算子树类型 (rate-0 / rate-1 / partial), 剪枝跳过纯冻结/纯信息子树
  - `_build_node_types()` 改用前缀和 + 迭代, 替代递归 + np.all
  - rate-1 子树: 硬判决 + 极性变换直接得到信息位, 跳过逐位递归
  - 递归调用从 89100 降至 26700 (70% 减少), 解码耗时下降 53%
  - PolarDecoder 实例缓存消除批量解码的初始化开销
  - MAC 环回总耗时 0.443s → 0.289s (35% 提升)
- Polar SC 解码器改用预分配二维数组, 消除递归中的数组分配开销
- 加扰器 LFSR 输出使用周期缓存 + `np.tile`, 消除逐比特 Python 循环
- 移除 14 个 `run_phase*` 可视化冗余测试 (原占测试总时长 96%)
- 测试时间: 170s → 4.16s (提速 41 倍)
- SDR 部署文档更新, 反映 P0-P2 任务全部完成, 当前阻塞于 E310 硬件就绪

## [0.26.0]

### Added

- Phase 14 双节点端到端仿真 (`sim/link_sim.py`)
  - `sim_dual_node_link()`: 双 SleNode 数据交换仿真, 测量 FER 与字节误码率
  - `sim_dual_node_secure_link()`: 配对 + 加密双节点通信仿真, 明文/密文 FER 对比
  - `sim_dual_node_mcs_adapt()`: MCS 自适应仿真, 跟踪 MCS 等级与成功率变化
  - `_run_dual_frames()`: 多 SNR 帧传输内部辅助函数
  - `run_phase14_simulation()`: 2x2 可视化 (FER/BER、明文/密文、MCS 历史、成功率)
  - `tests/test_link_sim_phy.py`: 5 个测试 (TestDualNodeLink + test_run_phase14)
- 测试覆盖率补充: 96% (345 miss, 新增 32 个测试, 1621 → 1653)
  - `tests/test_node.py`: 新增 10 个测试 — 配对完成/失败流程、加密收发、信令发送、默认回调
  - `tests/test_security.py`: 新增 14 个测试 — 全部 pack/unpack 输入校验 ValueError 路径
  - `tests/test_crypto.py`: 新增 2 个测试 — NO_INPUT/PASSWORD_VERIFY 鉴权方式确认码
  - `tests/test_channel.py`: 新增 4 个测试 — 私有方法 (rayleigh/rician/multipath) 和零功率噪声
  - `tests/test_measurement.py`: 新增 2 个测试 — TYPE_2 扰动索引循环覆盖

### Fixed

- `node.py` 接收端不再调用 `on_tx_feedback()`, 修复接收侧 QoS 状态污染
- 仿真循环中 ARQ 重传锁定问题: FER 测量模式下每帧独立, 失败后清除 ARQ 挂起状态
- `node.py` `_setup_crypto()` 处理 `integrity_key` 为 None 的情况 (认证加密模式)

### Removed

- `code_block_seg.py` 死代码清理: 移除 53 行不可达代码, 覆盖率 78% → 100%
  - `R == 1.0` 分支 (速率表中无 1.0 速率)
  - `R_adj <= 0` 守卫 (所有标准速率 R_adj > 0)
  - `_subsegment_last_block` 子分段路径 (K_1024 > threshold_1024 恒成立)
  - `_find_rate_str` 辅助函数及 5 个关联测试

## [0.25.0]

### Added
- SLE 节点实体类 (`node.py`): 统一收发接口, 整合 MAC/PHY 各模块
  - `NodeConfig`: 节点配置 (地址、角色、帧类型、MCS、带宽、导频、加密等)
  - `SleNode`: 节点主体, 链路生命周期管理 (广播/扫描/接入/配对/数据交换/断连)
  - `send()` / `transmit()` / `receive()`: 数据收发接口, 集成 QoS 队列与 ARQ
  - 配对流程: `start_pairing()` / `process_pairing_message()` 驱动安全子系统
  - MCS 自适应: `recommended_mcs` / `update_mcs()` 基于链路质量动态调整
  - 状态回调: `NodeCallback` 通知状态变迁、连接、断开事件
  - `_build_ctrl_info()`: 从 QoS 字段构建 A2 物理层控制信息
  - `_build_ctrl_bits()`: 兼容原始比特级控制信息构建
  - `tests/test_node.py`: 36 个测试覆盖初始化、生命周期、收发、回调、MCS、信令、配对

- 测试覆盖率提升: 85% → 96%, 新增 84 个测试 (1496 → 1580)
  - `tests/test_link_sim_phy.py`: Phase 1-13 仿真测试 (74 个测试)
    - `_ber` / `_apply_cfo` / `_channel_impair` 辅助函数测试
    - `sim_gfsk_link` / `sim_psk_link` / `sim_polar_coded_psk_link` 无编码/编码 BER 仿真
    - `sim_frame_link` 帧级仿真 (FT2/FT3/FT4, 多种导频配置)
    - `sim_channel_eq_link` 信道均衡 (AWGN/Rayleigh/Rician/multipath, ZF/MMSE)
    - `sim_hopping_link` 跳频链路 (多带宽, 信道阻塞)
    - `sim_pipeline_link` / `sim_pipeline_channel_link` 全链路 Pipeline 仿真
    - `run_phase1_simulation` ~ `run_phase13_simulation` 可视化函数验证
  - `tests/test_measurement.py`: 测量信号补充测试 (10 个测试)
    - 8 音信号, 无效参数边界, type2 扰动路径, 随机天线对排序
- QoS 服务质量管理模块 (`mac/qos.py`): 实现标准 6.5 节数据传输质量控制
  - ArqState: 异步/同步链路 ARQ 序列号管理 (FT1 1-bit / FT3/FT4 5-bit SN), ACK/NACK 反馈处理
  - HarqController: TB 模式与 CBG 模式 HARQ 反馈编解码, 部分重传决策 (MCS=15)
  - FlowController: 发送缓冲区流控管理, 高/低水位背压机制
  - LinkQualityTracker: 滑动窗口 FER 估计, AMC MCS 自适应建议, LQI 字段编解码
  - TxQueue: 5 级优先级发送队列, 重传优先, 容量限制
  - QosManager: 集成管理器, 统一 ARQ/HARQ/流控/质量跟踪/队列, 提供控制信息字段接口
  - QosLink (`phy/mac_interface.py`): 带 QoS 管理的端到端数据链路封装, 自动填充控制信息字段
  - Phase 13 QoS 仿真 (`sim/link_sim.py`): QoS ARQ 重传/AMC 自适应/流控背压仿真与可视化
  - 96 个测试 (69 单元 + 13 集成 + 14 仿真), 全部通过
- 端到端集成测试增强: 新增 18 个 MAC-PHY 集成测试 (1382 → 1400)
  - TestEncryptedPhyRoundtrip (3 个测试): 配对→加密→PHY 传输→解密验证, 多帧 payload_count 递增, MIC 篡改拒绝
  - TestMultiFrameTypeIntegration (6 个测试): FT1/FT2/FT3/FT4 帧类型 roundtrip, 多 MCS 等级扫描, 多种信令类型
  - TestNoisyChannelMacData (3 个测试): AWGN 信道高/低 SNR MAC 数据传输, 广播帧含噪声传输
  - TestLinkStateDrivenExchange (3 个测试): 链路状态机驱动双向数据交换、断开、重连
  - TestMultiLinkConcurrentData (3 个测试): 多链路独立数据传输、调度器分发帧、信令/数据交织
- 测试覆盖率补充: 总体 84% → 85%, 新增 28 个测试 (1354 → 1382)
  - `tests/test_modulator.py`: TestSLEDemodulator (3 个测试) — `demodulator.py` 0% → 100%
  - `tests/test_channel.py`: TestDoppler (6 个测试) — `channel.py` 88% → 92%
  - `tests/test_link_manager.py`: TestPairingTransitions + TestSupervisionCheck (8 个测试) — `link_manager.py` 89% → 95%
  - `tests/test_code_block_seg.py`: TestSubSegmentation + TestSubsegmentLastBlockDirect + TestFindRateStr (11 个测试) — `code_block_seg.py` 67% → 78%
- `sim/link_sim.py` Phase 12: AMC 自适应调制编码 + HARQ 重传 + 跳频多径仿真
  - sim_amc_throughput: 全 MCS (0-12) 吞吐量与 FER 扫描, AMC 包络线选择
  - sim_harq_link: HARQ 重传链路仿真, 对比有/无重传 FER 与吞吐量
  - sim_hopping_multipath_link: 跳频 vs 固定信道 Rayleigh 衰落 FER 对比
  - run_phase12_simulation: 6 子图可视化 (FER/吞吐量/MCS 选择/HARQ/跳频)
- `tests/test_link_sim_mac.py`: 15 个 Phase 12 仿真测试
  - TestAmcThroughput: AMC 吞吐量包络、MCS 选择、FER 单调性
  - TestHarqLink: HARQ FER 改善、平均传输次数约束、吞吐量
  - TestHoppingMultipathLink: 跳频链路 FER 范围与长度一致性
- 文档更新: 补充 Phase 9-12 仿真、安全模块、测量帧等缺失模块
  - `docs/explanation/architecture.md`: MAC 层模块表新增 access/scheduler/security, 仿真阶段补全至 Phase 12
  - `docs/explanation/standard-mapping.md`: 新增第 9 章安全子系统、6.2.3/6.2.4/6.3.6-6.3.11 条款映射
  - `docs/how-to/run-simulation.md`: 新增 Phase 9-12 操作指南 (MAC 帧仿真/安全仿真/AMC/HARQ/跳频)
  - `docs/reference/index.md`: 新增 mac_interface/measurement/access/scheduler/security 等 8 个模块引用
- `mac/security_manager.py`: 安全流程集成管理模块 (标准 9.2-9.4)
  - ECDHKeyPair: P-256 椭圆曲线密钥对生成与 ECDH 共享密钥计算
  - PairingManager: 配对状态机, 驱动 G/T 节点间配对信令交互
  - FrameCryptoContext: 帧级 AES-CCM 加解密上下文, 管理 payload_count
  - run_pairing_procedure: 端到端配对流程 (仿真/测试用)
- `mac/link_manager.py`: 扩展链路状态机, 新增 PAIRING 状态
  - LinkState.PAIRING: 配对态 (CONNECTED↔PAIRING)
  - EventType: START_PAIRING, PAIRING_COMPLETE, PAIRING_FAILED 事件
- `tests/test_security_manager.py`: 31 个安全流程集成测试
- `sim/link_sim.py` Phase 11: 接入→配对→加密端到端仿真
  - sim_secure_link: 接入建链 + ECDH 配对 + AES-CCM 加密数据帧 PHY 传输
  - sim_encrypted_vs_plain: 加密与明文传输 FER 对比
  - sim_pairing_signaling_phy: 配对信令经 PHY 管道传输成功率
  - run_phase11_simulation: 4 子图可视化
- `tests/test_link_sim_mac.py`: 11 个 Phase 11 仿真测试
  - TestECDHKeyPair: P-256 密钥对生成与共享密钥一致性
  - TestPairingManagerBasic: 配对管理器基本功能与状态转换
  - TestPairingFlow: 完整信令交互流程 (公钥交换/随机数/确认码)
  - TestPairingFailure: 配对失败场景 (错误确认码/失败消息)
  - TestRunPairingProcedure: 端到端配对验证
  - TestFrameCryptoContext: 帧加密/解密/篡改检测/AAD
  - TestPairingThenEncryption: 配对后加密数据传输集成验证
- `sim/link_sim.py` Phase 10: 多链路调度仿真
  - sim_multi_link: 多链路超帧内分时传输, 统计总体 FER 和每链路 FER
  - sim_access_scheduled_link: 接入建链 + 调度器驱动数据传输端到端仿真
  - sim_event_group_timing: 事件组时序计算与资源利用率分析
  - sim_superframe_capacity: 超帧容量分析 (链路数-冲突-利用率)
  - run_phase10_simulation: 可视化入口 (4 子图)
- `tests/test_link_sim_mac.py`: 17 个 Phase 10 仿真测试
- `tests/test_mac_phy_integration.py`: MAC-PHY 集成联调测试扩展 (12 个新测试)
  - TestBroadcastFramePhy: 广播帧/扩展广播帧/接入响应帧通过 PHY pipeline 全链路
  - TestAccessPhyIntegration: 接入流程各阶段帧经 PHY encode/decode 的端到端验证
  - TestSchedulerPhyIntegration: 调度器事件调度表驱动的帧传输与时序一致性
  - TestFullStackIntegration: 接入+调度器+PHY 完整协议栈联调
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
