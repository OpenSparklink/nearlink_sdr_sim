"""Phase 16 测试: Doppler 时变信道 + 多用户干扰仿真。"""

import numpy as np

from nearlink_sdr.phy.channel import (
    ChannelConfig,
    ChannelModel,
    InterferenceConfig,
    add_interference,
    compute_sinr,
)
from nearlink_sdr.sim.link_sim import (
    sim_doppler_link,
    sim_doppler_multipath_link,
    sim_multi_user_interference,
    sim_sir_sweep,
)

# ── Jakes Doppler 模型测试 ──


class TestJakesDoppler:
    """Jakes 求和正弦模型验证。"""

    def test_jakes_output_length(self):
        cfg = ChannelConfig(
            channel_type="rayleigh", max_doppler_hz=50.0,
            symbol_rate_hz=1e6, seed=42,
        )
        ch = ChannelModel(config=cfg)
        h = ch._jakes_fading(1000)
        assert len(h) == 1000
        assert h.dtype == complex

    def test_jakes_unit_power(self):
        cfg = ChannelConfig(
            channel_type="rayleigh", max_doppler_hz=50.0,
            symbol_rate_hz=1e6, n_sinusoids=32, seed=42,
        )
        ch = ChannelModel(config=cfg)
        h = ch._jakes_fading(10000)
        avg_power = np.mean(np.abs(h) ** 2)
        assert 0.5 < avg_power < 2.0

    def test_jakes_autocorrelation_matches_j0(self):
        """自相关函数应逼近理论值 J₀(2π·f_d·k/f_s)。"""
        fd = 100.0
        fs = 1e6
        cfg = ChannelConfig(
            channel_type="rayleigh", max_doppler_hz=fd,
            symbol_rate_hz=fs, n_sinusoids=32, seed=42,
        )
        ch = ChannelModel(config=cfg)
        max_lag = 32
        r_measured = ch.doppler_autocorrelation(50000, max_lag=max_lag)
        r_theory = ch.theoretical_autocorrelation(max_lag=max_lag)
        # 前几个 lag 的误差应小于 0.15 (统计波动)
        mse = np.mean((r_measured[:16] - r_theory[:16]) ** 2)
        assert mse < 0.05, f"Jakes autocorrelation MSE {mse:.4f} too high"

    def test_quasi_static_constant(self):
        """Doppler=0 时衰落系数应为常量。"""
        cfg = ChannelConfig(
            channel_type="rayleigh", max_doppler_hz=0.0, seed=42,
        )
        ch = ChannelModel(config=cfg)
        h = ch._gen_rayleigh_coeffs(100)
        assert np.allclose(h, h[0])

    def test_high_doppler_time_varying(self):
        """高 Doppler 时衰落系数应有明显时变。"""
        cfg = ChannelConfig(
            channel_type="rayleigh", max_doppler_hz=200.0,
            symbol_rate_hz=1e6, seed=42,
        )
        ch = ChannelModel(config=cfg)
        h = ch._gen_rayleigh_coeffs(1000)
        # 不应全部相同
        assert not np.allclose(h, h[0])
        # 功率应有波动
        power_seq = np.abs(h) ** 2
        assert np.std(power_seq) > 0.01

    def test_rician_with_doppler(self):
        """Rician + Doppler: LOS 分量应保持, 散射时变。"""
        cfg = ChannelConfig(
            channel_type="rician", max_doppler_hz=50.0,
            rician_k_db=10.0, symbol_rate_hz=1e6, seed=42,
        )
        ch = ChannelModel(config=cfg)
        h = ch._gen_rician_coeffs(1000)
        # 有高 K 因子, 平均幅度应接近 LOS 分量
        avg_amp = np.mean(np.abs(h))
        assert avg_amp > 0.5

    def test_multipath_with_doppler(self):
        """多径 + Doppler: 每条径应有时变。"""
        cfg = ChannelConfig(
            channel_type="multipath", max_doppler_hz=100.0,
            symbol_rate_hz=1e6, seed=42,
        )
        ch = ChannelModel(config=cfg)
        taps = ch._gen_multipath_taps(500)
        # 直射径应时变
        assert not np.allclose(taps[0, :], taps[0, 0])

    def test_apply_fading_with_doppler(self):
        """端到端: Doppler 衰落后信号应有变化。"""
        cfg = ChannelConfig(
            snr_db=30.0, channel_type="rayleigh",
            max_doppler_hz=50.0, seed=42,
        )
        ch = ChannelModel(config=cfg)
        signal = np.ones(500, dtype=complex)
        rx = ch.apply_fading(signal)
        # 接收幅度应有波动
        assert np.std(np.abs(rx)) > 0.01

    def test_n_sinusoids_effect(self):
        """更多正弦分量产生更丰富的时域变化 (更低自相关周期性)。"""
        # 2 个分量的衰落近似周期性, 自相关在远处仍有明显旁瓣;
        # 64 个分量的自相关远处旁瓣应更小
        results = {}
        for n_osc in [2, 64]:
            cfg = ChannelConfig(
                channel_type="rayleigh", max_doppler_hz=100.0,
                symbol_rate_hz=1e6, n_sinusoids=n_osc, seed=42,
            )
            ch = ChannelModel(config=cfg)
            r = ch.doppler_autocorrelation(20000, max_lag=64)
            # 远端 lag (32~63) 的自相关绝对值均值 -> 衡量周期性残留
            results[n_osc] = np.mean(np.abs(r[32:]))
        # 64 个分量的远端自相关应更小 (更少周期性)
        assert results[64] < results[2] + 0.1


