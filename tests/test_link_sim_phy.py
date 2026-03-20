"""Phase 1-8 物理层链路仿真的单元测试。

覆盖 sim_gfsk_link / sim_psk_link / sim_polar_coded_psk_link /
sim_frame_link / sim_channel_eq_link / sim_hopping_link /
sim_pipeline_link / sim_pipeline_channel_link 及辅助函数。
"""

import numpy as np

from nearlink_sdr.sim.link_sim import (
    _apply_cfo,
    _ber,
    _channel_impair,
    sim_channel_eq_link,
    sim_frame_link,
    sim_gfsk_link,
    sim_hopping_link,
    sim_pipeline_channel_link,
    sim_pipeline_link,
    sim_polar_coded_psk_link,
    sim_psk_link,
)

# ── 辅助函数 ──


class TestBer:
    def test_identical(self):
        tx = np.array([0, 1, 0, 1])
        assert _ber(tx, tx) == 0.0

    def test_all_errors(self):
        tx = np.array([0, 0, 0, 0])
        rx = np.array([1, 1, 1, 1])
        assert _ber(tx, rx) == 1.0

    def test_half_errors(self):
        tx = np.array([0, 0, 1, 1])
        rx = np.array([0, 1, 1, 0])
        assert _ber(tx, rx) == 0.5

    def test_empty(self):
        assert _ber(np.array([]), np.array([])) == 0.0

    def test_different_lengths(self):
        tx = np.array([0, 1, 0])
        rx = np.array([0, 1])
        assert _ber(tx, rx) == 0.0


class TestApplyCfo:
    def test_zero_cfo(self):
        sig = np.ones(100, dtype=complex)
        result = _apply_cfo(sig, 0.0, 1e6)
        np.testing.assert_array_equal(result, sig)

    def test_nonzero_cfo_rotates(self):
        sig = np.ones(100, dtype=complex)
        result = _apply_cfo(sig, 1000.0, 1e6)
        assert result.dtype == complex
        assert len(result) == len(sig)
        # 相位应随时间旋转
        assert not np.allclose(result, sig)

    def test_cfo_preserves_amplitude(self):
        sig = np.ones(50, dtype=complex) * 2.0
        result = _apply_cfo(sig, 500.0, 1e6)
        np.testing.assert_allclose(np.abs(result), 2.0, atol=1e-12)


class TestChannelImpair:
    def test_awgn_basic(self):
        rng = np.random.default_rng(42)
        iq = np.ones(64, dtype=complex)
        result = _channel_impair(
            iq, 30.0, "awgn", 6.0, 0.0, "none", 4, rng,
        )
        assert len(result) == len(iq)

    def test_rayleigh_with_eq(self):
        rng = np.random.default_rng(42)
        iq = np.ones(64, dtype=complex)
        result = _channel_impair(
            iq, 20.0, "rayleigh", 6.0, 0.0, "mmse", 4, rng,
        )
        assert len(result) == len(iq)

    def test_with_cfo(self):
        rng = np.random.default_rng(42)
        iq = np.ones(64, dtype=complex)
        result = _channel_impair(
            iq, 20.0, "awgn", 6.0, 500.0, "none", 4, rng,
        )
        assert len(result) == len(iq)

    def test_multipath_mmse(self):
        rng = np.random.default_rng(42)
        iq = np.ones(128, dtype=complex)
        result = _channel_impair(
            iq, 20.0, "multipath", 6.0, 0.0, "mmse", 4, rng,
        )
        assert len(result) == len(iq)

    def test_rician_no_eq(self):
        rng = np.random.default_rng(42)
        iq = np.ones(64, dtype=complex)
        result = _channel_impair(
            iq, 20.0, "rician", 6.0, 0.0, "none", 4, rng,
        )
        assert len(result) == len(iq)

    def test_rayleigh_with_cfo_and_eq(self):
        rng = np.random.default_rng(42)
        iq = np.ones(64, dtype=complex)
        result = _channel_impair(
            iq, 20.0, "rayleigh", 6.0, 200.0, "mmse", 4, rng,
        )
        assert len(result) == len(iq)


# ── Phase 1: 无编码 BER ──


