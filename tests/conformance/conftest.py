"""共享 fixture — TXS-10002-2025 一致性测试。"""

from __future__ import annotations

import numpy as np
import pytest

from nearlink_sdr.phy.tx_pipeline import TxConfig

# ── 帧类型 × 参数矩阵 ──

# FT1 = GFSK, FT2 = PSK (MCS6-12), FT3 = PSK (MCS0-12), FT4 = PSK 扩展
BANDWIDTHS_MHZ = [1, 2, 4]
TX_RX_INTERVALS_US = [25, 50, 75, 100, 125]
PILOT_DENSITIES = [0, 4, 8, 16]  # 0 = 无导频


def make_ft1_config(bw_mhz: int = 1, sps: int = 8) -> TxConfig:
    """FT1 (GFSK) 配置, MCS 与 FT1 无关, 使用 rate=1 (无编码)。"""
    return TxConfig(
        frame_type=1,
        mcs_index=8,
        pid=0x873456,
        whitening_seed=0x4E,
        crc_seed=0x555555,
        crc_len=24,
        ctrl_bits_len=20,
        sps=sps,
        symbol_rate_mhz=float(bw_mhz),
    )


def make_ft2_config(
    mcs: int = 7, pilot: int = 8, bw_mhz: int = 1,
) -> TxConfig:
    """FT2 (PSK, MCS6-12) 配置。"""
    return TxConfig(
        frame_type=2,
        mcs_index=mcs,
        pid=0x123456,
        crc_len=24,
        ctrl_bits_len=28,
        pilot_interval=pilot,
        sps=4,
        symbol_rate_mhz=float(bw_mhz),
    )


def make_ft3_config(
    mcs: int = 4, pilot: int = 8, bw_mhz: int = 1,
) -> TxConfig:
    """FT3 (PSK, MCS0-12) 配置。"""
    return TxConfig(
        frame_type=3,
        mcs_index=mcs,
        pid=3,
        crc_len=24,
        ctrl_bits_len=28,
        pilot_interval=pilot,
        sps=4,
        symbol_rate_mhz=float(bw_mhz),
    )


def make_ft4_config(
    mcs: int = 4, pilot: int = 8, bw_mhz: int = 1,
) -> TxConfig:
    """FT4 (PSK, 扩展帧) 配置。"""
    return TxConfig(
        frame_type=4,
        mcs_index=mcs,
        pid=4,
        crc_len=32,
        ctrl_bits_len=28,
        pilot_interval=pilot,
        sps=4,
        symbol_rate_mhz=float(bw_mhz),
    )


@pytest.fixture
def rng():
    """确定性随机数生成器。"""
    return np.random.default_rng(20250101)