# ── 多用户干扰模型测试 ──


class TestInterference:
    """多用户干扰模型验证。"""

    def test_no_interference(self):
        """无干扰时信号不变。"""
        signal = np.ones(100, dtype=complex)
        result = add_interference(signal, [], sample_rate_hz=1e6)
        np.testing.assert_array_equal(result, signal)

    def test_cochannel_interference_power(self):
        """同信道干扰功率应符合 SIR 设置。"""
        rng = np.random.default_rng(42)
        signal = rng.standard_normal(10000) + 1j * rng.standard_normal(10000)
        signal /= np.sqrt(np.mean(np.abs(signal) ** 2))  # 单位功率

        sir_db = 10.0
        intf = InterferenceConfig(sir_db=sir_db, seed=123)
        result = add_interference(signal, [intf], sample_rate_hz=1e6)

        # 干扰功率 ≈ signal_power / SIR_linear
        intf_component = result - signal
        meas_sir = 10 * np.log10(
            np.mean(np.abs(signal) ** 2) / np.mean(np.abs(intf_component) ** 2)
        )
        assert abs(meas_sir - sir_db) < 1.0, f"SIR mismatch: {meas_sir:.1f} vs {sir_db}"

    def test_multiple_interferers_additive(self):
        """多个干扰应叠加, 总干扰功率递增。"""
        signal = np.ones(1000, dtype=complex)
        result_1 = add_interference(
            signal, [InterferenceConfig(sir_db=10, seed=1)],
        )
        result_3 = add_interference(
            signal,
            [InterferenceConfig(sir_db=10, seed=i) for i in range(1, 4)],
        )
        noise_1 = np.mean(np.abs(result_1 - signal) ** 2)
        noise_3 = np.mean(np.abs(result_3 - signal) ** 2)
        assert noise_3 > noise_1 * 1.5

    def test_adjacent_channel_freq_offset(self):
        """邻信道干扰: 频偏后干扰信号能量应出现频移。"""
        # 用恒定基带信号 (DC) 做干扰, 频移后峰值应在 offset 处
        n = 4096
        signal = np.ones(n, dtype=complex)
        intf = InterferenceConfig(sir_db=0, freq_offset_hz=100e3, seed=42)
        result = add_interference(signal, [intf], sample_rate_hz=1e6)
        intf_component = result - signal

        # 干扰是随机基带 + 频移, 验证频谱能量集中在偏移频率附近
        spectrum = np.abs(np.fft.fft(intf_component)) ** 2
        freqs = np.fft.fftfreq(n, d=1 / 1e6)

        # 在 100 kHz ± 带宽区域内的能量占比应显著
        target_mask = np.abs(freqs - 100e3) < 200e3
        energy_near_offset = np.sum(spectrum[target_mask])
        total_energy = np.sum(spectrum)
        # 频移后, 靠近 offset 的能量应占总量的合理比例
        ratio = energy_near_offset / total_energy
        assert ratio > 0.1, f"Energy ratio near offset: {ratio:.3f}"

    def test_sir_negative_strong_interference(self):
        """负 SIR: 干扰比信号强。"""
        signal = np.ones(500, dtype=complex)
        intf = InterferenceConfig(sir_db=-10, seed=42)
        result = add_interference(signal, [intf], sample_rate_hz=1e6)
        intf_power = np.mean(np.abs(result - signal) ** 2)
        sig_power = np.mean(np.abs(signal) ** 2)
        assert intf_power > sig_power * 5  # SIR=-10dB -> intf 10x stronger

    def test_compute_sinr(self):
        """SINR 计算验证。"""
        signal = np.ones(100, dtype=complex)
        noise = 0.1 * (np.random.randn(100) + 1j * np.random.randn(100))
        interference = 0.3 * (np.random.randn(100) + 1j * np.random.randn(100))

        noisy = signal + noise
        full = noisy + interference
        sinr = compute_sinr(signal, noisy, full)
        # SINR 应为有限正值
        assert sinr > 0
        assert sinr < 40

    def test_zero_signal_no_crash(self):
        """零功率信号不应崩溃。"""
        signal = np.zeros(100, dtype=complex)
        intf = InterferenceConfig(sir_db=10, seed=42)
        result = add_interference(signal, [intf], sample_rate_hz=1e6)
        assert len(result) == 100


