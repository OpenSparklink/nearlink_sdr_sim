"""射频合规参数模块测试 — 标准第 8 章。"""

from __future__ import annotations

import pytest

from nearlink_sdr.phy.rf_compliance import (
    ACTIVE_CLOCK_JITTER_US,
    ACTIVE_CLOCK_PPM,
    GFSK_FREQ_DEV_SPECS,
    INTERMOD_TABLE,
    MAX_INPUT_LEVEL_DBM,
    OOB_5G,
    OOB_2400,
    OOB_SUB1G,
    PSK_EVM_LIMITS,
    SELECTIVITY_TABLE,
    SLEEP_CLOCK_JITTER_US,
    SLEEP_CLOCK_PPM,
    UWB_CLOCK_TOLERANCE_PPM,
    UWB_FREQ_TOLERANCE_PPM,
    UWB_MAX_NRMSE_PCT,
    ChannelBandwidth,
    FreqBand,
    GFSKFreqDevResult,
    PowerClass,
    PSKModulation,
    RFComplianceReport,
    UWBSpectrumMask,
    check_clock_accuracy,
    check_evm,
    check_freq_tolerance,
    check_gfsk_freq_dev,
    check_rssi_accuracy,
    check_uwb_nrmse,
    classify_power,
    get_psk_spectrum_mask,
    gfsk_inband_spurious_limit_dbm,
    reference_sensitivity,
    selectivity_freq_offsets,
    uwb_channel_center_freq_mhz,
    validate_power_step,
)

# ===== 8.2.1 输出功率等级 =====


class TestPowerClass:
    def test_classify_class0(self):
        assert classify_power(25.0) == PowerClass.CLASS_0

    def test_classify_class1(self):
        assert classify_power(20.0) == PowerClass.CLASS_1

    def test_classify_class2(self):
        assert classify_power(17.0) == PowerClass.CLASS_2

    def test_classify_class3(self):
        assert classify_power(12.0) == PowerClass.CLASS_3

    def test_classify_class4(self):
        assert classify_power(8.0) == PowerClass.CLASS_4

    def test_classify_class5(self):
        assert classify_power(2.0) == PowerClass.CLASS_5

    def test_classify_class6(self):
        assert classify_power(-5.0) == PowerClass.CLASS_6

    def test_classify_boundary_20(self):
        assert classify_power(20.0) == PowerClass.CLASS_1

    def test_power_step_valid(self):
        assert validate_power_step(10.0, 15.0) is True

    def test_power_step_exact_8db(self):
        assert validate_power_step(0.0, 8.0) is True

    def test_power_step_invalid(self):
        assert validate_power_step(0.0, 9.0) is False


# ===== 8.2.2.1 GFSK 频率偏差 =====


class TestGFSKFreqDev:
    def test_spec_table_complete(self):
        expected_rates = [0.1, 0.125, 0.25, 0.5, 1.0, 2.0, 4.0]
        for rate in expected_rates:
            assert rate in GFSK_FREQ_DEV_SPECS

    def test_1msps_pass(self):
        result = check_gfsk_freq_dev(1.0, 200.0, 250.0, 200.0, 0.1)
        assert result.passed

    def test_1msps_fd1_too_low(self):
        result = check_gfsk_freq_dev(1.0, 200.0, 200.0, 200.0, 0.1)
        assert not result.fd1_ok
        assert not result.passed

    def test_1msps_fd1_too_high(self):
        result = check_gfsk_freq_dev(1.0, 200.0, 300.0, 200.0, 0.1)
        assert not result.fd1_ok

    def test_fd2_below_min(self):
        result = check_gfsk_freq_dev(1.0, 200.0, 250.0, 100.0, 0.1)
        assert not result.fd2_ok

    def test_ratio_fail(self):
        result = check_gfsk_freq_dev(1.0, 200.0, 260.0, 180.0, 0.0)
        assert not result.ratio_ok

    def test_zero_crossing_fail(self):
        result = check_gfsk_freq_dev(1.0, 200.0, 250.0, 200.0, 0.2)
        assert not result.zero_crossing_ok

    def test_min_deviation_fail(self):
        result = check_gfsk_freq_dev(1.0, 100.0, 250.0, 200.0, 0.0)
        assert not result.min_ok

    def test_unsupported_rate(self):
        with pytest.raises(ValueError, match="不支持"):
            check_gfsk_freq_dev(3.0, 100.0, 200.0, 150.0)

    def test_all_rates_nominal(self):
        for rate, spec in GFSK_FREQ_DEV_SPECS.items():
            fd1 = (spec.fd1_min_khz + spec.fd1_max_khz) / 2
            fd2 = fd1 * 0.85  # 确保 fd2/fd1 >= 0.8 且 fd2 >= min
            fd2 = max(fd2, spec.fd2_min_khz + 1)
            result = check_gfsk_freq_dev(
                rate,
                spec.min_deviation_khz + 10,
                fd1,
                fd2,
                0.05,
            )
            assert result.passed, f"rate={rate} 未通过"


