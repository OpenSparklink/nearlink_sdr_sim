# SDR E310 部署规划

本文档概述将 NearLink SDR 从纯仿真环境迁移到 USRP E310 硬件的路径。

## 当前完成度

### 物理层 (第 6 章) -- 全部完成

| 功能 | 模块 | 标准章节 |
|------|------|----------|
| GFSK 调制解调 | `phy/gfsk.py` | 6.2.1.1 |
| BPSK/QPSK 调制解调 | `phy/psk.py` | 6.2.1.2 |
| 帧结构 FT1-FT4 | `phy/frame.py` | 6.3 |
| 前导码 | `phy/preamble.py` | 6.2.2 |
| 同步信号 1-6 | `phy/sync_sequence.py` | 6.2.3 |
| 导频 | `phy/pilot.py` | 6.7 |
| 控制信息 A/B 组 | `phy/control_info.py` | 6.4 |
| CRC-12/24A/24B/32 | `common/crc.py` | 6.10.1 |
| Polar 编解码 (SSC) | `common/polar.py` | 6.9.1 |
| 码块分割 | `common/code_block_seg.py` | 6.9.1.2/3 |
| 跳频序列 (2.4/5.1/5.8 GHz) | `phy/freq_hopping.py` | 6.10.3 |
| 信道比特加扰 | `common/scrambler.py` | 6.10.4 |
| MCS 表与速率匹配 | `common/mcs.py` | 6.10.5/6 |
| BCH 编码 | `common/bch.py` | 6.11 |
| TX/RX 流水线 | `phy/tx_pipeline.py`, `phy/rx_pipeline.py` | 6.10 |
| 测量信号 1/2 (多音) | `phy/measurement.py` | 6.2.4 |
| 测量帧类型 1-4 + UWB | `phy/measurement_frame.py` | 6.3.6-11 |
| 安全随机函数 | `mac/crypto.py` | 6.10.7 |
| PRBS11/PRBS17 | `common/prbs.py` | 8.3.5 |
| USRP E310 接口 | `phy/usrp.py` | - |
| MAC-PHY 适配层 | `phy/mac_interface.py` | - |
| 信道模型 + 均衡器 | `phy/channel.py`, `phy/equalizer.py` | - |

### MAC 层 (第 7 章) -- 全部完成

| 功能 | 模块 | 标准章节 |
|------|------|----------|
| 控制面/数据面/复用帧结构 | `mac/frame.py` | 7.3 |
| 信令注册表 (112 类型) | `mac/signaling.py` | 7.3.2 全覆盖 |
| 链路控制信令 | `mac/link_control.py` | 7.3.2.2-114 |
| 功率控制 | `mac/power_control.py` | 7.2.13 |
| 广播帧 + 子信息 (7.1.4.1-9) | `mac/broadcast.py` | 7.1.4 |
| 链路管理状态机 (含休眠/唤醒) | `mac/link_manager.py` | 7.1/7.2/7.2.14 |
| 接入流程 | `mac/access.py` | 7.1.3 |
| 时隙调度器 | `mac/scheduler.py` | 6.3.1/7.1.4 |
| QoS 管理 (ARQ/HARQ/流控) | `mac/qos.py` | 6.5 |
| 配对信令 | `mac/security.py` | 9.2 |
| 加密模块 (AES-CCM/ECDH/KDF) | `mac/crypto.py` | 9.3/9.4 |
| 安全管理器 | `mac/security_manager.py` | 9.2-9.4 |

### 仿真 (15 阶段 + USRP 环回)

| 阶段 | 内容 |
|------|------|
| Phase 1 | GFSK/BPSK/QPSK 未编码 BER |
| Phase 2 | Polar 编码 BER/FER |
| Phase 3 | 帧级导频 BER/FER |
| Phase 4 | 多径衰落 + 均衡器性能 |
| Phase 5 | 频率选择性信道 |
| Phase 6 | 全 TX/RX 流水线 |
| Phase 7 | 多径 + 频偏集成 |
| Phase 8 | Pipeline 全帧类型对比 |
| Phase 9 | MAC 帧端到端 (信令/数据/复用) |
| Phase 10 | 多链路调度仿真 |
| Phase 11 | 接入 → 配对 → 加密端到端 |
| Phase 12 | AMC + HARQ + 跳频多径 |
| Phase 13 | QoS ARQ/AMC/流控自适应 |
| Phase 14 | 双节点 SleNode 端到端 |
| Phase 15 | SleNode 集成仿真 (跳频/接入/功率/信道) |
| USRP Sim | MockUSRP 环回 (IQ/PHY/MAC/跳频/批量) |

### 统一实体

| 功能 | 模块 |
|------|------|
| SLE 节点实体 | `node.py` |
| USRP 环回仿真引擎 | `sim/usrp_sim.py` |

### 测试质量

- 2592 个测试用例, 全部通过
- 整体覆盖率 91%, 核心模块覆盖率 97%+, 测试执行时间 5.00 秒
- 标准第 14 章测试向量 (TV101-TV206, SyncWord2) 全部验证通过
- 一致性测试 244 个 (协议/射频/安全)

