"""测量帧结构测试 -- TXS-10002-2025 标准 6.3.6-6.3.11"""

from __future__ import annotations

import numpy as np
import pytest

from nearlink_sdr.phy.measurement_frame import (
    MeasFrameConfig,
    RadioFrameType,
    UWBPulseConfig,
    build_measurement_frame_1,
    build_measurement_frame_2,
    build_measurement_frame_3,
    build_measurement_frame_4,
    build_nack_feedback,
    build_uwb_measurement_field,
    build_uwb_pulse_measurement_frame,
    build_uwb_sync_field,
    equalization_guard,
)

# -----------------------------------------------------------------------
# 6.3.6 半可靠组播反馈
# -----------------------------------------------------------------------


class TestNackFeedback:
    """半可靠组播 NACK 反馈序列测试。"""

    def test_ft1_length(self):
        """FT1 使用 m31 序列, 长度 31。"""
        seq = build_nack_feedback(RadioFrameType.FT1, m_index=0)
        assert len(seq) == 31

    def test_ft2_length(self):
        """FT2 使用两段 m31 拼接, 长度 62。"""
        seq = build_nack_feedback(RadioFrameType.FT2, m_index=0)
        assert len(seq) == 62

    def test_ft3_length(self):
        """FT3 使用两段 m31 拼接, 长度 62。"""
        seq = build_nack_feedback(RadioFrameType.FT3, m_index=0)
        assert len(seq) == 62

    def test_ft4_length(self):
        """FT4 使用两段 m63 拼接, 长度 126。"""
        seq = build_nack_feedback(RadioFrameType.FT4, m_index=0)
        assert len(seq) == 126

    def test_cyclic_shift_preserves_length(self):
        seq_no_shift = build_nack_feedback(RadioFrameType.FT1, m_index=0, cyclic_shift=0)
        seq_shifted = build_nack_feedback(RadioFrameType.FT1, m_index=0, cyclic_shift=5)
        assert len(seq_no_shift) == len(seq_shifted)

    def test_cyclic_shift_changes_content(self):
        seq_a = build_nack_feedback(RadioFrameType.FT1, m_index=0, cyclic_shift=0)
        seq_b = build_nack_feedback(RadioFrameType.FT1, m_index=0, cyclic_shift=3)
        assert not np.array_equal(seq_a, seq_b)

    def test_invalid_ft_raises(self):
        with pytest.raises(ValueError, match="radio_ft"):
            build_nack_feedback(5, m_index=0)

    def test_different_m_index(self):
        seq_a = build_nack_feedback(RadioFrameType.FT2, m_index=0)
        seq_b = build_nack_feedback(RadioFrameType.FT2, m_index=1)
        assert not np.array_equal(seq_a, seq_b)


# -----------------------------------------------------------------------
# 6.3.7 均衡保护
# -----------------------------------------------------------------------


class TestEqualizationGuard:
    """均衡保护序列测试。"""

    def test_last_bit_one(self):
        guard = equalization_guard(1)
        np.testing.assert_array_equal(guard, [0, 1, 0, 1])

    def test_last_bit_zero(self):
        guard = equalization_guard(0)
        np.testing.assert_array_equal(guard, [1, 0, 1, 0])

    def test_length(self):
        assert len(equalization_guard(0)) == 4
        assert len(equalization_guard(1)) == 4


# -----------------------------------------------------------------------
# 6.3.7 测量帧类型 1
# -----------------------------------------------------------------------


class TestMeasurementFrame1:
    """测量帧类型 1 结构测试。"""

    @pytest.fixture()
    def config(self):
        return MeasFrameConfig(
            sync_signal=np.array([1, 0, 1, 1], dtype=np.int8),
            measurement_signal=np.ones(20, dtype=np.int8),
            switch_interval_samples=8,
            symbol_rate_mhz=1.0,
            radio_frame_type=2,
            is_first_sender=True,
        )

    def test_first_sender_contains_all_parts(self, config):
        frame = build_measurement_frame_1(config)
        # 应包含 前导 + 同步(4) + 均衡保护(4) + 切换(8) + 测量(20)
        assert len(frame) > 4 + 4 + 8 + 20

    def test_second_sender_structure(self, config):
        config.is_first_sender = False
        frame = build_measurement_frame_1(config)
        # 后发节点: 测量(20) + 切换(8) + 前导 + 同步(4) + 均衡保护(4)
        assert len(frame) > 20 + 8 + 4 + 4

    def test_first_and_second_differ(self, config):
        frame_first = build_measurement_frame_1(config)
        config.is_first_sender = False
        frame_second = build_measurement_frame_1(config)
        # 长度相同但内容不同
        assert len(frame_first) == len(frame_second)
        assert not np.array_equal(frame_first, frame_second)

    def test_guard_matches_sync_last_bit(self, config):
        config.sync_signal = np.array([1, 0, 1, 1], dtype=np.int8)
        frame = build_measurement_frame_1(config)
        # 同步信号最后一位是 1, 均衡保护应为 0101
        preamble_len = len(
            __import__("nearlink_sdr.phy.preamble", fromlist=["generate_preamble"])
            .generate_preamble(2, 1.0)
        )
        sync_len = 4
        guard = frame[preamble_len + sync_len: preamble_len + sync_len + 4]
        np.testing.assert_array_equal(guard, [0, 1, 0, 1])