# ===== 8.2.2.2 PSK EVM =====


class TestPSKEVM:
    def test_bpsk_pass(self):
        assert check_evm(PSKModulation.PI2_BPSK, 15.0, 35.0, 40.0)

    def test_bpsk_fail_rms(self):
        assert not check_evm(PSKModulation.PI2_BPSK, 25.0, 35.0, 40.0)

    def test_qpsk_pass(self):
        assert check_evm(PSKModulation.PI4_QPSK, 10.0, 25.0, 30.0)

    def test_qpsk_fail_peak(self):
        assert not check_evm(PSKModulation.PI4_QPSK, 10.0, 25.0, 35.0)

    def test_8psk_pass(self):
        assert check_evm(PSKModulation.PI8_8PSK, 8.0, 18.0, 22.0)

    def test_8psk_boundary(self):
        assert check_evm(PSKModulation.PI8_8PSK, 9.0, 20.0, 25.0)

    def test_evm_limits_coverage(self):
        for mod in PSKModulation:
            assert mod in PSK_EVM_LIMITS


# ===== 8.2.2.3 频率容限 =====


class TestFreqTolerance:
    def test_2400_gfsk_pass(self):
        assert check_freq_tolerance(
            FreqBand.BAND_2400, "GFSK", 100.0, 30.0, 300.0)

    def test_2400_gfsk_fail_offset(self):
        assert not check_freq_tolerance(
            FreqBand.BAND_2400, "GFSK", 200.0, 30.0, 300.0)

    def test_5g_bpsk_pass(self):
        assert check_freq_tolerance(
            FreqBand.BAND_5100, "BPSK/QPSK", 100.0, 15.0, 30.0)

    def test_sub1g_pass(self):
        assert check_freq_tolerance(
            FreqBand.SUB_1G, "GFSK", 0.04, 0.0, 0.0,
            carrier_freq_mhz=490.0)

    def test_sub1g_fail_no_carrier(self):
        assert not check_freq_tolerance(
            FreqBand.SUB_1G, "GFSK", 0.04, 0.0, 0.0,
            carrier_freq_mhz=0.0)

    def test_unsupported_mod(self):
        with pytest.raises(ValueError, match="不支持"):
            check_freq_tolerance(
                FreqBand.BAND_2400, "QAM", 10.0, 1.0, 1.0)


# ===== 8.2.2.4 / 8.2.2.5 时钟精度 =====


class TestClockAccuracy:
    def test_active_pass(self):
        assert check_clock_accuracy(15.0, 1.5, is_sleep=False)

    def test_active_fail_ppm(self):
        assert not check_clock_accuracy(25.0, 1.5, is_sleep=False)

    def test_active_fail_jitter(self):
        assert not check_clock_accuracy(15.0, 3.0, is_sleep=False)

    def test_sleep_pass(self):
        assert check_clock_accuracy(400.0, 10.0, is_sleep=True)

    def test_sleep_fail(self):
        assert not check_clock_accuracy(600.0, 10.0, is_sleep=True)

    def test_constants(self):
        assert ACTIVE_CLOCK_PPM == 20.0
        assert SLEEP_CLOCK_PPM == 500.0
        assert ACTIVE_CLOCK_JITTER_US == 2.0
        assert SLEEP_CLOCK_JITTER_US == 16.0


# ===== 8.2.3 无用发射 =====


