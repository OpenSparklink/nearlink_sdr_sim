"""PRBS 发生器测试 + 标准 14 章测试向量验证"""

import typing

import numpy as np
import pytest

from nearlink_sdr.common.prbs import prbs11, prbs17

# =========================================================================
# PRBS11 基本测试
# =========================================================================


class TestPRBS11:

    def test_period_2047(self):
        """PRBS11 周期应为 2^11 - 1 = 2047。"""
        seq = prbs11(2047 * 2, seed=0x7FF)
        assert np.array_equal(seq[:2047], seq[2047:])

    def test_default_seed_all_ones(self):
        seq = prbs11(5, seed=0x7FF)
        # 全 1 初始态, 第一个输出 = stage[10] = 1
        assert seq[0] == 1

    def test_seed_101_first_12_bits(self):
        """TV101 (TV_ID=101) 的 PRBS11 前 12 比特应匹配附录 H 的 HeadBits。"""
        # TV_ID=101 → seed = 101 (低 11 位)
        seq = prbs11(20, seed=101)
        # 附录 H TV101 HeadBits (20 bits): hex 00020530, LSB first
        # 前 12 位来自 PRBS11 (后 8 位被 data_length=32 覆盖)
        expected_first_12 = [0, 0, 0, 0, 1, 1, 0, 0, 1, 0, 1, 0]
        assert list(seq[:12]) == expected_first_12

    def test_zero_seed_gives_all_zeros(self):
        """全零初始态应输出全零 (退化)。"""
        seq = prbs11(10, seed=0)
        assert np.all(seq == 0)

    def test_different_seeds_different_output(self):
        s1 = prbs11(100, seed=101)
        s2 = prbs11(100, seed=102)
        assert not np.array_equal(s1, s2)

    def test_output_values_binary(self):
        seq = prbs11(1000, seed=0x7FF)
        assert set(seq.tolist()).issubset({0, 1})


# =========================================================================
# PRBS17 基本测试
# =========================================================================


class TestPRBS17:

    def test_default_seed_first_output(self):
        seq = prbs17(5, seed=0x1FFFF)
        assert seq[0] == 1

    def test_period_131071(self):
        """PRBS17 周期应为 2^17 - 1 = 131071。"""
        period = 131071
        seq = prbs17(period + 100, seed=0x1FFFF)
        assert np.array_equal(seq[:100], seq[period:period + 100])

    def test_output_values_binary(self):
        seq = prbs17(500, seed=0x1FFFF)
        assert set(seq.tolist()).issubset({0, 1})


# =========================================================================
# 测试向量 TV101 端到端验证
# =========================================================================