class TestGfskLink:
    def test_returns_expected_keys(self):
        result = sim_gfsk_link(
            num_data_bits=200,
            snr_range_db=np.array([0, 10]),
        )
        assert "snr_db" in result
        assert "ber" in result
        assert len(result["snr_db"]) == 2
        assert len(result["ber"]) == 2

    def test_high_snr_low_ber(self):
        result = sim_gfsk_link(
            num_data_bits=500,
            snr_range_db=np.array([20.0]),
        )
        assert result["ber"][0] < 0.05

    def test_ber_decreases_with_snr(self):
        result = sim_gfsk_link(
            num_data_bits=500,
            snr_range_db=np.array([0.0, 8.0, 16.0]),
        )
        # BER 应大致随 SNR 递减
        assert result["ber"][0] >= result["ber"][-1]

    def test_default_snr_range(self):
        result = sim_gfsk_link(num_data_bits=100)
        assert len(result["snr_db"]) == 9


class TestPskLink:
    def test_qpsk_keys(self):
        result = sim_psk_link(
            num_data_bits=200,
            mod_type="QPSK",
            snr_range_db=np.array([0, 10]),
        )
        assert "snr_db" in result
        assert "ber" in result
        assert len(result["snr_db"]) == 2

    def test_bpsk_high_snr(self):
        result = sim_psk_link(
            num_data_bits=500,
            mod_type="BPSK",
            snr_range_db=np.array([20.0]),
        )
        assert result["ber"][0] < 0.01

    def test_qpsk_ber_trend(self):
        result = sim_psk_link(
            num_data_bits=500,
            mod_type="QPSK",
            snr_range_db=np.array([0.0, 10.0, 20.0]),
        )
        assert result["ber"][0] >= result["ber"][-1]

    def test_frame_type_parameter(self):
        """frame_type 参数不影响 PSK 仿真本身的正确性。"""
        r2 = sim_psk_link(num_data_bits=200, frame_type=2,
                          snr_range_db=np.array([10.0]))
        r3 = sim_psk_link(num_data_bits=200, frame_type=3,
                          snr_range_db=np.array([10.0]))
        assert len(r2["ber"]) == 1
        assert len(r3["ber"]) == 1

    def test_default_snr_range(self):
        result = sim_psk_link(num_data_bits=100)
        assert len(result["snr_db"]) == 9


# ── Phase 2: Polar 编码 BER ──


class TestPolarCodedPskLink:
    def test_returns_expected_keys(self):
        result = sim_polar_coded_psk_link(
            num_info_bits=128,
            code_length=256,
            snr_range_db=np.array([0, 5]),
        )
        assert "snr_db" in result
        assert "ber" in result
        assert "fer" in result
        assert "code_params" in result

    def test_high_snr_no_errors(self):
        result = sim_polar_coded_psk_link(
            num_info_bits=128,
            code_length=256,
            rate_str="1/2",
            snr_range_db=np.array([12.0]),
        )
        assert result["ber"][0] == 0.0
        assert result["fer"][0] == 0.0

    def test_coding_gain(self):
        """编码应在中等 SNR 下降低 BER。"""
        coded = sim_polar_coded_psk_link(
            num_info_bits=128,
            code_length=256,
            rate_str="1/2",
            snr_range_db=np.array([4.0]),
        )
        uncoded = sim_psk_link(
            num_data_bits=128,
            mod_type="BPSK",
            snr_range_db=np.array([4.0]),
        )
        assert coded["ber"][0] <= uncoded["ber"][0]

    def test_fer_bounded(self):
        result = sim_polar_coded_psk_link(
            num_info_bits=128,
            code_length=256,
            snr_range_db=np.array([0.0, 10.0]),
        )
        for f in result["fer"]:
            assert 0.0 <= f <= 1.0

    def test_default_snr_range(self):
        result = sim_polar_coded_psk_link(num_info_bits=64, code_length=128)
        assert len(result["snr_db"]) == 14


# ── Phase 3: 帧级仿真 ──


class TestFrameLink:
    def test_ft2_keys(self):
        result = sim_frame_link(
            frame_type=2,
            num_data_bits=128,
            code_length=256,
            snr_range_db=np.array([0, 5]),
        )
        assert "snr_db" in result
        assert "ber" in result
        assert "fer" in result

    def test_ft3_runs(self):
        result = sim_frame_link(
            frame_type=3,
            num_data_bits=128,
            code_length=256,
            snr_range_db=np.array([5.0]),
        )
        assert len(result["ber"]) == 1

    def test_ft4_runs(self):
        result = sim_frame_link(
            frame_type=4,
            num_data_bits=128,
            code_length=256,
            snr_range_db=np.array([5.0]),
        )
        assert len(result["ber"]) == 1

    def test_pilot_interval_zero(self):
        result = sim_frame_link(
            frame_type=2,
            num_data_bits=128,
            code_length=256,
            pilot_interval=0,
            snr_range_db=np.array([5.0]),
        )
        assert len(result["ber"]) == 1

    def test_high_snr_low_ber(self):
        result = sim_frame_link(
            frame_type=2,
            num_data_bits=128,
            code_length=256,
            snr_range_db=np.array([15.0]),
        )
        assert result["ber"][0] < 0.1

    def test_default_snr_range(self):
        result = sim_frame_link(num_data_bits=64, code_length=128)
        assert len(result["snr_db"]) == 12