class TestGFSKSpurious:
    def test_1m_k2(self):
        assert gfsk_inband_spurious_limit_dbm(ChannelBandwidth.BW_1M, 2) == -20.0

    def test_1m_k3(self):
        assert gfsk_inband_spurious_limit_dbm(ChannelBandwidth.BW_1M, 3) == -30.0

    def test_2m_k4(self):
        assert gfsk_inband_spurious_limit_dbm(ChannelBandwidth.BW_2M, 4) == -20.0

    def test_2m_k5(self):
        assert gfsk_inband_spurious_limit_dbm(ChannelBandwidth.BW_2M, 5) == -23.0

    def test_2m_k6(self):
        assert gfsk_inband_spurious_limit_dbm(ChannelBandwidth.BW_2M, 6) == -30.0

    def test_4m_k8(self):
        assert gfsk_inband_spurious_limit_dbm(ChannelBandwidth.BW_4M, 8) == -20.0

    def test_4m_k10(self):
        assert gfsk_inband_spurious_limit_dbm(ChannelBandwidth.BW_4M, 10) == -23.0

    def test_4m_k11(self):
        assert gfsk_inband_spurious_limit_dbm(ChannelBandwidth.BW_4M, 11) == -30.0

    def test_100k_first_adj(self):
        assert gfsk_inband_spurious_limit_dbm(ChannelBandwidth.BW_100K, 0.2) == -30.0

    def test_100k_far(self):
        assert gfsk_inband_spurious_limit_dbm(ChannelBandwidth.BW_100K, 0.5) == -40.0


# ===== 8.2.3.2 PSK 频谱模板 =====


class TestPSKSpectrumMask:
    def test_wide_1m(self):
        mask = get_psk_spectrum_mask(ChannelBandwidth.BW_1M)
        assert mask.f1_mhz == 1.0
        assert mask.f4_mhz == 2.5

    def test_narrow_250k(self):
        mask = get_psk_spectrum_mask(ChannelBandwidth.BW_250K)
        assert mask.f1_mhz == 0.25
        assert mask.f3_mhz == 0.625

    def test_all_wide(self):
        for bw in [ChannelBandwidth.BW_1M, ChannelBandwidth.BW_2M,
                    ChannelBandwidth.BW_4M]:
            mask = get_psk_spectrum_mask(bw)
            assert mask.f4_mhz is not None

    def test_all_narrow(self):
        for bw in [ChannelBandwidth.BW_100K, ChannelBandwidth.BW_125K,
                    ChannelBandwidth.BW_250K, ChannelBandwidth.BW_500K]:
            mask = get_psk_spectrum_mask(bw)
            assert mask.f3_mhz is not None


# ===== 8.3.1 参考灵敏度 =====


class TestSensitivity:
    def test_gfsk_1m(self):
        assert reference_sensitivity(1000) == -70.0

    def test_gfsk_100k(self):
        assert reference_sensitivity(100) == pytest.approx(-79.9)

    def test_psk_mcs0_1m(self):
        assert reference_sensitivity(1000, mcs=0) == -81.0

    def test_psk_mcs12_4m(self):
        assert reference_sensitivity(4000, mcs=12) == -54.0

    def test_invalid_gfsk_bw(self):
        with pytest.raises(ValueError, match="不支持"):
            reference_sensitivity(300)

    def test_invalid_psk(self):
        with pytest.raises(ValueError, match="不支持"):
            reference_sensitivity(1000, mcs=99)

    def test_all_gfsk_bw(self):
        for bw in [100, 125, 250, 500, 1000, 2000, 4000]:
            val = reference_sensitivity(bw)
            assert val < 0

    def test_all_psk_mcs(self):
        for mcs in range(13):
            val = reference_sensitivity(1000, mcs=mcs)
            assert val < 0

    def test_max_input(self):
        assert MAX_INPUT_LEVEL_DBM == -10.0


# ===== 8.3.2 接收机选择性 =====


class TestSelectivity:
    def test_freq_offsets_1mhz(self):
        f1, f2, f3 = selectivity_freq_offsets(1000)
        assert f1 == 1.0
        assert f2 == 2.0
        assert f3 == 3.0

    def test_freq_offsets_all(self):
        for bw in [100, 125, 250, 500, 1000, 2000, 4000]:
            f1, f2, f3 = selectivity_freq_offsets(bw)
            assert f1 > 0 and f2 > f1 and f3 > f2

    def test_invalid_bw(self):
        with pytest.raises(ValueError, match="不支持"):
            selectivity_freq_offsets(300)

    def test_selectivity_table_entries(self):
        assert len(SELECTIVITY_TABLE) == 6

    def test_oob_tables_not_empty(self):
        assert len(OOB_SUB1G) > 0
        assert len(OOB_2400) > 0
        assert len(OOB_5G) > 0


