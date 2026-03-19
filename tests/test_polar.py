"""Tests for Polar code encoder/decoder per TXS-10002-2025."""

import numpy as np
import pytest

from nearlink_sdr.common.polar import (
    RATE_TABLE,
    RELIABILITY_SEQ_1024,
    VALID_CODE_LENGTHS,
    PolarDecoder,
    PolarEncoder,
    _get_frozen_and_info_sets,
    _get_reliability_sequence,
    get_info_bit_count,
)

# ── Reliability sequence tests ──


class TestReliabilitySequence:
    def test_length(self):
        assert len(RELIABILITY_SEQ_1024) == 1024

    def test_unique(self):
        assert len(set(RELIABILITY_SEQ_1024)) == 1024

    def test_range(self):
        assert min(RELIABILITY_SEQ_1024) == 0
        assert max(RELIABILITY_SEQ_1024) == 1023

    def test_first_entry_is_zero(self):
        """Bit index 0 is least reliable."""
        assert RELIABILITY_SEQ_1024[0] == 0

    def test_last_entry_is_1023(self):
        """Bit index 1023 is most reliable."""
        assert RELIABILITY_SEQ_1024[-1] == 1023

    def test_subsequence_n64(self):
        seq = _get_reliability_sequence(64)
        assert len(seq) == 64
        assert all(0 <= q < 64 for q in seq)
        assert len(set(seq)) == 64

    def test_subsequence_n128(self):
        seq = _get_reliability_sequence(128)
        assert len(seq) == 128
        assert all(0 <= q < 128 for q in seq)

    def test_subsequence_n256(self):
        seq = _get_reliability_sequence(256)
        assert len(seq) == 256
        assert all(0 <= q < 256 for q in seq)

    def test_subsequence_preserves_order(self):
        """Sub-sequence maintains the reliability ordering from the parent."""
        seq_1024 = RELIABILITY_SEQ_1024
        seq_64 = _get_reliability_sequence(64)
        filtered = [q for q in seq_1024 if q < 64]
        assert list(seq_64) == filtered


# ── Frozen/info set tests ──


class TestFrozenInfoSets:
    def test_partition_size(self):
        N, K = 256, 112
        frozen, info = _get_frozen_and_info_sets(N, K)
        assert len(frozen) == N - K
        assert len(info) == K

    def test_partition_disjoint(self):
        N, K = 128, 56
        frozen, info = _get_frozen_and_info_sets(N, K)
        assert frozen & info == set()

    def test_partition_covers_all(self):
        N, K = 64, 28
        frozen, info = _get_frozen_and_info_sets(N, K)
        assert frozen | info == set(range(N))

    def test_frozen_are_least_reliable(self):
        """Frozen bits should correspond to the least reliable positions."""
        N, K = 512, 224
        frozen, _ = _get_frozen_and_info_sets(N, K)
        seq = _get_reliability_sequence(N)
        least_reliable = set(seq[: N - K])
        assert frozen == least_reliable


# ── Rate table tests ──


class TestRateTable:
    def test_all_rates_present(self):
        expected_rates = {"1/4", "3/8", "1/2", "5/8", "3/4", "7/8"}
        assert set(RATE_TABLE.keys()) == expected_rates

    def test_all_code_lengths_present(self):
        for rate_str in RATE_TABLE:
            assert set(RATE_TABLE[rate_str].keys()) == VALID_CODE_LENGTHS

    def test_get_info_bit_count(self):
        assert get_info_bit_count("1/2", 1024) == 512
        assert get_info_bit_count("1/2", 512) == 224
        assert get_info_bit_count("3/4", 256) == 176
        assert get_info_bit_count("1/4", 64) == 12

    def test_invalid_rate(self):
        with pytest.raises(ValueError, match="Unsupported rate"):
            get_info_bit_count("2/3", 1024)

    def test_invalid_code_length(self):
        with pytest.raises(ValueError, match="Unsupported code length"):
            get_info_bit_count("1/2", 100)

    def test_k_less_than_n(self):
        for rate_str, entries in RATE_TABLE.items():
            for N, K in entries.items():
                assert K < N, f"K={K} >= N={N} for rate {rate_str}"


# ── Encoder tests ──


class TestPolarEncoder:
    def test_invalid_n(self):
        with pytest.raises(ValueError):
            PolarEncoder(100, 50)

    def test_invalid_k_zero(self):
        with pytest.raises(ValueError):
            PolarEncoder(64, 0)

    def test_invalid_k_equals_n(self):
        with pytest.raises(ValueError):
            PolarEncoder(64, 64)

    def test_output_length(self):
        enc = PolarEncoder(64, 28)
        info = np.zeros(28, dtype=np.int8)
        coded = enc.encode(info)
        assert coded.shape == (64,)

    def test_all_zero_input(self):
        """Encoding all-zero info bits with frozen=0 should produce all-zero codeword."""
        enc = PolarEncoder(64, 28)
        info = np.zeros(28, dtype=np.int8)
        coded = enc.encode(info)
        np.testing.assert_array_equal(coded, np.zeros(64, dtype=np.int8))

    def test_output_binary(self):
        enc = PolarEncoder(128, 56)
        rng = np.random.default_rng(42)
        info = rng.integers(0, 2, size=56, dtype=np.int8)
        coded = enc.encode(info)
        assert set(coded.tolist()).issubset({0, 1})

    def test_wrong_info_length(self):
        enc = PolarEncoder(64, 28)
        with pytest.raises(ValueError, match="Expected 28"):
            enc.encode(np.zeros(10, dtype=np.int8))

    @pytest.mark.parametrize("N,K", [(64, 28), (128, 56), (256, 112)])
    def test_linearity(self, N, K):
        """Polar code is linear: encode(a XOR b) == encode(a) XOR encode(b)."""
        enc = PolarEncoder(N, K)
        rng = np.random.default_rng(123)
        a = rng.integers(0, 2, size=K, dtype=np.int8)
        b = rng.integers(0, 2, size=K, dtype=np.int8)
        c_a = enc.encode(a)
        c_b = enc.encode(b)
        c_ab = enc.encode(a ^ b)
        np.testing.assert_array_equal(c_ab, c_a ^ c_b)