# ── Phase 4: 信道 + 均衡 ──


class TestChannelEqLink:
    def test_awgn_keys(self):
        result = sim_channel_eq_link(
            channel_type="awgn",
            snr_range_db=np.array([5.0, 10.0]),
            n_frames=5,
        )
        assert "snr_db" in result
        assert "ber" in result
        assert "fer" in result

    def test_rayleigh_no_eq(self):
        result = sim_channel_eq_link(
            channel_type="rayleigh",
            eq_method="none",
            snr_range_db=np.array([10.0]),
            n_frames=5,
        )
        assert len(result["ber"]) == 1

    def test_rayleigh_mmse_eq(self):
        result = sim_channel_eq_link(
            channel_type="rayleigh",
            eq_method="mmse",
            snr_range_db=np.array([10.0]),
            n_frames=5,
        )
        assert len(result["ber"]) == 1

    def test_rician(self):
        result = sim_channel_eq_link(
            channel_type="rician",
            eq_method="mmse",
            rician_k_db=6.0,
            snr_range_db=np.array([10.0]),
            n_frames=5,
        )
        assert len(result["ber"]) == 1

    def test_multipath_no_eq(self):
        result = sim_channel_eq_link(
            channel_type="multipath",
            eq_method="none",
            snr_range_db=np.array([10.0]),
            n_frames=5,
        )
        assert len(result["ber"]) == 1

    def test_multipath_mmse(self):
        result = sim_channel_eq_link(
            channel_type="multipath",
            eq_method="mmse",
            snr_range_db=np.array([10.0]),
            n_frames=5,
        )
        assert len(result["ber"]) == 1

    def test_multipath_zf(self):
        result = sim_channel_eq_link(
            channel_type="multipath",
            eq_method="zf",
            snr_range_db=np.array([10.0]),
            n_frames=5,
        )
        assert len(result["ber"]) == 1

    def test_eq_improves_rayleigh(self):
        no_eq = sim_channel_eq_link(
            channel_type="rayleigh",
            eq_method="none",
            snr_range_db=np.array([8.0]),
            n_frames=20,
            seed=42,
        )
        with_eq = sim_channel_eq_link(
            channel_type="rayleigh",
            eq_method="mmse",
            snr_range_db=np.array([8.0]),
            n_frames=20,
            seed=42,
        )
        assert with_eq["ber"][0] <= no_eq["ber"][0]


# ── Phase 5: 跳频 ──


class TestHoppingLink:
    def test_keys(self):
        result = sim_hopping_link(
            n_hops=5,
            snr_range_db=np.array([5.0, 10.0]),
        )
        assert "snr_db" in result
        assert "ber" in result
        assert "fer" in result
        assert "channels_used" in result

    def test_channels_used_nonempty(self):
        result = sim_hopping_link(
            n_hops=10,
            snr_range_db=np.array([10.0]),
        )
        assert len(result["channels_used"]) > 0

    def test_high_snr(self):
        result = sim_hopping_link(
            n_hops=10,
            snr_range_db=np.array([20.0]),
        )
        assert result["ber"][0] < 0.1

    def test_blocked_channels(self):
        result = sim_hopping_link(
            n_hops=10,
            blocked_ratio=0.3,
            snr_range_db=np.array([10.0]),
        )
        assert len(result["ber"]) == 1

    def test_bandwidth_2mhz(self):
        result = sim_hopping_link(
            n_hops=5,
            bandwidth_mhz=2,
            snr_range_db=np.array([10.0]),
        )
        assert len(result["channels_used"]) > 0

    def test_bandwidth_4mhz(self):
        result = sim_hopping_link(
            n_hops=5,
            bandwidth_mhz=4,
            snr_range_db=np.array([10.0]),
        )
        assert len(result["channels_used"]) > 0


# ── Phase 6: Pipeline ──


