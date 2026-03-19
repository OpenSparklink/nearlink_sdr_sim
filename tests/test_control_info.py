"""物理层控制信息测试 -- TXS-10002-2025 标准 6.4"""

import numpy as np
import pytest

from nearlink_sdr.phy.control_info import (
    ControlInfoA1,
    ControlInfoA2,
    ControlInfoA3,
    ControlInfoA4,
    ControlInfoA5,
    ControlInfoA6,
    ControlInfoA7,
    ControlInfoB1,
    ControlInfoB2,
    ControlInfoB3,
    ControlInfoB4,
    ControlInfoB5,
    ControlInfoType,
    _bits_to_int,
    _int_to_bits,
)


# =========================================================================
# 辅助函数
# =========================================================================


class TestBitConversion:
    """测试比特与整数转换。"""

    def test_int_to_bits_basic(self):
        bits = _int_to_bits(0b101, 3)
        assert list(bits) == [1, 0, 1]

    def test_int_to_bits_zero(self):
        bits = _int_to_bits(0, 8)
        assert list(bits) == [0] * 8

    def test_int_to_bits_full(self):
        bits = _int_to_bits(0xFF, 8)
        assert list(bits) == [1] * 8

    def test_bits_to_int_basic(self):
        bits = np.array([1, 0, 1], dtype=int)
        assert _bits_to_int(bits) == 5

    def test_roundtrip(self):
        for v in [0, 1, 127, 255, 1023, 2047]:
            w = v.bit_length() or 1
            assert _bits_to_int(_int_to_bits(v, w)) == v


# =========================================================================
# ControlInfoType 枚举
# =========================================================================


class TestControlInfoType:
    def test_a_group_values(self):
        assert ControlInfoType.A1 == 1
        assert ControlInfoType.A7 == 7

    def test_b_group_values(self):
        assert ControlInfoType.B1 == 0b10001
        assert ControlInfoType.B5 == 0b10101


# =========================================================================
# A1: 广播 / 发现 / 接入
# =========================================================================


class TestA1:
    SYNC_SEED = 0x123

    def test_pack_frame_type1_length(self):
        ci = ControlInfoA1(broadcast_type=3, packet_type=1,
                           reserved=0, data_length=100)
        bits = ci.pack(self.SYNC_SEED)
        assert len(bits) == 32  # 20 info + 12 CRC

    def test_pack_frame_type2_length(self):
        ci = ControlInfoA1(broadcast_type=3, packet_type=1,
                           reserved=0, data_length=100)
        bits = ci.pack(self.SYNC_SEED, lqi=0xA5)
        assert len(bits) == 40  # 8 LQI + 20 info + 12 CRC

    def test_roundtrip_no_lqi(self):
        ci = ControlInfoA1(broadcast_type=2, packet_type=5,
                           reserved=0, data_length=200)
        bits = ci.pack(self.SYNC_SEED)
        lqi, ci2 = ControlInfoA1.unpack(bits, self.SYNC_SEED, has_lqi=False)
        assert lqi is None
        assert ci2 == ci

    def test_roundtrip_with_lqi(self):
        ci = ControlInfoA1(broadcast_type=1, packet_type=3,
                           reserved=0x3F, data_length=255)
        bits = ci.pack(self.SYNC_SEED, lqi=0xC0)
        lqi, ci2 = ControlInfoA1.unpack(bits, self.SYNC_SEED, has_lqi=True)
        assert lqi == 0xC0
        assert ci2 == ci

    def test_crc_tamper(self):
        ci = ControlInfoA1(broadcast_type=0, packet_type=0,
                           reserved=0, data_length=0)
        bits = ci.pack(self.SYNC_SEED).copy()
        bits[5] ^= 1  # 篡改一个比特
        with pytest.raises(ValueError, match="CRC12"):
            ControlInfoA1.unpack(bits, self.SYNC_SEED, has_lqi=False)

    def test_different_seed_fails(self):
        ci = ControlInfoA1(broadcast_type=0, packet_type=0,
                           reserved=0, data_length=10)
        bits = ci.pack(self.SYNC_SEED)
        with pytest.raises(ValueError, match="CRC12"):
            ControlInfoA1.unpack(bits, 0x456, has_lqi=False)


# =========================================================================
# A2: 异步单播
# =========================================================================


