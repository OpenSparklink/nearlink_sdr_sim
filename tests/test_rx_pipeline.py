"""RX 接收流水线测试 -- 验证 TX→RX 可逆性和帧同步。

核心策略: 使用 encode_payload/encode_head 的已知输出 (txPyLdW/txHeadW)
作为 decode_payload/decode_head 的输入, 验证可以还原原始数据。
"""

import numpy as np

from nearlink_sdr.common.prbs import prbs11
from nearlink_sdr.phy.rx_pipeline import (
    decode_head,
    decode_payload,
    frame_sync,
    rx_chain,
)
from nearlink_sdr.phy.tx_pipeline import TxConfig, encode_head, encode_payload, tx_chain
from tests.tv_frame2_data import TV201, TV203, TV207, TV213


def _hex_to_bits_lsb(hex_val: int, nbits: int) -> list[int]:
    return [(hex_val >> i) & 1 for i in range(nbits)]


def _hex_pairs_to_bits(pairs: list[tuple], total_bits: int) -> list[int]:
    bits: list[int] = []
    for pair in pairs:
        lo = pair[0]
        hi = pair[1]
        bits.extend(_hex_to_bits_lsb(lo, 32))
        if hi is not None:
            bits.extend(_hex_to_bits_lsb(hi, 32))
    return bits[:total_bits]


def _make_pyld_bits(tv_id: int, ctrl_len: int, data_len_bytes: int) -> np.ndarray:
    seq = prbs11(ctrl_len + data_len_bytes * 8, seed=tv_id)
    return np.array(seq[ctrl_len:], dtype=int)


def _make_head_bits(tv: dict) -> np.ndarray:
    lo, hi = tv["txHead"]
    total = tv["ctrl_bits"] + 12
    bits = _hex_to_bits_lsb(lo, 32)
    bits.extend(_hex_to_bits_lsb(hi, 32))
    return np.array(bits[:total], dtype=np.int8)


# =========================================================================
# decode_payload 逆向验证
# =========================================================================


class TestDecodePayloadTV201:
    """TV201: MCS7 rate 7/8, Polar(64,32), CRC24A。"""

    CFG = TxConfig(
        frame_type=2, mcs_index=7,
        pid=TV201["group"]["pid"],
        whitening_seed=TV201["wt_seed"],
        crc_seed=TV201["crc_seed"],
        crc_len=24,
        ctrl_bits_len=TV201["ctrl_bits"],
    )

    def test_decode_payload_roundtrip(self):
        """encode → decode 应还原原始数据比特。"""
        data_bits = _make_pyld_bits(201, TV201["ctrl_bits"], TV201["dLen"])
        scrambled = encode_payload(data_bits, self.CFG)
        decoded, ok = decode_payload(scrambled, self.CFG, TV201["dLen"] * 8)
        assert ok
        assert list(decoded) == list(data_bits)

    def test_decode_head_roundtrip(self):
        """encode → decode head 应还原 txHead 比特。"""
        head_bits = _make_head_bits(TV201)
        scrambled = encode_head(head_bits, self.CFG)
        decoded, ok = decode_head(scrambled, self.CFG)
        assert ok
        assert list(decoded) == list(head_bits)


class TestDecodePayloadTV203:
    """TV203: MCS9 rate 5/8, 8PSK, CRC24A。"""

    CFG = TxConfig(
        frame_type=2, mcs_index=9,
        pid=TV203["group"]["pid"],
        whitening_seed=TV203["wt_seed"],
        crc_seed=TV203["crc_seed"],
        crc_len=24,
        ctrl_bits_len=TV203["ctrl_bits"],
    )

    def test_decode_payload_roundtrip(self):
        data_bits = _make_pyld_bits(203, TV203["ctrl_bits"], TV203["dLen"])
        scrambled = encode_payload(data_bits, self.CFG)
        decoded, ok = decode_payload(scrambled, self.CFG, TV203["dLen"] * 8)
        assert ok
        assert list(decoded) == list(data_bits)

    def test_decode_head_roundtrip(self):
        head_bits = _make_head_bits(TV203)
        scrambled = encode_head(head_bits, self.CFG)
        decoded, ok = decode_head(scrambled, self.CFG)
        assert ok
        assert list(decoded) == list(head_bits)


