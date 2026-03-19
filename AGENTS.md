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
├── mac/          # MAC 层 (待实现)
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
- 每个阶段完成后提交, commit message 格式: `Phase N: 简要描述`
- 提交前必须通过 lint 检查和全量测试

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
| 6.10.1 | Polar 编解码 | 完成 | `common/polar.py` |
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
| - | 功率控制 | 待实现 | - |
| - | MAC 层协议栈 | 待实现 | - |

## 硬件约束 (USRP E310)

- 频率范围: 70 MHz - 6 GHz
- 最大带宽: 56 MHz
- ADC/DAC: 12-bit
- RX 增益: 0 - 76 dB
- TX 增益: 0 - 89.75 dB
- 天线端口: TX/RX, RX2
- SLE 工作频段: 2.4 GHz (2402-2480 MHz)