class TestA2:
    SYNC_SEED = 0x456

    def test_pack_frame_type1_length(self):
        ci = ControlInfoA2(packet_type=1, empty_packet=0, tx_sn=1,
                           rx_sn=0, flow_ctrl=1, sys_mgmt_rx=0,
                           reserved=0, data_length=512)
        bits = ci.pack(self.SYNC_SEED)
        assert len(bits) == 32

    def test_roundtrip_no_lqi(self):
        ci = ControlInfoA2(packet_type=2, empty_packet=1, tx_sn=0,
                           rx_sn=1, flow_ctrl=0, sys_mgmt_rx=1,
                           reserved=3, data_length=2047)
        bits = ci.pack(self.SYNC_SEED)
        lqi, ci2 = ControlInfoA2.unpack(bits, self.SYNC_SEED, has_lqi=False)
        assert ci2 == ci

    def test_roundtrip_with_lqi(self):
        ci = ControlInfoA2(packet_type=3, empty_packet=0, tx_sn=1,
                           rx_sn=1, flow_ctrl=1, sys_mgmt_rx=1,
                           reserved=0, data_length=1000)
        bits = ci.pack(self.SYNC_SEED, lqi=0x55)
        lqi, ci2 = ControlInfoA2.unpack(bits, self.SYNC_SEED, has_lqi=True)
        assert lqi == 0x55
        assert ci2 == ci


# =========================================================================
# A3: 同步单播
# =========================================================================


class TestA3:
    SYNC_SEED = 0x789

    def test_pack_frame_type1_length(self):
        ci = ControlInfoA3(packet_type=0, empty_packet=0, tx_sn=15,
                           rx_sn=20, flow_ctrl=1, async_sched=0,
                           reserved=0, data_length=100)
        bits = ci.pack(self.SYNC_SEED)
        assert len(bits) == 40  # 28 info + 12 CRC

    def test_frame_type2_length(self):
        ci = ControlInfoA3(packet_type=0, empty_packet=0, tx_sn=0,
                           rx_sn=0, flow_ctrl=0, async_sched=0,
                           reserved=0, data_length=0)
        bits = ci.pack(self.SYNC_SEED, lqi=0x00)
        assert len(bits) == 48  # 8 + 28 + 12

    def test_roundtrip_5bit_sn(self):
        ci = ControlInfoA3(packet_type=1, empty_packet=1, tx_sn=31,
                           rx_sn=31, flow_ctrl=1, async_sched=1,
                           reserved=3, data_length=2047)
        bits = ci.pack(self.SYNC_SEED)
        _, ci2 = ControlInfoA3.unpack(bits, self.SYNC_SEED, has_lqi=False)
        assert ci2.tx_sn == 31
        assert ci2.rx_sn == 31
        assert ci2 == ci


# =========================================================================
# A4: 组播组长
# =========================================================================


class TestA4:
    SYNC_SEED = 0xABC

    def test_pack_length(self):
        ci = ControlInfoA4(packet_type=0, empty_packet=0, tx_sn=1,
                           rx_sn=0xFF, flow_ctrl=1, async_sched=0,
                           reserved=0, data_length=500)
        bits = ci.pack(self.SYNC_SEED)
        assert len(bits) == 40  # 28 + 12

    def test_roundtrip(self):
        ci = ControlInfoA4(packet_type=2, empty_packet=0, tx_sn=0,
                           rx_sn=0xA5, flow_ctrl=0, async_sched=1,
                           reserved=7, data_length=1234)
        bits = ci.pack(self.SYNC_SEED, lqi=0x33)
        lqi, ci2 = ControlInfoA4.unpack(bits, self.SYNC_SEED, has_lqi=True)
        assert lqi == 0x33
        assert ci2.rx_sn == 0xA5
        assert ci2 == ci


# =========================================================================
# A5: 组播组员
# =========================================================================


class TestA5:
    SYNC_SEED = 0xDEF

    def test_pack_length(self):
        ci = ControlInfoA5(packet_type=0, empty_packet=0, tx_sn=0,
                           rx_sn=0, flow_ctrl=0, async_sched=0,
                           reserved=0, data_length=0)
        bits = ci.pack(self.SYNC_SEED)
        assert len(bits) == 32  # 20 + 12

    def test_roundtrip(self):
        ci = ControlInfoA5(packet_type=1, empty_packet=1, tx_sn=1,
                           rx_sn=1, flow_ctrl=1, async_sched=1,
                           reserved=3, data_length=2047)
        bits = ci.pack(self.SYNC_SEED)
        _, ci2 = ControlInfoA5.unpack(bits, self.SYNC_SEED, has_lqi=False)
        assert ci2 == ci


# =========================================================================
# A6: 同步广播
# =========================================================================


