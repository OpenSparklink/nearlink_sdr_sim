"""FT1/FT3/FT4 帧类型 pipeline 测试。

FT1: GFSK 全链路, 基于 TV101 参数
FT3/FT4: PSK 帧类型, 合成测试 (无标准测试向量)
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


def _hex_to_bits_lsb(hex_val: int, nbits: int) -> list[int]:
    return [(hex_val >> i) & 1 for i in range(nbits)]


# =========================================================================
# FT1 (GFSK) 测试
# =========================================================================


class TestFT1Pipeline:
    """FT1 GFSK pipeline 测试, 基于 TV101 参数。

    TV101: FT1, A1, PID=0x873456, dLen=32B, CRC24A seed=0x555555, wt=0x4E
    """

    CFG = TxConfig(
        frame_type=1,
        mcs_index=8,  # rate 1/1 = uncoded, 实际 FT1 无 MCS
        pid=0x873456,
        whitening_seed=0x4E,
        crc_seed=0x555555,
        crc_len=24,
        ctrl_bits_len=20,
        sps=8,
    )

    def _make_head_bits(self) -> np.ndarray:
        """TV101 头部: 20 ctrl + 12 CRC = 32 bits。"""
        from nearlink_sdr.common.crc import CRC12_POLY, crc_attach

        head = list(prbs11(20, seed=101))
        dl_bits = _hex_to_bits_lsb(32, 8)  # data_length = 32 bytes
        head[12:20] = dl_bits
        head_arr = np.array(head, dtype=int)
        sync_seed = 0x27C8F4C6 & 0xFFF
        return crc_attach(head_arr, CRC12_POLY, 12, seed=sync_seed)

    def _make_data_bits(self) -> np.ndarray:
        """TV101 载荷: 256 bits from PRBS11。"""
        seq = prbs11(20 + 256, seed=101)
        return np.array(seq[20:], dtype=int)

    def test_encode_payload_roundtrip(self):
        """encode → decode 载荷应可逆。"""
        data = self._make_data_bits()
        scrambled = encode_payload(data, self.CFG)
        decoded, ok = decode_payload(scrambled, self.CFG, 256)
        assert ok
        assert list(decoded) == list(data)

    def test_encode_head_roundtrip(self):
        """encode → decode 头部应可逆 (FT1 无 Polar 编码)。"""
        head = self._make_head_bits()
        scrambled = encode_head(head, self.CFG)
        decoded, ok = decode_head(scrambled, self.CFG)
        assert ok
        assert list(decoded) == list(head)

    def test_txheadw_matches_standard(self):
        """txHeadW 应匹配附录 H TV101。"""
        head = self._make_head_bits()
        scrambled = encode_head(head, self.CFG)
        expected = _hex_to_bits_lsb(0xBEDA1401, 32)
        assert list(scrambled) == expected

    def test_tx_chain_gfsk(self):
        """FT1 tx_chain 应产生 GFSK IQ 信号。"""
        head = self._make_head_bits()
        data = self._make_data_bits()
        iq = tx_chain(head, data, self.CFG)
        assert len(iq) > 0
        assert np.iscomplexobj(iq)

    def test_ft1_loopback(self):
        """FT1 TX → RX 无噪声闭环。"""
        head = self._make_head_bits()
        data = self._make_data_bits()
        iq = tx_chain(head, data, self.CFG)
        result = rx_chain(iq, self.CFG, 32)
        assert result.crc_ok
        assert list(result.data_bits) == list(data)


# =========================================================================
# FT3 (QPSK, segment_with_crc) 测试
# =========================================================================


class TestFT3Pipeline:
    """FT3 pipeline 测试, 合成数据。

    FT3: QPSK, Polar 256 for head, segment_with_crc for payload.
    """

    CFG = TxConfig(
        frame_type=3,
        mcs_index=5,  # rate 5/8, QPSK
        pid=0,  # m_seq_index
        whitening_seed=0x52,
        crc_seed=0x123456,
        crc_len=24,
        ctrl_bits_len=27,  # B 组控制信息 27 bits
        pilot_interval=4,
        sps=4,
    )

    def _make_head_bits(self) -> np.ndarray:
        """B 组控制信息 27 + CRC24B = 51 bits。"""
        rng = np.random.default_rng(301)
        return rng.integers(0, 2, 51).astype(np.int8)

    def _make_data_bits(self, n_bytes: int = 10) -> np.ndarray:
        rng = np.random.default_rng(302)
        return rng.integers(0, 2, n_bytes * 8).astype(int)

    def test_encode_payload_roundtrip(self):
        """FT3 encode → decode 载荷。"""
        data = self._make_data_bits()
        scrambled = encode_payload(data, self.CFG)
        decoded, ok = decode_payload(scrambled, self.CFG, 80)
        assert ok
        assert list(decoded) == list(data)

    def test_encode_head_roundtrip(self):
        """FT3 encode → decode 头部 (Polar 256)。"""
        head = self._make_head_bits()
        scrambled = encode_head(head, self.CFG)
        assert len(scrambled) == 256
        decoded, ok = decode_head(scrambled, self.CFG)
        assert ok
        assert list(decoded) == list(head)

    def test_tx_chain_produces_iq(self):
        """FT3 tx_chain 应产生 PSK IQ 信号。"""
        head = self._make_head_bits()
        data = self._make_data_bits()
        iq = tx_chain(head, data, self.CFG)
        assert len(iq) > 0
        assert np.iscomplexobj(iq)

    def test_ft3_loopback(self):
        """FT3 TX → RX 无噪声闭环。"""
        head = self._make_head_bits()
        data = self._make_data_bits()
        iq = tx_chain(head, data, self.CFG)
        result = rx_chain(iq, self.CFG, 10)
        assert result.crc_ok
        assert list(result.data_bits) == list(data)


# =========================================================================
# FT4 (BPSK, segment_with_crc) 测试
# =========================================================================


class TestFT4Pipeline:
    """FT4 pipeline 测试, 合成数据。

    FT4: BPSK, Polar 256 for head, segment_with_crc for payload.
    """

    CFG = TxConfig(
        frame_type=4,
        mcs_index=0,  # rate 1/4, BPSK
        pid=0,  # m_seq_index
        whitening_seed=0x33,
        crc_seed=0x654321,
        crc_len=24,
        ctrl_bits_len=27,  # B 组控制信息
        pilot_interval=4,
        sps=4,
    )

    def _make_head_bits(self) -> np.ndarray:
        rng = np.random.default_rng(401)
        return rng.integers(0, 2, 51).astype(np.int8)

    def _make_data_bits(self, n_bytes: int = 8) -> np.ndarray:
        rng = np.random.default_rng(402)
        return rng.integers(0, 2, n_bytes * 8).astype(int)

    def test_encode_payload_roundtrip(self):
        """FT4 encode → decode 载荷。"""
        data = self._make_data_bits()
        scrambled = encode_payload(data, self.CFG)
        decoded, ok = decode_payload(scrambled, self.CFG, 64)
        assert ok
        assert list(decoded) == list(data)

    def test_encode_head_roundtrip(self):
        """FT4 encode → decode 头部 (Polar 256)。"""
        head = self._make_head_bits()
        scrambled = encode_head(head, self.CFG)
        assert len(scrambled) == 256
        decoded, ok = decode_head(scrambled, self.CFG)
        assert ok
        assert list(decoded) == list(head)

    def test_tx_chain_produces_iq(self):
        """FT4 tx_chain 应产生 PSK IQ 信号。"""
        head = self._make_head_bits()
        data = self._make_data_bits()
        iq = tx_chain(head, data, self.CFG)
        assert len(iq) > 0
        assert np.iscomplexobj(iq)

    def test_ft4_loopback(self):
        """FT4 TX → RX 无噪声闭环。"""
        head = self._make_head_bits()
        data = self._make_data_bits()
        iq = tx_chain(head, data, self.CFG)
        result = rx_chain(iq, self.CFG, 8)
        assert result.crc_ok
        assert list(result.data_bits) == list(data)


# =========================================================================
# 帧同步多帧类型测试
# =========================================================================


class TestFrameSyncMultiFT:
    """不同帧类型的帧同步检测。"""

    def test_ft3_sync(self):
        cfg = TxConfig(frame_type=3, mcs_index=5, pid=0, sps=1,
                       whitening_seed=0x52, crc_seed=0, crc_len=24,
                       ctrl_bits_len=27, pilot_interval=4)
        rng = np.random.default_rng(303)
        head = rng.integers(0, 2, 51).astype(np.int8)
        data = rng.integers(0, 2, 80).astype(int)
        iq = tx_chain(head, data, cfg)
        pos = frame_sync(iq, cfg)
        assert pos >= 0

    def test_ft4_sync(self):
        cfg = TxConfig(frame_type=4, mcs_index=0, pid=0, sps=1,
                       whitening_seed=0x33, crc_seed=0, crc_len=24,
                       ctrl_bits_len=27, pilot_interval=4)
        rng = np.random.default_rng(403)
        head = rng.integers(0, 2, 51).astype(np.int8)
        data = rng.integers(0, 2, 64).astype(int)
        iq = tx_chain(head, data, cfg)
        pos = frame_sync(iq, cfg)
        assert pos >= 0
