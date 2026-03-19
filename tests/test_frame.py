"""Tests for frame structure assembly and parsing per TXS-10002-2025."""

import numpy as np
import pytest

from nearlink_sdr.phy.frame import (
    FrameConfig,
    _bits_to_symbols_count,
    _demodulate_symbols,
    _modulate_bits,
    assemble_frame_bits,
    frame_to_symbols,
    symbols_to_data_bits,
)

# ── FrameConfig tests ──


class TestFrameConfig:
    def test_valid_frame_types(self):
        for ft in (1, 2, 3, 4):
            cfg = FrameConfig(frame_type=ft)
            assert cfg.frame_type == ft

    def test_invalid_frame_type(self):
        with pytest.raises(ValueError):
            FrameConfig(frame_type=5)

    def test_default_mod_type_1(self):
        cfg = FrameConfig(frame_type=1)
        assert cfg.mod_type == "GFSK"

    def test_default_mod_type_2(self):
        cfg = FrameConfig(frame_type=2)
        assert cfg.mod_type == "QPSK"

    def test_default_mod_type_3(self):
        cfg = FrameConfig(frame_type=3)
        assert cfg.mod_type == "QPSK"

    def test_default_mod_type_4(self):
        cfg = FrameConfig(frame_type=4)
        assert cfg.mod_type == "BPSK"

    def test_custom_mod_type(self):
        cfg = FrameConfig(frame_type=2, mod_type="BPSK")
        assert cfg.mod_type == "BPSK"


# ── Frame assembly tests ──


class TestAssembleFrame:
    def test_type1_has_all_fields(self):
        cfg = FrameConfig(frame_type=1)
        ctrl = np.zeros(16, dtype=np.int8)
        data = np.ones(80, dtype=np.int8)
        fields = assemble_frame_bits(ctrl, data, cfg)
        assert len(fields.preamble_bits) > 0
        assert len(fields.sync_bits) == 32
        assert len(fields.ctrl_bits) == 16
        assert len(fields.data_bits) == 80

    def test_type2_sync_is_64_bits(self):
        cfg = FrameConfig(frame_type=2)
        fields = assemble_frame_bits(
            np.zeros(64, dtype=np.int8),
            np.zeros(100, dtype=np.int8),
            cfg,
        )
        assert len(fields.sync_bits) == 64

    def test_type3_sync_is_62_bits(self):
        cfg = FrameConfig(frame_type=3)
        fields = assemble_frame_bits(
            np.zeros(256, dtype=np.int8),
            np.zeros(100, dtype=np.int8),
            cfg,
        )
        assert len(fields.sync_bits) == 62

    def test_type4_sync_is_126_bits(self):
        cfg = FrameConfig(frame_type=4)
        fields = assemble_frame_bits(
            np.zeros(256, dtype=np.int8),
            np.zeros(100, dtype=np.int8),
            cfg,
        )
        assert len(fields.sync_bits) == 126


# ── Modulation helper tests ──


class TestModulationHelpers:
    def test_bpsk_roundtrip(self):
        bits = np.array([0, 1, 0, 1, 1, 0], dtype=np.int8)
        syms = _modulate_bits(bits, "BPSK")
        recovered = _demodulate_symbols(syms, "BPSK")
        np.testing.assert_array_equal(recovered, bits)

    def test_qpsk_roundtrip(self):
        bits = np.array([0, 0, 0, 1, 1, 1, 1, 0], dtype=np.int8)
        syms = _modulate_bits(bits, "QPSK")
        recovered = _demodulate_symbols(syms, "QPSK")
        np.testing.assert_array_equal(recovered, bits)

    def test_bpsk_symbol_count(self):
        assert _bits_to_symbols_count(10, "BPSK") == 10

    def test_qpsk_symbol_count(self):
        assert _bits_to_symbols_count(10, "QPSK") == 5

    def test_bpsk_unit_magnitude(self):
        bits = np.array([0, 1, 0, 0, 1, 1], dtype=np.int8)
        syms = _modulate_bits(bits, "BPSK")
        np.testing.assert_array_almost_equal(np.abs(syms), 1.0)

    def test_qpsk_unit_magnitude(self):
        bits = np.array([0, 0, 0, 1, 1, 1, 1, 0], dtype=np.int8)
        syms = _modulate_bits(bits, "QPSK")
        np.testing.assert_array_almost_equal(np.abs(syms), 1.0)


