"""位置信息测量信号测试 -- TXS-10002-2025 标准 6.2.4"""

from __future__ import annotations

import numpy as np
import pytest

from nearlink_sdr.phy.measurement import (
    SecurityType,
    antenna_pair_order_random,
    antenna_pair_order_sequential,
    measurement_signal_1,
    measurement_signal_2,
)

# -----------------------------------------------------------------------
# 6.2.4.1 测量信号 1
# -----------------------------------------------------------------------


class TestMeasurementSignal1:
    """测量信号 1 基本属性测试"""

    SEED = b"\xAA" * 16

    @pytest.mark.parametrize("n", [16, 32, 64, 128, 256, 512, 1024, 2048])
    def test_length(self, n):
        seq = measurement_signal_1(
            n, SecurityType.TYPE_4, seed=self.SEED
        )
        assert len(seq) == n

    def test_binary_values(self):
        seq = measurement_signal_1(
            64, SecurityType.TYPE_1, seed=self.SEED,
            slot_number=10, n_disturb_max=5,
        )
        assert set(seq).issubset({0, 1})

    def test_type4_all_zeros(self):
        seq = measurement_signal_1(128, SecurityType.TYPE_4)
        assert np.all(seq == 0)

    def test_type3_constant_bits(self):
        seed = b"\xBB" * 16
        tx = measurement_signal_1(
            64, SecurityType.TYPE_3, seed=seed,
            slot_number=5, is_tx=True,
        )
        # 安全类型3: 全部比特相同
        assert len(set(tx)) == 1

    def test_type3_tx_rx_may_differ(self):
        seed = b"\xCC" * 16
        tx = measurement_signal_1(
            64, SecurityType.TYPE_3, seed=seed,
            slot_number=7, is_tx=True,
        )
        rx = measurement_signal_1(
            64, SecurityType.TYPE_3, seed=seed,
            slot_number=7, is_tx=False,
        )
        # TX 和 RX 序列可能全0或全1, 取决于安全序列
        assert len(set(tx)) == 1
        assert len(set(rx)) == 1

    def test_type1_deterministic(self):
        s1 = measurement_signal_1(
            32, SecurityType.TYPE_1, seed=self.SEED,
            slot_number=42, n_disturb_max=5,
        )
        s2 = measurement_signal_1(
            32, SecurityType.TYPE_1, seed=self.SEED,
            slot_number=42, n_disturb_max=5,
        )
        assert np.array_equal(s1, s2)

    def test_type1_different_slots(self):
        s1 = measurement_signal_1(
            32, SecurityType.TYPE_1, seed=self.SEED,
            slot_number=0, n_disturb_max=5,
        )
        s2 = measurement_signal_1(
            32, SecurityType.TYPE_1, seed=self.SEED,
            slot_number=1, n_disturb_max=5,
        )
        assert not np.array_equal(s1, s2)

    def test_type2_binary(self):
        seq = measurement_signal_1(
            64, SecurityType.TYPE_2, seed=self.SEED,
            slot_number=3, n_disturb_max=8,
        )
        assert set(seq).issubset({0, 1})

    def test_type1_tx_rx_differ(self):
        tx = measurement_signal_1(
            64, SecurityType.TYPE_1, seed=self.SEED,
            slot_number=10, is_tx=True, n_disturb_max=5,
        )
        rx = measurement_signal_1(
            64, SecurityType.TYPE_1, seed=self.SEED,
            slot_number=10, is_tx=False, n_disturb_max=5,
        )
        # TX 和 RX 使用不同的安全子序列
        assert not np.array_equal(tx, rx)

    def test_disturb_max_zero(self):
        """n_disturb_max=0 时无扰动符号"""
        seq = measurement_signal_1(
            32, SecurityType.TYPE_1, seed=self.SEED,
            slot_number=0, n_disturb_max=0,
        )
        # 结果应该全是 a 或 1-a
        assert len(set(seq)) == 1


# -----------------------------------------------------------------------
# 6.2.4.2 测量信号 2
# -----------------------------------------------------------------------


class TestMeasurementSignal2:
    """测量信号 2 多音波形测试"""

    def test_output_complex(self):
        sig = measurement_signal_2(
            n_tones=2, bandwidth_mhz=1,
            duration_us=10.0, sample_rate=4e6,
        )
        assert sig.dtype == np.complex128 or np.issubdtype(
            sig.dtype, np.complexfloating
        )

    def test_single_tone_dc(self):
        """N=1 时为直流信号"""
        sig = measurement_signal_2(
            n_tones=1, bandwidth_mhz=1,
            duration_us=10.0, sample_rate=4e6,
        )
        # 直流信号的虚部应接近 0
        assert np.allclose(sig.imag, 0, atol=1e-10)
        # 实部应为常数
        assert np.allclose(sig.real, sig.real[0], atol=1e-10)

    def test_output_length(self):
        rate = 4e6
        dur = 10.0
        sig = measurement_signal_2(
            n_tones=4, bandwidth_mhz=2,
            duration_us=dur, sample_rate=rate,
        )
        expected = int(dur * 1e-6 * rate)
        assert len(sig) == expected

    @pytest.mark.parametrize("n", [2, 4, 8])
    def test_valid_tone_counts(self, n):
        sig = measurement_signal_2(
            n_tones=n, bandwidth_mhz=2,
            duration_us=5.0, sample_rate=8e6,
        )
        assert len(sig) > 0

    @pytest.mark.parametrize("bw", [1, 2, 4])
    def test_valid_bandwidths(self, bw):
        sig = measurement_signal_2(
            n_tones=2, bandwidth_mhz=bw,
            duration_us=5.0, sample_rate=8e6,
        )
        assert len(sig) > 0

    def test_phase_set_2(self):
        sig1 = measurement_signal_2(
            n_tones=4, bandwidth_mhz=2,
            duration_us=5.0, sample_rate=8e6,
            phase_set=1,
        )
        sig2 = measurement_signal_2(
            n_tones=4, bandwidth_mhz=2,
            duration_us=5.0, sample_rate=8e6,
            phase_set=2,
        )
        assert not np.allclose(sig1, sig2)