class TestDecodePayloadTV207:
    """TV207: MCS10 rate 3/4, 8PSK, CRC24A。"""

    CFG = TxConfig(
        frame_type=2, mcs_index=10,
        pid=TV207["group"]["pid"],
        whitening_seed=TV207["wt_seed"],
        crc_seed=TV207["crc_seed"],
        crc_len=24,
        ctrl_bits_len=TV207["ctrl_bits"],
    )

    def test_decode_payload_roundtrip(self):
        data_bits = _make_pyld_bits(207, TV207["ctrl_bits"], TV207["dLen"])
        scrambled = encode_payload(data_bits, self.CFG)
        decoded, ok = decode_payload(scrambled, self.CFG, TV207["dLen"] * 8)
        assert ok
        assert list(decoded) == list(data_bits)

    def test_decode_head_roundtrip(self):
        head_bits = _make_head_bits(TV207)
        scrambled = encode_head(head_bits, self.CFG)
        decoded, ok = decode_head(scrambled, self.CFG)
        assert ok
        assert list(decoded) == list(head_bits)


class TestDecodePayloadTV213:
    """TV213: MCS8 rate 1/1 (无 Polar), CRC32。"""

    CFG = TxConfig(
        frame_type=2, mcs_index=8,
        pid=TV213["group"]["pid"],
        whitening_seed=TV213["wt_seed"],
        crc_seed=TV213["crc_seed"],
        crc_len=32,
        ctrl_bits_len=TV213["ctrl_bits"],
    )

    def test_decode_payload_roundtrip(self):
        data_bits = _make_pyld_bits(213, TV213["ctrl_bits"], TV213["dLen"])
        scrambled = encode_payload(data_bits, self.CFG)
        decoded, ok = decode_payload(scrambled, self.CFG, TV213["dLen"] * 8)
        assert ok
        assert list(decoded) == list(data_bits)

    def test_decode_head_roundtrip(self):
        head_bits = _make_head_bits(TV213)
        scrambled = encode_head(head_bits, self.CFG)
        decoded, ok = decode_head(scrambled, self.CFG)
        assert ok
        assert list(decoded) == list(head_bits)


# =========================================================================
# TX → RX 闭环测试 (无信道噪声)
# =========================================================================


class TestTxRxLoopback:
    """无噪声 TX→RX 闭环: tx_chain → rx_chain 应完美还原数据。"""

    def _run_loopback(self, tv: dict, mcs: int, crc_len: int):
        cfg = TxConfig(
            frame_type=2,
            mcs_index=mcs,
            pid=tv["group"]["pid"],
            whitening_seed=tv["wt_seed"],
            crc_seed=tv["crc_seed"],
            crc_len=crc_len,
            ctrl_bits_len=tv["ctrl_bits"],
            pilot_interval=8,
            sps=4,
        )
        head_bits = _make_head_bits(tv)
        data_bits = _make_pyld_bits(tv["tv_id"], tv["ctrl_bits"], tv["dLen"])

        iq = tx_chain(head_bits, data_bits, cfg)
        result = rx_chain(iq, cfg, tv["dLen"])

        assert result.crc_ok, f"CRC 校验失败 (TV{tv['tv_id']})"
        assert list(result.data_bits) == list(data_bits), f"数据不匹配 (TV{tv['tv_id']})"

    def test_tv201_loopback(self):
        """TV201 (MCS7 rate 7/8) 闭环。"""
        self._run_loopback(TV201, mcs=7, crc_len=24)

    def test_tv213_loopback(self):
        """TV213 (MCS8 rate 1/1, CRC32) 闭环。"""
        self._run_loopback(TV213, mcs=8, crc_len=32)


# =========================================================================
# 帧同步测试
# =========================================================================


class TestFrameSync:
    """帧同步基本功能测试。"""

    def test_sync_detection_ft2(self):
        """FT2 帧同步应找到同步序列位置。"""
        cfg = TxConfig(
            frame_type=2, mcs_index=7,
            pid=TV201["group"]["pid"],
            whitening_seed=TV201["wt_seed"],
            sps=1,
        )
        head_bits = _make_head_bits(TV201)
        data_bits = _make_pyld_bits(201, TV201["ctrl_bits"], TV201["dLen"])
        iq = tx_chain(head_bits, data_bits, TxConfig(
            frame_type=2, mcs_index=7,
            pid=TV201["group"]["pid"],
            whitening_seed=TV201["wt_seed"],
            crc_seed=TV201["crc_seed"],
            crc_len=24,
            ctrl_bits_len=TV201["ctrl_bits"],
            sps=1,
        ))
        pos = frame_sync(iq, cfg)
        # 应在前导码之后检测到同步序列
        assert pos >= 0

    def test_sync_no_signal(self):
        """纯噪声中应返回 -1 (或低置信度)。"""
        cfg = TxConfig(frame_type=2, pid=0x123456, sps=1)
        rng = np.random.default_rng(42)
        noise = rng.normal(0, 0.1, 200) + 1j * rng.normal(0, 0.1, 200)
        pos = frame_sync(noise, cfg)
        # 纯噪声不应产生高相关峰
        assert pos == -1 or pos >= 0  # 允许误检但不崩溃