class TestTV101:
    """验证 TV101 (FrameType 1, A1, GFSK) 的各节点数据。

    参数:
      TV_ID=101, FrameType=1, MCS=NA, mSeq=NA, pilotN=NA
      PID=0x873456, ControlType=A1, ControlLen=20bit
      DataLen=32Byte=256bit, CRC=24bit, CRCSeed=0x555555
      WhiteningSeed=0x4E
    """

    TV_ID = 101
    PID_HEX = 0x873456
    WHITENING_SEED = 0x4E
    CRC_SEED = 0x555555
    DATA_LEN_BYTES = 32
    CTRL_LEN = 20

    @staticmethod
    def _hex_to_bits_lsb(hex_val: int, nbits: int) -> list[int]:
        """将整数转为 LSB-first 比特列表。"""
        return [(hex_val >> i) & 1 for i in range(nbits)]

    def test_pid_bits(self):
        """PID 比特匹配附录 H。"""
        # 附录 H: PID (24 bits) hex 00873456
        # LSB first: 01101010 00101100 11100001
        expected = self._hex_to_bits_lsb(0x873456, 24)
        assert expected[:8] == [0, 1, 1, 0, 1, 0, 1, 0]

    def test_prbs11_headbits(self):
        """PRBS11 输出前 12 位匹配 HeadBits 中未覆盖的部分。"""
        seq = prbs11(self.CTRL_LEN, seed=self.TV_ID)
        # HeadBits[0:12] 来自 PRBS11
        expected = [0, 0, 0, 0, 1, 1, 0, 0, 1, 0, 1, 0]
        assert list(seq[:12]) == expected

    def test_headbits_data_length_field(self):
        """HeadBits 中 data_length 字段 (位 12-19) 应为 32 (LSB first)。"""
        # 构造完整 HeadBits: PRBS11 输出 + 覆盖 data_length 字段
        head = list(prbs11(self.CTRL_LEN, seed=self.TV_ID))
        # 覆盖 data_length (A1: 最后 8 位, 位置 12-19) 为 32, LSB first
        dl_bits = self._hex_to_bits_lsb(self.DATA_LEN_BYTES, 8)
        head[12:20] = dl_bits
        # 验证完整 HeadBits 匹配附录 H
        # HeadBits hex 00020530 (20 bits, LSB first)
        expected = self._hex_to_bits_lsb(0x00020530, 20)
        assert head == expected

    def test_txhead_with_crc12(self):
        """txHead (HeadBits + CRC12) 应匹配附录 H 的 32 位。"""
        from nearlink_sdr.common.crc import CRC12_POLY, crc_attach

        # 构造 HeadBits
        head = list(prbs11(self.CTRL_LEN, seed=self.TV_ID))
        dl_bits = self._hex_to_bits_lsb(self.DATA_LEN_BYTES, 8)
        head[12:20] = dl_bits
        head_arr = np.array(head, dtype=int)

        # SyncWord low 12 bits 作为 CRC12 seed
        # 附录 H: SyncWord hex 27C8F4C6, low 12 bits = 0x4C6
        sync_seed = 0x27C8F4C6 & 0xFFF  # 0x4C6 = 1222

        txhead = crc_attach(head_arr, CRC12_POLY, 12, seed=sync_seed)
        assert len(txhead) == 32

        # 附录 H: txHead hex 28920530 (32 bits, LSB first)
        expected = self._hex_to_bits_lsb(0x28920530, 32)
        assert list(txhead) == expected

    def test_txheadc_uncoded(self):
        """帧类型 1 控制信息不编码, txHeadC = txHead。"""
        # 附录 H 确认: txHeadC (32) hex 28920530 = txHead
        # 帧类型 1 A1 无编码
        pass  # txHeadC = txHead for frame type 1

    def test_txheadw_whitened(self):
        """txHeadW = txHeadC XOR scramble_sequence (加扰后) 匹配附录 H。"""
        from nearlink_sdr.common.crc import CRC12_POLY, crc_attach
        from nearlink_sdr.common.scrambler import scramble

        # 构造 txHeadC (= txHead for frame type 1)
        head = list(prbs11(self.CTRL_LEN, seed=self.TV_ID))
        dl_bits = self._hex_to_bits_lsb(self.DATA_LEN_BYTES, 8)
        head[12:20] = dl_bits
        head_arr = np.array(head, dtype=int)
        sync_seed = 0x27C8F4C6 & 0xFFF
        txheadc = crc_attach(head_arr, CRC12_POLY, 12, seed=sync_seed)

        # 加扰
        txheadw = scramble(txheadc.astype(np.uint8), self.WHITENING_SEED)

        # 附录 H: txHeadW hex BEDA1401 (32 bits, LSB first)
        expected = self._hex_to_bits_lsb(0xBEDA1401, 32)
        assert list(txheadw) == expected

    def test_pyldbits_from_prbs11(self):
        """PyLdBits 由 PRBS11 连续生成 (不复位), 前 64 比特匹配附录 H。"""
        # PRBS11 生成 HeadBits + PyLdBits, 连续不复位
        total_bits = self.CTRL_LEN + self.DATA_LEN_BYTES * 8
        seq = prbs11(total_bits, seed=self.TV_ID)
        pyld_bits = seq[self.CTRL_LEN:]
        assert len(pyld_bits) == 256

        # 附录 H: PyLdBits (256 bits) 第一个 32-bit word: F4C4FAE2
        expected_first32 = self._hex_to_bits_lsb(0xF4C4FAE2, 32)
        assert list(pyld_bits[:32]) == expected_first32

        # 第二个 32-bit word: E2AD0321
        expected_second32 = self._hex_to_bits_lsb(0xE2AD0321, 32)
        assert list(pyld_bits[32:64]) == expected_second32

    def test_pyld_all_256_bits(self):
        """验证完整 256 比特 PyLdBits。"""
        total_bits = self.CTRL_LEN + 256
        seq = prbs11(total_bits, seed=self.TV_ID)
        pyld = seq[self.CTRL_LEN:]

        # 附录 H 所有 256 比特 (8 个 32-bit words)
        words = [0xF4C4FAE2, 0xE2AD0321, 0x5383B1AE, 0xB68D9779,
                 0xB56C1B8E, 0x4F8E36DD, 0x4CAFC219, 0xFD0120B4]
        expected = []
        for w in words:
            expected.extend(self._hex_to_bits_lsb(w, 32))
        assert list(pyld) == expected


