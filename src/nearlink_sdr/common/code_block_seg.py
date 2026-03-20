"""Code block segmentation per TXS-10002-2025 sections 6.9.1.2 and 6.9.1.3."""

import math

import numpy as np

from nearlink_sdr.common.crc import CRC24B_POLY, crc_calculate
from nearlink_sdr.common.polar import RATE_TABLE

# Table 24: alternative rate matching table for 6.9.1.2 (without CRC segmentation)
RATE_TABLE_2 = {
    "5/8": {1024: 640, 512: 316, 256: 156, 128: 74, 64: 36},
    "3/4": {1024: 768, 512: 382, 256: 189, 128: 90, 64: 45},
    "7/8": {1024: 896, 512: 446, 256: 221, 128: 106, 64: 53},
}

# Table 20: segmentation lookup table
# index -> (N512, N256, N128)
_SEG_TABLE_20 = [
    (0, 0, 0),  # 0
    (0, 0, 1),  # 1
    (0, 0, 2),  # 2
    (0, 1, 1),  # 3
    (0, 1, 2),  # 4
    (0, 2, 1),  # 5
    (0, 2, 2),  # 6
    (1, 1, 1),  # 7
    (1, 1, 2),  # 8
    (1, 2, 1),  # 9
    (1, 2, 2),  # 10
    (2, 1, 1),  # 11
    (2, 1, 2),  # 12
    (2, 2, 1),  # 13
    (2, 2, 2),  # 14
]

_RATE_FRACTIONS = {
    "1/4": 0.25,
    "3/8": 0.375,
    "1/2": 0.5,
    "5/8": 0.625,
    "3/4": 0.75,
    "7/8": 0.875,
}


def _get_rate_value(rate_str: str) -> float:
    if rate_str not in _RATE_FRACTIONS:
        raise ValueError(f"Unsupported rate '{rate_str}'")
    return _RATE_FRACTIONS[rate_str]


def _get_k_for_segmentation(rate_str: str, use_table24: bool = False) -> dict[int, int]:
    """Get K values for each code length at the given rate.

    For 6.9.1.2 (without CRC), use_table24=True for rates in Table 24.
    For 6.9.1.3 (with CRC), always use Table 23.
    """
    if use_table24 and rate_str in RATE_TABLE_2:
        return RATE_TABLE_2[rate_str]
    return RATE_TABLE[rate_str]


def segment_without_crc(
    bits: np.ndarray,
    rate_str: str,
    crc_len: int = 0,
) -> list[tuple[int, np.ndarray]]:
    """Code block segmentation without per-block CRC (section 6.9.1.2).

    Used for frame type 2.

    Args:
        bits: input bit sequence b_0..b_{B-1}, where B = K + L (info + CRC).
        rate_str: target code rate string.
        crc_len: L, the CRC length already appended to bits.

    Returns:
        List of (code_length_N, info_bits) tuples for each segment.
    """
    B = len(bits)
    R = _get_rate_value(rate_str)

    # K values for each code length from Table 24 (if available) or Table 23
    k_table = _get_k_for_segmentation(rate_str, use_table24=True)
    K_1024 = k_table[1024]
    K_512 = k_table[512]
    K_256 = k_table[256]
    K_128 = k_table[128]
    K_64 = k_table[64]

    # Step 1: determine N_1024
    threshold = R * (1024 + 512 + 256 + 128)
    if threshold < B:
        N_1024 = math.floor(
            (B - (512 + 256 + 128 + 8) * R) / (1024 * R)
        )
        K_m = B - N_1024 * K_1024
    else:
        N_1024 = 0
        K_m = B

    # Step 2: Table 20 lookup
    index = 0 if K_m <= 0 else math.floor((K_m - 1) / (128 * R))

    index = min(index, 14)  # clamp to table range
    N_512, N_256, N_128 = _SEG_TABLE_20[index]

    # Step 3: N_64
    remaining = K_m - N_512 * K_512 - N_256 * K_256 - N_128 * K_128
    N_64 = math.ceil(remaining / K_64) if remaining > 0 else 0

    # Build output segments
    segments = []
    pos = 0

    for _ in range(N_1024):
        seg_bits = bits[pos : pos + K_1024]
        segments.append((1024, seg_bits))
        pos += K_1024

    for _ in range(N_512):
        seg_bits = bits[pos : pos + K_512]
        segments.append((512, seg_bits))
        pos += K_512

    for _ in range(N_256):
        seg_bits = bits[pos : pos + K_256]
        segments.append((256, seg_bits))
        pos += K_256

    for _ in range(N_128):
        seg_bits = bits[pos : pos + K_128]
        segments.append((128, seg_bits))
        pos += K_128

    for i in range(N_64):
        if i < N_64 - 1:
            seg_bits = bits[pos : pos + K_64]
            pos += K_64
        else:
            # Last N_64 block takes remaining bits (may be < K_64)
            seg_bits = bits[pos:]
            pos = len(bits)
        segments.append((64, seg_bits))

    return segments


