"""TX 发射流水线测试 -- 对标 TXS-10002-2025 第 14 章测试向量。

使用已验证的 TV201/TV203/TV207/TV213 数据, 验证 encode_payload
和 encode_head 的输出与标准一致。
"""

import numpy as np
import pytest

from nearlink_sdr.common.prbs import prbs11
from nearlink_sdr.phy.tx_pipeline import TxConfig, encode_head, encode_payload, tx_chain
from tests.tv_frame2_data import TV201, TV203, TV207, TV213


def _hex_to_bits_lsb(hex_val: int, nbits: int) -> list[int]:
    """十六进制值转 LSB-first 比特列表。"""
    return [(hex_val >> i) & 1 for i in range(nbits)]


def _hex_pairs_to_bits(pairs: list[tuple], total_bits: int) -> list[int]:
    """十六进制对列表转比特序列。"""
    bits: list[int] = []
    for pair in pairs:
        lo = pair[0]
        hi = pair[1]
        bits.extend(_hex_to_bits_lsb(lo, 32))
        if hi is not None:
            bits.extend(_hex_to_bits_lsb(hi, 32))
    return bits[:total_bits]


def _make_pyld_bits(tv_id: int, ctrl_len: int, data_len_bytes: int) -> np.ndarray:
    """从 PRBS11 生成载荷比特。"""
    seq = prbs11(ctrl_len + data_len_bytes * 8, seed=tv_id)
    return np.array(seq[ctrl_len:], dtype=int)


def _make_head_bits(tv: dict) -> np.ndarray:
    """从测试向量数据构造 txHead 比特 (含 CRC12)。"""
    lo, hi = tv["txHead"]
    # txHead 由 HeadBits + CRC12 组成
    # 总长 = ctrl_bits + 12
    total = tv["ctrl_bits"] + 12
    bits = _hex_to_bits_lsb(lo, 32)
    hi_bits = _hex_to_bits_lsb(hi, 32)
    bits.extend(hi_bits)
    return np.array(bits[:total], dtype=np.int8)


# =========================================================================
# TV201: FT=2, A3, MCS=7 (rate 7/8), dLen=1B, CRC24A
# =========================================================================


class TestTV201Pipeline:
    """TV201 端到端验证: encode_payload + encode_head。"""

    CFG = TxConfig(
        frame_type=2,
        mcs_index=7,
        pid=TV201["group"]["pid"],
        whitening_seed=TV201["wt_seed"],
        crc_seed=TV201["crc_seed"],
        crc_len=24,
        ctrl_bits_len=TV201["ctrl_bits"],
    )

    def test_encode_payload(self):
        """encode_payload 输出应等于 txPyLdW。"""
        data_bits = _make_pyld_bits(201, TV201["ctrl_bits"], TV201["dLen"])
        result = encode_payload(data_bits, self.CFG)

        lo, hi = TV201["txPyLdW"]
        expected = _hex_to_bits_lsb(lo, 32) + _hex_to_bits_lsb(hi, 32)
        assert list(result) == expected

    def test_encode_head(self):
        """encode_head 输出应等于 txHeadW。"""
        head_bits = _make_head_bits(TV201)
        result = encode_head(head_bits, self.CFG)

        lo, hi = TV201["txHeadW"]
        expected = _hex_to_bits_lsb(lo, 32) + _hex_to_bits_lsb(hi, 32)
        assert list(result) == expected

    def test_tx_chain_produces_iq(self):
        """tx_chain 应输出非零复数 IQ 信号。"""
        head_bits = _make_head_bits(TV201)
        data_bits = _make_pyld_bits(201, TV201["ctrl_bits"], TV201["dLen"])
        iq = tx_chain(head_bits, data_bits, self.CFG)

        assert iq.dtype == complex
        assert len(iq) > 0
        assert np.any(np.abs(iq) > 0)


# =========================================================================
# TV203: FT=2, A3, MCS=9 (rate 5/8, 8PSK), dLen=68B, CRC24A
# =========================================================================


class TestTV203Pipeline:
    """TV203 端到端验证: encode_payload + encode_head (8PSK MCS9 rate 5/8)。"""

    CFG = TxConfig(
        frame_type=2,
        mcs_index=9,
        pid=TV203["group"]["pid"],
        whitening_seed=TV203["wt_seed"],
        crc_seed=TV203["crc_seed"],
        crc_len=24,
        ctrl_bits_len=TV203["ctrl_bits"],
    )

    def test_encode_payload(self):
        """encode_payload 输出应等于 txPyLdW (960 bits)。"""
        data_bits = _make_pyld_bits(203, TV203["ctrl_bits"], TV203["dLen"])
        result = encode_payload(data_bits, self.CFG)

        assert len(result) == 960
        expected = _hex_pairs_to_bits(TV203["txPyLdW"], 960)
        assert list(result) == expected

    def test_encode_head(self):
        """encode_head 输出应等于 txHeadW。"""
        head_bits = _make_head_bits(TV203)
        result = encode_head(head_bits, self.CFG)

        lo, hi = TV203["txHeadW"]
        expected = _hex_to_bits_lsb(lo, 32) + _hex_to_bits_lsb(hi, 32)
        assert list(result) == expected

    def test_tx_chain_produces_iq(self):
        """tx_chain 应输出非零复数 IQ 信号 (8PSK)。"""
        head_bits = _make_head_bits(TV203)
        data_bits = _make_pyld_bits(203, TV203["ctrl_bits"], TV203["dLen"])
        iq = tx_chain(head_bits, data_bits, self.CFG)

        assert iq.dtype == complex
        assert len(iq) > 0
        assert np.any(np.abs(iq) > 0)


