import numpy as np

from nearlink_sdr.common.bch import (
    BCH_31_26_GEN,
    BCH_63_24_GEN,
    _gf2_poly_mod,
    bch_31_26_encode,
    bch_63_24_encode,
)


class TestGF2PolyMod:
    """GF(2)多项式模运算测试。"""

    def test_identity(self):
        """d^0 mod (d+1) = 1."""
        dividend = np.array([1], dtype=int)
        divisor = np.array([1, 1], dtype=int)
        result = _gf2_poly_mod(dividend, divisor)
        assert len(result) == 1
        assert result[0] == 1

    def test_exact_division(self):
        """(d^2+1) mod (d+1) = 0, 因为 d^2+1 = (d+1)^2 over GF(2)."""
        dividend = np.array([1, 0, 1], dtype=int)
        divisor = np.array([1, 1], dtype=int)
        result = _gf2_poly_mod(dividend, divisor)
        assert result[0] == 0

    def test_known_remainder(self):
        """d^5 mod (d^5+d^2+1) = d^2+1。"""
        dividend = np.zeros(6, dtype=int)
        dividend[5] = 1
        divisor = BCH_31_26_GEN.copy()
        result = _gf2_poly_mod(dividend, divisor)
        expected = np.array([1, 0, 1, 0, 0], dtype=int)
        np.testing.assert_array_equal(result, expected)


class TestBCH3126:
    """BCH(31,26)编码器测试。"""

    def test_output_length(self):
        info = np.zeros(26, dtype=int)
        codeword = bch_31_26_encode(info)
        assert len(codeword) == 31

    def test_all_zero_info(self):
        """全0输入应产生全0码字。"""
        info = np.zeros(26, dtype=int)
        codeword = bch_31_26_encode(info)
        np.testing.assert_array_equal(codeword, np.zeros(31, dtype=int))

    def test_info_preserved(self):
        """编码后前26位应等于输入信息位。"""
        info = np.array([1, 0, 1, 1] + [0] * 22, dtype=int)
        codeword = bch_31_26_encode(info)
        np.testing.assert_array_equal(codeword[:26], info)

    def test_codeword_divisible_by_generator(self):
        """有效码字应能被生成多项式整除。"""
        np.random.seed(42)
        for _ in range(10):
            info = np.random.randint(0, 2, 26)
            codeword = bch_31_26_encode(info)
            remainder = _gf2_poly_mod(codeword, BCH_31_26_GEN)
            np.testing.assert_array_equal(remainder, np.zeros(5, dtype=int))

    def test_generator_degree(self):
        """生成多项式阶数应为5。"""
        assert len(BCH_31_26_GEN) == 6
        assert BCH_31_26_GEN[5] == 1


class TestBCH6324:
    """BCH(63,24)编码器测试。"""

    def test_output_length(self):
        info = np.zeros(24, dtype=int)
        codeword = bch_63_24_encode(info)
        assert len(codeword) == 63

    def test_all_zero_info(self):
        info = np.zeros(24, dtype=int)
        codeword = bch_63_24_encode(info)
        np.testing.assert_array_equal(codeword, np.zeros(63, dtype=int))

    def test_info_preserved(self):
        info = np.array([1, 0, 1, 1, 0, 0, 1, 0] + [0] * 16, dtype=int)
        codeword = bch_63_24_encode(info)
        np.testing.assert_array_equal(codeword[:24], info)

    def test_codeword_divisible_by_generator(self):
        np.random.seed(123)
        for _ in range(10):
            info = np.random.randint(0, 2, 24)
            codeword = bch_63_24_encode(info)
            remainder = _gf2_poly_mod(codeword, BCH_63_24_GEN)
            np.testing.assert_array_equal(remainder, np.zeros(39, dtype=int))

    def test_generator_degree(self):
        assert len(BCH_63_24_GEN) == 40
        assert BCH_63_24_GEN[39] == 1

    def test_different_inputs_different_codewords(self):
        info_a = np.zeros(24, dtype=int)
        info_a[0] = 1
        info_b = np.zeros(24, dtype=int)
        info_b[1] = 1
        cw_a = bch_63_24_encode(info_a)
        cw_b = bch_63_24_encode(info_b)
        assert not np.array_equal(cw_a, cw_b)
