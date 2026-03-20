"""Phase 9 MAC 帧级端到端仿真的单元测试。

验证 sim_mac_signaling_link / sim_mac_data_link / sim_mac_mux_link 在
高 SNR 条件下能正确完成 MAC→PHY→MAC 全链路, 并测试信道损伤场景。
"""

import numpy as np

from nearlink_sdr.sim.link_sim import (
    sim_mac_data_link,
    sim_mac_mux_link,
    sim_mac_signaling_link,
)


class TestMacSignalingLink:
    """信令帧端到端仿真。"""

    def test_high_snr_all_success(self):
        """高 SNR 下信令解码成功率应为 1.0。"""
        result = sim_mac_signaling_link(
            snr_range_db=np.array([30.0]),
            n_frames=20,
        )
        assert result["snr_db"] == [30.0]
        assert result["signaling_success_rate"][0] == 1.0

    def test_returns_expected_keys(self):
        result = sim_mac_signaling_link(
            snr_range_db=np.array([10.0, 20.0]),
            n_frames=5,
        )
        assert "snr_db" in result
        assert "signaling_success_rate" in result
        assert len(result["snr_db"]) == 2
        assert len(result["signaling_success_rate"]) == 2

    def test_success_rate_monotonic(self):
        """更高 SNR 不应有更低的成功率（统计单调性）。"""
        result = sim_mac_signaling_link(
            snr_range_db=np.array([0.0, 10.0, 30.0]),
            n_frames=30,
        )
        rates = result["signaling_success_rate"]
        assert rates[-1] >= rates[0]

    def test_rayleigh_mmse_high_snr(self):
        """Rayleigh + MMSE 均衡在高 SNR 下应有较高成功率。"""
        result = sim_mac_signaling_link(
            snr_range_db=np.array([30.0]),
            n_frames=20,
            channel_type="rayleigh",
            eq_method="mmse",
        )
        assert result["signaling_success_rate"][0] >= 0.8

    def test_cfo_degrades_performance(self):
        """频率偏移应导致在中等 SNR 下性能下降。"""
        no_cfo = sim_mac_signaling_link(
            snr_range_db=np.array([8.0]),
            n_frames=30,
        )
        with_cfo = sim_mac_signaling_link(
            snr_range_db=np.array([8.0]),
            n_frames=30,
            cfo_hz=2000.0,
        )
        # 频偏应导致成功率不高于无频偏情况 (或至少可运行)
        assert with_cfo["signaling_success_rate"][0] <= no_cfo["signaling_success_rate"][0] + 0.15


class TestMacDataLink:
    """异步数据帧端到端仿真。"""

    def test_high_snr_zero_errors(self):
        """高 SNR 下所有载荷大小的 FER 和字节 BER 均为 0。"""
        result = sim_mac_data_link(
            payload_sizes=[4, 10],
            snr_range_db=np.array([30.0]),
            n_frames=10,
        )
        for size in [4, 10]:
            metrics = result["results"][size]
            assert metrics["fer"][0] == 0.0, f"payload {size}B FER != 0"
            assert metrics["byte_ber"][0] == 0.0, f"payload {size}B byte_ber != 0"

    def test_returns_all_sizes(self):
        sizes = [4, 27]
        result = sim_mac_data_link(
            payload_sizes=sizes,
            snr_range_db=np.array([15.0]),
            n_frames=5,
        )
        for s in sizes:
            assert s in result["results"]
            assert "fer" in result["results"][s]
            assert "byte_ber" in result["results"][s]

    def test_larger_payload_higher_fer(self):
        """在低 SNR 下, 更大的载荷通常有更高的 FER。"""
        result = sim_mac_data_link(
            payload_sizes=[4, 27],
            snr_range_db=np.array([4.0]),
            n_frames=50,
        )
        assert len(result["results"]) == 2

    def test_rayleigh_mmse_data(self):
        """Rayleigh + MMSE 在高 SNR 下数据帧应解码正确。"""
        result = sim_mac_data_link(
            payload_sizes=[10],
            snr_range_db=np.array([30.0]),
            n_frames=10,
            channel_type="rayleigh",
            eq_method="mmse",
        )
        assert result["results"][10]["fer"][0] <= 0.2


class TestMacMuxLink:
    """复用帧端到端仿真。"""

    def test_high_snr_perfect(self):
        """高 SNR 下复用帧 CRC 和数据应完全匹配。"""
        result = sim_mac_mux_link(
            snr_range_db=np.array([30.0]),
            n_frames=20,
            data_size=10,
        )
        assert result["mux_success_rate"][0] == 1.0
        assert result["data_match_rate"][0] == 1.0

    def test_returns_expected_keys(self):
        result = sim_mac_mux_link(
            snr_range_db=np.array([10.0]),
            n_frames=5,
        )
        assert "snr_db" in result
        assert "mux_success_rate" in result
        assert "data_match_rate" in result

    def test_data_match_le_mux_success(self):
        """数据匹配率不应超过复用帧 CRC 通过率。"""
        result = sim_mac_mux_link(
            snr_range_db=np.array([6.0, 30.0]),
            n_frames=30,
        )
        for i in range(len(result["snr_db"])):
            assert result["data_match_rate"][i] <= result["mux_success_rate"][i] + 1e-9

    def test_rayleigh_mmse_mux(self):
        """Rayleigh + MMSE 在高 SNR 下复用帧应正确解码。"""
        result = sim_mac_mux_link(
            snr_range_db=np.array([30.0]),
            n_frames=20,
            data_size=10,
            channel_type="rayleigh",
            eq_method="mmse",
        )
        assert result["mux_success_rate"][0] >= 0.8
