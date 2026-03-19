import numpy as np
import pytest

from nearlink_sdr.phy.preamble import (
    generate_preamble,
    gfsk_preamble_bits,
    psk_preamble_phases,
    psk_preamble_symbols,
)


class TestGFSKPreamble:
    """GFSK前导码测试 (帧类型1)。"""

    def test_alternating_pattern(self):
        bits = gfsk_preamble_bits(1.0, 10.0)
        expected = np.array([0, 1] * 5, dtype=int)
        np.testing.assert_array_equal(bits, expected)

    def test_first_symbol_is_zero(self):
        bits = gfsk_preamble_bits(2.0, 10.0)
        assert bits[0] == 0

    @pytest.mark.parametrize("rate,duration,expected_len", [
        (1.0, 10.0, 10),
        (2.0, 10.0, 20),
        (4.0, 10.0, 40),
    ])
    def test_length_vs_rate(self, rate, duration, expected_len):
        bits = gfsk_preamble_bits(rate, duration)
        assert len(bits) == expected_len


class TestPSKPreamble:
    """PSK前导码测试 (帧类型2/3/4)。"""

    def test_phase_alternation(self):
        phases = psk_preamble_phases(1.0, 10.0)
        for i in range(len(phases)):
            if i % 2 == 0:
                assert phases[i] == pytest.approx(np.pi / 4)
            else:
                assert phases[i] == pytest.approx(0.0)

    @pytest.mark.parametrize("rate,duration,expected_len", [
        (1.0, 10.0, 10),
        (1.0, 12.0, 12),
        (1.0, 16.0, 16),
        (2.0, 10.0, 20),
        (4.0, 16.0, 64),
    ])
    def test_length(self, rate, duration, expected_len):
        phases = psk_preamble_phases(rate, duration)
        assert len(phases) == expected_len

    def test_symbols_unit_amplitude(self):
        symbols = psk_preamble_symbols(1.0, 10.0)
        np.testing.assert_allclose(np.abs(symbols), 1.0)

    def test_symbols_phase_correct(self):
        symbols = psk_preamble_symbols(1.0, 10.0)
        phases = np.angle(symbols)
        np.testing.assert_allclose(phases[0::2], np.pi / 4, atol=1e-12)
        np.testing.assert_allclose(phases[1::2], 0.0, atol=1e-12)


class TestGeneratePreamble:
    """统一接口测试。"""

    def test_frame_type_1_returns_bits(self):
        result = generate_preamble(1, 1.0)
        assert result.dtype == int or np.issubdtype(result.dtype, np.integer)
        assert len(result) == 10

    @pytest.mark.parametrize("ft,expected_len", [
        (2, 10),
        (3, 12),
        (4, 16),
    ])
    def test_frame_type_psk_length(self, ft, expected_len):
        result = generate_preamble(ft, 1.0)
        assert np.issubdtype(result.dtype, np.complexfloating)
        assert len(result) == expected_len
