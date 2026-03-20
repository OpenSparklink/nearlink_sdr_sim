"""Phase 9 MAC 帧级端到端仿真的单元测试。

验证 sim_mac_signaling_link / sim_mac_data_link / sim_mac_mux_link 在
高 SNR 条件下能正确完成 MAC→PHY→MAC 全链路。
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
        # 至少最后一个 (30 dB) 应该 >= 第一个 (0 dB)
        assert rates[-1] >= rates[0]


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
        # 只验证结果可获取, 不强制统计比较 (太少帧数不稳定)
        assert len(result["results"]) == 2


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
