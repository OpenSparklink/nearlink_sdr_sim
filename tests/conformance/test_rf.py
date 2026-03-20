"""射频一致性测试 — TXS-10002-2025 第 12 章。

覆盖:
- 12.1 发射机测试: 输出功率 / GFSK频偏 / PSK EVM / 频率容限 / 时钟精度 / 无用发射
- 12.2 接收机测试: 灵敏度 / 最大输入 / 选择性 / 互调 / RSSI
- 12.3 UWB 测试: 信道频率 / 频谱模板 / 频率容限 / 均方根误差
"""

from __future__ import annotations

import pytest

from nearlink_sdr.phy.rf_compliance import (
    ACTIVE_CLOCK_PPM,
    GFSK_FREQ_DEV_SPECS,
    GFSK_SENSITIVITY,
    INTERMOD_TABLE,
    MAX_INPUT_LEVEL_DBM,
    OOB_5G,
    OOB_2400,
    PSK_EVM_LIMITS,
    PSK_SENSITIVITY,
    PSK_SPECTRUM_MASK_NARROW,
    PSK_SPECTRUM_MASK_WIDE,
    RSSI_ACCURACY_DB,
    SELECTIVITY_TABLE,
    SLEEP_CLOCK_PPM,
    UWB_MAX_NRMSE_PCT,
    ChannelBandwidth,
    FreqBand,
    PowerClass,
    PSKModulation,
    UWBSpectrumMask,
    check_clock_accuracy,
    check_evm,
    check_freq_tolerance,
    check_gfsk_freq_dev,
    check_rssi_accuracy,
    check_rx_spurious_emission,
    check_uwb_nrmse,
    classify_power,
    get_psk_spectrum_mask,
    gfsk_inband_spurious_limit_dbm,
    reference_sensitivity,
    selectivity_freq_offsets,
    uwb_channel_center_freq_mhz,
    validate_power_step,
)

# ═══════════════════════════════════════════════════════════════════════
# 12.1 发射机测试
# ═══════════════════════════════════════════════════════════════════════


class TestOutputPower:
    """12.1.1 输出功率等级 — VALD-01"""

    @pytest.mark.parametrize("pmax,expected_cls", [
        (25.0, PowerClass.CLASS_0),
        (19.0, PowerClass.CLASS_1),
        (16.0, PowerClass.CLASS_2),
        (12.0, PowerClass.CLASS_3),
        (7.0, PowerClass.CLASS_4),
        (2.0, PowerClass.CLASS_5),
        (-3.0, PowerClass.CLASS_6),
    ])
    def test_classify_power(self, pmax: float, expected_cls: PowerClass):
        assert classify_power(pmax) == expected_cls

    @pytest.mark.parametrize("prev,curr", [
        (10.0, 14.0),
        (0.0, 8.0),
        (20.0, 12.0),
    ])
    def test_power_step_valid(self, prev: float, curr: float):
        assert validate_power_step(prev, curr)

    def test_power_step_invalid(self):
        assert not validate_power_step(0.0, 10.0)


class TestGFSKFreqDev:
    """12.1.2.1 GFSK 频率偏差 — VALD-02"""

    @pytest.mark.parametrize("rate", list(GFSK_FREQ_DEV_SPECS.keys()))
    def test_nominal_within_spec(self, rate: float):
        """使用规范中间值, 应通过。"""
        spec = GFSK_FREQ_DEV_SPECS[rate]
        fd1 = (spec.fd1_min_khz + spec.fd1_max_khz) / 2
        fd2 = fd1 * 0.9  # > 0.8 ratio
        result = check_gfsk_freq_dev(rate, spec.min_deviation_khz, fd1, fd2)
        assert result.passed

    @pytest.mark.parametrize("rate", [0.1, 1.0, 4.0])
    def test_fd1_out_of_range(self, rate: float):
        """fd1 超出上限, 应失败。"""
        spec = GFSK_FREQ_DEV_SPECS[rate]
        fd1 = spec.fd1_max_khz + 10.0
        fd2 = fd1 * 0.9
        result = check_gfsk_freq_dev(rate, spec.min_deviation_khz, fd1, fd2)
        assert not result.fd1_ok

    def test_min_deviation_below_threshold(self):
        """最小频偏低于门限, 应失败。"""
        spec = GFSK_FREQ_DEV_SPECS[1.0]
        fd1 = (spec.fd1_min_khz + spec.fd1_max_khz) / 2
        result = check_gfsk_freq_dev(1.0, spec.min_deviation_khz - 10, fd1, fd1 * 0.9)
        assert not result.min_ok


class TestPSKEVM:
    """12.1.2.2 PSK EVM — VALD-03"""

    @pytest.mark.parametrize("mod", list(PSKModulation))
    def test_evm_within_limit(self, mod: PSKModulation):
        lim = PSK_EVM_LIMITS[mod]
        assert check_evm(mod, lim.rms_pct - 1, lim.pct99 - 1, lim.peak_pct - 1)

    @pytest.mark.parametrize("mod", list(PSKModulation))
    def test_evm_exceeds_rms(self, mod: PSKModulation):
        lim = PSK_EVM_LIMITS[mod]
        assert not check_evm(mod, lim.rms_pct + 1, lim.pct99 - 1, lim.peak_pct - 1)

    def test_evm_exceeds_peak(self):
        lim = PSK_EVM_LIMITS[PSKModulation.PI4_QPSK]
        assert not check_evm(PSKModulation.PI4_QPSK, 5.0, 10.0, lim.peak_pct + 1)