# ── Decoder tests ──


class TestPolarDecoder:
    def test_invalid_n(self):
        with pytest.raises(ValueError):
            PolarDecoder(100, 50)

    def test_output_length(self):
        dec = PolarDecoder(64, 28)
        llr = np.ones(64, dtype=np.float64) * 10.0
        decoded = dec.decode(llr)
        assert decoded.shape == (28,)

    def test_wrong_llr_length(self):
        dec = PolarDecoder(64, 28)
        with pytest.raises(ValueError, match="Expected 64"):
            dec.decode(np.ones(32))

    def test_all_zero_noiseless(self):
        """All-zero codeword with perfect LLR should decode to all-zero info."""
        N, K = 64, 28
        dec = PolarDecoder(N, K)
        llr = np.ones(N) * 100.0  # strongly favor 0
        decoded = dec.decode(llr)
        np.testing.assert_array_equal(decoded, np.zeros(K, dtype=np.int8))


# ── Roundtrip tests ──


class TestPolarRoundtrip:
    @pytest.mark.parametrize("N,K", [
        (64, 12), (64, 28), (64, 44),
        (128, 56),
        (256, 112),
    ])
    def test_noiseless_roundtrip(self, N, K):
        """Encode then decode with perfect channel should recover info bits."""
        enc = PolarEncoder(N, K)
        dec = PolarDecoder(N, K)
        rng = np.random.default_rng(2024)
        info = rng.integers(0, 2, size=K, dtype=np.int8)
        coded = enc.encode(info)
        # BPSK mapping: 0 -> +1, 1 -> -1, then LLR = 2*y/sigma^2 ≈ large positive for 0
        bpsk = 1.0 - 2.0 * coded.astype(np.float64)
        llr = bpsk * 100.0  # very high SNR
        decoded = dec.decode(llr)
        np.testing.assert_array_equal(decoded, info)

    def test_noiseless_roundtrip_n512(self):
        N, K = 512, 224
        enc = PolarEncoder(N, K)
        dec = PolarDecoder(N, K)
        rng = np.random.default_rng(99)
        info = rng.integers(0, 2, size=K, dtype=np.int8)
        coded = enc.encode(info)
        bpsk = 1.0 - 2.0 * coded.astype(np.float64)
        llr = bpsk * 100.0
        decoded = dec.decode(llr)
        np.testing.assert_array_equal(decoded, info)

    def test_noiseless_roundtrip_n1024(self):
        N, K = 1024, 512
        enc = PolarEncoder(N, K)
        dec = PolarDecoder(N, K)
        rng = np.random.default_rng(77)
        info = rng.integers(0, 2, size=K, dtype=np.int8)
        coded = enc.encode(info)
        bpsk = 1.0 - 2.0 * coded.astype(np.float64)
        llr = bpsk * 100.0
        decoded = dec.decode(llr)
        np.testing.assert_array_equal(decoded, info)

    def test_moderate_snr_roundtrip(self):
        """At moderate SNR, SC decoder should still recover most bits correctly."""
        N, K = 256, 112
        enc = PolarEncoder(N, K)
        dec = PolarDecoder(N, K)
        rng = np.random.default_rng(555)
        info = rng.integers(0, 2, size=K, dtype=np.int8)
        coded = enc.encode(info)
        bpsk = 1.0 - 2.0 * coded.astype(np.float64)
        # SNR ~ 4 dB: sigma ~ 0.63
        sigma = 0.63
        noise = rng.normal(0, sigma, size=N)
        received = bpsk + noise
        llr = 2.0 * received / (sigma ** 2)
        decoded = dec.decode(llr)
        ber = np.mean(decoded != info)
        # At 4 dB with R=112/256~0.44 and N=256, SC should have low BER
        assert ber < 0.1, f"BER {ber:.3f} too high at moderate SNR"

    @pytest.mark.parametrize("rate_str", ["1/4", "1/2", "3/4"])
    def test_rate_table_roundtrip(self, rate_str):
        """Verify roundtrip works for standard rate table entries."""
        N = 128
        K = get_info_bit_count(rate_str, N)
        enc = PolarEncoder(N, K)
        dec = PolarDecoder(N, K)
        rng = np.random.default_rng(42)
        info = rng.integers(0, 2, size=K, dtype=np.int8)
        coded = enc.encode(info)
        bpsk = 1.0 - 2.0 * coded.astype(np.float64)
        llr = bpsk * 100.0
        decoded = dec.decode(llr)
        np.testing.assert_array_equal(decoded, info)

    def test_multiple_random_messages(self):
        """Test multiple random messages for the same encoder/decoder pair."""
        N, K = 64, 28
        enc = PolarEncoder(N, K)
        dec = PolarDecoder(N, K)
        rng = np.random.default_rng(2025)
        for _ in range(20):
            info = rng.integers(0, 2, size=K, dtype=np.int8)
            coded = enc.encode(info)
            bpsk = 1.0 - 2.0 * coded.astype(np.float64)
            llr = bpsk * 50.0
            decoded = dec.decode(llr)
            np.testing.assert_array_equal(decoded, info)
