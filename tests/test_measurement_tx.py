"""测量链路传输与测量量测试 -- TXS-10002-2025 标准 6.7/6.8。

验证测量链路参数、时间资源调度和测量量计算。
"""

from __future__ import annotations

import cmath
import math

import numpy as np

from nearlink_sdr.phy.measurement_tx import (
    UWB_CONFIG_TIME_GRANULARITY_TC,
    ChannelSpliceMode,
    CIRConfig,
    EventFrameType,
    HoppingOrder,
    MeasBandwidth,
    MeasDirection,
    MeasLinkParams,
    NodeMeasConfig,
    SecurityType,
    TimeRefType,
    UWBMeasLinkParams,
    UWBMeasMode,
    angle_estimate,
    compute_csi_feedback,
    csi_to_rx_power,
    ds_twr_2msg,
    ds_twr_3msg,
    event_schedule,
    event_start_times,
    extract_cir,
    range_doppler,
    uwb_event_count_per_mode,
    uwb_event_sender,
)

# -----------------------------------------------------------------------
# 枚举测试
# -----------------------------------------------------------------------


class TestEnums:
    def test_meas_direction(self):
        assert MeasDirection.UNIDIRECTIONAL == 0
        assert MeasDirection.BIDIRECTIONAL == 1

    def test_hopping_order(self):
        assert HoppingOrder.LOW_TO_HIGH == 0
        assert HoppingOrder.HIGH_TO_LOW == 1
        assert HoppingOrder.ALGORITHMIC == 2

    def test_meas_bandwidth(self):
        assert MeasBandwidth.BW_1MHZ == 0
        assert MeasBandwidth.BW_4MHZ == 2

    def test_security_type(self):
        assert SecurityType.NONE == 0
        assert SecurityType.SECURE == 1

    def test_time_ref_type(self):
        assert TimeRefType.FIRST_PATH == 0
        assert TimeRefType.STRONGEST_PATH == 1
        assert TimeRefType.TX_TIME == 2


# -----------------------------------------------------------------------
# 参数模型测试
# -----------------------------------------------------------------------


class TestMeasLinkParams:
    def test_defaults(self):
        p = MeasLinkParams()
        assert p.event_count == 4
        assert p.ft1_period == 2
        assert p.has_init_phase is False
        assert p.direction == MeasDirection.UNIDIRECTIONAL

    def test_multi_antenna(self):
        p = MeasLinkParams()
        assert p.has_multi_antenna is False
        p.first_node.antenna_count = 2
        assert p.has_multi_antenna is True

    def test_node_config_defaults(self):
        n = NodeMeasConfig()
        assert n.sync_signal_length == 64
        assert n.meas_signal_length == 128
        assert n.antenna_count == 1
        assert n.security_type == SecurityType.NONE


# -----------------------------------------------------------------------
# 6.7.4 事件调度测试
# -----------------------------------------------------------------------


class TestEventSchedule:
    def test_all_type1_period_1(self):
        """ft1_period=1: 所有事件都是类型1。"""
        p = MeasLinkParams(event_count=4, ft1_period=1, has_init_phase=False)
        sched = event_schedule(p)
        assert len(sched) == 4
        assert all(ft == EventFrameType.TYPE_1 for _, ft in sched)

    def test_all_type2_period_0(self):
        """ft1_period=0: 所有事件都是类型2。"""
        p = MeasLinkParams(event_count=3, ft1_period=0)
        sched = event_schedule(p)
        assert all(ft == EventFrameType.TYPE_2 for _, ft in sched)

    def test_alternating_period_2(self):
        """ft1_period=2: 偶数索引类型1, 奇数类型2。"""
        p = MeasLinkParams(event_count=6, ft1_period=2, has_init_phase=False)
        sched = event_schedule(p)
        for idx, ft in sched:
            if idx % 2 == 0:
                assert ft == EventFrameType.TYPE_1
            else:
                assert ft == EventFrameType.TYPE_2

    def test_with_init_phase(self):
        """初始化阶段: 第0个事件为INIT。"""
        p = MeasLinkParams(event_count=5, ft1_period=2, has_init_phase=True)
        sched = event_schedule(p)
        assert sched[0] == (0, EventFrameType.INIT)
        # 后续事件按 ft1_period 分配
        assert sched[1][1] == EventFrameType.TYPE_2  # idx=1, 奇数
        assert sched[2][1] == EventFrameType.TYPE_1  # idx=2, 偶数
        assert sched[3][1] == EventFrameType.TYPE_2  # idx=3, 奇数
        assert sched[4][1] == EventFrameType.TYPE_1  # idx=4, 偶数

    def test_init_phase_period_0(self):
        """初始化+ft1_period=0: INIT后全部TYPE_2。"""
        p = MeasLinkParams(event_count=3, ft1_period=0, has_init_phase=True)
        sched = event_schedule(p)
        assert sched[0][1] == EventFrameType.INIT
        assert sched[1][1] == EventFrameType.TYPE_2
        assert sched[2][1] == EventFrameType.TYPE_2

    def test_single_event(self):
        p = MeasLinkParams(event_count=1, ft1_period=1)
        sched = event_schedule(p)
        assert len(sched) == 1
        assert sched[0] == (0, EventFrameType.TYPE_1)