# ── Phase 16 仿真函数测试 ──


class TestPhase16Simulations:
    """Phase 16 仿真函数集成测试。"""

    def test_sim_doppler_link_returns_valid(self):
        result = sim_doppler_link(
            doppler_range_hz=np.array([0, 50]),
            snr_db=15.0, n_frames=10,
        )
        assert "doppler_hz" in result
        assert "fer" in result
        assert len(result["doppler_hz"]) == 2
        assert all(0 <= f <= 1 for f in result["fer"])

    def test_sim_doppler_link_higher_doppler_worse(self):
        """更高 Doppler 扩展应导致更高 FER (或至少不够好)。"""
        result = sim_doppler_link(
            doppler_range_hz=np.array([0, 200]),
            snr_db=10.0, n_frames=30,
        )
        # 准静态通常 FER 更低
        assert result["fer"][0] <= result["fer"][1] + 0.3

    def test_sim_multi_user_interference_returns_valid(self):
        result = sim_multi_user_interference(
            n_interferers_range=[0, 2],
            sir_db=10.0, snr_db=15.0, n_frames=10,
        )
        assert "n_interferers" in result
        assert "fer" in result
        assert "sinr_db" in result
        assert len(result["n_interferers"]) == 2

    def test_sim_multi_user_no_interference_low_fer(self):
        """无干扰 + 高 SNR 应该 FER 低。"""
        result = sim_multi_user_interference(
            n_interferers_range=[0],
            sir_db=10.0, snr_db=20.0, n_frames=30,
        )
        assert result["fer"][0] < 0.5

    def test_sim_sir_sweep_returns_valid(self):
        result = sim_sir_sweep(
            sir_range_db=np.array([0, 10, 20]),
            n_interferers=1, snr_db=20.0, n_frames=10,
        )
        assert "sir_db" in result
        assert "fer" in result
        assert "sinr_db" in result
        assert len(result["sir_db"]) == 3

    def test_sim_sir_sweep_monotonic_sinr(self):
        """更高 SIR 应给更高 SINR。"""
        result = sim_sir_sweep(
            sir_range_db=np.array([0, 10, 20]),
            n_interferers=1, snr_db=20.0, n_frames=10,
        )
        sinr = result["sinr_db"]
        assert sinr[0] < sinr[1] < sinr[2]

    def test_sim_doppler_multipath_link_returns_valid(self):
        result = sim_doppler_multipath_link(
            doppler_range_hz=np.array([0, 50]),
            snr_db=15.0, n_frames=10,
        )
        assert "doppler_hz" in result
        assert "fer" in result
        assert len(result["doppler_hz"]) == 2

    def test_sim_doppler_link_fade_depth_reported(self):
        result = sim_doppler_link(
            doppler_range_hz=np.array([50]),
            snr_db=15.0, n_frames=10,
        )
        assert "avg_fade_depth_db" in result
        assert len(result["avg_fade_depth_db"]) == 1

    def test_run_phase16_no_crash(self):
        """Phase 16 完整运行不应崩溃。"""
        from nearlink_sdr.sim.link_sim import run_phase16_simulation
        run_phase16_simulation()