# ── Frame-to-symbols tests ──


class TestFrameToSymbols:
    def test_type1_returns_bits(self):
        """Frame type 1 should return bit array (for GFSK modulator)."""
        cfg = FrameConfig(frame_type=1)
        fields = assemble_frame_bits(
            np.zeros(16, dtype=np.int8),
            np.ones(80, dtype=np.int8),
            cfg,
        )
        out = frame_to_symbols(fields, cfg)
        assert out.dtype == np.int8
        assert set(out.tolist()).issubset({0, 1})

    def test_type2_returns_complex(self):
        cfg = FrameConfig(frame_type=2, pilot_interval=16)
        fields = assemble_frame_bits(
            np.zeros(64, dtype=np.int8),
            np.zeros(100, dtype=np.int8),
            cfg,
        )
        out = frame_to_symbols(fields, cfg)
        assert np.iscomplexobj(out)
        assert len(out) > 0

    def test_type3_has_pilots(self):
        cfg = FrameConfig(frame_type=3, pilot_interval=4)
        fields = assemble_frame_bits(
            np.zeros(256, dtype=np.int8),
            np.zeros(200, dtype=np.int8),
            cfg,
        )
        out = frame_to_symbols(fields, cfg)
        # With pilots, should be longer than without
        n_preamble = len(fields.preamble_bits)
        n_sync_syms = 62  # BPSK: 62 bits → 62 symbols
        n_ctrl_syms = 128  # 256 bits QPSK → 128 symbols
        n_data_syms = 100  # 200 bits QPSK → 100 symbols
        min_without_pilots = n_preamble + n_sync_syms + n_ctrl_syms + n_data_syms
        assert len(out) > min_without_pilots

    def test_type4_produces_output(self):
        cfg = FrameConfig(frame_type=4, pilot_interval=4)
        fields = assemble_frame_bits(
            np.zeros(256, dtype=np.int8),
            np.zeros(100, dtype=np.int8),
            cfg,
        )
        out = frame_to_symbols(fields, cfg)
        assert len(out) > 0

    def test_no_pilot_data(self):
        """Frame type 2 with no pilot for data."""
        cfg = FrameConfig(frame_type=2, pilot_interval=0)
        fields = assemble_frame_bits(
            np.zeros(64, dtype=np.int8),
            np.zeros(100, dtype=np.int8),
            cfg,
        )
        out = frame_to_symbols(fields, cfg)
        assert len(out) > 0


# ── Frame roundtrip tests ──


class TestFrameRoundtrip:
    def test_type1_roundtrip(self):
        """Frame type 1 assemble → to_symbols → parse should recover data."""
        cfg = FrameConfig(frame_type=1)
        ctrl = np.array([1, 0, 1, 0] * 4, dtype=np.int8)  # 16 bits
        data = np.array([1, 0, 0, 1] * 20, dtype=np.int8)  # 80 bits
        fields = assemble_frame_bits(ctrl, data, cfg)
        syms = frame_to_symbols(fields, cfg)
        ctrl_rx, data_rx = symbols_to_data_bits(
            syms, cfg,
            n_ctrl_coded_bits=16,
            n_data_bits=80,
        )
        np.testing.assert_array_equal(ctrl_rx, ctrl)
        np.testing.assert_array_equal(data_rx, data)

    def test_qpsk_moddemod_random(self):
        """QPSK mod/demod roundtrip with random data."""
        rng = np.random.default_rng(42)
        bits = rng.integers(0, 2, size=100, dtype=np.int8)
        # Ensure even length for QPSK
        bits = bits[:100]
        syms = _modulate_bits(bits, "QPSK")
        recovered = _demodulate_symbols(syms, "QPSK")
        np.testing.assert_array_equal(recovered, bits)