# ===== 8.3.2.3 干扰互调 =====


class TestIntermod:
    def test_table_count(self):
        assert len(INTERMOD_TABLE) == 7

    def test_all_n_values(self):
        for entry in INTERMOD_TABLE:
            assert entry.n_values == (3, 4, 5)
            assert entry.interferer_level_dbm == -50.0


# ===== 8.3.4 RSSI =====


class TestRSSI:
    def test_pass(self):
        ref = -70.0
        actual = ref + 6.0
        measured = actual + 3.0
        assert check_rssi_accuracy(measured, actual, ref)

    def test_fail(self):
        ref = -70.0
        actual = ref + 6.0
        measured = actual + 8.0
        assert not check_rssi_accuracy(measured, actual, ref)

    def test_below_condition(self):
        ref = -70.0
        actual = ref + 2.0
        assert check_rssi_accuracy(999.0, actual, ref)


# ===== 8.4 UWB =====


class TestUWBChannel:
    def test_nc0(self):
        assert uwb_channel_center_freq_mhz(0) == pytest.approx(499.2)

    def test_nc1(self):
        assert uwb_channel_center_freq_mhz(1) == pytest.approx(624.0)

    def test_nc79(self):
        assert uwb_channel_center_freq_mhz(79) == pytest.approx(
            499.2 + 79 * 124.8)

    def test_special_125(self):
        assert uwb_channel_center_freq_mhz(125) == 7542.6

    def test_special_126(self):
        assert uwb_channel_center_freq_mhz(126) == 18041.8

    def test_special_127(self):
        assert uwb_channel_center_freq_mhz(127) == 8541.0

    def test_invalid(self):
        with pytest.raises(ValueError, match="超出范围"):
            uwb_channel_center_freq_mhz(100)


class TestUWBSpectrum:
    def test_in_main_lobe(self):
        mask = UWBSpectrumMask(pulse_width_ns=2.0)
        assert mask.check_spectrum(1e8, -5.0)

    def test_transition_band(self):
        mask = UWBSpectrumMask(pulse_width_ns=2.0)
        tp_s = 2e-9
        freq = 0.7 / tp_s
        assert mask.check_spectrum(freq, -12.0)
        assert not mask.check_spectrum(freq, -8.0)

    def test_outer_band(self):
        mask = UWBSpectrumMask(pulse_width_ns=2.0)
        tp_s = 2e-9
        freq = 0.9 / tp_s
        assert mask.check_spectrum(freq, -20.0)
        assert not mask.check_spectrum(freq, -15.0)

    def test_transition_band_boundaries(self):
        mask = UWBSpectrumMask(pulse_width_ns=2.0)
        lo, hi = mask.transition_band_hz()
        assert hi > lo > 0


class TestUWBNRMSE:
    def test_pass(self):
        assert check_uwb_nrmse(15.0, 15.0)

    def test_sync_too_high(self):
        assert not check_uwb_nrmse(30.0, 15.0)

    def test_meas_too_high(self):
        assert not check_uwb_nrmse(15.0, 30.0)

    def test_diff_too_large(self):
        assert not check_uwb_nrmse(10.0, 20.0)

    def test_zero_values(self):
        assert not check_uwb_nrmse(0.0, 10.0)

    def test_constants(self):
        assert UWB_MAX_NRMSE_PCT == 25.0
        assert UWB_FREQ_TOLERANCE_PPM == 20.0
        assert UWB_CLOCK_TOLERANCE_PPM == 20.0


# ===== RFComplianceReport =====


class TestRFReport:
    def test_empty_report_not_passed(self):
        r = RFComplianceReport()
        assert not r.passed

    def test_all_pass(self):
        r = RFComplianceReport(
            power_class=PowerClass.CLASS_3,
            power_step_ok=True,
            gfsk_dev=GFSKFreqDevResult(True, True, True, True, True),
            evm_ok=True,
            freq_tolerance_ok=True,
            clock_ok=True,
            spurious_ok=True,
            sensitivity_dbm=-70.0,
            selectivity_ok=True,
            rssi_ok=True,
            uwb_spectrum_ok=True,
            uwb_nrmse_ok=True,
        )
        assert r.passed

    def test_one_fail(self):
        r = RFComplianceReport(
            power_step_ok=True,
            evm_ok=False,
        )
        assert not r.passed