---

## 未实现的进阶特性

以下是标准中定义但当前未实现的进阶功能, 不影响核心 SLE 通信:

| 特性 | 标准章节 | 说明 |
|------|----------|------|
| 睡眠时钟精度计算 | 8.2.2.4-5 | DORMANT/WAKING 状态已实现, 精确漂移补偿需硬件 |

---

## SDR E310 迁移规划

### 前置条件

1. USRP E310 硬件就绪, UHD 驱动已安装
2. 宿主机与 E310 网络连通 (或直接在 E310 ARM 上运行)
3. SLE 2.4 GHz 频段射频校准完成

### 软件仿真验证 (已完成)

以下步骤已通过 MockUSRP 环回仿真完成验证:

- IQ 级环回: TX IQ 样本 → LoopbackBuffer → RX, AWGN/多径信道可选
- PHY 全链路: 编码 → 调制 → MockUSRP TX → 信道 → MockUSRP RX → 解调 → 解码
- MAC 帧级: AsyncDataFrame 打包 → PHY → 环回 → PHY → 解包
- 跳频序列: 在多个信道上依次发射/接收
- 双节点: SleNode G + SleNode T 端到端通信
- 批量帧: 多帧 BER/FER 统计

验证代码: `sim/usrp_sim.py` + `tests/test_usrp_sim.py` (33 个测试)

### 阶段一: 硬件验证

**目标**: 验证 `phy/usrp.py` 在真实硬件上的基本功能

```
scripts/hw_verify.py:
  1. 初始化 USRPDevice(use_mock=False)
  2. 验证频率设置 (2402-2480 MHz)
  3. 验证增益控制 (TX/RX)
  4. 发射单载波 → 频谱仪确认
  5. 回环测试 (TX→RX, 外部衰减器/线缆)
```

关键参数:
- 采样率: 1 MHz (GFSK) 或 2 MHz (QPSK)
- 中心频率: 2440 MHz (信道 19)
- TX 增益: 20 dB (初始低功率)
- RX 增益: 40 dB

### 阶段二: 物理层回环

**目标**: TX pipeline → 空口/线缆 → RX pipeline 回环验证

```
scripts/phy_loopback.py:
  1. 构造 FT2 帧 (GFSK, MCS=0)
  2. mac_to_iq() 生成 IQ 样本
  3. SLETransceiver.transmit_iq() 发射
  4. SLETransceiver.receive_iq() 接收
  5. iq_to_mac() 解码比较
  6. 统计 BER/PER
```

注意事项:
- 首次使用线缆回环 + 衰减器, 排除空口干扰
- 频偏校准: E310 TCXO 精度 ±2.5 ppm, 对应 ±6 kHz@2.4 GHz
- AGC: 初始固定增益, 后续增加自动增益控制

### 阶段三: 双机通信

**目标**: 两台 E310 之间收发通信

```
scripts/tx_node.py:    # G 节点发射端
scripts/rx_node.py:    # T 节点接收端

流程:
  G 节点:
    1. 广播帧发射 (周期性)
    2. 等待接入请求
    3. 建立连接
    4. 数据帧发射

  T 节点:
    1. 扫描广播帧
    2. 前导码检测 + 同步
    3. 解码广播帧
    4. 发送接入请求
    5. 数据帧接收
```

### 阶段四: 协议栈集成

**目标**: MAC 状态机驱动的完整协议栈运行

```
main.py (重构):
  - CLI 入口: tx/rx/loopback/sim 模式选择
  - G 节点模式: 广播 → 接入 → 连接 → 数据传输
  - T 节点模式: 扫描 → 接入 → 连接 → 数据接收
  - 仿真模式: 各 Phase 仿真

关键集成:
  LinkManager → mac_to_iq() → SLETransceiver → 空口 → iq_to_mac() → LinkManager
```

### 阶段五: 性能优化

- 实时性: NumPy 计算耗时评估, 瓶颈识别
- 缓冲区管理: TX/RX 缓冲区大小调优
- 跳频延迟: `tune_channel()` 切换时间测量
- 功率控制: TX 增益动态调节
- 时钟同步: PPS/GPS 外部参考时钟 (可选)

---

## 部署优先级

| 优先级 | 任务 | 状态 |
|--------|------|------|
| P0 | 广播帧子信息补全 (7.1.4.1-9) | 已完成 |
| P0 | 接入流程实现 (7.1.3) | 已完成 |
| P1 | 时隙调度子系统 | 已完成 |
| P1 | MockUSRP 环回仿真验证 | 已完成 |
| P2 | 控制面信令类型 (7.3.2 全覆盖) | 已完成 |
| P2 | 休眠唤醒状态 (DORMANT/WAKING) | 已完成 |
| **P3** | **硬件验证脚本** | **待 E310 硬件就绪** |
| **P3** | **物理层线缆回环** | **待硬件验证完成** |
| **P4** | **双机空口通信** | **待物理层回环调通** |
| **P5** | **协议栈 CLI 集成** | **待双机通信稳定** |
| **P6** | **实时性能优化** | **待部署后评估** |