# -----------------------------------------------------------------------
# 6.2.4.3 多天线天线对排序
# -----------------------------------------------------------------------


class TestAntennaPairOrder:
    """多天线天线对排序测试"""

    def test_sequential_3x2(self):
        pairs = antenna_pair_order_sequential(3, 2)
        expected = [
            (0, 0), (0, 1),
            (1, 0), (1, 1),
            (2, 0), (2, 1),
        ]
        assert pairs == expected

    def test_sequential_count(self):
        pairs = antenna_pair_order_sequential(4, 3)
        assert len(pairs) == 12

    def test_sequential_1x1(self):
        pairs = antenna_pair_order_sequential(1, 1)
        assert pairs == [(0, 0)]

    def test_sequential_unique(self):
        pairs = antenna_pair_order_sequential(3, 3)
        assert len(pairs) == len(set(pairs))

    def test_random_same_elements(self):
        seed = b"\xEE" * 16
        seq = antenna_pair_order_sequential(3, 2)
        rand = antenna_pair_order_random(3, 2, seed, 0, k=3)
        assert sorted(rand) == sorted(seq)

    def test_random_count(self):
        seed = b"\xFF" * 16
        rand = antenna_pair_order_random(2, 3, seed, 0, k=3)
        assert len(rand) == 6

    def test_random_deterministic(self):
        seed = b"\xDD" * 16
        r1 = antenna_pair_order_random(3, 2, seed, 10, k=3)
        r2 = antenna_pair_order_random(3, 2, seed, 10, k=3)
        assert r1 == r2

    def test_random_1x1_unchanged(self):
        seed = b"\xAA" * 16
        result = antenna_pair_order_random(1, 1, seed, 0, k=3)
        assert result == [(0, 0)]

    def test_random_different_slots(self):
        seed = b"\xBB" * 16
        r1 = antenna_pair_order_random(3, 3, seed, 0, k=4)
        r2 = antenna_pair_order_random(3, 3, seed, 5, k=4)
        assert sorted(r1) == sorted(r2)


class TestMeasurementSignal1Extended:
    """测试 type2 的非零 n_disturb_max 路径。"""

    SEED = b"\xAA" * 16

    def test_type2_nonzero_disturb(self):
        seq = measurement_signal_1(
            64, SecurityType.TYPE_2, seed=self.SEED,
            slot_number=3, n_disturb_max=5,
        )
        assert set(seq).issubset({0, 1})

    def test_type2_large_n(self):
        seq = measurement_signal_1(
            256, SecurityType.TYPE_2, seed=self.SEED,
            slot_number=10, n_disturb_max=11,
        )
        assert len(seq) == 256

    def test_type2_disturb_max_zero(self):
        seq = measurement_signal_1(
            32, SecurityType.TYPE_2, seed=self.SEED,
            slot_number=0, n_disturb_max=0,
        )
        assert np.all(seq == 0)

    def test_invalid_n_measur(self):
        with pytest.raises(ValueError):
            measurement_signal_1(17, SecurityType.TYPE_4)

    def test_invalid_tones(self):
        with pytest.raises(ValueError):
            measurement_signal_2(3, 1, 5.0, 4e6)

    def test_invalid_bandwidth(self):
        with pytest.raises(ValueError):
            measurement_signal_2(2, 3, 5.0, 4e6)

    def test_invalid_phase_set(self):
        with pytest.raises(ValueError):
            measurement_signal_2(4, 2, 5.0, 8e6, phase_set=3)

    def test_8tone(self):
        sig = measurement_signal_2(8, 2, 5.0, 8e6, phase_set=1)
        assert len(sig) > 0
        sig2 = measurement_signal_2(8, 2, 5.0, 8e6, phase_set=2)
        assert not np.allclose(sig, sig2)

    def test_random_different_slots(self):
        seed = b"\xDD" * 16
        r1 = antenna_pair_order_random(3, 2, seed, 0, k=3)
        r2 = antenna_pair_order_random(3, 2, seed, 1, k=3)
        # 不同时隙号一般产生不同排列
        assert r1 != r2

    def test_random_unique(self):
        seed = b"\xAA" * 16
        rand = antenna_pair_order_random(4, 2, seed, 5, k=4)
        assert len(rand) == len(set(rand))


class TestType2DisturbLoop:
    """确保 TYPE_2 扰动索引计算循环被执行。"""

    def test_type2_produces_disturb_bits(self):
        """扫描 seed/slot 组合, 确保找到产生非零扰动的情况。"""
        found = False
        for slot in range(20):
            seq = measurement_signal_1(
                64, SecurityType.TYPE_2,
                seed=b"\x11" * 16, slot_number=slot,
                n_disturb_max=8,
            )
            if np.any(seq == 1):
                found = True
                break
        assert found, "未找到产生扰动位的 slot"

    def test_type2_multiple_disturb_max(self):
        """不同 n_disturb_max 值覆盖扰动计算路径。"""
        for ndm in [3, 7, 15]:
            seq = measurement_signal_1(
                128, SecurityType.TYPE_2,
                seed=b"\xFF" * 16, slot_number=5,
                n_disturb_max=ndm,
            )
            assert len(seq) == 128
            assert set(seq).issubset({0, 1})
