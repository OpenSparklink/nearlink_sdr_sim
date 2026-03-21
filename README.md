# NearLink SDR

[![CI](https://github.com/sanchuanhehe/nearlink_sdr_sim/actions/workflows/ci.yml/badge.svg)](https://github.com/sanchuanhehe/nearlink_sdr_sim/actions/workflows/ci.yml)

符合 TXS-10002-2025 SparkLink SLE 标准的软件无线电链路级仿真系统，目标硬件平台为 USRP E310。

## 功能

- 物理层：GFSK/BPSK/QPSK 调制解调、Polar 编解码、帧结构、前导码、同步信号、跳频、导频、信道估计与均衡
- MAC 层：链路管理状态机、信令编解码、功率控制、QoS、安全子系统
- 仿真：BER 曲线、全链路 Pipeline、多径/频偏/Doppler 信道、MAC 帧级仿真、多链路调度
- 一致性测试：协议/射频/安全，对标标准第 10-13 章

## 快速开始

```bash
# 安装依赖
uv sync

# 运行测试
uv run pytest tests/ -v --tb=short

# 构建文档
uv run sphinx-build docs docs/_build/html

# lint 检查
uv run ruff check src/ tests/ examples/
```

## 项目结构

```
src/nearlink_sdr/
├── common/       # 通用编码 (CRC, BCH, Polar, 码块分割, 加扰, MCS)
├── phy/          # 物理层 (调制, 帧结构, 信道, 均衡, 同步, 跳频, USRP)
├── mac/          # MAC 层 (链路管理, 信令, 安全, QoS, 广播, 调度)
└── sim/          # 仿真 (链路仿真, USRP 环回)
tests/            # 2626 个测试用例
examples/         # 可运行的示例脚本
docs/             # Sphinx 文档 (Diataxis 四象限)
```

## 技术栈

- Python 3.14+, uv, hatchling
- NumPy, SciPy, Matplotlib
- pytest + pytest-cov, ruff
- Sphinx + MyST-Parser

## 许可证

MIT
