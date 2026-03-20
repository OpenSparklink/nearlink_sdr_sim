"""USRP 仿真与 PHY Pipeline 性能基准测试。

用于跟踪关键路径的处理延迟,防止性能回归。
基准值基于参考硬件测量,上限设置为参考值的 5 倍以适应不同 CI 环境。

当前参考值 (Intel i7-12700H / Python 3.14):
- IQ 环回 (2000 samps):  ~50 us/frame
- PHY 全链路 (80b FT2):  ~1.3 ms/frame
- MAC 数据帧 (32B):      ~2.3 ms/frame
- 批量吞吐 (20B x 100):  ~210 ms total
"""

import time

import numpy as np

from nearlink_sdr.phy.tx_pipeline import TxConfig
from nearlink_sdr.sim.usrp_sim import USRPLoopbackSim

# 上限倍数: 参考值的 N 倍, 容纳 CI 和低端硬件差异
_MARGIN = 5


class TestIQLoopbackPerf:
    """IQ 级环回延迟基准。"""

    def test_iq_loopback_latency(self):
        sim = USRPLoopbackSim(snr_db=50.0)
        iq = np.random.default_rng(42).standard_normal(2000).astype(np.complex64)

        # 预热
        for _ in range(50):
            sim.loopback_iq(iq)

        n = 500
        t0 = time.perf_counter()
        for _ in range(n):
            sim.loopback_iq(iq)
        dt_us = (time.perf_counter() - t0) / n * 1e6

        sim.close()
        # 参考: ~50 us, 上限 250 us
        assert dt_us < 50 * _MARGIN, f"IQ loopback {dt_us:.0f} us 超出上限"


class TestPHYLoopbackPerf:
    """PHY 全链路环回延迟基准。"""

    def test_ft2_phy_latency(self):
        sim = USRPLoopbackSim(snr_db=50.0)
        data = np.random.default_rng(42).integers(0, 2, 80).astype(np.int8)
        cfg = TxConfig(frame_type=2, mcs_index=7, sps=4)

        # 预热
        for _ in range(10):
            sim.loopback_phy(data, cfg)

        n = 100
        t0 = time.perf_counter()
        for _ in range(n):
            sim.loopback_phy(data, cfg)
        dt_ms = (time.perf_counter() - t0) / n * 1e3

        sim.close()
        # 参考: ~1.3 ms, 上限 6.5 ms
        assert dt_ms < 1.3 * _MARGIN, f"PHY loopback {dt_ms:.1f} ms 超出上限"


class TestMACLoopbackPerf:
    """MAC 数据帧环回延迟基准。"""

    def test_mac_data_latency(self):
        sim = USRPLoopbackSim(snr_db=50.0)
        payload = b"Hello SLE Benchmark Data Payload!"
        cfg = TxConfig(frame_type=2, mcs_index=7)

        for _ in range(10):
            sim.loopback_mac_data(payload, cfg)

        n = 100
        t0 = time.perf_counter()
        for _ in range(n):
            sim.loopback_mac_data(payload, cfg)
        dt_ms = (time.perf_counter() - t0) / n * 1e3

        sim.close()
        # 参考: ~2.3 ms, 上限 11.5 ms
        assert dt_ms < 2.3 * _MARGIN, f"MAC loopback {dt_ms:.1f} ms 超出上限"


class TestBatchThroughput:
    """批量帧吞吐基准。"""

    def test_batch_100_frames(self):
        sim = USRPLoopbackSim(snr_db=50.0)
        payloads = [bytes(range(20)) for _ in range(100)]
        cfg = TxConfig(frame_type=2, mcs_index=7)

        # 预热
        sim.run_batch(payloads[:5], cfg)

        t0 = time.perf_counter()
        result = sim.run_batch(payloads, cfg)
        dt_ms = (time.perf_counter() - t0) * 1e3

        sim.close()
        assert result.fer == 0.0, "高 SNR 下 FER 应为 0"
        # 参考: ~210 ms, 上限 1050 ms
        assert dt_ms < 210 * _MARGIN, f"Batch {dt_ms:.0f} ms 超出上限"


class TestUSRPOverhead:
    """USRP 环回层开销分析。

    对比直接 pipeline roundtrip 和经 USRP 环回的差异,
    验证 USRP 抽象层引入的开销可忽略。
    """

    def test_usrp_overhead_negligible(self):
        from nearlink_sdr.phy.mac_interface import roundtrip_data

        payload = b"Hello SLE"
        cfg = TxConfig(frame_type=2, mcs_index=7)

        # 直连 roundtrip (无 USRP)
        n = 100
        t0 = time.perf_counter()
        for _ in range(n):
            roundtrip_data(payload, cfg)
        dt_direct = (time.perf_counter() - t0) / n * 1e3

        # USRP 环回
        sim = USRPLoopbackSim(snr_db=50.0)
        for _ in range(10):
            sim.loopback_mac_data(payload, cfg)

        t0 = time.perf_counter()
        for _ in range(n):
            sim.loopback_mac_data(payload, cfg)
        dt_usrp = (time.perf_counter() - t0) / n * 1e3
        sim.close()

        # USRP 层开销不超过直连的 50%
        overhead_pct = (dt_usrp - dt_direct) / dt_direct * 100
        assert overhead_pct < 50, (
            f"USRP overhead {overhead_pct:.0f}% 过高 "
            f"(direct={dt_direct:.2f} ms, usrp={dt_usrp:.2f} ms)"
        )
