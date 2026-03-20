import numpy as np
import pytest

from nearlink_sdr.phy.sync_sequence import (
    SYNC1_BROADCAST,
    SYNC2_BROADCAST,
    sync_signal_1,
    sync_signal_1_validate,
    sync_signal_2,
    sync_signal_3,
    sync_signal_4,
    sync_signal_5,
    sync_signal_6,
)


class TestBroadcastSyncWords:
    """广播帧固定同步序列验证。"""

    def test_sync1_broadcast_length(self):
        assert len(SYNC1_BROADCAST) == 32

    def test_sync2_broadcast_length(self):
        assert len(SYNC2_BROADCAST) == 64

    def test_sync1_broadcast_hex_match(self):
        """验证0x5A2BDA62的LSB优先比特表示。"""
        hex_val = 0x5A2BDA62
        for i in range(32):
            assert SYNC1_BROADCAST[i] == ((hex_val >> i) & 1)

    def test_sync2_broadcast_hex_match(self):
        """验证0x7DE7585C6D226540的LSB优先比特表示。"""
        hex_val = 0x7DE7585C6D226540
        for i in range(64):
            assert SYNC2_BROADCAST[i] == ((hex_val >> i) & 1)


class TestSyncSignal1:
    """同步信号1测试 (32比特, BCH(31,26)+m31)。"""

    def test_broadcast_returns_fixed(self):
        result = sync_signal_1(None)
        np.testing.assert_array_equal(result, SYNC1_BROADCAST)

    def test_output_length(self):
        result = sync_signal_1(0x123456)
        assert len(result) == 32

    def test_last_bit_is_zero(self):
        """末尾补0。"""
        result = sync_signal_1(0xABCDEF)
        assert result[31] == 0

    def test_different_ids_different_results(self):
        s1 = sync_signal_1(0x000001)
        s2 = sync_signal_1(0x000002)
        assert not np.array_equal(s1, s2)

    def test_binary_values(self):
        result = sync_signal_1(0x555555)
        assert set(result.tolist()).issubset({0, 1})


class TestSyncSignal2:
    """同步信号2测试 (64比特, BCH(63,24)+m63)。"""

    def test_broadcast_returns_fixed(self):
        result = sync_signal_2(None)
        np.testing.assert_array_equal(result, SYNC2_BROADCAST)

    def test_output_length(self):
        result = sync_signal_2(0xFEDCBA)
        assert len(result) == 64

    def test_last_bit_is_zero(self):
        result = sync_signal_2(0x112233)
        assert result[63] == 0

    def test_different_ids_different_results(self):
        s1 = sync_signal_2(0x000001)
        s2 = sync_signal_2(0x000002)
        assert not np.array_equal(s1, s2)


class TestSyncSignal3:
    """同步信号3测试 (31+31 m序列串联)。"""

    def test_output_length(self):
        result = sync_signal_3(0)
        assert len(result) == 62

    def test_is_repeated_m31(self):
        result = sync_signal_3(0)
        np.testing.assert_array_equal(result[:31], result[31:])

    @pytest.mark.parametrize("idx", range(6))
    def test_all_indices(self, idx):
        result = sync_signal_3(idx)
        assert len(result) == 62

    def test_different_indices_different_sequences(self):
        s0 = sync_signal_3(0)
        s1 = sync_signal_3(1)
        assert not np.array_equal(s0, s1)


class TestSyncSignal4:
    """同步信号4测试 (63+63 m序列串联)。"""

    def test_output_length(self):
        result = sync_signal_4(0)
        assert len(result) == 126

    def test_is_repeated_m63(self):
        result = sync_signal_4(0)
        np.testing.assert_array_equal(result[:63], result[63:])

    @pytest.mark.parametrize("idx", range(6))
    def test_all_indices(self, idx):
        result = sync_signal_4(idx)
        assert len(result) == 126