class TestPipelineLink:
    def test_ft2_keys(self):
        result = sim_pipeline_link(
            frame_type=2,
            mcs_index=7,
            n_data_bytes=5,
            snr_range_db=np.array([10.0, 20.0]),
            n_frames=5,
        )
        assert "snr_db" in result
        assert "ber" in result
        assert "fer" in result

    def test_ft1(self):
        result = sim_pipeline_link(
            frame_type=1,
            mcs_index=8,
            n_data_bytes=5,
            snr_range_db=np.array([20.0]),
            n_frames=5,
        )
        assert len(result["ber"]) == 1

    def test_ft3(self):
        result = sim_pipeline_link(
            frame_type=3,
            mcs_index=0,
            n_data_bytes=5,
            snr_range_db=np.array([15.0]),
            n_frames=5,
        )
        assert len(result["ber"]) == 1

    def test_ft4(self):
        result = sim_pipeline_link(
            frame_type=4,
            mcs_index=0,
            n_data_bytes=5,
            snr_range_db=np.array([15.0]),
            n_frames=5,
        )
        assert len(result["ber"]) == 1

    def test_high_snr_low_fer(self):
        result = sim_pipeline_link(
            frame_type=2,
            mcs_index=5,
            n_data_bytes=5,
            snr_range_db=np.array([30.0]),
            n_frames=10,
        )
        assert result["fer"][0] < 0.5


# ── Phase 7: 信道 + Pipeline ──


class TestPipelineChannelLink:
    def test_awgn_keys(self):
        result = sim_pipeline_channel_link(
            frame_type=2,
            mcs_index=7,
            n_data_bytes=5,
            channel_type="awgn",
            snr_range_db=np.array([10.0, 20.0]),
            n_frames=5,
        )
        assert "snr_db" in result
        assert "ber" in result
        assert "fer" in result
        assert len(result["snr_db"]) == 2

    def test_rayleigh_no_eq(self):
        result = sim_pipeline_channel_link(
            frame_type=2,
            mcs_index=7,
            n_data_bytes=5,
            channel_type="rayleigh",
            eq_method="none",
            snr_range_db=np.array([10.0]),
            n_frames=5,
        )
        assert len(result["ber"]) == 1

    def test_rayleigh_mmse(self):
        result = sim_pipeline_channel_link(
            frame_type=2,
            mcs_index=7,
            n_data_bytes=5,
            channel_type="rayleigh",
            eq_method="mmse",
            snr_range_db=np.array([10.0]),
            n_frames=5,
        )
        assert len(result["ber"]) == 1

    def test_rician(self):
        result = sim_pipeline_channel_link(
            frame_type=2,
            mcs_index=7,
            n_data_bytes=5,
            channel_type="rician",
            eq_method="none",
            snr_range_db=np.array([10.0]),
            n_frames=5,
        )
        assert len(result["ber"]) == 1

    def test_with_cfo(self):
        result = sim_pipeline_channel_link(
            frame_type=2,
            mcs_index=7,
            n_data_bytes=5,
            channel_type="awgn",
            cfo_hz=500.0,
            snr_range_db=np.array([20.0]),
            n_frames=5,
        )
        assert len(result["ber"]) == 1

    def test_ft1(self):
        result = sim_pipeline_channel_link(
            frame_type=1,
            mcs_index=8,
            n_data_bytes=5,
            channel_type="awgn",
            snr_range_db=np.array([20.0]),
            n_frames=5,
        )
        assert len(result["ber"]) == 1

    def test_ft3(self):
        result = sim_pipeline_channel_link(
            frame_type=3,
            mcs_index=0,
            n_data_bytes=5,
            channel_type="awgn",
            snr_range_db=np.array([15.0]),
            n_frames=5,
        )
        assert len(result["ber"]) == 1

    def test_multipath_mmse(self):
        result = sim_pipeline_channel_link(
            frame_type=2,
            mcs_index=7,
            n_data_bytes=5,
            channel_type="multipath",
            eq_method="mmse",
            snr_range_db=np.array([15.0]),
            n_frames=5,
        )
        assert len(result["ber"]) == 1


# run_phase*_simulation 可视化入口函数已由底层 sim 函数测试充分覆盖,
# 无需在 CI 中运行完整的参数扫描 (原耗时 164s)。


