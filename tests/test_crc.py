import numpy as np
import pytest
from nearlink_sdr.common.crc import (
    crc_calculate, crc_attach, crc_check,
    CRC12_POLY, CRC24A_POLY, CRC24B_POLY, CRC32_POLY,
)


class TestCRC:
    def test_crc24a_zero_input(self):
        data = np.zeros(8, dtype=int)
        parity = crc_calculate(data, CRC24A_POLY, 24, seed=0)
        assert parity.shape == (24,)
        assert np.all(parity == 0)

    def test_crc24a_attach_and_check(self):
        rng = np.random.default_rng(42)
        data = rng.integers(0, 2, 80)
        encoded = crc_attach(data, CRC24A_POLY, 24, seed=0x555555)
        assert len(encoded) == 80 + 24
        assert crc_check(encoded, CRC24A_POLY, 24, seed=0x555555)

    def test_crc24a_detect_error(self):
        rng = np.random.default_rng(42)
        data = rng.integers(0, 2, 80)
        encoded = crc_attach(data, CRC24A_POLY, 24, seed=0x555555)
        encoded[3] ^= 1  # 翻转一比特
        assert not crc_check(encoded, CRC24A_POLY, 24, seed=0x555555)

    def test_crc24b_attach_and_check(self):
        rng = np.random.default_rng(99)
        data = rng.integers(0, 2, 120)
        encoded = crc_attach(data, CRC24B_POLY, 24, seed=0x555555)
        assert crc_check(encoded, CRC24B_POLY, 24, seed=0x555555)

    def test_crc32_attach_and_check(self):
        rng = np.random.default_rng(7)
        data = rng.integers(0, 2, 256)
        encoded = crc_attach(data, CRC32_POLY, 32, seed=0)
        assert crc_check(encoded, CRC32_POLY, 32, seed=0)

    def test_crc12_attach_and_check(self):
        rng = np.random.default_rng(12)
        data = rng.integers(0, 2, 32)
        seed = 0xABC & 0xFFF
        encoded = crc_attach(data, CRC12_POLY, 12, seed=seed)
        assert crc_check(encoded, CRC12_POLY, 12, seed=seed)

    def test_crc24a_with_mask(self):
        rng = np.random.default_rng(55)
        data = rng.integers(0, 2, 64)
        mask = rng.integers(0, 2, 24)
        encoded = crc_attach(data, CRC24A_POLY, 24, seed=0, mask=mask)
        assert crc_check(encoded, CRC24A_POLY, 24, seed=0, mask=mask)
        # 没有mask时解不出来
        assert not crc_check(encoded, CRC24A_POLY, 24, seed=0)

    def test_crc_deterministic(self):
        data = np.array([1, 0, 1, 1, 0, 0, 1, 0], dtype=int)
        p1 = crc_calculate(data, CRC24A_POLY, 24, seed=0)
        p2 = crc_calculate(data, CRC24A_POLY, 24, seed=0)
        assert np.array_equal(p1, p2)