class TestSyncValidation:
    """同步序列验证条件测试。"""

    def test_broadcast_word_passes(self):
        """广播帧本身不应通过验证（条件3）。"""
        assert sync_signal_1_validate(SYNC1_BROADCAST) is False

    def test_too_many_consecutive(self):
        seq = np.zeros(32, dtype=int)
        seq[:7] = 1  # 7个连续1
        assert sync_signal_1_validate(seq) is False

    def test_valid_sequence(self):
        """满足全部约束的序列应通过验证。"""
        # 连续0/1不超过6, 跳转少于26次, 与广播不同
        seq = np.array([0, 0, 1, 1, 0, 0, 1, 1] * 4, dtype=int)
        assert sync_signal_1_validate(seq) is True

    def test_too_many_transitions(self):
        """每位都跳变则有31次跳转，超过26次阈值。"""
        seq = np.array([0, 1] * 16, dtype=int)
        # 31 transitions > 26, should fail
        # Actually [0,1]*16 has 31 transitions, let's check
        transitions = np.sum(np.abs(np.diff(seq)))
        if transitions >= 26:
            assert sync_signal_1_validate(seq) is False
        else:
            assert sync_signal_1_validate(seq) is True


# -----------------------------------------------------------------------
# 6.2.3.5 同步信号 5
# -----------------------------------------------------------------------


class TestSyncSignal5:
    """同步信号5测试 (GFSK, 安全随机序列)"""

    SEED = b"\xAA" * 16

    @pytest.mark.parametrize("n_sync", [32, 64, 128])
    def test_length(self, n_sync):
        seq = sync_signal_5(self.SEED, slot_number=100, n_sync=n_sync)
        assert len(seq) == n_sync

    def test_binary_values(self):
        seq = sync_signal_5(self.SEED, slot_number=0, n_sync=64)
        assert set(seq).issubset({0, 1})

    def test_deterministic(self):
        s1 = sync_signal_5(self.SEED, 42, n_sync=32)
        s2 = sync_signal_5(self.SEED, 42, n_sync=32)
        assert np.array_equal(s1, s2)

    def test_different_slots(self):
        s1 = sync_signal_5(self.SEED, 0, n_sync=32)
        s2 = sync_signal_5(self.SEED, 1, n_sync=32)
        assert not np.array_equal(s1, s2)

    def test_tx_rx_differ(self):
        tx = sync_signal_5(self.SEED, 10, n_sync=64, is_tx=True)
        rx = sync_signal_5(self.SEED, 10, n_sync=64, is_tx=False)
        assert not np.array_equal(tx, rx)

    def test_different_seeds(self):
        seed2 = b"\xBB" * 16
        s1 = sync_signal_5(self.SEED, 0, n_sync=32)
        s2 = sync_signal_5(seed2, 0, n_sync=32)
        assert not np.array_equal(s1, s2)


# -----------------------------------------------------------------------
# 6.2.3.6 同步信号 6
# -----------------------------------------------------------------------


class TestSyncSignal6:
    """同步信号6测试 (无相位旋转BPSK, 安全随机序列)"""

    SEED = b"\xCC" * 16

    @pytest.mark.parametrize("n_sync", [32, 64, 128])
    def test_length(self, n_sync):
        seq = sync_signal_6(self.SEED, slot_number=50, n_sync=n_sync)
        assert len(seq) == n_sync

    def test_binary_values(self):
        seq = sync_signal_6(self.SEED, slot_number=0, n_sync=128)
        assert set(seq).issubset({0, 1})

    def test_deterministic(self):
        s1 = sync_signal_6(self.SEED, 99, n_sync=64)
        s2 = sync_signal_6(self.SEED, 99, n_sync=64)
        assert np.array_equal(s1, s2)

    def test_tx_rx_differ(self):
        tx = sync_signal_6(self.SEED, 5, n_sync=32, is_tx=True)
        rx = sync_signal_6(self.SEED, 5, n_sync=32, is_tx=False)
        assert not np.array_equal(tx, rx)

    def test_same_as_signal5(self):
        """同步信号5和6使用相同的生成逻辑"""
        seed = b"\xDD" * 16
        s5 = sync_signal_5(seed, 77, n_sync=64, is_tx=True)
        s6 = sync_signal_6(seed, 77, n_sync=64, is_tx=True)
        assert np.array_equal(s5, s6)