class TestEventStartTimes:
    def test_first_group(self):
        p = MeasLinkParams(
            event_group_start_us=1000.0,
            event_count=3,
            ft1_period=1,
            ft1_inter_event_us=500.0,
        )
        times = event_start_times(p, group_index=0)
        assert len(times) == 3
        assert times[0] == 1000.0
        assert times[1] == 1500.0
        assert times[2] == 2000.0

    def test_second_group_offset(self):
        p = MeasLinkParams(
            event_group_start_us=0.0,
            event_group_period_us=10000.0,
            event_count=2,
            ft1_period=1,
            ft1_inter_event_us=300.0,
        )
        times = event_start_times(p, group_index=1)
        assert times[0] == 10000.0
        assert times[1] == 10300.0

    def test_mixed_intervals(self):
        """类型1和类型2使用不同间隔。"""
        p = MeasLinkParams(
            event_group_start_us=0.0,
            event_count=4,
            ft1_period=2,
            ft1_inter_event_us=500.0,
            ft2_inter_event_us=300.0,
        )
        times = event_start_times(p, group_index=0)
        assert times[0] == 0.0
        # event 0 = TYPE_1, 间隔 500
        assert times[1] == 500.0
        # event 1 = TYPE_2, 间隔 300
        assert times[2] == 800.0
        # event 2 = TYPE_1, 间隔 500
        assert times[3] == 1300.0

    def test_init_event_interval(self):
        p = MeasLinkParams(
            event_group_start_us=0.0,
            event_count=3,
            ft1_period=1,
            has_init_phase=True,
            init_inter_event_us=400.0,
            ft1_inter_event_us=500.0,
        )
        times = event_start_times(p, group_index=0)
        assert times[0] == 0.0
        assert times[1] == 400.0   # INIT -> next: 400us
        assert times[2] == 900.0   # TYPE_1 -> next: 500us


# -----------------------------------------------------------------------
# 6.8.5.1 DS-TWR 两消息测试
# -----------------------------------------------------------------------


class TestDsTwr2Msg:
    def test_symmetric_case(self):
        """对称情况: Ra=100, Db=80 → Tprop=10。"""
        assert ds_twr_2msg(100.0, 80.0) == 10.0

    def test_zero_propagation(self):
        """零飞行时间: Ra=Db。"""
        assert ds_twr_2msg(50.0, 50.0) == 0.0

    def test_typical_uwb(self):
        """典型 UWB 测距: ~10ns 飞行时间 (~3m)。"""
        tprop = ds_twr_2msg(1020.0, 1000.0)
        assert abs(tprop - 10.0) < 1e-10


# -----------------------------------------------------------------------
# 6.8.5.2 DS-TWR 三消息测试
# -----------------------------------------------------------------------


class TestDsTwr3Msg:
    def test_symmetric_case(self):
        """对称情况。"""
        # Ra=Rb=110, Da=Db=100 → Tprop = (110*110 - 100*100)/(110+110+100+100)
        # = (12100-10000)/420 = 2100/420 = 5.0
        tprop = ds_twr_3msg(110.0, 110.0, 100.0, 100.0)
        assert abs(tprop - 5.0) < 1e-10

    def test_asymmetric(self):
        """非对称情况。"""
        tprop = ds_twr_3msg(120.0, 100.0, 90.0, 80.0)
        expected = (120 * 100 - 90 * 80) / (120 + 100 + 90 + 80)
        assert abs(tprop - expected) < 1e-10

    def test_zero_denominator(self):
        """分母为零时返回0。"""
        assert ds_twr_3msg(0, 0, 0, 0) == 0.0

    def test_known_distance(self):
        """已知飞行时间 10ns, 验证公式正确性。"""
        tprop = 10.0  # ns
        # 模拟: 先发→后发, 后发→先发, 先发→后发
        # Ra = 2*tprop + Db (first round), Rb = 2*tprop + Da (second round)
        da = 50.0
        db = 60.0
        ra = 2 * tprop + db  # = 80
        rb = 2 * tprop + da  # = 70
        result = ds_twr_3msg(ra, rb, da, db)
        assert abs(result - tprop) < 1e-10