def segment_with_crc(
    bits: np.ndarray,
    rate_str: str,
) -> list[tuple[int, np.ndarray]]:
    """Code block segmentation with per-block CRC24B (section 6.9.1.3).

    Used for frame type 3 and 4.

    Args:
        bits: input bit sequence b_0..b_{B-1}.
        rate_str: target code rate string.

    Returns:
        List of (code_length_N, info_bits_with_crc) tuples for each segment.
        For the last segment, further sub-segmentation may be applied.
    """
    B = len(bits)
    _get_rate_value(rate_str)  # validate

    # K_cb: max info bits for 1024 code length at rate R
    k_table = RATE_TABLE[rate_str]
    K_cb = k_table[1024]

    # Determine number of code blocks
    if K_cb >= B:
        C = 1
        L = 0
    else:
        L = 24
        C = math.ceil(B / (K_cb - L))

    # Generate segments
    segments = []
    pos = 0

    if C == 1:
        # Single segment, no per-block CRC
        segments.append((1024, bits.copy()))
    else:
        for r in range(C):
            K_r = K_cb if r <= C - 2 else B - (C - 1) * (K_cb - L) + L

            # Extract info bits for this segment
            info_len = K_r - L
            seg_info = bits[pos : pos + info_len]
            pos += info_len

            # Append CRC24B
            crc_bits = crc_calculate(seg_info, CRC24B_POLY, 24)
            seg_with_crc = np.concatenate([seg_info, crc_bits])
            segments.append((1024, seg_with_crc))

    # For the last segment, apply further sub-segmentation per the standard
    if len(segments) > 0:
        _, last_bits = segments[-1]
        sub_segs = _subsegment_last_block(last_bits, rate_str)
        if sub_segs is not None:
            segments = segments[:-1] + sub_segs

    return segments


def _subsegment_last_block(
    bits: np.ndarray,
    rate_str: str,
) -> list[tuple[int, np.ndarray]] | None:
    """Further sub-segment the last code block per section 6.9.1.3.

    Returns None if no sub-segmentation is needed (K_r fits in 1024 at rate R).
    """
    K_r = len(bits)
    _get_rate_value(rate_str)  # validate
    k_table = RATE_TABLE[rate_str]
    K_1024 = k_table[1024]

    # Check if it fits directly in a 1024 block
    if K_r <= K_1024:
        # No sub-segmentation, pad if needed
        if K_r < K_1024:
            padded = np.concatenate([
                np.zeros(K_1024 - K_r, dtype=np.int8),
                bits,
            ])
        else:
            padded = bits
        return [(1024, padded)]

    # K_r > K_1024: K_1024 > 1024 * R_adj for all standard rates,
    # so this always truncates to K_1024.
    return [(1024, bits[:K_1024])]