# -----------------------------------------------------------------------
# 6.3.8 测量帧类型 2
# -----------------------------------------------------------------------


class TestMeasurementFrame2:
    """测量帧类型 2 结构测试。"""

    def test_only_measurement_signal(self):
        meas = np.array([1, 0, 1, 0, 1], dtype=np.int8)
        config = MeasFrameConfig(measurement_signal=meas)
        frame = build_measurement_frame_2(config)
        np.testing.assert_array_equal(frame, meas)

    def test_returns_copy(self):
        meas = np.array([1, 0, 1], dtype=np.int8)
        config = MeasFrameConfig(measurement_signal=meas)
        frame = build_measurement_frame_2(config)
        frame[0] = 99
        assert config.measurement_signal[0] == 1


# -----------------------------------------------------------------------
# 6.3.9 测量帧类型 3
# -----------------------------------------------------------------------


class TestMeasurementFrame3:
    """测量帧类型 3 结构测试。"""

    @pytest.fixture()
    def config(self):
        return MeasFrameConfig(
            sync_signal=np.array([0, 1, 0, 1], dtype=np.int8),
            measurement_signal=np.ones(16, dtype=np.int8),
            switch_interval_samples=4,
            radio_frame_type=2,
        )

    def test_first_sender_no_measurement(self, config):
        config.is_first_sender = True
        frame = build_measurement_frame_3(config)
        preamble = __import__(
            "nearlink_sdr.phy.preamble", fromlist=["generate_preamble"]
        ).generate_preamble(2, 1.0)
        # 先发节点仅包含 前导 + 同步 + 均衡保护
        expected_len = len(preamble) + 4 + 4
        assert len(frame) == expected_len

    def test_second_sender_has_measurement(self, config):
        config.is_first_sender = False
        frame = build_measurement_frame_3(config)
        preamble = __import__(
            "nearlink_sdr.phy.preamble", fromlist=["generate_preamble"]
        ).generate_preamble(2, 1.0)
        expected_len = len(preamble) + 4 + 4 + 4 + 16
        assert len(frame) == expected_len


# -----------------------------------------------------------------------
# 6.3.10 测量帧类型 4
# -----------------------------------------------------------------------


class TestMeasurementFrame4:
    """测量帧类型 4 结构测试。"""

    def test_structure_same_for_both_roles(self):
        config = MeasFrameConfig(
            sync_signal=np.array([1, 1, 0, 0], dtype=np.int8),
            measurement_signal=np.ones(10, dtype=np.int8),
            switch_interval_samples=4,
            radio_frame_type=2,
        )
        config.is_first_sender = True
        frame_first = build_measurement_frame_4(config)
        config.is_first_sender = False
        frame_second = build_measurement_frame_4(config)
        np.testing.assert_array_equal(frame_first, frame_second)

    def test_contains_all_parts(self):
        meas = np.ones(12, dtype=np.int8)
        config = MeasFrameConfig(
            sync_signal=np.array([0, 1], dtype=np.int8),
            measurement_signal=meas,
            switch_interval_samples=6,
            radio_frame_type=2,
        )
        frame = build_measurement_frame_4(config)
        preamble = __import__(
            "nearlink_sdr.phy.preamble", fromlist=["generate_preamble"]
        ).generate_preamble(2, 1.0)
        expected_len = len(preamble) + 2 + 4 + 6 + 12
        assert len(frame) == expected_len


# -----------------------------------------------------------------------
# 6.3.11 超宽带脉冲测量帧
# -----------------------------------------------------------------------


