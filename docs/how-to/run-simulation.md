# 运行链路仿真

## 无编码 BER 仿真

使用内置仿真函数, 在多个信噪比上批量计算 BER:

```python
import numpy as np
from nearlink_sdr.sim.link_sim import sim_gfsk_link, sim_psk_link

# GFSK 仿真
result = sim_gfsk_link(
    num_data_bits=5000,
    snr_range_db=np.arange(0, 16, 2),
)
for snr, ber in zip(result["snr_db"], result["ber"]):
    print(f"SNR={snr:2d} dB  BER={ber:.5f}")

# QPSK 仿真
result = sim_psk_link(
    num_data_bits=5000,
    mod_type="QPSK",
    snr_range_db=np.arange(0, 16, 2),
)
```

## Polar 编码 BER 仿真

```python
from nearlink_sdr.sim.link_sim import sim_polar_coded_psk_link

result = sim_polar_coded_psk_link(
    num_info_bits=5000,
    mod_type="BPSK",
    rate_str="1/2",
    code_length=256,
    snr_range_db=np.arange(-2, 10, 1),
)
```

## 多径信道仿真

```python
from nearlink_sdr.phy.channel import ChannelModel
import numpy as np

ch = ChannelModel(snr_db=15.0, channel_type="rayleigh")
signal = np.ones(100) + 0j
rx = ch.apply_multipath(signal, delays=[0, 3, 7], gains=[1.0, 0.5, 0.3])
```

## 跳频序列生成

```python
from nearlink_sdr.phy.freq_hopping import generate_hopping_sequence

seq = generate_hopping_sequence(
    peer_addr=0x123456,
    hop_count=100,
    band="2.4GHz",
)
```

## 绘制 BER 曲线

```python
from nearlink_sdr.sim.link_sim import run_phase1_simulation

run_phase1_simulation()
# 结果保存到 ber_phase1.png
```

## 全链路 Pipeline 仿真

使用 `sim_pipeline_link` 运行端到端 Pipeline 仿真, 内部调用完整的 `tx_chain` → AWGN 信道 → `rx_chain` 链路:

```python
import numpy as np
from nearlink_sdr.sim.link_sim import sim_pipeline_link

# FT2 QPSK MCS7 (码率 7/8)
result = sim_pipeline_link(
    frame_type=2,
    mcs_index=7,
    n_data_bytes=10,
    snr_range_db=np.arange(0, 16, 2),
    n_frames=50,
)
for snr, ber, fer in zip(result["snr_db"], result["ber"], result["fer"]):
    print(f"Eb/N0={snr:5.1f} dB  BER={ber:.5f}  FER={fer:.3f}")
```

支持所有帧类型:

```python
# FT1 GFSK (无编码)
result = sim_pipeline_link(frame_type=1, mcs_index=8)

# FT4 BPSK MCS0 (码率 1/4, 高编码增益)
result = sim_pipeline_link(frame_type=4, mcs_index=0)
```

批量仿真并生成 BER/FER 曲线图:

```bash
uv run python -m nearlink_sdr.sim.link_sim phase6
# 结果保存到 ber_phase6.png
```

## 信道损伤仿真

使用 `sim_pipeline_channel_link` 模拟衰落信道、载波频偏和均衡对链路的影响:

```python
import numpy as np
from nearlink_sdr.sim.link_sim import sim_pipeline_channel_link

# Rayleigh 平坦衰落, 无均衡
result = sim_pipeline_channel_link(
    frame_type=2,
    mcs_index=7,
    channel_type="rayleigh",
    eq_method="none",
    snr_range_db=np.arange(0, 20, 2),
    n_frames=50,
)

# Rayleigh + MMSE 均衡 (genie-aided)
result = sim_pipeline_channel_link(
    frame_type=2,
    mcs_index=7,
    channel_type="rayleigh",
    eq_method="mmse",
    snr_range_db=np.arange(0, 20, 2),
    n_frames=50,
)

# AWGN + 500Hz 载波频偏
result = sim_pipeline_channel_link(
    frame_type=2,
    mcs_index=7,
    channel_type="awgn",
    cfo_hz=500.0,
    snr_range_db=np.arange(0, 16, 2),
)
```

批量信道损伤仿真 (含均衡对比):

```bash
uv run python -m nearlink_sdr.sim.link_sim phase7
# 结果保存到 ber_phase7.png
```