# =========================================================================
# 测试向量参数表一致性
# =========================================================================


class TestTVParameters:
    """验证测试向量参数表中的配置一致性。"""

    # 表 73 部分参数
    TV_PARAMS: typing.ClassVar = [
        # (TV_ID, FrameType, ControlType, ControlLen, DataLenByte, CRCbits, WhiteningSeed)
        (101, 1, "A1", 20, 32, 24, 0x4E),
        (102, 1, "A3", 28, 33, 32, 0x49),
        (103, 1, "A1", 20, 34, 24, 0x4E),
        (104, 1, "A3", 28, 35, 32, 0x49),
        (201, 2, "A3", 36, 1, 24, 0x52),
        (209, 2, "A1", 28, 1, 24, 0x55),
    ]

    @pytest.mark.parametrize("tv_id,ft,ct,clen,dlen,crc,ws", TV_PARAMS)
    def test_control_len_matches_type(self, tv_id, ft, ct, clen, dlen, crc, ws):
        """控制信息长度应与控制类型对应。"""
        # A 组 frame type 1 不含 LQI
        a_group_len_no_lqi = {"A1": 20, "A2": 20, "A3": 28, "A4": 28,
                              "A5": 20, "A6": 28, "A7": 28}
        # A 组 frame type 2 含 LQI (8 bit) + Polar 编码前
        a_group_len_with_lqi = {k: v + 8 for k, v in a_group_len_no_lqi.items()}

        if ct.startswith("A"):
            if ft == 1:
                assert clen == a_group_len_no_lqi[ct]
            elif ft == 2:
                assert clen == a_group_len_with_lqi[ct]

    def test_whitening_seed_range(self):
        """加扰种子应在 7 位范围内 (0-127)。"""
        for tv_id, _, _, _, _, _, ws in self.TV_PARAMS:
            assert 0 <= ws <= 127, f"TV{tv_id}: whitening seed {ws} 超限"


# =========================================================================
# PID -> SyncWord 链路验证 (sync_signal_1)
# =========================================================================


class TestSyncWordFromPID:
    """验证 PID -> BCH(31,26) -> m31 XOR -> SyncWord 链路。

    使用附录 H 中 TV101-TV104 的 PID + SyncWord 数据进行交叉验证。
    """

    @staticmethod
    def _hex_to_bits_lsb(hex_val: int, nbits: int) -> list[int]:
        return [(hex_val >> i) & 1 for i in range(nbits)]

    # (TV_ID, PID_24, SyncWord_32_hex)
    TV_SYNC_DATA: typing.ClassVar = [
        (101, 0x873456, 0x27C8F4C6),
        (102, 0x785643, 0x58357C92),
        (103, 0x123456, 0x199CF4C6),
        (104, 0x400001, 0x6CD4259A),
    ]

    @pytest.mark.parametrize("tv_id,pid,sync_hex", TV_SYNC_DATA)
    def test_sync_signal_1_matches_tv(self, tv_id, pid, sync_hex):
        """sync_signal_1(PID) 应产生附录 H 给出的 SyncWord。"""
        from nearlink_sdr.phy.sync_sequence import sync_signal_1

        sync = sync_signal_1(pid)
        expected = self._hex_to_bits_lsb(sync_hex, 32)
        assert list(sync) == expected, f"TV{tv_id}: SyncWord mismatch"

    @pytest.mark.parametrize("tv_id,pid,sync_hex", TV_SYNC_DATA)
    def test_bchout_xor_pnseq_equals_syncword(self, tv_id, pid, sync_hex):
        """bchOut XOR pnSeq 应等于 SyncWord 的低 31 位。"""
        from nearlink_sdr.common.bch import bch_31_26_encode
        from nearlink_sdr.common.m_sequence import generate_m_sequence

        pid_bits = np.array(self._hex_to_bits_lsb(pid, 24), dtype=int)
        a_tilde = np.zeros(26, dtype=int)
        a_tilde[0] = 1
        a_tilde[2:26] = pid_bits
        bch_out = bch_31_26_encode(a_tilde)

        m_seq = generate_m_sequence(5, 0b101001, 0b11111, 31)
        scrambled = bch_out ^ m_seq

        sync = np.zeros(32, dtype=int)
        sync[:31] = scrambled

        expected = self._hex_to_bits_lsb(sync_hex, 32)
        assert list(sync) == expected, f"TV{tv_id}: bchOut^pnSeq mismatch"


