"""信道比特加扰 (6.10.4) 测试"""

import numpy as np
import pytest

from nearlink_sdr.common.scrambler import (
    broadcast_seed,
    data_link_seed,
    descramble,
    scramble,
    scramble_sequence,
)


class TestScrambleSequence:
    """加扰序列生成"""

    def test_length(self):
        seq = scramble_sequence(100, 0x4E)
        assert len(seq) == 100

    def test_binary(self):
        seq = scramble_sequence(200, 0x52)
        assert set(np.unique(seq)).issubset({0, 1})

    def test_seed_zero_raises(self):
        """种子 0 虽然合法但不会报错"""
        seq = scramble_sequence(10, 0)
        assert len(seq) == 10

    def test_seed_out_of_range(self):
        with pytest.raises(ValueError):
            scramble_sequence(10, 128)
        with pytest.raises(ValueError):
            scramble_sequence(10, -1)

    def test_deterministic(self):
        s1 = scramble_sequence(500, 78)
        s2 = scramble_sequence(500, 78)
        np.testing.assert_array_equal(s1, s2)

    def test_different_seeds_different_output(self):
        s1 = scramble_sequence(200, 0x4E)
        s2 = scramble_sequence(200, 0x49)
        assert not np.array_equal(s1, s2)

    def test_period_127(self):
        """x^7+x^4+1 的 LFSR 周期为 2^7-1=127 (非退化种子)"""
        seq = scramble_sequence(300, 0x4E)
        chunk1 = seq[:127]
        chunk2 = seq[127:254]
        np.testing.assert_array_equal(chunk1, chunk2)

    def test_lfsr_first_bits_known(self):
        """seed=1: Galois LFSR 输出 MSB, 前 7 步输出全 0 (状态左移到 bit6 才输出 1)"""
        seq = scramble_sequence(7, 1)
        np.testing.assert_array_equal(seq[:6], [0, 0, 0, 0, 0, 0])
        assert seq[6] == 1

    def test_seed_0x41_first_bits(self):
        """seed=0x41=0b1000001: bit6=1, 首次输出 1
        step 0: out=1, state=(0x82&0x7F)^0x11=0x02^0x11=0x13
        step 1: out=0, state=0x26
        step 2: out=0, state=0x4C
        step 3: out=1 (0x4C bit6=1)
        """
        seq = scramble_sequence(4, 0x41)
        np.testing.assert_array_equal(seq[:4], [1, 0, 0, 1])


class TestScrambleDescramble:
    """加扰/解扰自逆性"""

    def test_roundtrip(self):
        rng = np.random.default_rng(42)
        bits = rng.integers(0, 2, size=256).astype(np.uint8)
        seed = 0x4E
        scrambled = scramble(bits, seed)
        recovered = descramble(scrambled, seed)
        np.testing.assert_array_equal(recovered, bits)

    def test_scramble_changes_data(self):
        bits = np.ones(100, dtype=np.uint8)
        scrambled = scramble(bits, 0x52)
        assert not np.array_equal(bits, scrambled)

    def test_all_zeros(self):
        bits = np.zeros(127, dtype=np.uint8)
        scrambled = scramble(bits, 0x4E)
        # 加扰全零等于加扰序列本身
        seq = scramble_sequence(127, 0x4E)
        np.testing.assert_array_equal(scrambled, seq)

    def test_various_lengths(self):
        rng = np.random.default_rng(99)
        for length in [1, 7, 8, 64, 127, 128, 256, 1024]:
            bits = rng.integers(0, 2, size=length).astype(np.uint8)
            recovered = descramble(scramble(bits, 0x55), 0x55)
            np.testing.assert_array_equal(recovered, bits)


class TestBroadcastSeed:
    """广播帧加扰种子"""

    def test_broadcast_channels(self):
        """广播信道 76,77,78 的种子"""
        assert broadcast_seed(76) == 76
        assert broadcast_seed(77) == 77
        assert broadcast_seed(78) == 78

    def test_channel_0(self):
        assert broadcast_seed(0) == 0

    def test_large_channel_masks(self):
        """物理信道号 > 127 时取低 7 位"""
        assert broadcast_seed(128) == 0
        assert broadcast_seed(200) == 200 & 0x7F

    def test_tv_whitening_seeds(self):
        """验证测试向量中的广播帧 Whitening Seed"""
        # TV_ID 101: FrameType=1 (广播), Whitening Seed=0x4E=78
        assert broadcast_seed(78) == 0x4E
        # TV_ID 102: Whitening Seed=0x49=73
        assert broadcast_seed(73) == 0x49


class TestDataLinkSeed:
    """数据链路加扰种子"""

    def test_bit6_always_one(self):
        for slot in range(64):
            seed = data_link_seed(slot)
            assert (seed >> 6) & 1 == 1

    def test_low_6_bits(self):
        assert data_link_seed(0) == 0x40
        assert data_link_seed(18) == 0x40 | 18  # = 0x52
        assert data_link_seed(63) == 0x40 | 63  # = 0x7F

    def test_mask_high_bits(self):
        """大于 63 的时隙号只取低 6 位"""
        assert data_link_seed(64) == 0x40
        assert data_link_seed(100) == 0x40 | (100 & 0x3F)

    def test_tv_whitening_seeds(self):
        """验证测试向量中的数据帧 Whitening Seed"""
        # TV_ID 201: FrameType=2, Whitening Seed=0x52=0b1010010
        # bit6=1, bits[0:5]=010010=18
        assert data_link_seed(18) == 0x52
        # TV_ID 202: Whitening Seed=0x53=0b1010011, slot=19
        assert data_link_seed(19) == 0x53

    def test_range_values(self):
        """种子范围 0x40 ~ 0x7F"""
        for slot in range(64):
            seed = data_link_seed(slot)
            assert 0x40 <= seed <= 0x7F
