# 快速入门

本教程引导你从安装到运行第一次链路仿真, 完成对 nearlink-sdr 的初步了解。

## 前置条件

- Python 3.14 或更高版本
- [uv](https://docs.astral.sh/uv/) 包管理器

## 安装

克隆仓库并安装依赖:

```bash
git clone <repo-url> nearlink-sdr
cd nearlink-sdr
uv sync
```

## 运行测试

确认所有模块工作正常:

```bash
uv run pytest tests/ -v --tb=short
```

## 第一次仿真: GFSK 链路

GFSK 是 SparkLink SLE 帧类型 1 使用的调制方式。下面的代码演示一次完整的 GFSK 调制-信道-解调流程:

```python
import numpy as np
from nearlink_sdr.phy.gfsk import GFSKModulator, GFSKDemodulator
from nearlink_sdr.phy.channel import ChannelModel

# 生成随机数据比特
rng = np.random.default_rng(42)
data_bits = rng.integers(0, 2, 200)

# 调制
mod = GFSKModulator(sps=8, mod_index=0.5)
tx_signal = mod.modulate(data_bits)

# 通过 AWGN 信道
ch = ChannelModel(snr_db=12.0)
rx_signal = ch.apply_awgn(tx_signal)

# 解调
demod = GFSKDemodulator(sps=8)
rx_bits = demod.demodulate(rx_signal)

# 计算误码率
ber = np.mean(data_bits != rx_bits[:len(data_bits)])
print(f"BER = {ber:.4f}")
```

## 第一次仿真: PSK 编码链路

帧类型 2/3/4 使用 PSK 调制。结合 Polar 编码可以获得编码增益:

```python
import numpy as np
from nearlink_sdr.common.polar import PolarEncoder, PolarDecoder, get_info_bit_count
from nearlink_sdr.phy.psk import PSKModulator, PSKDemodulator
from nearlink_sdr.phy.channel import ChannelModel

# Polar 编码参数: 码长 256, 码率 1/2
code_length = 256
K = get_info_bit_count("1/2", code_length)
enc = PolarEncoder(code_length, K)
dec = PolarDecoder(code_length, K)

# 信息比特
rng = np.random.default_rng(42)
info_bits = rng.integers(0, 2, K, dtype=np.int8)

# 编码
coded_bits = enc.encode(info_bits)

# BPSK 调制 (0 -> +1, 1 -> -1)
bpsk_signal = 1.0 - 2.0 * coded_bits.astype(np.float64)

# AWGN 信道
snr_db = 2.0
snr_lin = 10.0 ** (snr_db / 10.0)
R = K / code_length
noise_var = 1.0 / (2.0 * R * snr_lin)
noise = rng.normal(0, np.sqrt(noise_var), code_length)
received = bpsk_signal + noise

# SC 解码
llr = 2.0 * received / noise_var
decoded = dec.decode(llr)

errors = np.sum(info_bits != decoded)
print(f"比特错误数: {errors}/{K}")
```

## BER 曲线仿真

项目内置了批量仿真函数, 可以直接绘制 BER 曲线:

```python
from nearlink_sdr.sim.link_sim import run_phase1_simulation

run_phase1_simulation()
# 输出 BER 数据并保存 ber_phase1.png
```

## 下一步

- 阅读 [操作指南](../how-to/index.md) 了解具体任务的操作方法
- 阅读 [设计说明](../explanation/architecture.md) 理解系统架构
- 查阅 [技术参考](../reference/index.md) 获取完整的接口文档
