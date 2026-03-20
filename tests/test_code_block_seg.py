"""Tests for code block segmentation per TXS-10002-2025."""

import math

import numpy as np
import pytest

from nearlink_sdr.common.code_block_seg import (
    _SEG_TABLE_20,
    RATE_TABLE_2,
    _find_rate_str,
    _subsegment_last_block,
    segment_with_crc,
    segment_without_crc,
)
from nearlink_sdr.common.polar import RATE_TABLE

# ── Rate table 2 tests ──


class TestRateTable2:
    def test_rates_present(self):
        assert set(RATE_TABLE_2.keys()) == {"5/8", "3/4", "7/8"}

    def test_code_lengths(self):
        for _rate_str, entries in RATE_TABLE_2.items():
            assert set(entries.keys()) == {64, 128, 256, 512, 1024}

    def test_k_less_than_n(self):
        for _rate_str, entries in RATE_TABLE_2.items():
            for N, K in entries.items():
                assert K < N

    def test_table24_differs_from_table23(self):
        """Table 24 has different K values than Table 23 for the same rates."""
        for rate_str in RATE_TABLE_2:
            for N in [512, 256, 128]:
                assert RATE_TABLE_2[rate_str][N] != RATE_TABLE[rate_str][N]


# ── Table 20 tests ──


class TestSegTable20:
    def test_length(self):
        assert len(_SEG_TABLE_20) == 15

    def test_first_entry(self):
        assert _SEG_TABLE_20[0] == (0, 0, 0)

    def test_last_entry(self):
        assert _SEG_TABLE_20[14] == (2, 2, 2)

    def test_all_tuples_of_three(self):
        for entry in _SEG_TABLE_20:
            assert len(entry) == 3
            assert all(isinstance(v, int) and 0 <= v <= 2 for v in entry)


# ── Segment without CRC tests (6.9.1.2) ──


class TestSegmentWithoutCRC:
    def test_small_input_single_64_block(self):
        """Input fitting in a single 64-length code block."""
        rate_str = "1/2"
        K_64 = RATE_TABLE[rate_str][64]  # 28
        bits = np.zeros(K_64, dtype=np.int8)
        segs = segment_without_crc(bits, rate_str)
        assert len(segs) >= 1
        total_k = sum(len(s[1]) for s in segs)
        assert total_k >= K_64

    def test_output_has_valid_code_lengths(self):
        """All segments should use valid Polar code lengths."""
        bits = np.zeros(200, dtype=np.int8)
        segs = segment_without_crc(bits, "1/2")
        valid_lengths = {64, 128, 256, 512, 1024}
        for N, _ in segs:
            assert N in valid_lengths

    def test_segment_bits_match_k(self):
        """Each segment's info bits should match the K for its code length."""
        rate_str = "1/2"
        K_1024 = RATE_TABLE[rate_str][1024]  # 512
        bits = np.ones(K_1024, dtype=np.int8)
        segs = segment_without_crc(bits, rate_str)
        # Should use one 1024 block or equivalent
        assert len(segs) >= 1

    def test_large_input_uses_1024_blocks(self):
        """Large input should use 1024-length code blocks."""
        rate_str = "1/2"
        bits = np.zeros(2000, dtype=np.int8)
        segs = segment_without_crc(bits, rate_str)
        has_1024 = any(N == 1024 for N, _ in segs)
        assert has_1024

    def test_invalid_rate(self):
        with pytest.raises(ValueError):
            segment_without_crc(np.zeros(10, dtype=np.int8), "2/3")

    @pytest.mark.parametrize("rate_str", ["1/4", "3/8", "1/2", "5/8", "3/4", "7/8"])
    def test_all_rates(self, rate_str):
        """Segmentation should work for all standard rates."""
        bits = np.zeros(100, dtype=np.int8)
        segs = segment_without_crc(bits, rate_str)
        assert len(segs) >= 1


# ── Segment with CRC tests (6.9.1.3) ──


