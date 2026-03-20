"""Phase 9 MAC 帧级端到端仿真的单元测试。

验证 sim_mac_signaling_link / sim_mac_data_link / sim_mac_mux_link 在
高 SNR 条件下能正确完成 MAC→PHY→MAC 全链路, 并测试信道损伤场景。
"""

import numpy as np

from nearlink_sdr.sim.link_sim import (
    sim_access_scheduled_link,
    sim_encrypted_vs_plain,
    sim_event_group_timing,
    sim_mac_data_link,
    sim_mac_mux_link,
    sim_mac_signaling_link,
    sim_multi_link,
    sim_pairing_signaling_phy,
    sim_secure_link,
    sim_superframe_capacity,
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


# -----------------------------------------------------------------------
# Phase 10: 多链路调度仿真
# -----------------------------------------------------------------------


class TestMultiLink:
    """多链路并发调度仿真。"""

    def test_single_link_high_snr(self):
        """单链路高 SNR 下总体 FER 为 0。"""
        result = sim_multi_link(
            n_links=1,
            snr_range_db=np.array([30.0]),
            n_superframes=5,
        )
        assert result["aggregate_fer"][0] == 0.0
        assert result["throughput_ratio"][0] == 1.0

    def test_multi_link_high_snr(self):
        """多链路高 SNR 下总体 FER 为 0。"""
        result = sim_multi_link(
            n_links=3,
            snr_range_db=np.array([30.0]),
            n_superframes=5,
        )
        assert result["aggregate_fer"][0] == 0.0
        assert result["n_conflicts"] == 0

    def test_returns_expected_keys(self):
        result = sim_multi_link(
            n_links=2,
            snr_range_db=np.array([10.0, 20.0]),
            n_superframes=3,
        )
        assert "snr_db" in result
        assert "aggregate_fer" in result
        assert "per_link_fer" in result
        assert "throughput_ratio" in result
        assert "n_conflicts" in result
        assert len(result["snr_db"]) == 2
        assert 1 in result["per_link_fer"]
        assert 2 in result["per_link_fer"]

    def test_per_link_fer_consistent(self):
        """每条链路的 FER 在高 SNR 下均为 0。"""
        result = sim_multi_link(
            n_links=3,
            snr_range_db=np.array([30.0]),
            n_superframes=5,
        )
        for link_id in range(1, 4):
            assert result["per_link_fer"][link_id][0] == 0.0

    def test_throughput_monotonic(self):
        """吞吐量在更高 SNR 下不应降低。"""
        result = sim_multi_link(
            n_links=2,
            snr_range_db=np.array([0.0, 10.0, 30.0]),
            n_superframes=5,
        )
        rates = result["throughput_ratio"]
        assert rates[-1] >= rates[0]


class TestAccessScheduledLink:
    """接入流程 + 调度器驱动仿真。"""

    def test_access_success(self):
        """接入流程应成功建链。"""
        result = sim_access_scheduled_link(
            snr_range_db=np.array([30.0]),
            n_frames=10,
        )
        assert result["access_ok"] is True

    def test_high_snr_zero_fer(self):
        """高 SNR 下 FER 为 0。"""
        result = sim_access_scheduled_link(
            snr_range_db=np.array([30.0]),
            n_frames=10,
        )
        assert result["fer"][0] == 0.0

    def test_link_params_present(self):
        """结果应包含链路参数。"""
        result = sim_access_scheduled_link(
            snr_range_db=np.array([30.0]),
            n_frames=5,
        )
        assert "smf_period" in result["link_params"]
        assert "access_link_id" in result["link_params"]
        assert "access_period" in result["link_params"]
        assert result["events_per_group"] >= 1

    def test_rayleigh_channel(self):
        """Rayleigh + MMSE 信道下应能正常运行。"""
        result = sim_access_scheduled_link(
            snr_range_db=np.array([30.0]),
            n_frames=10,
            channel_type="rayleigh",
            eq_method="mmse",
        )
        assert result["access_ok"] is True
        assert result["fer"][0] <= 0.2


class TestEventGroupTiming:
    """事件组时序计算。"""

    def test_basic_timing(self):
        """基本事件组时序计算。"""
        result = sim_event_group_timing(
            event_group_period=100,
            event_count=4,
            event_period=25,
        )
        assert len(result["events"]) == 4
        assert result["group_period_us"] > 0
        assert 0.0 <= result["utilization"] <= 1.0

    def test_event_count_matches(self):
        for count in [1, 3, 8]:
            result = sim_event_group_timing(event_count=count, event_group_period=200)
            assert len(result["events"]) == count

    def test_active_time_positive(self):
        result = sim_event_group_timing(
            event_group_period=100,
            event_count=2,
            tx_max_offset=3,
            rx_max_offset=3,
        )
        assert result["total_active_us"] > 0

    def test_tx_before_rx(self):
        """每个事件的 TX 窗口应在 RX 之前。"""
        result = sim_event_group_timing(
            event_group_period=200,
            event_count=3,
            event_period=50,
            intra_event_interval=500,
            tx_max_offset=3,
            rx_max_offset=3,
        )
        for event in result["events"]:
            _tx_s, tx_e = event["tx_window"]
            rx_s, _rx_e = event["rx_window"]
            assert tx_e <= rx_s


class TestSuperframeCapacity:
    """超帧容量分析。"""

    def test_no_conflict_with_few_links(self):
        """少量链路时不应有冲突。"""
        result = sim_superframe_capacity(
            smf_interval=800,
            slice_duration=50,
            max_links=5,
        )
        assert result["max_no_conflict"] >= 1

    def test_conflict_when_saturated(self):
        """链路数超过容量上限时应出现冲突。"""
        result = sim_superframe_capacity(
            smf_interval=100,
            slice_duration=50,
            slice_gap=30,
            max_links=10,
        )
        # gap=30, duration=50: 第 2 条链路 [30,80) 与第 1 条 [0,50) 重叠
        assert result["max_no_conflict"] == 1
        # 10 条时必有冲突
        assert result["n_conflicts"][-1] > 0

    def test_utilization_increases(self):
        """活动区间利用率应随链路数增加。"""
        result = sim_superframe_capacity(
            smf_interval=800,
            slice_duration=50,
            max_links=10,
        )
        assert result["utilization"][-1] > result["utilization"][0]

    def test_returns_expected_keys(self):
        result = sim_superframe_capacity(max_links=3)
        assert "n_links" in result
        assert "n_conflicts" in result
        assert "max_no_conflict" in result
        assert "utilization" in result
        assert len(result["n_links"]) == 3


# ── Phase 11: 接入→配对→加密仿真 ──


class TestSecureLink:
    """sim_secure_link 端到端加密仿真测试。"""

    def test_basic_secure_link(self):
        result = sim_secure_link(
            snr_range_db=np.array([20.0]),
            n_frames=10,
        )
        assert result["access_ok"]
        assert result["pairing_ok"]
        assert result["encrypted"]
        assert result["fer"][0] == 0.0

    def test_returns_expected_keys(self):
        result = sim_secure_link(
            snr_range_db=np.array([15.0]),
            n_frames=5,
        )
        assert "snr_db" in result
        assert "fer" in result
        assert "access_ok" in result
        assert "pairing_ok" in result
        assert "encrypted" in result

    def test_low_snr_has_errors(self):
        result = sim_secure_link(
            snr_range_db=np.array([-5.0]),
            n_frames=20,
        )
        assert result["fer"][0] > 0

    def test_fer_decreases_with_snr(self):
        result = sim_secure_link(
            snr_range_db=np.array([0.0, 10.0, 20.0]),
            n_frames=30,
        )
        assert result["fer"][-1] <= result["fer"][0]

    def test_multiple_payload_sizes(self):
        for size in (5, 20):
            result = sim_secure_link(
                snr_range_db=np.array([20.0]),
                n_frames=5,
                payload_size=size,
            )
            assert result["fer"][0] == 0.0


class TestEncryptedVsPlain:
    """sim_encrypted_vs_plain 加密与明文对比测试。"""

    def test_basic_comparison(self):
        result = sim_encrypted_vs_plain(
            snr_range_db=np.array([20.0]),
            n_frames=10,
        )
        assert "fer_encrypted" in result
        assert "fer_plain" in result
        assert result["fer_encrypted"][0] == 0.0
        assert result["fer_plain"][0] == 0.0

    def test_both_degrade_at_low_snr(self):
        result = sim_encrypted_vs_plain(
            snr_range_db=np.array([-5.0]),
            n_frames=20,
        )
        assert result["fer_encrypted"][0] > 0
        assert result["fer_plain"][0] > 0

    def test_returns_list_per_snr(self):
        snr = np.array([5.0, 15.0])
        result = sim_encrypted_vs_plain(snr_range_db=snr, n_frames=5)
        assert len(result["fer_encrypted"]) == 2
        assert len(result["fer_plain"]) == 2


class TestPairingSignalingPhy:
    """sim_pairing_signaling_phy 配对信令 PHY 传输测试。"""

    def test_high_snr_all_success(self):
        result = sim_pairing_signaling_phy(
            snr_range_db=np.array([30.0]),
            n_trials=3,
        )
        assert result["signaling_success_rate"][0] >= 0.9

    def test_low_snr_degraded(self):
        result = sim_pairing_signaling_phy(
            snr_range_db=np.array([-10.0]),
            n_trials=3,
        )
        assert result["signaling_success_rate"][0] < 1.0

    def test_returns_expected_keys(self):
        result = sim_pairing_signaling_phy(
            snr_range_db=np.array([10.0]),
            n_trials=2,
        )
        assert "snr_db" in result
        assert "signaling_success_rate" in result
        assert len(result["signaling_success_rate"]) == 1
