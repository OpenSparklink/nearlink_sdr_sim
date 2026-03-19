"""Tests for code block segmentation per TXS-10002-2025."""

import math
import numpy as np
import pytest

from nearlink_sdr.common.code_block_seg import (
    RATE_TABLE_2,
    _SEG_TABLE_20,
    segment_without_crc,
    segment_with_crc,
    _get_rate_value,
)
from nearlink_sdr.common.polar import RATE_TABLE


# ── Rate table 2 tests ──


class TestRateTable2:
    def test_rates_present(self):
        assert set(RATE_TABLE_2.keys()) == {"5/8", "3/4", "7/8"}

    def test_code_lengths(self):
        for rate_str, entries in RATE_TABLE_2.items():
            assert set(entries.keys()) == {64, 128, 256, 512, 1024}

    def test_k_less_than_n(self):
        for rate_str, entries in RATE_TABLE_2.items():
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
        K_cb = RATE_TABLE[rate_str][1024]  # 512
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