class TestA6:
    SYNC_SEED = 0x111

    def test_pack_length(self):
        ci = ControlInfoA6(packet_type=0, packet_sn=10, packet_group=3,
                           end_indicator=1, sys_mgmt_rx=0,
                           reserved=0, data_length=100)
        bits = ci.pack(self.SYNC_SEED)
        assert len(bits) == 40  # 28 + 12

    def test_roundtrip(self):
        ci = ControlInfoA6(packet_type=2, packet_sn=31, packet_group=7,
                           end_indicator=0, sys_mgmt_rx=1,
                           reserved=0x1F, data_length=1500)
        bits = ci.pack(self.SYNC_SEED, lqi=0xFE)
        lqi, ci2 = ControlInfoA6.unpack(bits, self.SYNC_SEED, has_lqi=True)
        assert lqi == 0xFE
        assert ci2 == ci


# =========================================================================
# A7: 系统管理帧
# =========================================================================


class TestA7:
    SYNC_SEED = 0x222

    def test_pack_length(self):
        ci = ControlInfoA7(packet_sn=0, packet_group=0,
                           reserved=0, data_length=0)
        bits = ci.pack(self.SYNC_SEED)
        assert len(bits) == 40  # 28 + 12

    def test_roundtrip(self):
        ci = ControlInfoA7(packet_sn=17, packet_group=5,
                           reserved=0x1FF, data_length=2000)
        bits = ci.pack(self.SYNC_SEED)
        _, ci2 = ControlInfoA7.unpack(bits, self.SYNC_SEED, has_lqi=False)
        assert ci2 == ci

    def test_frame_type2_roundtrip(self):
        ci = ControlInfoA7(packet_sn=10, packet_group=3,
                           reserved=0, data_length=500)
        bits = ci.pack(self.SYNC_SEED, lqi=0xAB)
        lqi, ci2 = ControlInfoA7.unpack(bits, self.SYNC_SEED, has_lqi=True)
        assert lqi == 0xAB
        assert ci2 == ci


# =========================================================================
# B1: 单播 / 组播 PSK
# =========================================================================


class TestB1:
    LLID = 0x123456

    def test_pack_length(self):
        ci = ControlInfoB1(frame_format=0, harq_feedback=0,
                           packet_sn=0, mcs=5, data_length=100,
                           flow_ctrl=1, upper_link=0)
        bits = ci.pack(self.LLID)
        assert len(bits) == 51  # 27 + 24

    def test_roundtrip(self):
        ci = ControlInfoB1(frame_format=1, harq_feedback=0xA5,
                           packet_sn=1, mcs=12, data_length=2047,
                           flow_ctrl=0, upper_link=1)
        bits = ci.pack(self.LLID)
        ci2 = ControlInfoB1.unpack(bits, self.LLID)
        assert ci2 == ci

    def test_crc_tamper(self):
        ci = ControlInfoB1(frame_format=0, harq_feedback=0,
                           packet_sn=0, mcs=0, data_length=0,
                           flow_ctrl=0, upper_link=0)
        bits = ci.pack(self.LLID).copy()
        bits[10] ^= 1
        with pytest.raises(ValueError, match="CRC24B"):
            ControlInfoB1.unpack(bits, self.LLID)

    def test_wrong_llid_fails(self):
        ci = ControlInfoB1(frame_format=0, harq_feedback=0,
                           packet_sn=0, mcs=0, data_length=0,
                           flow_ctrl=0, upper_link=0)
        bits = ci.pack(self.LLID)
        with pytest.raises(ValueError, match="CRC24B"):
            ControlInfoB1.unpack(bits, 0x654321)


# =========================================================================
# B2: 反馈组播组长
# =========================================================================


class TestB2:
    LLID = 0xABCDEF

    def test_pack_length(self):
        ci = ControlInfoB2(harq_feedback=0, flow_ctrl=0, upper_link=0)
        bits = ci.pack(self.LLID)
        assert len(bits) == 51

    def test_roundtrip(self):
        ci = ControlInfoB2(harq_feedback=0x1FFFFFF,
                           flow_ctrl=1, upper_link=1)
        bits = ci.pack(self.LLID)
        ci2 = ControlInfoB2.unpack(bits, self.LLID)
        assert ci2 == ci


# =========================================================================
# B3: 同步广播
# =========================================================================


class TestB3:
    LLID = 0x112233

    def test_pack_length(self):
        ci = ControlInfoB3(packet_group=1, packet_sn=2, mcs=3,
                           data_length=100, flow_ctrl=1,
                           max_sn_indicator=0)
        bits = ci.pack(self.LLID)
        assert len(bits) == 51

    def test_roundtrip(self):
        ci = ControlInfoB3(packet_group=31, packet_sn=31, mcs=15,
                           data_length=2047, flow_ctrl=0,
                           max_sn_indicator=1)
        bits = ci.pack(self.LLID)
        ci2 = ControlInfoB3.unpack(bits, self.LLID)
        assert ci2 == ci