class TestFreqTolerance:
    """12.1.2.3 频率容限 — VALD-04"""

    @pytest.mark.parametrize("mod_type", ["GFSK", "BPSK/QPSK", "8PSK"])
    def test_2400_band_within_spec(self, mod_type: str):
        from nearlink_sdr.phy.rf_compliance import FREQ_TOLERANCE_2400
        spec = FREQ_TOLERANCE_2400[mod_type]
        assert check_freq_tolerance(
            FreqBand.BAND_2400, mod_type,
            spec.freq_offset_khz * 0.5,
            spec.freq_drift_khz * 0.5,
            spec.drift_rate_hz_per_us * 0.5,
        )

    @pytest.mark.parametrize("mod_type", ["GFSK", "BPSK/QPSK", "8PSK"])
    def test_5g_band_within_spec(self, mod_type: str):
        from nearlink_sdr.phy.rf_compliance import FREQ_TOLERANCE_5G
        spec = FREQ_TOLERANCE_5G[mod_type]
        assert check_freq_tolerance(
            FreqBand.BAND_5100, mod_type,
            spec.freq_offset_khz * 0.8,
            spec.freq_drift_khz * 0.8,
            spec.drift_rate_hz_per_us * 0.8,
        )

    def test_sub1g_within_ppm(self):
        assert check_freq_tolerance(
            FreqBand.SUB_1G, "GFSK",
            5.0, 0.0, 0.0, carrier_freq_mhz=868.0,
        )

    def test_sub1g_exceeds_ppm(self):
        assert not check_freq_tolerance(
            FreqBand.SUB_1G, "GFSK",
            1000.0, 0.0, 0.0, carrier_freq_mhz=868.0,
        )


class TestClockAccuracy:
    """12.1.2.4/5 时钟精度 — VALD-05"""

    def test_active_within_spec(self):
        assert check_clock_accuracy(ACTIVE_CLOCK_PPM - 1, 1.0, is_sleep=False)

    def test_active_exceeds_ppm(self):
        assert not check_clock_accuracy(ACTIVE_CLOCK_PPM + 1, 1.0, is_sleep=False)

    def test_sleep_within_spec(self):
        assert check_clock_accuracy(SLEEP_CLOCK_PPM - 10, 10.0, is_sleep=True)

    def test_sleep_exceeds_jitter(self):
        assert not check_clock_accuracy(100.0, 20.0, is_sleep=True)


class TestGFSKSpurious:
    """12.1.3.1 GFSK 频段内杂散 — VALD-07"""

    @pytest.mark.parametrize("bw,offset,expected_max", [
        (ChannelBandwidth.BW_1M, 2.0, -20.0),
        (ChannelBandwidth.BW_1M, 3.0, -30.0),
        (ChannelBandwidth.BW_2M, 4.0, -20.0),
        (ChannelBandwidth.BW_2M, 5.0, -23.0),
        (ChannelBandwidth.BW_4M, 8.0, -20.0),
        (ChannelBandwidth.BW_4M, 10.0, -23.0),
        (ChannelBandwidth.BW_4M, 12.0, -30.0),
    ])
    def test_inband_limit(self, bw, offset, expected_max):
        assert gfsk_inband_spurious_limit_dbm(bw, offset) == expected_max


class TestPSKSpectrumMask:
    """12.1.3.2 PSK 频谱模板 — VALD-08"""

    @pytest.mark.parametrize("bw", list(PSK_SPECTRUM_MASK_WIDE.keys()))
    def test_wide_mask_exists(self, bw):
        mask = get_psk_spectrum_mask(bw)
        assert mask.f1_mhz > 0
        assert mask.f4_mhz is not None

    @pytest.mark.parametrize("bw", list(PSK_SPECTRUM_MASK_NARROW.keys()))
    def test_narrow_mask_exists(self, bw):
        mask = get_psk_spectrum_mask(bw)
        assert mask.f1_mhz > 0
        assert mask.f3_mhz is not None


# ═══════════════════════════════════════════════════════════════════════
# 12.2 接收机测试
# ═══════════════════════════════════════════════════════════════════════


class TestSensitivity:
    """12.2.1 参考灵敏度 — VALD-01"""

    @pytest.mark.parametrize("bw_khz", [100, 125, 250, 500, 1000, 2000, 4000])
    def test_gfsk_sensitivity_defined(self, bw_khz: int):
        val = reference_sensitivity(bw_khz)
        assert val < 0  # 灵敏度为负 dBm 值
        assert val == GFSK_SENSITIVITY[bw_khz]

    @pytest.mark.parametrize("mcs", [0, 4, 7, 12])
    def test_psk_sensitivity_defined(self, mcs: int):
        for bw in [1000, 2000, 4000]:
            val = reference_sensitivity(bw, mcs)
            assert val < 0
            assert val == PSK_SENSITIVITY[(mcs, bw)]

    def test_max_input_level(self):
        assert MAX_INPUT_LEVEL_DBM == -10.0


