"""Frame structure assembly and parsing per TXS-10002-2025 sections 6.3.2-6.3.5.

Supports frame types 1-4 with preamble, sync sequence, control info,
data payload, and pilot insertion.
"""

import numpy as np
from dataclasses import dataclass, field

from nearlink_sdr.phy.preamble import generate_preamble
from nearlink_sdr.phy.sync_sequence import (
    sync_signal_1, sync_signal_2, sync_signal_3, sync_signal_4,
)
from nearlink_sdr.phy.pilot import insert_pilots, remove_pilots


@dataclass
class FrameConfig:
    """Configuration for a radio frame."""
    frame_type: int  # 1, 2, 3, or 4
    symbol_rate_mhz: float = 1.0
    pilot_interval: int = 0  # 0=no pilot, 4/8/16
    crc_len: int = 24  # 24 or 32
    mod_type: str = ""  # auto-determined if empty
    sync_m_index: int | None = None  # m-sequence index for sync signal

    def __post_init__(self):
        if self.frame_type not in (1, 2, 3, 4):
            raise ValueError(f"frame_type must be 1-4, got {self.frame_type}")
        if not self.mod_type:
            self.mod_type = _default_mod_type(self.frame_type)


def _default_mod_type(frame_type: int) -> str:
    """Default modulation type for each frame type."""
    return {1: "GFSK", 2: "QPSK", 3: "QPSK", 4: "BPSK"}[frame_type]


# ── Frame parameters per type ──

# Sync signal config per frame type
_SYNC_CONFIG = {
    1: {"func": sync_signal_1, "bits": 32, "sync_mod": "GFSK"},
    2: {"func": sync_signal_2, "bits": 64, "sync_mod": "QPSK"},
    3: {"func": sync_signal_3, "bits": 62, "sync_mod": "BPSK"},
    4: {"func": sync_signal_4, "bits": 126, "sync_mod": "BPSK"},
}

# Control info encoding per frame type
_CTRL_CONFIG = {
    1: {"coded_bits": None, "ctrl_mod": "GFSK", "pilot_interval": 0},
    2: {"coded_bits": 64, "ctrl_mod": "QPSK", "pilot_interval": 16},
    3: {"coded_bits": 256, "ctrl_mod": "QPSK", "pilot_interval": 4},
    4: {"coded_bits": 256, "ctrl_mod": "BPSK", "pilot_interval": 4},
}


@dataclass
class FrameFields:
    """Assembled frame fields as bit/symbol arrays."""
    preamble_bits: np.ndarray = field(default_factory=lambda: np.array([], dtype=np.int8))
    sync_bits: np.ndarray = field(default_factory=lambda: np.array([], dtype=np.int8))
    ctrl_bits: np.ndarray = field(default_factory=lambda: np.array([], dtype=np.int8))
    data_bits: np.ndarray = field(default_factory=lambda: np.array([], dtype=np.int8))
    frame_type: int = 1


def assemble_frame_bits(
    ctrl_info_bits: np.ndarray,
    data_payload_bits: np.ndarray,
    config: FrameConfig,
) -> FrameFields:
    """Assemble a complete frame at the bit level.

    This produces the bit-level frame structure before modulation.

    Args:
        ctrl_info_bits: physical layer control information bits.
        data_payload_bits: data + integrity protection + CRC bits.
        config: frame configuration.

    Returns:
        FrameFields with all frame segments.
    """
    fields = FrameFields(frame_type=config.frame_type)

    # Preamble
    fields.preamble_bits = generate_preamble(config.frame_type, config.symbol_rate_mhz)

    # Sync sequence
    sync_cfg = _SYNC_CONFIG[config.frame_type]
    if config.frame_type in (1, 2):
        fields.sync_bits = sync_cfg["func"](config.sync_m_index)
    else:
        # sync_signal_3/4 take m_seq_index, default 0
        idx = config.sync_m_index if config.sync_m_index is not None else 0
        fields.sync_bits = sync_cfg["func"](idx)

    # Control info
    fields.ctrl_bits = ctrl_info_bits

    # Data payload
    fields.data_bits = data_payload_bits

    return fields


