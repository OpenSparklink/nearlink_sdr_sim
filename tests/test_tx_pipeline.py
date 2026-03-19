"""TX 发射流水线测试 -- 对标 TXS-10002-2025 第 14 章测试向量。

使用已验证的 TV201/TV203/TV207/TV213 数据, 验证 encode_payload
和 encode_head 的输出与标准一致。
"""

import numpy as np
import pytest

from nearlink_sdr.common.prbs import prbs11
from nearlink_sdr.phy.tx_pipeline import TxConfig, encode_head, encode_payload, tx_chain
from tests.tv_frame2_data import TV201, TV202, TV203, TV205, TV206, TV207, TV209, TV213


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
# TV202: FT=2, A3, MCS=7 (rate 7/8), dLen=67B (多码块), CRC24A
# =========================================================================


class TestTV202Pipeline:
    """TV202 端到端验证: MCS7 rate 7/8, 多码块 (67 字节)。"""

    CFG = TxConfig(
        frame_type=2,
        mcs_index=7,
        pid=TV202["group"]["pid"],
        whitening_seed=TV202["wt_seed"],
        crc_seed=TV202["crc_seed"],
        crc_len=24,
        ctrl_bits_len=TV202["ctrl_bits"],
    )

    def test_encode_payload(self):
        """encode_payload 输出应等于 txPyLdW (704 bits)。"""
        data_bits = _make_pyld_bits(202, TV202["ctrl_bits"], TV202["dLen"])
        result = encode_payload(data_bits, self.CFG)
        assert len(result) == 704
        expected = _hex_pairs_to_bits(TV202["txPyLdW"], 704)
        assert list(result) == expected

    def test_encode_head(self):
        """encode_head 输出应等于 txHeadW。"""
        head_bits = _make_head_bits(TV202)
        result = encode_head(head_bits, self.CFG)
        lo, hi = TV202["txHeadW"]
        expected = _hex_to_bits_lsb(lo, 32) + _hex_to_bits_lsb(hi, 32)
        assert list(result) == expected


# =========================================================================
# TV205: FT=2, A3, MCS=6 (rate 3/4, QPSK), dLen=1B, CRC24A
# =========================================================================


class TestTV205Pipeline:
    """TV205 端到端验证: MCS6 rate 3/4 QPSK, 最小载荷。"""

    CFG = TxConfig(
        frame_type=2,
        mcs_index=6,
        pid=TV205["group"]["pid"],
        whitening_seed=TV205["wt_seed"],
        crc_seed=TV205["crc_seed"],
        crc_len=24,
        ctrl_bits_len=TV205["ctrl_bits"],
    )

    def test_encode_payload(self):
        """encode_payload 输出应等于 txPyLdW (64 bits)。"""
        data_bits = _make_pyld_bits(205, TV205["ctrl_bits"], TV205["dLen"])
        result = encode_payload(data_bits, self.CFG)
        lo, hi = TV205["txPyLdW"]
        expected = _hex_to_bits_lsb(lo, 32) + _hex_to_bits_lsb(hi, 32)
        assert list(result) == expected

    def test_encode_head(self):
        """encode_head 输出应等于 txHeadW。"""
        head_bits = _make_head_bits(TV205)
        result = encode_head(head_bits, self.CFG)
        lo, hi = TV205["txHeadW"]
        expected = _hex_to_bits_lsb(lo, 32) + _hex_to_bits_lsb(hi, 32)
        assert list(result) == expected


# =========================================================================
# TV206: FT=2, A3, MCS=6 (rate 3/4, QPSK), dLen=177B (大载荷), CRC24A
# =========================================================================


class TestTV206Pipeline:
    """TV206 端到端验证: MCS6 rate 3/4 QPSK, 大载荷。"""

    CFG = TxConfig(
        frame_type=2,
        mcs_index=6,
        pid=TV206["group"]["pid"],
        whitening_seed=TV206["wt_seed"],
        crc_seed=TV206["crc_seed"],
        crc_len=24,
        ctrl_bits_len=TV206["ctrl_bits"],
    )

    def test_encode_payload(self):
        """encode_payload 输出应等于 txPyLdW (1984 bits)。"""
        data_bits = _make_pyld_bits(206, TV206["ctrl_bits"], TV206["dLen"])
        result = encode_payload(data_bits, self.CFG)
        assert len(result) == 1984
        expected = _hex_pairs_to_bits(TV206["txPyLdW"], 1984)
        assert list(result) == expected

    def test_encode_head(self):
        """encode_head 输出应等于 txHeadW。"""
        head_bits = _make_head_bits(TV206)
        result = encode_head(head_bits, self.CFG)
        lo, hi = TV206["txHeadW"]
        expected = _hex_to_bits_lsb(lo, 32) + _hex_to_bits_lsb(hi, 32)
        assert list(result) == expected


# =========================================================================
# TV209: FT=2, A1, MCS=11 (rate 7/8, 8PSK), dLen=1B, CRC24A
# =========================================================================


class TestTV209Pipeline:
    """TV209 端到端验证: MCS11 rate 7/8 8PSK, PID=0x234567。"""

    CFG = TxConfig(
        frame_type=2,
        mcs_index=11,
        pid=TV209["group"]["pid"],
        whitening_seed=TV209["wt_seed"],
        crc_seed=TV209["crc_seed"],
        crc_len=24,
        ctrl_bits_len=TV209["ctrl_bits"],
    )

    def test_encode_payload(self):
        """encode_payload 输出应等于 txPyLdW (64 bits)。"""
        data_bits = _make_pyld_bits(209, TV209["ctrl_bits"], TV209["dLen"])
        result = encode_payload(data_bits, self.CFG)
        lo, hi = TV209["txPyLdW"]
        expected = _hex_to_bits_lsb(lo, 32) + _hex_to_bits_lsb(hi, 32)
        assert list(result) == expected

    def test_encode_head(self):
        """encode_head 输出应等于 txHeadW。"""
        head_bits = _make_head_bits(TV209)
        result = encode_head(head_bits, self.CFG)
        lo, hi = TV209["txHeadW"]
        expected = _hex_to_bits_lsb(lo, 32) + _hex_to_bits_lsb(hi, 32)
        assert list(result) == expected


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