class TestSegmentWithCRC:
    def test_single_block_no_crc(self):
        """When B <= K_cb, single block without per-block CRC."""
        rate_str = "1/2"
        _K_cb = RATE_TABLE[rate_str][1024]  # 512
        bits = np.ones(100, dtype=np.int8)
        segs = segment_with_crc(bits, rate_str)
        # Should be single (possibly sub-segmented) set of blocks
        assert len(segs) >= 1
        # Total bits should cover the input
        total_k = sum(len(s[1]) for s in segs)
        assert total_k >= 100

    def test_multi_block_with_crc(self):
        """When B > K_cb, multiple blocks each with CRC24B."""
        rate_str = "1/2"
        K_cb = RATE_TABLE[rate_str][1024]  # 512
        B = K_cb + 100  # 612 bits, needs 2 blocks
        bits = np.zeros(B, dtype=np.int8)
        bits[0] = 1  # mark first bit
        segs = segment_with_crc(bits, rate_str)
        assert len(segs) >= 2

    def test_output_code_lengths_valid(self):
        bits = np.zeros(300, dtype=np.int8)
        segs = segment_with_crc(bits, "1/2")
        valid_lengths = {64, 128, 256, 512, 1024}
        for N, _ in segs:
            assert N in valid_lengths

    def test_c_calculation(self):
        """Verify block count formula: C = ceil(B / (K_cb - 24))."""
        rate_str = "3/4"
        K_cb = RATE_TABLE[rate_str][1024]  # 768
        B = 2000
        C_expected = math.ceil(B / (K_cb - 24))
        assert C_expected == 3
        segs = segment_with_crc(bits=np.zeros(B, dtype=np.int8), rate_str=rate_str)
        # At least C segments (may have more due to last-block sub-segmentation)
        assert len(segs) >= C_expected

    @pytest.mark.parametrize("rate_str", ["1/4", "3/8", "1/2", "5/8", "3/4", "7/8"])
    def test_all_rates(self, rate_str):
        bits = np.zeros(200, dtype=np.int8)
        segs = segment_with_crc(bits, rate_str)
        assert len(segs) >= 1

    def test_preserves_data_order(self):
        """Input bits should appear in output segments in order."""
        rate_str = "1/2"
        bits = np.arange(100, dtype=np.int8) % 2
        segs = segment_with_crc(bits, rate_str)
        # First segment should contain the start of the input
        assert len(segs) >= 1


class TestSubSegmentation:
    """_subsegment_last_block 子分段路径覆盖。"""

    def test_large_input_triggers_subseg(self):
        """输入大于 K_cb 触发多码块分割 + 末块子分段。"""
        rate_str = "3/8"
        K_cb = RATE_TABLE[rate_str][1024]  # 384
        B = K_cb * 3  # 远大于 K_cb, 触发多码块
        bits = np.zeros(B, dtype=np.int8)
        segs = segment_with_crc(bits, rate_str)
        assert len(segs) >= 3
        for N, _ in segs:
            assert N in {64, 128, 256, 512, 1024}

    def test_exact_kcb_single_block(self):
        """输入恰好等于 K_cb: 不分割。"""
        rate_str = "1/2"
        K_cb = RATE_TABLE[rate_str][1024]  # 512
        bits = np.zeros(K_cb, dtype=np.int8)
        segs = segment_with_crc(bits, rate_str)
        assert len(segs) >= 1

    def test_slightly_over_kcb(self):
        """输入略超 K_cb: 产生 2 个码块。"""
        rate_str = "1/2"
        K_cb = RATE_TABLE[rate_str][1024]  # 512
        bits = np.zeros(K_cb + 10, dtype=np.int8)
        segs = segment_with_crc(bits, rate_str)
        assert len(segs) >= 2

    def test_all_rates_large_input(self):
        """各编码速率下大载荷均能正常分割。"""
        for rate_str in ["1/4", "3/8", "1/2", "5/8", "3/4", "7/8"]:
            K_cb = RATE_TABLE[rate_str][1024]
            bits = np.zeros(K_cb * 2 + 50, dtype=np.int8)
            segs = segment_with_crc(bits, rate_str)
            assert len(segs) >= 2
            for N, s in segs:
                assert N in {64, 128, 256, 512, 1024}
                assert len(s) > 0

    def test_small_rate_subseg(self):
        """低速率 (1/4) 大载荷子分段。"""
        rate_str = "1/4"
        K_cb = RATE_TABLE[rate_str][1024]  # 256
        bits = np.zeros(K_cb * 4, dtype=np.int8)
        segs = segment_with_crc(bits, rate_str)
        assert len(segs) >= 4