# -----------------------------------------------------------------------
# 6.8.5.3 角度测量量测试
# -----------------------------------------------------------------------


class TestAngleEstimate:
    def test_broadside(self):
        """正面到达: 相位差=0 → 角度=90°。"""
        angle = angle_estimate(0.0, 0.06, 0.03)
        assert abs(angle - math.pi / 2) < 1e-10

    def test_endfire(self):
        """端射方向: cos(θ)=1 → θ=0。"""
        wavelength = 0.06  # m
        d = 0.03  # m, half wavelength
        delta_phi = 2 * math.pi * d / wavelength  # = pi
        angle = angle_estimate(delta_phi, wavelength, d)
        assert abs(angle) < 1e-10

    def test_clipping(self):
        """超范围相位差被裁剪。"""
        # 大相位差导致 cos > 1, 应被裁剪到 0
        angle = angle_estimate(100.0, 0.06, 0.03)
        assert abs(angle) < 1e-10

    def test_45_degrees(self):
        """45度到达角。"""
        wavelength = 0.06
        d = 0.03
        theta = math.pi / 4  # 45°
        delta_phi = 2 * math.pi * d * math.cos(theta) / wavelength
        estimated = angle_estimate(delta_phi, wavelength, d)
        assert abs(estimated - theta) < 1e-6


# -----------------------------------------------------------------------
# 6.8.5.4 CIR 测试
# -----------------------------------------------------------------------


class TestExtractCIR:
    def test_basic_extraction(self):
        sig = np.arange(1000, dtype=np.complex128)
        cfg = CIRConfig(
            sample_rate_hz=1e9,
            delay_offset_ns=0.0,
            delay_length_ns=10.0,
        )
        cir = extract_cir(sig, cfg, ref_sample=100)
        assert len(cir) == 10  # 10ns * 1GHz = 10 samples
        np.testing.assert_array_equal(cir, sig[100:110])

    def test_with_offset(self):
        sig = np.ones(500, dtype=np.complex128) * 3.0
        cfg = CIRConfig(
            sample_rate_hz=1e9,
            delay_offset_ns=5.0,
            delay_length_ns=10.0,
        )
        cir = extract_cir(sig, cfg, ref_sample=50)
        assert len(cir) == 10
        assert cir[0] == 3.0

    def test_boundary_clamping(self):
        sig = np.ones(20, dtype=np.complex128)
        cfg = CIRConfig(
            sample_rate_hz=1e9,
            delay_offset_ns=0.0,
            delay_length_ns=100.0,  # 请求超出信号长度
        )
        cir = extract_cir(sig, cfg, ref_sample=15)
        assert len(cir) == 5  # 只有 20-15=5 个采样

    def test_uwb_sample_rate(self):
        sr = 499.2e6
        sig = np.zeros(int(sr * 200e-9), dtype=np.complex128)
        cfg = CIRConfig(sample_rate_hz=sr, delay_length_ns=50.0)
        cir = extract_cir(sig, cfg, ref_sample=0)
        expected_len = int(50.0 * sr / 1e9)
        assert len(cir) == expected_len


# -----------------------------------------------------------------------
# 6.8.5.5 距离多普勒测试
# -----------------------------------------------------------------------


class TestRangeDoppler:
    def test_1d(self):
        sig = np.array([1, 2, 3, 4], dtype=np.complex128)
        rd = range_doppler(sig)
        np.testing.assert_array_almost_equal(rd, np.fft.fft(sig))

    def test_2d(self):
        cir = np.random.randn(8, 32) + 1j * np.random.randn(8, 32)
        rd = range_doppler(cir)
        assert rd.shape == (8, 32)
        np.testing.assert_array_almost_equal(rd, np.fft.fft(cir, axis=0))

    def test_single_frame(self):
        cir = np.ones((1, 16), dtype=np.complex128)
        rd = range_doppler(cir)
        # FFT of single frame along axis=0 = identity
        np.testing.assert_array_almost_equal(rd, cir)