# =========================================================================
# TV207: FT=2, A7, MCS=10 (rate 3/4, 8PSK), dLen=178B, CRC24A
# =========================================================================


class TestTV207Pipeline:
    """TV207 端到端验证: encode_payload + encode_head (8PSK MCS10 rate 3/4)。"""

    CFG = TxConfig(
        frame_type=2,
        mcs_index=10,
        pid=TV207["group"]["pid"],
        whitening_seed=TV207["wt_seed"],
        crc_seed=TV207["crc_seed"],
        crc_len=24,
        ctrl_bits_len=TV207["ctrl_bits"],
    )

    def test_encode_payload(self):
        """encode_payload 输出应等于 txPyLdW (1984 bits)。"""
        data_bits = _make_pyld_bits(207, TV207["ctrl_bits"], TV207["dLen"])
        result = encode_payload(data_bits, self.CFG)

        assert len(result) == 1984
        expected = _hex_pairs_to_bits(TV207["txPyLdW"], 1984)
        assert list(result) == expected

    def test_encode_head(self):
        """encode_head 输出应等于 txHeadW。"""
        head_bits = _make_head_bits(TV207)
        result = encode_head(head_bits, self.CFG)

        lo, hi = TV207["txHeadW"]
        expected = _hex_to_bits_lsb(lo, 32) + _hex_to_bits_lsb(hi, 32)
        assert list(result) == expected

    def test_tx_chain_produces_iq(self):
        """tx_chain 应输出非零复数 IQ 信号 (8PSK rate 3/4)。"""
        head_bits = _make_head_bits(TV207)
        data_bits = _make_pyld_bits(207, TV207["ctrl_bits"], TV207["dLen"])
        iq = tx_chain(head_bits, data_bits, self.CFG)

        assert iq.dtype == complex
        assert len(iq) > 0
        assert np.any(np.abs(iq) > 0)


# =========================================================================
# TV213: FT=2, A5, MCS=8 (rate 1/1, 无编码), dLen=123B, CRC32
# =========================================================================


class TestTV213Pipeline:
    """TV213 端到端验证: encode_payload + encode_head (QPSK MCS8 rate 1/1, CRC32)。"""

    CFG = TxConfig(
        frame_type=2,
        mcs_index=8,
        pid=TV213["group"]["pid"],
        whitening_seed=TV213["wt_seed"],
        crc_seed=TV213["crc_seed"],
        crc_len=32,
        ctrl_bits_len=TV213["ctrl_bits"],
    )

    def test_encode_payload(self):
        """encode_payload 输出应等于 txPyLdW (1016 bits, 无 Polar)。"""
        data_bits = _make_pyld_bits(213, TV213["ctrl_bits"], TV213["dLen"])
        result = encode_payload(data_bits, self.CFG)

        assert len(result) == 1016
        expected = _hex_pairs_to_bits(TV213["txPyLdW"], 1016)
        assert list(result) == expected

    def test_encode_head(self):
        """encode_head 输出应等于 txHeadW。"""
        head_bits = _make_head_bits(TV213)
        result = encode_head(head_bits, self.CFG)

        lo, hi = TV213["txHeadW"]
        expected = _hex_to_bits_lsb(lo, 32) + _hex_to_bits_lsb(hi, 32)
        assert list(result) == expected

    def test_tx_chain_produces_iq(self):
        """tx_chain 应输出非零复数 IQ 信号 (无编码, CRC32)。"""
        head_bits = _make_head_bits(TV213)
        data_bits = _make_pyld_bits(213, TV213["ctrl_bits"], TV213["dLen"])
        iq = tx_chain(head_bits, data_bits, self.CFG)

        assert iq.dtype == complex
        assert len(iq) > 0
        assert np.any(np.abs(iq) > 0)


# =========================================================================
# TxConfig 参数验证
# =========================================================================


class TestTxConfig:
    """TxConfig 属性测试。"""

    def test_mcs7_properties(self):
        cfg = TxConfig(mcs_index=7)
        assert cfg.mod_str == "QPSK"
        assert cfg.rate_str == "7/8"
        assert not cfg.is_uncoded

    def test_mcs8_uncoded(self):
        cfg = TxConfig(mcs_index=8)
        assert cfg.mod_str == "QPSK"
        assert cfg.rate_str == "1/1"
        assert cfg.is_uncoded

    def test_mcs9_8psk(self):
        cfg = TxConfig(mcs_index=9)
        assert cfg.mod_str == "8PSK"
        assert cfg.rate_str == "5/8"
        assert not cfg.is_uncoded

    def test_mcs10_8psk(self):
        cfg = TxConfig(mcs_index=10)
        assert cfg.mod_str == "8PSK"
        assert cfg.rate_str == "3/4"
        assert not cfg.is_uncoded

    def test_mcs12_uncoded(self):
        cfg = TxConfig(mcs_index=12)
        assert cfg.mod_str == "8PSK"
        assert cfg.rate_str == "1/1"
        assert cfg.is_uncoded

    def test_crc_poly_selection(self):
        from nearlink_sdr.common.crc import CRC24A_POLY, CRC32_POLY

        cfg24 = TxConfig(crc_len=24)
        assert cfg24.crc_poly == CRC24A_POLY

        cfg32 = TxConfig(crc_len=32)
        assert cfg32.crc_poly == CRC32_POLY

    def test_invalid_mcs(self):
        with pytest.raises(ValueError):
            TxConfig(mcs_index=99)