def frame_to_symbols(
    fields: FrameFields,
    config: FrameConfig,
) -> np.ndarray:
    """Convert frame fields to a modulated symbol stream with pilot insertion.

    For frame type 1 (GFSK), returns the concatenated bit sequence (not complex symbols).
    For frame types 2-4 (PSK), returns complex symbol stream with pilots.

    Args:
        fields: assembled frame fields.
        config: frame configuration.

    Returns:
        For type 1: bit array (to be fed to GFSK modulator).
        For types 2-4: complex symbol array (baseband).
    """
    if config.frame_type == 1:
        # Frame type 1: simple bit concatenation, no pilots, no channel coding
        return np.concatenate([
            fields.preamble_bits,
            fields.sync_bits,
            fields.ctrl_bits,
            fields.data_bits,
        ]).astype(np.int8)

    # PSK frame types (2, 3, 4)
    segments = []
    symbol_count = 0

    # Preamble symbols (phase alternating [π/4, 0])
    n_preamble = len(fields.preamble_bits)
    preamble_phases = np.where(
        fields.preamble_bits == 0,
        np.pi / 4,
        0.0,
    )
    preamble_syms = np.exp(1j * preamble_phases)
    segments.append(preamble_syms)
    symbol_count += len(preamble_syms)

    # Sync symbols
    sync_mod = _SYNC_CONFIG[config.frame_type]["sync_mod"]
    sync_syms = _modulate_bits(fields.sync_bits, sync_mod)
    segments.append(sync_syms)
    symbol_count += len(sync_syms)

    # Control symbols with pilot insertion
    ctrl_cfg = _CTRL_CONFIG[config.frame_type]
    ctrl_syms = _modulate_bits(fields.ctrl_bits, ctrl_cfg["ctrl_mod"])
    if ctrl_cfg["pilot_interval"] > 0:
        # Determine if last pilot should be omitted based on data existence
        has_data = len(fields.data_bits) > 0
        data_has_pilot = config.pilot_interval > 0
        omit_ctrl_last = not has_data or not data_has_pilot
        ctrl_with_pilot, _ = insert_pilots(
            ctrl_syms,
            ctrl_cfg["pilot_interval"],
            ctrl_cfg["ctrl_mod"],
            start_symbol_index=symbol_count,
            omit_last_pilot=omit_ctrl_last,
        )
        segments.append(ctrl_with_pilot)
        symbol_count += len(ctrl_with_pilot)
    else:
        segments.append(ctrl_syms)
        symbol_count += len(ctrl_syms)

    # Data symbols with pilot insertion
    if len(fields.data_bits) > 0:
        data_syms = _modulate_bits(fields.data_bits, config.mod_type)
        if config.pilot_interval > 0:
            data_with_pilot, _ = insert_pilots(
                data_syms,
                config.pilot_interval,
                config.mod_type,
                start_symbol_index=symbol_count,
                omit_last_pilot=True,
            )
            segments.append(data_with_pilot)
        else:
            segments.append(data_syms)

    return np.concatenate(segments)


def symbols_to_data_bits(
    symbols: np.ndarray,
    config: FrameConfig,
    n_ctrl_coded_bits: int = 0,
    n_data_bits: int = 0,
) -> tuple[np.ndarray, np.ndarray]:
    """Parse received symbol stream back to control and data bits.

    This is a simplified parser that assumes known frame parameters.

    Args:
        symbols: received complex symbol stream.
        config: frame configuration.
        n_ctrl_coded_bits: number of coded control bits.
        n_data_bits: number of data bits (before modulation).

    Returns:
        (ctrl_bits, data_bits) — demodulated bit arrays.
    """
    if config.frame_type == 1:
        # Frame type 1: bit-level parsing
        n_preamble = len(generate_preamble(1, config.symbol_rate_mhz))
        n_sync = 32
        offset = n_preamble + n_sync
        ctrl_bits = symbols[offset : offset + n_ctrl_coded_bits].real.astype(np.int8)
        data_start = offset + n_ctrl_coded_bits
        data_bits = symbols[data_start : data_start + n_data_bits].real.astype(np.int8)
        return ctrl_bits, data_bits

    # PSK frame types
    pos = 0

    # Skip preamble
    n_preamble = len(generate_preamble(config.frame_type, config.symbol_rate_mhz))
    pos += n_preamble

    # Skip sync
    sync_bits_len = _SYNC_CONFIG[config.frame_type]["bits"]
    sync_mod = _SYNC_CONFIG[config.frame_type]["sync_mod"]
    n_sync_syms = _bits_to_symbols_count(sync_bits_len, sync_mod)
    pos += n_sync_syms

    # Control symbols
    ctrl_cfg = _CTRL_CONFIG[config.frame_type]
    n_ctrl_syms = _bits_to_symbols_count(
        ctrl_cfg["coded_bits"] or n_ctrl_coded_bits,
        ctrl_cfg["ctrl_mod"],
    )
    n_ctrl_with_pilots = n_ctrl_syms
    if ctrl_cfg["pilot_interval"] > 0:
        n_pilots = n_ctrl_syms // ctrl_cfg["pilot_interval"]
        n_ctrl_with_pilots = n_ctrl_syms + n_pilots

    ctrl_raw = symbols[pos : pos + n_ctrl_with_pilots]
    if ctrl_cfg["pilot_interval"] > 0:
        ctrl_syms = remove_pilots(ctrl_raw, ctrl_cfg["pilot_interval"])
    else:
        ctrl_syms = ctrl_raw
    ctrl_bits = _demodulate_symbols(ctrl_syms, ctrl_cfg["ctrl_mod"])
    pos += n_ctrl_with_pilots

    # Data symbols
    remaining = symbols[pos:]
    if config.pilot_interval > 0 and len(remaining) > 0:
        data_syms = remove_pilots(remaining, config.pilot_interval)
    else:
        data_syms = remaining
    data_bits = _demodulate_symbols(data_syms, config.mod_type)

    if n_data_bits > 0:
        data_bits = data_bits[:n_data_bits]

    return ctrl_bits, data_bits


