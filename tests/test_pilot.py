"""Tests for pilot insertion/extraction per TXS-10002-2025."""

import numpy as np
import pytest

from nearlink_sdr.phy.pilot import (
    PILOT_PHASE_DEG,
    EVEN_ROTATION_DEG,
    pilot_symbol,
    insert_pilots,
    remove_pilots,
)


class TestPilotSymbol:
    def test_bpsk_odd_position(self):
        """Index 0 is odd, BPSK pilot should be at 90°."""
        p = pilot_symbol("BPSK", 0)
        expected = np.exp(1j * np.deg2rad(90.0))
        np.testing.assert_almost_equal(p, expected)

    def test_bpsk_even_position(self):
        """Index 1 is even, BPSK pilot gets -90° rotation → 0°."""
        p = pilot_symbol("BPSK", 1)
        expected = np.exp(1j * np.deg2rad(90.0 - 90.0))
        np.testing.assert_almost_equal(p, expected)

    def test_qpsk_odd_position(self):
        p = pilot_symbol("QPSK", 0)
        expected = np.exp(1j * np.deg2rad(45.0))
        np.testing.assert_almost_equal(p, expected)

    def test_qpsk_even_position(self):
        p = pilot_symbol("QPSK", 1)
        expected = np.exp(1j * np.deg2rad(45.0 - 45.0))
        np.testing.assert_almost_equal(p, expected)

    def test_8psk_pilot(self):
        p = pilot_symbol("8PSK", 2)
        # Index 2 → even position, phase = 22.5 - 22.5 = 0
        # Wait, index 2: is_even = (2%2)==1 → False, so odd
        expected = np.exp(1j * np.deg2rad(22.5))
        np.testing.assert_almost_equal(p, expected)

    def test_unit_magnitude(self):
        for mod in ["BPSK", "QPSK", "8PSK"]:
            for idx in range(4):
                p = pilot_symbol(mod, idx)
                np.testing.assert_almost_equal(abs(p), 1.0)


class TestInsertPilots:
    def test_no_pilot_interval(self):
        data = np.ones(10, dtype=complex)
        out, count = insert_pilots(data, 0, "BPSK")
        assert count == 10
        np.testing.assert_array_equal(out, data)

    def test_insert_every_4(self):
        data = np.ones(8, dtype=complex)
        out, count = insert_pilots(data, 4, "BPSK", omit_last_pilot=False)
        # 8 data + 2 pilots = 10
        assert count == 10

    def test_insert_every_16(self):
        data = np.ones(32, dtype=complex)
        out, count = insert_pilots(data, 16, "QPSK", omit_last_pilot=False)
        # 32 data + 2 pilots = 34
        assert count == 34

    def test_omit_last_pilot(self):
        data = np.ones(16, dtype=complex)
        out, count = insert_pilots(data, 4, "BPSK", omit_last_pilot=True)
        # 16 data + 4 pilots - 1 omitted = 19
        assert count == 19

    def test_partial_last_group(self):
        data = np.ones(6, dtype=complex)
        out, count = insert_pilots(data, 4, "BPSK", omit_last_pilot=False)
        # 4 data + 1 pilot + 2 data = 7
        assert count == 7


class TestRemovePilots:
    def test_no_pilot(self):
        data = np.ones(10, dtype=complex)
        out = remove_pilots(data, 0)
        assert len(out) == 10

    def test_roundtrip_no_omit(self):
        """Insert then remove should recover original data."""
        rng = np.random.default_rng(42)
        data = rng.standard_normal(20) + 1j * rng.standard_normal(20)
        with_pilots, _ = insert_pilots(data, 4, "BPSK", omit_last_pilot=False)
        recovered = remove_pilots(with_pilots, 4, last_pilot_omitted=False)
        np.testing.assert_array_almost_equal(recovered, data)

    def test_remove_known_pattern(self):
        # 4 data + 1 pilot + 4 data + 1 pilot = 10 symbols
        data = np.arange(10, dtype=complex)
        # After removal: indices 0,1,2,3, 5,6,7,8 (skip 4 and 9)
        out = remove_pilots(data, 4)
        assert len(out) == 8

    def test_empty_input(self):
        out = remove_pilots(np.array([], dtype=complex), 4)
        assert len(out) == 0
