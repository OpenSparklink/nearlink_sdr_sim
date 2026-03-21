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

## SleNode 集成仿真 (Phase 15)

Phase 15 基于 `SleNode` 实体进行端到端仿真:

```python
from nearlink_sdr.sim.link_sim import (
    sim_node_hopping_link,
    sim_node_access_flow,
    sim_node_channel_sweep,
    sim_node_power_adapt,
    run_phase15_simulation,
)

# 跳频数据链路仿真
result = sim_node_hopping_link(n_frames=50, snr_db=12.0)
print(f"FER = {result['fer']:.4f}")

# 接入流程仿真
result = sim_node_access_flow()
print(f"广播帧数: {result['n_broadcast_frames']}")

# 信道扫频
result = sim_node_channel_sweep(snr_range_db=[0, 5, 10, 15])

# 功率自适应仿真
result = sim_node_power_adapt(n_frames=100)

# 批量执行并生成可视化图
run_phase15_simulation()
```
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

## MAC 帧级仿真

Phase 9 通过 MAC-PHY 适配层将 MAC 帧编码为 IQ 信号, 经信道传输后在接收端还原 MAC 载荷:

```python
import numpy as np
from nearlink_sdr.sim.link_sim import (
    sim_mac_signaling_link,
    sim_mac_data_link,
    sim_mac_mux_link,
)

# 信令帧传输
result = sim_mac_signaling_link(
    snr_range_db=np.arange(0, 20, 2),
    n_frames=50,
)

# 数据帧传输
result = sim_mac_data_link(
    snr_range_db=np.arange(0, 16, 2),
    n_frames=50,
    mcs_index=7,
)

# 复用帧传输
result = sim_mac_mux_link(
    snr_range_db=np.arange(0, 16, 2),
    n_frames=50,
)
```

```bash
uv run python -m nearlink_sdr.sim.link_sim phase9
```

## 多链路调度仿真

Phase 10 仿真调度器驱动的多链路并发传输:

```python
import numpy as np
from nearlink_sdr.sim.link_sim import (
    sim_multi_link,
    sim_access_scheduled_link,
)

# 多链路并发仿真
result = sim_multi_link(
    snr_range_db=np.arange(0, 16, 2),
    n_links=3,
)

# 接入建链 + 调度仿真
result = sim_access_scheduled_link(
    snr_range_db=np.arange(0, 16, 2),
)
```

```bash
uv run python -m nearlink_sdr.sim.link_sim phase10
```

## 安全通信仿真

Phase 11 模拟完整的安全链路建立: 接入→配对→加密数据传输:

```python
import numpy as np
from nearlink_sdr.sim.link_sim import (
    sim_secure_link,
    sim_encrypted_vs_plain,
)

# 安全链路端到端仿真
result = sim_secure_link(
    snr_range_db=np.arange(0, 16, 2),
    n_frames=50,
    mcs_index=7,
)
print(f"接入成功: {result['access_ok']}, 配对成功: {result['pairing_ok']}")

# 加密与明文 FER 对比
result = sim_encrypted_vs_plain(
    snr_range_db=np.arange(0, 16, 2),
    n_frames=50,
)
```

```bash
uv run python -m nearlink_sdr.sim.link_sim phase11
```

## AMC 自适应调制编码仿真

Phase 12 扫描全部 MCS 等级 (0-12), 生成 AMC 包络吞吐量曲线:

```python
import numpy as np
from nearlink_sdr.sim.link_sim import sim_amc_throughput

result = sim_amc_throughput(
    snr_range_db=np.arange(-2, 22, 1),
    n_frames=50,
)

# AMC 包络吞吐量 (每个 SNR 点选择最优 MCS)
for snr, tp, mcs in zip(
    result["snr_db"], result["amc_throughput"], result["amc_mcs"]
):
    print(f"SNR={snr:5.1f} dB  MCS={mcs:2d}  Throughput={tp:.3f} bit/symbol")

# 仅仿真特定 MCS 子集
result = sim_amc_throughput(mcs_indices=[0, 4, 8, 12])
```

## HARQ 重传仿真

对比有/无 HARQ 重传的 FER 和吞吐量:

```python
import numpy as np
from nearlink_sdr.sim.link_sim import sim_harq_link

result = sim_harq_link(
    snr_range_db=np.arange(0, 16, 1),
    n_frames=100,
    mcs_index=7,
    max_retries=3,
)

for snr, fer_no, fer_harq, avg_tx in zip(
    result["snr_db"],
    result["fer_no_harq"],
    result["fer_harq"],
    result["avg_transmissions"],
):
    print(
        f"SNR={snr:5.1f} dB  "
        f"FER(no HARQ)={fer_no:.3f}  "
        f"FER(HARQ)={fer_harq:.3f}  "
        f"Avg TX={avg_tx:.2f}"
    )
```

## 跳频多径仿真

对比固定信道与跳频在 Rayleigh 衰落下的 FER:

```python
import numpy as np
from nearlink_sdr.sim.link_sim import sim_hopping_multipath_link

result = sim_hopping_multipath_link(
    snr_range_db=np.arange(0, 20, 2),
    n_frames=100,
    n_hop_channels=8,
)
```

生成 Phase 12 全部仿真图:

```bash
uv run python -m nearlink_sdr.sim.link_sim phase12
# 结果保存到 ber_phase12.png
```

## Phase 14: 双节点端到端仿真

使用 SleNode 实体进行完整的双节点数据交换仿真:

```python
import numpy as np
from nearlink_sdr.sim.link_sim import (
    sim_dual_node_link,
    sim_dual_node_secure_link,
    sim_dual_node_mcs_adapt,
)

# 基础 FER/BER 仿真
result = sim_dual_node_link(
    snr_range_db=np.arange(0, 16, 2),
    n_frames=50,
    mcs_index=7,
    payload_size=10,
)
for snr, fer in zip(result["snr_db"], result["fer"]):
    print(f"SNR={snr:2.0f} dB  FER={fer:.3f}")

# 安全通信仿真 (配对 + 加密)
result = sim_dual_node_secure_link(
    snr_range_db=np.arange(0, 16, 2),
    n_frames=50,
)
print(f"配对状态: {'成功' if result['pairing_ok'] else '失败'}")

# MCS 自适应跟踪
result = sim_dual_node_mcs_adapt(
    snr_db=8.0,
    n_frames=100,
    initial_mcs=7,
)
print(f"最终 MCS: {result['mcs_history'][-1]}")
```

生成 Phase 14 全部仿真图:

```bash
uv run python -m nearlink_sdr.sim.link_sim phase14
# 结果保存到 ber_phase14.png
```
