"""Pilot symbol insertion and extraction per TXS-10002-2025 section 6.2.1.2."""

import numpy as np

# Pilot reference phases for each modulation scheme (degrees)
# 标准定义: BPSK导频90°, QPSK导频45°, 8PSK导频22.5°
PILOT_PHASE_DEG = {
    "BPSK": 90.0,
    "QPSK": 45.0,
    "8PSK": 22.5,
}

# Phase rotation per even symbol for each modulation scheme (clockwise, degrees)
EVEN_ROTATION_DEG = {
    "BPSK": -90.0,
    "QPSK": -45.0,
    "8PSK": -22.5,
}


def pilot_symbol(mod_type: str, symbol_index: int) -> complex:
    """Generate a single pilot symbol with appropriate phase rotation.

    Args:
        mod_type: "BPSK", "QPSK", or "8PSK".
        symbol_index: 0-based symbol index in the frame (determines odd/even).
                     The standard says the first symbol is at "odd" position.

    Returns:
        Complex pilot symbol.
    """
    phase_deg = PILOT_PHASE_DEG[mod_type]
    # "无线帧的第一个符号认为处于奇数位" → index 0 is odd, index 1 is even, ...
    is_even = (symbol_index % 2) == 1
    if is_even:
        phase_deg += EVEN_ROTATION_DEG[mod_type]
    return np.exp(1j * np.deg2rad(phase_deg))


def insert_pilots(
    data_symbols: np.ndarray,
    pilot_interval: int,
    mod_type: str,
    start_symbol_index: int = 0,
    omit_last_pilot: bool = True,
) -> tuple[np.ndarray, int]:
    """Insert pilot symbols into data symbol stream.

    Every `pilot_interval` data symbols, one pilot symbol is inserted after them.
    The last pilot in the frame should be omitted per standard.

    Args:
        data_symbols: complex data symbol array.
        pilot_interval: N in standard (4, 8, or 16).
        mod_type: modulation type for pilot phase.
        start_symbol_index: the absolute symbol index of the first data symbol in the frame.
        omit_last_pilot: whether to omit the last pilot symbol.

    Returns:
        (output_symbols, total_symbol_count) — symbols with pilots inserted, and count.
    """
    if pilot_interval <= 0:
        return data_symbols.copy(), len(data_symbols)

    result = []
    sym_idx = start_symbol_index
    n_data = len(data_symbols)
    data_pos = 0
    pilot_positions = []

    while data_pos < n_data:
        # Take up to pilot_interval data symbols
        chunk_end = min(data_pos + pilot_interval, n_data)
        chunk = data_symbols[data_pos:chunk_end]
        result.append(chunk)
        sym_idx += len(chunk)
        data_pos = chunk_end

        # Insert pilot after this chunk if chunk is full
        if len(chunk) == pilot_interval and data_pos <= n_data:
            pilot_positions.append(len(result))
            p = pilot_symbol(mod_type, sym_idx)
            result.append(np.array([p]))
            sym_idx += 1

    output = np.concatenate(result) if result else np.array([], dtype=complex)

    # Omit last pilot if requested
    if omit_last_pilot and pilot_positions and len(output) > 0:
        # Check if the last element is a pilot
        # The last pilot position: find the last pilot we inserted
        # We need to check if the very last symbol of the output is a pilot
        total_data_inserted = n_data
        n_pilots = len(pilot_positions)
        if n_pilots > 0:
            # Check if last inserted data filled exactly to a pilot boundary
            if total_data_inserted % pilot_interval == 0:
                # Last symbol is a pilot → remove it
                output = output[:-1]

    return output, len(output)


def remove_pilots(
    symbols: np.ndarray,
    pilot_interval: int,
    last_pilot_omitted: bool = True,
) -> np.ndarray:
    """Remove pilot symbols from the received symbol stream.

    Args:
        symbols: received symbols with pilots.
        pilot_interval: N (4, 8, or 16).
        last_pilot_omitted: whether the last pilot was omitted at TX.

    Returns:
        Data symbols with pilots removed.
    """
    if pilot_interval <= 0:
        return symbols.copy()

    stride = pilot_interval + 1  # data + pilot
    result = []
    pos = 0

    while pos < len(symbols):
        remaining = len(symbols) - pos
        if remaining >= stride:
            # Full group: take data, skip pilot
            result.append(symbols[pos : pos + pilot_interval])
            pos += stride
        else:
            # Partial group at end (no pilot or pilot was omitted)
            result.append(symbols[pos:])
            pos = len(symbols)

    return np.concatenate(result) if result else np.array([], dtype=complex)