# -----------------------------------------------------------------------
# CSI 反馈测试
# -----------------------------------------------------------------------


class TestCSIFeedback:
    def test_compute_feedback(self):
        fb = compute_csi_feedback(-50.0, 1.0 + 0j)
        assert fb.ref_power_dbm == -50.0
        assert abs(abs(fb.relative_iq) - 1024.0) < 0.01

    def test_roundtrip_power(self):
        """rx_power → feedback → csi_to_rx_power 应还原。"""
        fb = compute_csi_feedback(-40.0, 0.5 + 0.5j)
        recovered = csi_to_rx_power(fb)
        assert abs(recovered - (-40.0)) < 0.01

    def test_zero_iq(self):
        fb = compute_csi_feedback(-60.0, 0j)
        assert fb.relative_iq == 0j

    def test_phase_preserved(self):
        """相位信息应保留。"""
        original_phase = math.pi / 3
        channel = cmath.exp(1j * original_phase)
        fb = compute_csi_feedback(-30.0, channel)
        recovered_phase = cmath.phase(fb.relative_iq)
        assert abs(recovered_phase - original_phase) < 1e-10

    def test_various_powers(self):
        for pwr in [-80, -60, -40, -20, 0]:
            fb = compute_csi_feedback(float(pwr), 1.0 + 0j)
            recovered = csi_to_rx_power(fb)
            assert abs(recovered - pwr) < 0.01


# -----------------------------------------------------------------------
# 6.8 UWB 测量链路参数与调度测试
# -----------------------------------------------------------------------


class TestUWBMeasMode:
    def test_modes(self):
        assert UWBMeasMode.ONE_WAY == 0
        assert UWBMeasMode.DS_TWR_2MSG == 1
        assert UWBMeasMode.DS_TWR_3MSG == 2

    def test_channel_splice_mode(self):
        assert ChannelSpliceMode.NONE == 0
        assert ChannelSpliceMode.OVERLAP == 1
        assert ChannelSpliceMode.CONTINUOUS == 2
        assert ChannelSpliceMode.NON_CONTINUOUS == 3


class TestUWBMeasLinkParams:
    def test_defaults(self):
        p = UWBMeasLinkParams()
        assert p.mode == UWBMeasMode.DS_TWR_2MSG
        assert p.event_count == 4
        assert p.channels == [0]
        assert p.secure_mode is False

    def test_antenna_pairs(self):
        p = UWBMeasLinkParams(tx_antenna_count=2, rx_antenna_count=3)
        assert p.total_antenna_pairs == 6

    def test_single_antenna(self):
        p = UWBMeasLinkParams()
        assert p.total_antenna_pairs == 1

    def test_granularity_constant(self):
        assert UWB_CONFIG_TIME_GRANULARITY_TC == 256


class TestUWBEventSender:
    def test_fixed_sender(self):
        p = UWBMeasLinkParams(first_sender=0, alternate_sender=False)
        for i in range(5):
            assert uwb_event_sender(p, i) == 0

    def test_fixed_sender_1(self):
        p = UWBMeasLinkParams(first_sender=1, alternate_sender=False)
        assert uwb_event_sender(p, 0) == 1

    def test_alternate_sender(self):
        p = UWBMeasLinkParams(first_sender=0, alternate_sender=True)
        assert uwb_event_sender(p, 0) == 0
        assert uwb_event_sender(p, 1) == 1
        assert uwb_event_sender(p, 2) == 0
        assert uwb_event_sender(p, 3) == 1

    def test_alternate_from_1(self):
        p = UWBMeasLinkParams(first_sender=1, alternate_sender=True)
        assert uwb_event_sender(p, 0) == 1
        assert uwb_event_sender(p, 1) == 0


class TestUWBEventCount:
    def test_one_way(self):
        assert uwb_event_count_per_mode(UWBMeasMode.ONE_WAY) == 1

    def test_2msg(self):
        assert uwb_event_count_per_mode(UWBMeasMode.DS_TWR_2MSG) == 2

    def test_3msg(self):
        assert uwb_event_count_per_mode(UWBMeasMode.DS_TWR_3MSG) == 3