# ── Internal modulation helpers ──


def _modulate_bits(bits: np.ndarray, mod_type: str) -> np.ndarray:
    """Simple bit-to-symbol mapping (no pulse shaping)."""
    if mod_type == "BPSK":
        # 0 → 90°, 1 → -90°
        phases = np.where(bits == 0, np.pi / 2, -np.pi / 2)
        symbols = np.exp(1j * phases)
        # Even symbols get -90° rotation
        for i in range(len(symbols)):
            if i % 2 == 1:
                symbols[i] *= np.exp(-1j * np.pi / 2)
        return symbols
    elif mod_type == "QPSK":
        # 2 bits per symbol
        n_sym = len(bits) // 2
        symbols = np.zeros(n_sym, dtype=complex)
        qpsk_map = {
            (0, 0): 45.0,
            (0, 1): 135.0,
            (1, 1): -135.0,
            (1, 0): -45.0,
        }
        for i in range(n_sym):
            b0, b1 = int(bits[2 * i]), int(bits[2 * i + 1])
            phase = np.deg2rad(qpsk_map[(b0, b1)])
            symbols[i] = np.exp(1j * phase)
            # Even symbol rotation
            if i % 2 == 1:
                symbols[i] *= np.exp(-1j * np.deg2rad(45.0))
        return symbols
    elif mod_type == "GFSK":
        return bits.astype(np.int8)
    else:
        raise ValueError(f"Unsupported mod_type: {mod_type}")


def _demodulate_symbols(symbols: np.ndarray, mod_type: str) -> np.ndarray:
    """Simple symbol-to-bit hard decision (no matched filter)."""
    if mod_type == "BPSK":
        bits = np.zeros(len(symbols), dtype=np.int8)
        for i in range(len(symbols)):
            sym = symbols[i]
            if i % 2 == 1:
                sym *= np.exp(1j * np.pi / 2)  # undo even rotation
            # bit 0 → 90° (imag>0), bit 1 → -90° (imag<0)
            bits[i] = 0 if np.imag(sym) > 0 else 1
        return bits
    elif mod_type == "QPSK":
        bits = np.zeros(len(symbols) * 2, dtype=np.int8)
        for i in range(len(symbols)):
            sym = symbols[i]
            if i % 2 == 1:
                sym *= np.exp(1j * np.deg2rad(45.0))  # undo rotation
            phase = np.rad2deg(np.angle(sym)) % 360
            # Map back to closest constellation point
            if 0 <= phase < 90:
                bits[2 * i], bits[2 * i + 1] = 0, 0
            elif 90 <= phase < 180:
                bits[2 * i], bits[2 * i + 1] = 0, 1
            elif 180 <= phase < 270:
                bits[2 * i], bits[2 * i + 1] = 1, 1
            else:
                bits[2 * i], bits[2 * i + 1] = 1, 0
        return bits
    elif mod_type == "GFSK":
        return symbols.astype(np.int8)
    else:
        raise ValueError(f"Unsupported mod_type: {mod_type}")


def _bits_to_symbols_count(n_bits: int, mod_type: str) -> int:
    """Calculate number of symbols for given number of bits."""
    if mod_type == "QPSK":
        return n_bits // 2
    return n_bits