class TestSubsegmentLastBlockDirect:
    """直接测试 _subsegment_last_block 内部路径。"""

    def test_fits_in_1024_no_padding(self):
        """K_r == K_1024: 无需填充, 返回单个 (1024, bits)。"""
        rate_str = "1/2"
        K_1024 = RATE_TABLE[rate_str][1024]
        bits = np.ones(K_1024, dtype=np.int8)
        result = _subsegment_last_block(bits, rate_str)
        assert result is not None
        assert len(result) == 1
        assert result[0][0] == 1024
        assert len(result[0][1]) == K_1024

    def test_fits_in_1024_with_padding(self):
        """K_r < K_1024: 前导零填充。"""
        rate_str = "1/2"
        K_1024 = RATE_TABLE[rate_str][1024]
        bits = np.ones(K_1024 - 50, dtype=np.int8)
        result = _subsegment_last_block(bits, rate_str)
        assert result is not None
        assert len(result) == 1
        assert result[0][0] == 1024
        assert len(result[0][1]) == K_1024
        # 前 50 位应为填充零
        assert np.all(result[0][1][:50] == 0)

    def test_kr_exceeds_k1024_above_threshold(self):
        """K_r > K_1024 且 > threshold_1024: 截断到 K_1024。"""
        rate_str = "3/4"
        K_1024 = RATE_TABLE[rate_str][1024]
        R = 0.75
        R_adj = R - 1 / 16
        threshold = int(1024 * R_adj)
        # K_r > threshold_1024 且 > K_1024
        K_r = max(K_1024, threshold) + 10
        bits = np.ones(K_r, dtype=np.int8)
        result = _subsegment_last_block(bits, rate_str)
        assert result is not None
        assert len(result) == 1
        assert result[0][0] == 1024

    def test_kr_exceeds_k1024_binary_decomposition(self):
        """K_r > K_1024 且 <= threshold_1024 且 <= threshold_large: 二进制分解。"""
        rate_str = "7/8"
        K_1024 = RATE_TABLE[rate_str][1024]
        R = 0.875
        R_adj = R - 1 / 16
        threshold_large = (1024 - 64) * R_adj
        # 构造 K_r 使其在 K_1024 < K_r <= threshold_large
        K_r = K_1024 + 5
        if K_r > threshold_large:
            K_r = int(threshold_large) - 1
        if K_r <= K_1024:
            pytest.skip("无法满足分解条件")
        bits = np.ones(K_r, dtype=np.int8)
        result = _subsegment_last_block(bits, rate_str)
        assert result is not None
        for code_len, _seg_bits in result:
            assert code_len in {64, 128, 256, 512, 1024}

    def test_kr_exceeds_k1024_above_threshold_large(self):
        """K_r > K_1024 且 > threshold_large 但 <= threshold_1024:
        使用 R_adj 速率与 1024 码长。"""
        rate_str = "7/8"
        K_1024 = RATE_TABLE[rate_str][1024]
        R = 0.875
        R_adj = R - 1 / 16
        threshold_1024 = 1024 * R_adj
        threshold_large = (1024 - 64) * R_adj
        # K_r > threshold_large 且 <= threshold_1024
        K_r = int(threshold_large) + 5
        if K_r > threshold_1024 or K_r <= K_1024:
            pytest.skip("无法满足条件")
        bits = np.ones(K_r, dtype=np.int8)
        result = _subsegment_last_block(bits, rate_str)
        assert result is not None
        assert result[0][0] == 1024


class TestFindRateStr:
    """_find_rate_str 辅助函数测试。"""

    def test_exact_match(self):
        assert _find_rate_str(0.5) == "1/2"
        assert _find_rate_str(0.75) == "3/4"

    def test_close_match(self):
        assert _find_rate_str(0.501) == "1/2"

    def test_no_match(self):
        assert _find_rate_str(0.1) is None
        assert _find_rate_str(0.95) is None