class TestSelectivity:
    """12.2.2 接收机选择性 — VALD-03"""

    @pytest.mark.parametrize("bw_khz", [100, 250, 1000, 2000, 4000])
    def test_freq_offsets_available(self, bw_khz: int):
        f1, f2, f3 = selectivity_freq_offsets(bw_khz)
        assert 0 < f1 < f2 < f3

    def test_selectivity_table_entries(self):
        assert len(SELECTIVITY_TABLE) >= 4

    def test_oob_2400_defined(self):
        assert len(OOB_2400) > 0
        for entry in OOB_2400:
            assert entry.freq_range[0] < entry.freq_range[1]

    def test_oob_5g_defined(self):
        assert len(OOB_5G) > 0


class TestIntermod:
    """12.2.2.3 干扰互调 — VALD-05"""

    def test_intermod_all_bandwidths(self):
        bws_covered = {e.bw_khz for e in INTERMOD_TABLE}
        for bw in [100, 125, 250, 500, 1000, 2000, 4000]:
            assert bw in bws_covered

    def test_intermod_parameters(self):
        for entry in INTERMOD_TABLE:
            assert entry.signal_offset_db == 6.0
            assert entry.interferer_level_dbm == -50.0
            assert 3 in entry.n_values


class TestRSSI:
    """12.2.3 RSSI 精度 — VALD-06"""

    def test_accurate_rssi(self):
        sens = reference_sensitivity(1000)
        actual = sens + 6.0
        measured = actual + 3.0
        assert check_rssi_accuracy(measured, actual, sens)

    def test_inaccurate_rssi(self):
        sens = reference_sensitivity(1000)
        actual = sens + 6.0
        measured = actual + RSSI_ACCURACY_DB + 1.0
        assert not check_rssi_accuracy(measured, actual, sens)

    def test_below_test_range(self):
        """低于测试门限的信号不判定为失败。"""
        sens = reference_sensitivity(1000)
        assert check_rssi_accuracy(-100.0, sens - 10.0, sens)


class TestRxSpurious:
    """12.2.4 接收机杂散发射"""

    def test_below_limit(self):
        assert check_rx_spurious_emission(-60.0)

    def test_at_limit(self):
        assert check_rx_spurious_emission(-57.0)

    def test_above_limit(self):
        assert not check_rx_spurious_emission(-50.0)


# ═══════════════════════════════════════════════════════════════════════
# 12.3 UWB 射频测试
# ═══════════════════════════════════════════════════════════════════════


class TestUWBChannel:
    """12.3.1 UWB 信道频率"""

    @pytest.mark.parametrize("nc,expected_mhz", [
        (0, 499.2),
        (1, 624.0),
        (9, 1622.4),
        (79, 10358.4),
    ])
    def test_standard_channels(self, nc: int, expected_mhz: float):
        assert abs(uwb_channel_center_freq_mhz(nc) - expected_mhz) < 0.01

    @pytest.mark.parametrize("nc,expected_mhz", [
        (125, 7542.6),
        (126, 18041.8),
        (127, 8541.0),
    ])
    def test_special_channels(self, nc: int, expected_mhz: float):
        assert uwb_channel_center_freq_mhz(nc) == expected_mhz

    def test_invalid_channel(self):
        with pytest.raises(ValueError):
            uwb_channel_center_freq_mhz(200)


class TestUWBSpectrumMask:
    """12.3.2 UWB 频谱模板"""

    def test_passband(self):
        mask = UWBSpectrumMask(pulse_width_ns=2.0)
        assert mask.check_spectrum(100e6, -5.0)

    def test_transition_band(self):
        mask = UWBSpectrumMask(pulse_width_ns=2.0)
        lo, hi = mask.transition_band_hz()
        mid = (lo + hi) / 2
        assert mask.check_spectrum(mid, -12.0)
        assert not mask.check_spectrum(mid, -8.0)

    def test_stopband(self):
        mask = UWBSpectrumMask(pulse_width_ns=2.0)
        _, hi = mask.transition_band_hz()
        assert mask.check_spectrum(hi + 1e6, -20.0)
        assert not mask.check_spectrum(hi + 1e6, -15.0)


class TestUWBNRMSE:
    """12.3.5 UWB 均方根误差"""

    def test_both_within_limit(self):
        assert check_uwb_nrmse(20.0, 20.0)

    def test_sync_exceeds_limit(self):
        assert not check_uwb_nrmse(UWB_MAX_NRMSE_PCT + 1, 15.0)

    def test_meas_exceeds_limit(self):
        assert not check_uwb_nrmse(15.0, UWB_MAX_NRMSE_PCT + 1)

    def test_diff_exceeds_2db(self):
        """sync/meas 比值超 2dB 应失败。"""
        assert not check_uwb_nrmse(24.0, 10.0)

    def test_diff_within_2db(self):
        assert check_uwb_nrmse(20.0, 18.0)
