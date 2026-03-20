# AGENTS.md

本文件为 NearLink SDR 项目的工程规范, 供自动化工具和开发者参考。

## 项目概述

构建符合 TXS-10002-2025 SparkLink SLE 标准的软件无线电系统, 目标硬件平台为 USRP E310。

## 技术栈

- 语言: Python 3.14+
- 包管理: uv
- 构建: hatchling, src layout
- 测试: pytest + pytest-cov
- Lint: ruff
- 标准文档: `../Summary-of-Sparkling-Information/Standard/TXS-10002-2025.md`

## 目录结构

```
src/nearlink_sdr/
├── common/       # 通用编码模块 (CRC, BCH, Polar, m序列, 码块分割)
├── phy/          # 物理层模块 (调制解调, 帧结构, 导频, 同步序列, 跳频, USRP接口)
├── mac/          # MAC 层 (功率控制信令, 帧结构, 信令注册)
└── sim/          # 链路仿真
tests/            # 测试文件, 与 src 模块一一对应
```

## 开发规范

### 代码风格
- ruff 检查必须通过 (`uv run ruff check src/ tests/`)
- 行长度上限 100 字符
- import 排序按 isort 规则
- 中文注释和文档字符串中允许使用全角标点

### 测试要求
- 每个模块必须有对应的测试文件
- 新功能必须附带测试, 所有测试必须通过
- 运行方式: `uv run pytest tests/ -v --tb=short`

### 提交规范
- 每个阶段完成后提交, commit message 格式使用 Angular Commit Convention:
  - `feat: <描述>` 新功能
  - `fix: <描述>` 修复
  - `docs: <描述>` 文档
  - `refactor: <描述>` 重构
  - `perf: <描述>` 性能优化
  - `test: <描述>` 测试
  - `chore: <描述>` 构建/工具
- 如有 body, 使用中文, 用 `-` 列出具体变更
- 提交前必须通过 lint 检查和全量测试
- 提交修改前更新 CHANGELOG.md
- 添加新功能或修改要更新文档, 文档依据 [diataxis](https://diataxis.fr/) 标准

### 分阶段开发
- 每个阶段完成后闭环验证: 编码 -> 测试 -> lint -> 提交
- 新功能对标 TXS-10002-2025 标准章节, 注明对应条款号

## 标准对标进度

| 标准章节 | 内容 | 状态 | 模块 |
|----------|------|------|------|
| 6.2.1.1 | GFSK 调制 | 完成 | `phy/gfsk.py` |
| 6.2.1.2 | PSK 调制 (BPSK/QPSK) | 完成 | `phy/psk.py` |
| 6.3 | 帧结构 | 完成 | `phy/frame.py` |
| 6.4 | 前导码 | 完成 | `phy/preamble.py` |
| 6.5/6.6 | 同步信号 | 完成 | `phy/sync_sequence.py` |
| 6.7 | 导频 | 完成 | `phy/pilot.py` |
| 6.9 | CRC | 完成 | `common/crc.py` |
| 6.10.1 | Polar 编解码 | 修复 | `common/polar.py` (信息位按索引升序) |
| 6.10.2 | 码块分割 | 完成 | `common/code_block_seg.py` |
| 6.10.3 | 跳频序列 | 完成 | `phy/freq_hopping.py` |
| 6.4 | 物理层控制信息 A/B 组 | 完成 | `phy/control_info.py` |
| 6.10.4 | 信道比特加扰 | 完成 | `common/scrambler.py` |
| 6.10.5 | MCS 表 | 完成 | `common/mcs.py` |
| 6.10.6 | 速率匹配表 | 完成 | `common/mcs.py` |
| 6.11 | BCH 编码 | 完成 | `common/bch.py` |
| 8.1.2 | 射频信道与频率表 | 完成 | `phy/freq_hopping.py` |
| - | 信道模型与均衡器 | 完成 | `phy/channel.py`, `phy/equalizer.py` |
| - | USRP E310 硬件接口 | 完成 | `phy/usrp.py` |
| 8.3.5 | PRBS11/PRBS17 伪随机序列 | 完成 | `common/prbs.py` |
| 14 | 测试向量 TV101-TV104 (帧类型1) | 完成 | `tests/test_prbs.py` |
| 14 | 测试向量 TV201/TV209 (帧类型2) | 完成 | `tests/test_prbs.py` |
| 14 | 测试向量 TV202 (帧类型2 多码块) | 完成 | `tests/test_prbs.py` |
| 14 | 测试向量 TV206 (帧类型2 大载荷) | 完成 | `tests/test_prbs.py` |
| 14 | SyncWord2 验证 (5组PID) | 完成 | `tests/test_prbs.py` |
| 7.2.13 | 功率控制流程 | 完成 | `mac/power_control.py` |
| 7.3.2.27 | PowerControlRequest 信令 | 完成 | `mac/power_control.py` |
| 7.3.2.28 | PowerControlResponse 信令 | 完成 | `mac/power_control.py` |
| 7.3.2.29 | PowerChangeIndication 信令 | 完成 | `mac/power_control.py` |
| 7.3.2 | 控制面帧结构 | 完成 | `mac/frame.py` |
| 7.3.3 | 数据面帧结构 | 完成 | `mac/frame.py` |
| 7.3.4 | 复用帧 | 完成 | `mac/frame.py` |
| 7.3 | 信令注册与编解码 | 完成 | `mac/signaling.py` |
| 7.1.4 | 广播帧结构 | 完成 | `mac/broadcast.py` |
| 7.3.2.2-2.5 | 收发间隔更新信令 | 完成 | `mac/link_control.py` |
| 7.3.2.6-2.11 | 安全流程信令 | 完成 | `mac/link_control.py` |
| 7.3.2.14 | 未知特性反馈 | 完成 | `mac/link_control.py` |
| 7.3.2.19-2.22 | 信道管理信令 | 完成 | `mac/link_control.py` |
| 7.3.2.25-2.26 | PHY 更新信令 | 完成 | `mac/link_control.py` |
| 7.3.2.33-2.34 | 异步链路参数重配置 | 完成 | `mac/link_control.py` |
| 7.3.2.45 | 广播链路断开 | 完成 | `mac/link_control.py` |
| 7.3.2.51-2.55 | 角色切换/PING/时间偏移 | 完成 | `mac/link_control.py` |
| 7.3.2.62-2.63 | 超时更新/组播断开 | 完成 | `mac/link_control.py` |
| 6.10 | TX 发射流水线 | 完成 | `phy/tx_pipeline.py` |
| 6.10 | RX 接收流水线 | 完成 | `phy/rx_pipeline.py` |
| 6.3 | FT1/FT3/FT4 帧类型全链路支持 | 完成 | `phy/tx_pipeline.py`, `phy/rx_pipeline.py` |
| - | 全链路 Pipeline 仿真 | 完成 | `sim/link_sim.py` (Phase 6) |
| - | 多径信道 + 频偏 Pipeline 仿真 | 完成 | `sim/link_sim.py` (Phase 7) |
| - | 均衡器集成到 Pipeline 仿真 | 完成 | `sim/link_sim.py`, `phy/channel.py` |

## 硬件约束 (USRP E310)

- 频率范围: 70 MHz - 6 GHz
- 最大带宽: 56 MHz
- ADC/DAC: 12-bit
- RX 增益: 0 - 76 dB
- TX 增益: 0 - 89.75 dB
- 天线端口: TX/RX, RX2
- SLE 工作频段: 2.4 GHz (2402-2480 MHz)