class TestDualNodeLink:
    """Phase 14 双节点仿真测试。"""

    def test_basic(self):
        from nearlink_sdr.sim.link_sim import sim_dual_node_link
        snr = np.array([6.0, 10.0, 14.0])
        r = sim_dual_node_link(snr_range_db=snr, n_frames=10)
        assert len(r["fer"]) == 3
        assert r["fer"][-1] <= r["fer"][0]
        assert r["tx_count"] > 0

    def test_default_snr(self):
        from nearlink_sdr.sim.link_sim import sim_dual_node_link
        r = sim_dual_node_link(n_frames=5)
        assert len(r["snr_db"]) > 0

    def test_secure_link(self):
        from nearlink_sdr.sim.link_sim import sim_dual_node_secure_link
        snr = np.array([8.0, 12.0])
        r = sim_dual_node_secure_link(snr_range_db=snr, n_frames=10)
        assert "fer_plain" in r
        assert "fer_encrypted" in r
        assert isinstance(r["pairing_ok"], bool)

    def test_mcs_adapt(self):
        from nearlink_sdr.sim.link_sim import sim_dual_node_mcs_adapt
        r = sim_dual_node_mcs_adapt(snr_db=10.0, n_frames=30)
        assert len(r["mcs_history"]) == 30
        assert all(0 <= m <= 12 for m in r["mcs_history"])


class TestNodeHoppingLink:
    """Phase 15 跳频链路仿真测试。"""

    def test_basic(self):
        from nearlink_sdr.sim.link_sim import sim_node_hopping_link
        r = sim_node_hopping_link(snr_db=14.0, n_frames=10)
        assert r["unique_channels"] >= 1
        assert 0.0 <= r["fer"] <= 1.0
        assert len(r["channels"]) == 10
        assert len(r["tx_powers"]) == 10

    def test_high_snr(self):
        from nearlink_sdr.sim.link_sim import sim_node_hopping_link
        r = sim_node_hopping_link(snr_db=30.0, n_frames=20)
        assert r["success_count"] > 0

    def test_low_snr(self):
        from nearlink_sdr.sim.link_sim import sim_node_hopping_link
        r = sim_node_hopping_link(snr_db=0.0, n_frames=10)
        assert "fer" in r


class TestNodeAccessFlow:
    """Phase 15 接入流程仿真测试。"""

    def test_full_flow(self):
        from nearlink_sdr.sim.link_sim import sim_node_access_flow
        r = sim_node_access_flow()
        assert r["broadcast_frame_valid"] is True
        assert r["data_roundtrip_ok"] is True
        assert r["scheduler_active"] is True
        assert r["disconnect_ok"] is True
        assert r["g_state"] == "DISCONNECTED"

    def test_different_seed(self):
        from nearlink_sdr.sim.link_sim import sim_node_access_flow
        r = sim_node_access_flow(seed=123)
        assert r["broadcast_frame_valid"] is True


class TestNodeChannelSweep:
    """Phase 15 信道扫频仿真测试。"""

    def test_basic(self):
        from nearlink_sdr.sim.link_sim import sim_node_channel_sweep
        snr = np.array([4.0, 10.0])
        r = sim_node_channel_sweep(snr_range_db=snr, n_frames=5)
        assert len(r["snr_db"]) == 2
        assert len(r["fer"]) == 2
        assert all(0.0 <= f <= 1.0 for f in r["fer"])

    def test_default_snr(self):
        from nearlink_sdr.sim.link_sim import sim_node_channel_sweep
        r = sim_node_channel_sweep(n_frames=3)
        assert len(r["snr_db"]) > 0
        assert len(r["mcs_history"]) == len(r["snr_db"])


class TestNodePowerAdapt:
    """Phase 15 功率自适应仿真测试。"""

    def test_basic(self):
        from nearlink_sdr.sim.link_sim import sim_node_power_adapt
        r = sim_node_power_adapt(snr_db=10.0, n_frames=15)
        assert len(r["power_history"]) == 15
        assert len(r["success_history"]) == 15
        assert 0.0 <= r["fer"] <= 1.0
        assert len(r["frame_idx"]) == 15

    def test_power_increase_on_failures(self):
        from nearlink_sdr.sim.link_sim import sim_node_power_adapt
        r = sim_node_power_adapt(snr_db=2.0, n_frames=30)
        assert max(r["power_history"]) >= r["power_history"][0]


class TestNodeMeasurement:
    """Phase 15 测量信号仿真测试。"""

    def test_basic(self):
        from nearlink_sdr.sim.link_sim import sim_node_measurement
        r = sim_node_measurement(n_measur=32)
        assert r["signal_length"] > 0
        assert r["signal_energy"] > 0.0

    def test_different_count(self):
        from nearlink_sdr.sim.link_sim import sim_node_measurement
        r1 = sim_node_measurement(n_measur=16)
        r2 = sim_node_measurement(n_measur=64)
        assert r2["signal_length"] >= r1["signal_length"]