class TestUWBSyncField:
    """超宽带脉冲同步字段测试。"""

    def test_sync_length(self):
        cfg = UWBPulseConfig(K=31, L=4, N_sync=8)
        sync = build_uwb_sync_field(cfg)
        assert len(sync) == 8 * 31 * 4

    def test_sync_zero_means_empty(self):
        cfg = UWBPulseConfig(N_sync=0)
        assert len(build_uwb_sync_field(cfg)) == 0

    def test_sync_repeats(self):
        cfg = UWBPulseConfig(K=7, L=2, N_sync=3, symbol_seq=np.ones(7))
        sync = build_uwb_sync_field(cfg)
        one_sym = sync[: 7 * 2]
        for i in range(3):
            np.testing.assert_array_equal(sync[i * 14: (i + 1) * 14], one_sym)

    def test_duty_cycle_zeros(self):
        """占空比 L=4 时, 每 4 个码片仅第一个非零。"""
        sym = np.array([1, -1, 1], dtype=np.float64)
        cfg = UWBPulseConfig(K=3, L=4, N_sync=1, symbol_seq=sym)
        sync = build_uwb_sync_field(cfg)
        assert len(sync) == 12
        expected = [1, 0, 0, 0, -1, 0, 0, 0, 1, 0, 0, 0]
        np.testing.assert_array_equal(sync, expected)


class TestUWBMeasurementField:
    """超宽带脉冲测量字段测试。"""

    def test_single_segment_single_cts(self):
        cfg = UWBPulseConfig(K=7, L=2, M_seg=1, N_seg=1)
        meas = build_uwb_measurement_field(cfg)
        assert len(meas) == 7 * 2

    def test_multiple_segments_with_gap(self):
        cfg = UWBPulseConfig(K=7, L=2, M_seg=3, N_seg=1, N_gap=2)
        meas = build_uwb_measurement_field(cfg)
        sym_len = 7 * 2
        gap_chips = 2 * sym_len
        # 3 segments, 2 gaps
        expected = 3 * sym_len + 2 * gap_chips
        assert len(meas) == expected

    def test_multiple_cts_per_segment(self):
        cfg = UWBPulseConfig(K=7, L=2, M_seg=2, N_seg=2, N_gap=1)
        meas = build_uwb_measurement_field(cfg)
        sym_len = 7 * 2
        gap_chips = 1 * sym_len
        # 2 segments * 2 cts + 1 gap
        expected = 4 * sym_len + 1 * gap_chips
        assert len(meas) == expected

    def test_scramble_applied(self):
        cfg_no_scr = UWBPulseConfig(K=3, L=1, M_seg=1, N_seg=2)
        cfg_scr = UWBPulseConfig(
            K=3, L=1, M_seg=1, N_seg=2,
            scramble=np.array([1.0, -1.0]),
        )
        meas_no = build_uwb_measurement_field(cfg_no_scr)
        meas_scr = build_uwb_measurement_field(cfg_scr)
        # 第 2 个 CTS 符号应被翻转
        assert not np.array_equal(meas_no, meas_scr)

    def test_empty_if_zero_segments(self):
        cfg = UWBPulseConfig(M_seg=0, N_seg=0)
        assert len(build_uwb_measurement_field(cfg)) == 0

    def test_security_mode_cp_and_zero(self):
        """安全模式下增加循环前缀和补零后缀。"""
        cfg = UWBPulseConfig(K=4, L=2, M_seg=1, N_seg=1, L_cp=2, L_zero=3)
        meas = build_uwb_measurement_field(cfg)
        # 正常 4*2=8, 加 CP=2 + zero=3 = 13
        assert len(meas) == 8 + 2 + 3


class TestUWBPulseFullFrame:
    """完整超宽带脉冲测量帧测试。"""

    def test_full_frame_length(self):
        cfg = UWBPulseConfig(K=31, L=4, N_sync=4, M_seg=2, N_seg=1, N_gap=2)
        frame = build_uwb_pulse_measurement_frame(cfg)
        sync_len = 4 * 31 * 4
        sym_len = 31 * 4
        gap_chips = 2 * sym_len
        meas_len = 2 * sym_len + 1 * gap_chips
        assert len(frame) == sync_len + meas_len

    def test_no_sync_frame(self):
        cfg = UWBPulseConfig(K=7, L=2, N_sync=0, M_seg=1, N_seg=1)
        frame = build_uwb_pulse_measurement_frame(cfg)
        assert len(frame) == 7 * 2

    def test_custom_cts_sequence(self):
        sym = np.array([1, -1, 1, -1], dtype=np.float64)
        cfg = UWBPulseConfig(K=4, L=1, N_sync=0, M_seg=1, N_seg=1)
        frame = build_uwb_pulse_measurement_frame(cfg, cts_symbol_seq=sym)
        np.testing.assert_array_equal(frame, sym)