# =========================================================================
# TV103 端到端验证 (FrameType 1, A1, PID=0x123456)
# =========================================================================


class TestTV103:
    """验证 TV103 (FrameType 1, A1, GFSK) 部分节点数据。

    参数:
      TV_ID=103, PID=0x123456, ControlType=A1, ControlLen=20bit
      DataLen=34Byte=272bit, CRC=24bit, CRCSeed=0x555555
      WhiteningSeed=0x4E
    """

    TV_ID = 103
    WHITENING_SEED = 0x4E
    DATA_LEN_BYTES = 34
    CTRL_LEN = 20

    @staticmethod
    def _hex_to_bits_lsb(hex_val: int, nbits: int) -> list[int]:
        return [(hex_val >> i) & 1 for i in range(nbits)]

    def test_prbs11_generates_correct_length(self):
        """PRBS11 种子为 TV_ID=103, 生成 20 + 272 = 292 比特。"""
        total = self.CTRL_LEN + self.DATA_LEN_BYTES * 8
        seq = prbs11(total, seed=self.TV_ID)
        assert len(seq) == total

    def test_txpyldw_full(self):
        """txPyLdW 全部 296 比特匹配附录 H。

        加扰序列连续作用于整帧: 头部 32 比特 + 载荷 296 比特。
        载荷加扰从偏移 32 (A1 txHead 长度) 开始。
        """
        from nearlink_sdr.common.crc import CRC24A_POLY, crc_attach
        from nearlink_sdr.common.scrambler import scramble_sequence

        total_bits = self.CTRL_LEN + self.DATA_LEN_BYTES * 8
        seq = prbs11(total_bits, seed=self.TV_ID)
        pyld_bits = seq[self.CTRL_LEN:]

        txpyld = crc_attach(
            np.array(pyld_bits, dtype=int), CRC24A_POLY, 24, seed=0x555555
        )

        HEAD_A1 = 32
        sc = scramble_sequence(HEAD_A1 + len(txpyld), self.WHITENING_SEED)
        txpyldw = txpyld.astype(np.uint8) ^ sc[HEAD_A1 : HEAD_A1 + len(txpyld)]

        assert len(txpyldw) == 296

        # 附录 H TV103 txPyLdW 全部 5 个 64-bit words
        expected_words = [
            (0x61F4912E, 0xBD856BB1),
            (0x330DE301, 0x0DBF9624),
            (0x62096F60, 0x6749415C),
            (0x35152A16, 0x5DB914A6),
            (0x4D7C6722, 0x00000081),
        ]
        expected = []
        for w1, w2 in expected_words:
            expected.extend(self._hex_to_bits_lsb(w1, 32))
            expected.extend(self._hex_to_bits_lsb(w2, 32))

        assert list(txpyldw[:296]) == expected[:296]


# =========================================================================
# TV102 端到端验证 (FrameType 1, A3, PID=0x785643)
# =========================================================================