# =========================================================================
# B4: 异步广播
# =========================================================================


class TestB4:
    LLID = 0x445566

    def test_pack_length(self):
        ci = ControlInfoB4(broadcast_group_id=0, data_update=0,
                           packet_sn=0, mcs=0, data_length=0,
                           flow_ctrl=0, max_sn_indicator=0)
        bits = ci.pack(self.LLID)
        assert len(bits) == 51

    def test_roundtrip(self):
        ci = ControlInfoB4(broadcast_group_id=31, data_update=1,
                           packet_sn=15, mcs=12, data_length=1500,
                           flow_ctrl=1, max_sn_indicator=1)
        bits = ci.pack(self.LLID)
        ci2 = ControlInfoB4.unpack(bits, self.LLID)
        assert ci2 == ci


# =========================================================================
# B5: 基础广播 / 发现 / 接入
# =========================================================================


class TestB5:
    LLID = 0x778899

    def test_pack_length(self):
        ci = ControlInfoB5(reserved=0, msg_type=0, accessible=0,
                           queryable=0, directed_content=0,
                           undirected_content=0, data_update=0,
                           mcs=0, data_length=0)
        bits = ci.pack(self.LLID)
        assert len(bits) == 51

    def test_roundtrip(self):
        ci = ControlInfoB5(reserved=0x7F, msg_type=5, accessible=1,
                           queryable=1, directed_content=1,
                           undirected_content=1, data_update=1,
                           mcs=10, data_length=255)
        bits = ci.pack(self.LLID)
        ci2 = ControlInfoB5.unpack(bits, self.LLID)
        assert ci2 == ci

    def test_msg_type_values(self):
        for mt in range(6):
            ci = ControlInfoB5(reserved=0, msg_type=mt, accessible=0,
                               queryable=0, directed_content=0,
                               undirected_content=0, data_update=0,
                               mcs=0, data_length=0)
            bits = ci.pack(self.LLID)
            ci2 = ControlInfoB5.unpack(bits, self.LLID)
            assert ci2.msg_type == mt


# =========================================================================
# 交叉验证
# =========================================================================


class TestCrossValidation:
    """跨控制信息类型的验证。"""

    def test_a_group_info_bits_count(self):
        """验证 A 组各类型的信息比特数 (不含 LQI 和 CRC)。"""
        seed = 0
        # A1: 20 bits
        a1 = ControlInfoA1(0, 0, 0, 0).pack(seed)
        assert len(a1) == 32  # 20 + 12
        # A2: 20 bits
        a2 = ControlInfoA2(0, 0, 0, 0, 0, 0, 0, 0).pack(seed)
        assert len(a2) == 32
        # A3: 28 bits
        a3 = ControlInfoA3(0, 0, 0, 0, 0, 0, 0, 0).pack(seed)
        assert len(a3) == 40
        # A4: 28 bits
        a4 = ControlInfoA4(0, 0, 0, 0, 0, 0, 0, 0).pack(seed)
        assert len(a4) == 40
        # A5: 20 bits
        a5 = ControlInfoA5(0, 0, 0, 0, 0, 0, 0, 0).pack(seed)
        assert len(a5) == 32
        # A6: 28 bits
        a6 = ControlInfoA6(0, 0, 0, 0, 0, 0, 0).pack(seed)
        assert len(a6) == 40
        # A7: 28 bits
        a7 = ControlInfoA7(0, 0, 0, 0).pack(seed)
        assert len(a7) == 40

    def test_b_group_all_51_bits(self):
        """验证 B 组所有类型均为 51 比特。"""
        llid = 0
        assert len(ControlInfoB1(0, 0, 0, 0, 0, 0, 0).pack(llid)) == 51
        assert len(ControlInfoB2(0, 0, 0).pack(llid)) == 51
        assert len(ControlInfoB3(0, 0, 0, 0, 0, 0).pack(llid)) == 51
        assert len(ControlInfoB4(0, 0, 0, 0, 0, 0, 0).pack(llid)) == 51
        assert len(ControlInfoB5(0, 0, 0, 0, 0, 0, 0, 0, 0).pack(llid)) == 51

    def test_a_group_with_lqi_adds_8_bits(self):
        """验证帧类型 2 (有 LQI) 比帧类型 1 多 8 位。"""
        seed = 0xABC
        ci = ControlInfoA1(1, 2, 0, 50)
        no_lqi = ci.pack(seed)
        with_lqi = ci.pack(seed, lqi=0x55)
        assert len(with_lqi) - len(no_lqi) == 8