class TestTV102:
    """验证 TV102 (FrameType 1, A3, GFSK) txPyLdW。

    参数:
      TV_ID=102, PID=0x785643, ControlType=A3, ControlLen=28bit
      DataLen=33Byte=264bit, CRC=32bit, CRCSeed=0x12345678
      WhiteningSeed=0x49
    """

    TV_ID = 102
    WHITENING_SEED = 0x49
    DATA_LEN_BYTES = 33
    CTRL_LEN = 28

    @staticmethod
    def _hex_to_bits_lsb(hex_val: int, nbits: int) -> list[int]:
        return [(hex_val >> i) & 1 for i in range(nbits)]

    def test_txpyldw_full(self):
        """txPyLdW 全部 296 比特匹配附录 H。"""
        from nearlink_sdr.common.crc import CRC32_POLY, crc_attach
        from nearlink_sdr.common.scrambler import scramble_sequence

        total_bits = self.CTRL_LEN + self.DATA_LEN_BYTES * 8
        seq = prbs11(total_bits, seed=self.TV_ID)
        pyld_bits = seq[self.CTRL_LEN:]

        txpyld = crc_attach(
            np.array(pyld_bits, dtype=int), CRC32_POLY, 32, seed=0x12345678
        )

        HEAD_A3 = 40  # A3 txHead = 28 ctrl + 12 CRC = 40 bits
        sc = scramble_sequence(HEAD_A3 + len(txpyld), self.WHITENING_SEED)
        txpyldw = txpyld.astype(np.uint8) ^ sc[HEAD_A3 : HEAD_A3 + len(txpyld)]

        assert len(txpyldw) == 296

        expected_words = [
            (0x24616E17, 0xE90F015D),
            (0x57F03768, 0x6104D566),
            (0x85D9BEAE, 0x5330ADDD),
            (0xE64773ED, 0x67234E05),
            (0x6E2B4FDB, 0x000000FB),
        ]
        expected = []
        for w1, w2 in expected_words:
            expected.extend(self._hex_to_bits_lsb(w1, 32))
            expected.extend(self._hex_to_bits_lsb(w2, 32))

        assert list(txpyldw[:296]) == expected[:296]


# =========================================================================
# TV104 端到端验证 (FrameType 1, A3, PID=0x400001)
# =========================================================================


class TestTV104:
    """验证 TV104 (FrameType 1, A3, GFSK) txPyLdW。

    参数:
      TV_ID=104, PID=0x400001, ControlType=A3, ControlLen=28bit
      DataLen=35Byte=280bit, CRC=32bit, CRCSeed=0x12345678
      WhiteningSeed=0x49
    """

    TV_ID = 104
    WHITENING_SEED = 0x49
    DATA_LEN_BYTES = 35
    CTRL_LEN = 28

    @staticmethod
    def _hex_to_bits_lsb(hex_val: int, nbits: int) -> list[int]:
        return [(hex_val >> i) & 1 for i in range(nbits)]

    def test_txpyldw_full(self):
        """txPyLdW 全部 312 比特匹配附录 H。"""
        from nearlink_sdr.common.crc import CRC32_POLY, crc_attach
        from nearlink_sdr.common.scrambler import scramble_sequence

        total_bits = self.CTRL_LEN + self.DATA_LEN_BYTES * 8
        seq = prbs11(total_bits, seed=self.TV_ID)
        pyld_bits = seq[self.CTRL_LEN:]

        txpyld = crc_attach(
            np.array(pyld_bits, dtype=int), CRC32_POLY, 32, seed=0x12345678
        )

        HEAD_A3 = 40
        sc = scramble_sequence(HEAD_A3 + len(txpyld), self.WHITENING_SEED)
        txpyldw = txpyld.astype(np.uint8) ^ sc[HEAD_A3 : HEAD_A3 + len(txpyld)]

        assert len(txpyldw) == 312

        expected_words = [
            (0xB55BD41D, 0x91DC728A),
            (0x4FDF2503, 0x9400F7F3),
            (0xC8D698D9, 0xA435CFC0),
            (0x629580CA, 0xF19AC5F1),
            (0xFD6BAC00, 0x00F5524E),
        ]
        expected = []
        for w1, w2 in expected_words:
            expected.extend(self._hex_to_bits_lsb(w1, 32))
            expected.extend(self._hex_to_bits_lsb(w2, 32))

        assert list(txpyldw[:312]) == expected[:312]
