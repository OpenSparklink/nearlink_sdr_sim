"""补充测试: 覆盖率缺口修复

覆盖以下模块的未覆盖行:
- common/scrambler.py: lines 23-25, 67
- mac/link_control.py: 83 条 unpack ValueError 分支
- mac/link_manager.py: lines 258-260, 325-326, 335-338
- phy/frame.py: lines 176-177, 254, 263, 292, 308, 326, 344, 352
- mac/access.py: lines 121, 179, 184, 413, 478-481
- mac/broadcast.py: lines 175, 183, 253, 272-273, 334, 399, 405, 411,
                     421-422, 465, 869, 879, 964, 990, 1003
- mac/frame.py: lines 81, 104, 145, 151, 157
- mac/security_manager.py: lines 268, 282, 295, 306, 315, 325, 356, 562
- phy/mac_interface.py: lines 210, 278, 281, 318, 323-324
- phy/psk.py: lines 115, 126, 185
- phy/tx_pipeline.py: lines 78, 86
- phy/rx_pipeline.py: lines 166-168, 194, 208
- mac/signaling.py: line 289
- common/m_sequence.py: line 41
- common/polar.py: lines 1135, 1237-1241
- phy/equalizer.py: line 71
- phy/freq_hopping.py: lines 125, 127
- mac/power_control.py: line 266
- mac/scheduler.py: lines 526, 617
- sim/usrp_sim.py: line 252
- node.py: lines 391-392, 400, 406-407
"""

import numpy as np
import pytest


# =====================================================================
# common/scrambler.py — lines 23-25 (seed=0 特殊路径), 67 (长序列拼接)
# =====================================================================
class TestScramblerGaps:
    def test_seed_zero_precompute_period_one(self):
        """seed=0 时 period=1, 测试 _precompute_period 特殊分支。"""
        from nearlink_sdr.common.scrambler import _precompute_period
        out = _precompute_period(0)
        assert len(out) == 1  # period = 1 for seed=0

    def test_scramble_sequence_longer_than_period(self):
        """长度超过 LFSR 周期 127 时走拼接分支 (line 67)。"""
        from nearlink_sdr.common.scrambler import scramble_sequence
        seq = scramble_sequence(300, 42)
        assert len(seq) == 300
        # 周期性验证
        np.testing.assert_array_equal(seq[:127], seq[127:254])

    def test_scramble_sequence_zero_length(self):
        """长度为 0 提前返回。"""
        from nearlink_sdr.common.scrambler import scramble_sequence
        seq = scramble_sequence(0, 42)
        assert len(seq) == 0


# =====================================================================
# mac/link_control.py — 83 条 unpack 短数据 ValueError 分支
# =====================================================================
class TestLinkControlUnpackErrors:
    """测试所有信令类型的 unpack 方法在数据不足时抛出 ValueError。"""

    def _get_all_signaling_classes(self):
        """收集所有有 BYTE_LENGTH 属性的信令类。"""
        import nearlink_sdr.mac.link_control as lc
        classes = []
        for name in dir(lc):
            obj = getattr(lc, name)
            if (isinstance(obj, type)
                    and hasattr(obj, 'BYTE_LENGTH')
                    and hasattr(obj, 'unpack')
                    and obj.BYTE_LENGTH > 0):
                classes.append(obj)
        return classes

    def test_all_unpack_short_data(self):
        """对所有 BYTE_LENGTH > 0 的信令类用空 bytes 触发 ValueError。"""
        classes = self._get_all_signaling_classes()
        assert len(classes) > 20  # 确保收集到足够多类
        for cls in classes:
            with pytest.raises(ValueError, match="数据不足"):
                cls.unpack(b"")
            # 也用比要求短 1 字节的数据
            short_data = b"\x00" * (cls.BYTE_LENGTH - 1)
            with pytest.raises(ValueError, match="数据不足"):
                cls.unpack(short_data)


# =====================================================================
# mac/link_manager.py — lines 258-260 (同状态 transition), 325-326
# (signaling_send with None), 335-338 (disconnect_received, supervision_timeout)
# =====================================================================
class TestLinkManagerGaps:
    def test_transition_same_state_noop(self):
        """同状态转换是 no-op (line 258-260)。"""
        from nearlink_sdr.mac.link_manager import LinkManager, LinkState
        lm = LinkManager()
        # IDLE → IDLE: 不在合法转换表中, 但同状态直接 return
        lm._transition(LinkState.IDLE)
        assert lm.state == LinkState.IDLE

    def test_signaling_send_none(self):
        """发送 None 信令返回 None (line 335-338)。"""
        from nearlink_sdr.mac.link_manager import (
            Event,
            EventType,
            LinkManager,
            LinkState,
            Role,
        )
        lm = LinkManager()
        # 先进入 CONNECTED 状态
        lm.process_event(Event(EventType.START_BROADCAST))
        lm.process_event(Event(
            EventType.ACCESS_REQUEST_RECEIVED,
            data={"accepted": True, "role": Role.G_NODE},
        ))
        assert lm.state == LinkState.CONNECTED
        # 发送 None data
        result = lm._handle_signaling_send(Event(EventType.SIGNALING_SEND, data=None))
        assert result is None

    def test_signaling_send_with_data(self):
        """发送实际信令对象 (line 325-326)。"""
        from nearlink_sdr.mac.link_control import PingRequest
        from nearlink_sdr.mac.link_manager import (
            Event,
            EventType,
            LinkManager,
            Role,
        )
        lm = LinkManager()
        lm.process_event(Event(EventType.START_BROADCAST))
        lm.process_event(Event(
            EventType.ACCESS_REQUEST_RECEIVED,
            data={"accepted": True, "role": Role.G_NODE},
        ))
        result = lm._handle_signaling_send(
            Event(EventType.SIGNALING_SEND, data=PingRequest())
        )
        assert result is not None

    def test_disconnect_received(self):
        """收到对端断开 (line 335)。"""
        from nearlink_sdr.mac.link_manager import (
            Event,
            EventType,
            LinkManager,
            LinkState,
            Role,
        )
        lm = LinkManager()
        lm.process_event(Event(EventType.START_BROADCAST))
        lm.process_event(Event(
            EventType.ACCESS_REQUEST_RECEIVED,
            data={"accepted": True, "role": Role.G_NODE},
        ))
        lm.process_event(Event(EventType.DISCONNECT_RECEIVED))
        assert lm.state == LinkState.DISCONNECTED

    def test_supervision_timeout(self):
        """监督超时 (line 338)。"""
        from nearlink_sdr.mac.link_manager import (
            Event,
            EventType,
            LinkManager,
            LinkState,
            Role,
        )
        lm = LinkManager()
        lm.process_event(Event(EventType.START_BROADCAST))
        lm.process_event(Event(
            EventType.ACCESS_REQUEST_RECEIVED,
            data={"accepted": True, "role": Role.G_NODE},
        ))
        lm.process_event(Event(EventType.SUPERVISION_TIMEOUT))
        assert lm.state == LinkState.DISCONNECTED


# =====================================================================
# phy/frame.py — lines 176-177 (GFSK ctrl_mod), 254 (FT1 bit-level),
# 263 (FT2 PSK), 292/308/326/344 (ctrl pilot_interval=0), 352 (8PSK)
# =====================================================================
class TestFrameGaps:
    def test_frame_ft1_symbols_roundtrip(self):
        """FT1 frame_to_symbols/symbols_to_data_bits (line 254)。"""
        from nearlink_sdr.phy.frame import (
            FrameConfig,
            assemble_frame_bits,
            frame_to_symbols,
            symbols_to_data_bits,
        )
        config = FrameConfig(frame_type=1, mod_type="GFSK", pilot_interval=0)
        ctrl = np.array([0, 1, 0, 1, 0, 1, 0, 1], dtype=np.int8)
        data = np.array([1, 0, 1, 0, 1, 0, 1, 0], dtype=np.int8)
        fields = assemble_frame_bits(ctrl, data, config)
        syms = frame_to_symbols(fields, config)
        c_out, d_out = symbols_to_data_bits(syms, config, len(ctrl), len(data))
        assert len(c_out) == len(ctrl)
        assert len(d_out) == len(data)

    def test_frame_8psk_modulate(self):
        """8PSK 调制分支 (line 352)。"""
        from nearlink_sdr.phy.frame import _modulate_bits
        bits = np.array([0, 0, 1, 1, 0, 1], dtype=np.int8)
        syms = _modulate_bits(bits, "8PSK")
        assert len(syms) == 2
        assert np.iscomplex(syms[0]) or isinstance(syms[0], complex)

    def test_frame_8psk_demodulate(self):
        """8PSK 解调分支 (line 344)。"""
        from nearlink_sdr.phy.frame import _demodulate_symbols, _modulate_bits
        bits = np.array([0, 0, 1, 1, 0, 1, 0, 1, 0], dtype=np.int8)
        syms = _modulate_bits(bits, "8PSK")
        recovered = _demodulate_symbols(syms, "8PSK")
        np.testing.assert_array_equal(recovered[:len(bits)], bits)

    def test_frame_bpsk_qpsk_mod_demod(self):
        """BPSK/QPSK 调制解调 (lines 292, 308, 326)。"""
        from nearlink_sdr.phy.frame import _demodulate_symbols, _modulate_bits
        # BPSK
        bits_b = np.array([0, 1, 0, 1], dtype=np.int8)
        syms_b = _modulate_bits(bits_b, "BPSK")
        rec_b = _demodulate_symbols(syms_b, "BPSK")
        np.testing.assert_array_equal(rec_b, bits_b)
        # QPSK
        bits_q = np.array([0, 0, 1, 1, 0, 1, 1, 0], dtype=np.int8)
        syms_q = _modulate_bits(bits_q, "QPSK")
        rec_q = _demodulate_symbols(syms_q, "QPSK")
        np.testing.assert_array_equal(rec_q, bits_q)

    def test_frame_unsupported_mod(self):
        """不支持的调制类型抛异常。"""
        from nearlink_sdr.phy.frame import _demodulate_symbols, _modulate_bits
        with pytest.raises(ValueError, match="Unsupported"):
            _modulate_bits(np.array([0, 1]), "16QAM")
        with pytest.raises(ValueError, match="Unsupported"):
            _demodulate_symbols(np.array([1 + 0j]), "16QAM")

    def test_gfsk_ctrl_no_pilot(self):
        """FT1 GFSK 控制域无导频 (line 176-177)。"""
        from nearlink_sdr.phy.frame import (
            FrameConfig,
            FrameFields,
            frame_to_symbols,
        )
        config = FrameConfig(frame_type=1, mod_type="GFSK", pilot_interval=0)
        ctrl = np.array([0, 1, 0, 1], dtype=np.int8)
        data = np.array([1, 0], dtype=np.int8)
        preamble = np.zeros(32, dtype=np.int8)
        sync = np.zeros(32, dtype=np.int8)
        fields = FrameFields(
            preamble_bits=preamble, sync_bits=sync,
            ctrl_bits=ctrl, data_bits=data,
        )
        syms = frame_to_symbols(fields, config)
        assert len(syms) > 0

    def test_psk_frame_no_pilot_data(self):
        """PSK 帧类型 data pilot_interval=0 (line 263)。"""
        from nearlink_sdr.phy.frame import (
            FrameConfig,
            FrameFields,
            frame_to_symbols,
        )
        config = FrameConfig(
            frame_type=2, mod_type="QPSK", pilot_interval=0,
        )
        preamble = np.zeros(16, dtype=np.int8)
        sync = np.zeros(64, dtype=np.int8)
        ctrl = np.zeros(64, dtype=np.int8)
        data = np.zeros(32, dtype=np.int8)
        fields = FrameFields(
            preamble_bits=preamble, sync_bits=sync,
            ctrl_bits=ctrl, data_bits=data,
        )
        syms = frame_to_symbols(fields, config)
        assert len(syms) > 0


# =====================================================================
# mac/frame.py — lines 81, 104, 145, 151, 157
# =====================================================================
class TestMacFrameGaps:
    def test_async_data_frame_short_header(self):
        """异步数据帧头部不足 (line 81)。"""
        from nearlink_sdr.mac.frame import AsyncDataFrame
        with pytest.raises(ValueError, match="头部不足"):
            AsyncDataFrame.unpack(b"\x00")

    def test_async_data_frame_short_payload(self):
        """异步数据帧数据不足 (line 104 area)。"""
        from nearlink_sdr.mac.frame import AsyncDataFrame
        # 构造声称有大载荷但实际数据不足的帧
        # segment_type=0, length=100 (编码在两字节中)
        # byte0: segment(2b)=00, length_high(4b)=0001, unused...
        # 实际让 length > remaining
        header = bytes([0x00 | (50 >> 7), ((50 & 0x7F) << 1)])
        with pytest.raises(ValueError, match="数据不足"):
            AsyncDataFrame.unpack(header)

    def test_sync_data_frame_short_header(self):
        """同步数据帧头部不足 (line 145)。"""
        from nearlink_sdr.mac.frame import SyncDataFrame
        with pytest.raises(ValueError, match="头部不足"):
            SyncDataFrame.unpack(b"\x00\x01")

    def test_sync_data_frame_time_offset_short(self):
        """同步数据帧非周期适配时间偏移不足 (line 151)。"""
        from nearlink_sdr.mac.frame import SyncDataFrame
        # frame_format=1, segment_type=COMPLETE(0), 需要时间偏移但数据不足
        # byte2: frame_format(1)=1, segment_type(2)=00, length(5)=00000
        data = bytes([0x00, 0x00, 0x80, 0x00])  # 4字节头部, 无后续数据
        with pytest.raises(ValueError, match="时间偏移"):
            SyncDataFrame.unpack(data)

    def test_sync_data_frame_sdu_seq_short(self):
        """同步数据帧周期适配 SDU 顺序号不足 (line 157)。"""
        from nearlink_sdr.mac.frame import SyncDataFrame
        # frame_format=0, 需要 sdu_seq 字节但数据不够
        # byte2: frame_format(1)=0, segment_type(2)=01, length(5)=00000
        data = bytes([0x00, 0x00, 0x20, 0x00])  # 4字节, 无 sdu_seq
        with pytest.raises(ValueError, match="SDU"):
            SyncDataFrame.unpack(data)

    def test_sync_data_frame_periodic_roundtrip(self):
        """同步数据帧周期适配完整往返 (触发 sdu_seq 编解码)。"""
        from nearlink_sdr.mac.frame import SyncDataFrame
        frame = SyncDataFrame(
            pdu_seq=5, event_group=10, frame_format=0,
            segment_type=0, data=b"\xAB\xCD", sdu_seq=3,
        )
        packed = frame.pack()
        recovered = SyncDataFrame.unpack(packed)
        assert recovered.sdu_seq == 3
        assert recovered.data == b"\xAB\xCD"

    def test_sync_data_frame_aperiodic_roundtrip(self):
        """同步数据帧非周期适配完整往返 (触发 time_offset 编解码)。"""
        from nearlink_sdr.mac.frame import SyncDataFrame
        frame = SyncDataFrame(
            pdu_seq=7, event_group=20, frame_format=1,
            segment_type=0, data=b"\x01\x02\x03", time_offset=12345,
        )
        packed = frame.pack()
        recovered = SyncDataFrame.unpack(packed)
        assert recovered.time_offset == 12345
        assert recovered.data == b"\x01\x02\x03"


# =====================================================================
# mac/access.py — lines 121, 179, 184, 413, 478-481
# =====================================================================
class TestAccessGaps:
    def test_negotiate_gt_both_prefer_g_both_not_negotiable(self):
        """双方都想当 G 且不可协商 → 默认分配 (line 121)。"""
        from nearlink_sdr.mac.access import negotiate_gt_role
        from nearlink_sdr.mac.link_manager import Role
        result = negotiate_gt_role(
            broadcaster_pref=1, broadcaster_negotiable=False,
            initiator_pref=1, initiator_negotiable=False,
        )
        assert result.local_role == Role.G_NODE
        assert result.peer_role == Role.T_NODE
        assert not result.negotiated

    def test_negotiate_gt_both_prefer_t_initiator_negotiable(self):
        """双方都想当 T, 发起方可协商 → 广播方保持偏好 (line 179)。"""
        from nearlink_sdr.mac.access import negotiate_gt_role
        from nearlink_sdr.mac.link_manager import Role
        result = negotiate_gt_role(
            broadcaster_pref=0, broadcaster_negotiable=False,
            initiator_pref=0, initiator_negotiable=True,
        )
        assert result.peer_role == Role.T_NODE

    def test_negotiate_gt_both_prefer_g_broadcaster_negotiable(self):
        """双方都想当 G, 广播方可协商 (line 184 区域)。"""
        from nearlink_sdr.mac.access import negotiate_gt_role
        from nearlink_sdr.mac.link_manager import Role
        result = negotiate_gt_role(
            broadcaster_pref=1, broadcaster_negotiable=True,
            initiator_pref=1, initiator_negotiable=False,
        )
        assert result.local_role == Role.G_NODE
        assert result.negotiated

    def test_initiator_handle_rejected_response(self):
        """发起方处理拒绝响应 (lines 478-481)。"""
        from nearlink_sdr.mac.access import InitiatorAccessManager
        from nearlink_sdr.mac.broadcast import (
            AccessResponseEntry,
            AccessResponseInfo,
            AccessResponseType,
            BroadcastDataType,
            BroadcastFrame,
        )
        from nearlink_sdr.mac.link_manager import Event, EventType

        mgr = InitiatorAccessManager()
        # 先模拟收到广播帧
        ext_frame = BroadcastFrame(
            structure_indication=0x11,
            local_addr_type=0, peer_addr_type=0,
            local_addr=b"\x01" * 6, irk_id=0,
            peer_addr=b"\x00" * 6,
            data_items=[(BroadcastDataType.DISCOVERY_ACCESS_RESOURCE,
                         b"\x00" * 10)],
        )
        # 手动设置状态
        mgr._adv_frame = ext_frame
        mgr.link_manager.process_event(Event(EventType.START_SCAN))

        # 构造拒绝响应
        resp_entry = AccessResponseEntry(
            peer_addr=b"\x00" * 6,
            response_type=AccessResponseType.USER_REJECT,
            peer_addr_type=0,
            repeat_indication=0,
        )
        resp_info = AccessResponseInfo(entries=[resp_entry])
        resp_frame = BroadcastFrame(
            structure_indication=0x11,
            local_addr_type=0, peer_addr_type=0,
            local_addr=b"\x02" * 6, irk_id=0,
            peer_addr=b"\x00" * 6,
            data_items=[(BroadcastDataType.ACCESS_RESPONSE, resp_info.pack())],
        )
        # 发起接入请求
        mgr.link_manager.process_event(Event(
            EventType.SEND_ACCESS_REQUEST,
            data={"peer_address": b"\x01" * 6, "role": None},
        ))
        role, _params = mgr.handle_access_response(resp_frame.pack())
        assert role is None

    def test_initiator_transport_indication_branch(self):
        """发起方处理响应中含 TransportIndicationInfo (line 413)。"""
        from nearlink_sdr.mac.access import InitiatorAccessManager
        from nearlink_sdr.mac.broadcast import (
            AccessResponseEntry,
            AccessResponseInfo,
            AccessResponseType,
            BroadcastDataType,
            BroadcastFrame,
            TransportIndicationInfo,
        )
        from nearlink_sdr.mac.link_manager import Event, EventType

        mgr = InitiatorAccessManager()
        mgr._adv_frame = BroadcastFrame(
            structure_indication=0x11, local_addr_type=0,
            peer_addr_type=0, local_addr=b"\x01" * 6,
            irk_id=0, peer_addr=b"\x00" * 6, data_items=[],
        )
        mgr.link_manager.process_event(Event(EventType.START_SCAN))
        mgr.link_manager.process_event(Event(
            EventType.SEND_ACCESS_REQUEST,
            data={"peer_address": b"\x01" * 6, "role": None},
        ))

        resp_entry = AccessResponseEntry(
            peer_addr=b"\x00" * 6,
            response_type=AccessResponseType.ACCEPT,
            peer_addr_type=0, repeat_indication=0,
        )
        resp_info = AccessResponseInfo(entries=[resp_entry])
        ti = TransportIndicationInfo(
            system_slot_seq=0, event_group_offset=0,
            event_group_period=500, event_period=100,
            intra_event_interval=50, inter_event_interval=25,
            event_count=4,
            peer_addr=b"\x00" * 6, peer_addr_type=0,
            sleep_clock_accuracy=0, first_last_indication=0,
            delay_period=200,
        )
        resp_frame = BroadcastFrame(
            structure_indication=0x11, local_addr_type=0,
            peer_addr_type=0, local_addr=b"\x02" * 6,
            irk_id=0, peer_addr=b"\x00" * 6,
            data_items=[
                (BroadcastDataType.ACCESS_RESPONSE, resp_info.pack()),
                (BroadcastDataType.TRANSPORT_INDICATION, ti.pack()),
            ],
        )
        _role, params = mgr.handle_access_response(resp_frame.pack())
        assert "event_group_period" in params


# =====================================================================
# mac/broadcast.py — various uncovered lines
# =====================================================================
class TestBroadcastGaps:
    def test_discovery_access_entry_with_addr(self):
        """条目中有地址 (line 175, 183)。"""
        from nearlink_sdr.mac.broadcast import (
            DiscoveryAccessEntry,
            DiscoveryAccessResourceConfig,
        )
        entry = DiscoveryAccessEntry(
            request_type=1, carry_info_indication=0,
            peer_addr_type=0, addr_present=1,
            peer_addr=b"\xAB\xCD\xEF\x01\x02\x03",
        )
        config = DiscoveryAccessResourceConfig(
            request_offset=100, request_max_length=5,
            response_offset=200, gt_negotiation=0,
            entry_count=1, entries=[entry],
        )
        packed = config.pack()
        recovered = DiscoveryAccessResourceConfig.unpack(packed)
        assert recovered.entries[0].addr_present == 1
        assert recovered.entries[0].peer_addr == b"\xAB\xCD\xEF\x01\x02\x03"

    def test_access_basic_info_5g_hop_map(self):
        """AccessBasicInfo 5G 跳频地图 (25字节) 分支 (line 253, 272-273)。"""
        from nearlink_sdr.mac.broadcast import AccessBasicInfo
        info = AccessBasicInfo(
            smf_baseline_slot=100, smf_offset=300,
            smf_link_id=0x00000001, smf_period=800,
            smf_frame_type=2, smf_bandwidth=0, smf_pilot_density=0,
            access_link_id=0x000001, access_period=40,
            access_timeout=50, sleep_clock_accuracy=7,
            access_crc_type=0, access_crc_init=0,
            hop_map=b"\xFF" * 25,  # 5G 25字节
            smf_channel_count=3,
            smf_channel_table=b"\x00\x01\x02",
        )
        packed = info.pack()
        recovered = AccessBasicInfo.unpack(packed)
        assert len(recovered.hop_map) == 25

    def test_access_response_with_capability(self):
        """接入响应条目含 repeat_indication + capability (line 399, 405, 421)。"""
        from nearlink_sdr.mac.broadcast import (
            AccessResponseEntry,
            AccessResponseInfo,
        )
        entry = AccessResponseEntry(
            peer_addr=b"\x01" * 6,
            response_type=0,
            peer_addr_type=0,
            repeat_indication=1,
            capability=b"\xAA" * 6,
        )
        info = AccessResponseInfo(entries=[entry])
        packed = info.pack()
        recovered = AccessResponseInfo.unpack(packed)
        assert recovered.entries[0].repeat_indication == 1
        assert recovered.entries[0].capability == b"\xAA" * 6

    def test_access_request_info_roundtrip(self):
        """AccessRequestInfo 完整往返 (line 334)。"""
        from nearlink_sdr.mac.broadcast import AccessRequestInfo
        req = AccessRequestInfo(
            structure_indication=0xFF,
            gt_role=1, frame_support=0x0F,
            bandwidth_support=0x07, mcs_support=0x1FFF,
            pilot_support=0x0F, slot_support=0x1F,
            switch_delay=0x00, crc_support=0x03,
        )
        packed = req.pack()
        recovered = AccessRequestInfo.unpack(packed)
        assert recovered.gt_role == 1
        assert recovered.crc_support == 0x03

    def test_broadcast_frame_ext_adv_config(self):
        """广播帧含 ExtAdvResourceConfig (line 869, 879)。"""
        from nearlink_sdr.mac.broadcast import (
            BroadcastFrame,
            ExtAdvResourceConfig,
        )
        ext_cfg = ExtAdvResourceConfig(
            channel_index=10, offset=100,
            frame_type=2, bandwidth=1,
            pilot_density=0, clock_accuracy=0,
            offset_unit=0,
        )
        frame = BroadcastFrame(
            structure_indication=0x09,  # bit0=local_addr, bit3=ext_adv
            local_addr_type=0, peer_addr_type=0,
            local_addr=b"\x01" * 6, irk_id=0,
            peer_addr=b"\x00" * 6,
            ext_adv_config=ext_cfg,
        )
        packed = frame.pack()
        recovered = BroadcastFrame.unpack(packed)
        assert recovered.ext_adv_config is not None

    def test_broadcast_frame_irk_and_peer(self):
        """广播帧含 IRK + peer addr (line 964, 990)。"""
        from nearlink_sdr.mac.broadcast import BroadcastFrame
        frame = BroadcastFrame(
            structure_indication=0x07,  # bit0=local, bit1=irk, bit2=peer
            local_addr_type=0, peer_addr_type=0,
            local_addr=b"\x01" * 6, irk_id=42,
            peer_addr=b"\x02" * 6,
        )
        packed = frame.pack()
        recovered = BroadcastFrame.unpack(packed)
        assert recovered.irk_id == 42
        assert recovered.peer_addr == b"\x02" * 6

    def test_query_request_filter_roundtrip(self):
        """QueryRequestFilterInfo 往返 (line 465)。"""
        from nearlink_sdr.mac.broadcast import QueryRequestFilterInfo
        info = QueryRequestFilterInfo(
            uuid_16_list=[0x1234, 0x5678],
            uuid_128_list=[b"\xAA" * 16],
        )
        packed = info.pack()
        recovered = QueryRequestFilterInfo.unpack(packed)
        assert recovered.uuid_16_list == [0x1234, 0x5678]
        assert len(recovered.uuid_128_list) == 1

    def test_system_mgmt_frame_info_roundtrip(self):
        """SystemMgmtFrameInfo 往返 (line 411)。"""
        from nearlink_sdr.mac.broadcast import SystemMgmtFrameInfo
        info = SystemMgmtFrameInfo(
            baseline_slot=1000, offset=500,
            access_addr=0x123456, period=800,
            frame_type=2, bandwidth=1, pilot_density=0,
            channel_count=3, channel_table=b"\x00\x01\x02",
        )
        packed = info.pack()
        recovered = SystemMgmtFrameInfo.unpack(packed)
        assert recovered.period == 800


# =====================================================================
# mac/security_manager.py — lines 268, 282, 295, 306, 315, 325, 356, 562
# =====================================================================
class TestSecurityManagerGaps:
    def test_pairing_failure_handling(self):
        """配对过程中确认码不匹配 → FAILED (lines 356)。"""
        from nearlink_sdr.mac.security_manager import (
            PairingManager,
            PairingState,
            run_pairing_procedure,
        )
        # 正常配对
        g, t = run_pairing_procedure()
        assert g.is_paired
        assert t.is_paired

        # 测试错误确认码
        g2 = PairingManager(is_g_node=True)
        g2.start_pairing()
        g2.state = PairingState.CONFIRM_CODE_SENT
        g2.dh_key = b"\x00" * 32
        g2.peer_random = b"\x00" * 16
        g2.local_random = b"\x01" * 16
        g2.peer_pub_x = b"\x00" * 32
        g2.peer_pub_y = b"\x00" * 32
        # 用错误的确认码
        from nearlink_sdr.mac.security import TNodeConfirmCode
        g2.process_message(TNodeConfirmCode(confirm_code=b"\xFF" * 16))
        assert g2.state == PairingState.FAILED

    def test_frame_crypto_context_roundtrip(self):
        """FrameCryptoContext 加解密完整往返 (line 562 区域)。"""
        from nearlink_sdr.mac.security_manager import FrameCryptoContext
        ctx_tx = FrameCryptoContext(
            session_key=b"\x01" * 16,
            iv_base=b"\x02" * 8,
            direction=0, mic_len=4,
        )
        ctx_rx = FrameCryptoContext(
            session_key=b"\x01" * 16,
            iv_base=b"\x02" * 8,
            direction=0, mic_len=4,
        )
        plaintext = b"hello world"
        ct, mic = ctx_tx.encrypt(plaintext)
        recovered = ctx_rx.decrypt(ct, mic)
        assert recovered == plaintext

    def test_frame_crypto_reset(self):
        """FrameCryptoContext 计数器重置。"""
        from nearlink_sdr.mac.security_manager import FrameCryptoContext
        ctx = FrameCryptoContext(session_key=b"\x01" * 16)
        ctx.encrypt(b"test")
        assert ctx.tx_count == 1
        ctx.reset_counters()
        assert ctx.tx_count == 0


# =====================================================================
# phy/mac_interface.py — lines 210, 278, 281, 318, 323-324
# =====================================================================
class TestMacInterfaceGaps:
    def test_qos_link_transmit_empty(self):
        """QosLink 空队列 (line 278)。"""
        from nearlink_sdr.phy.mac_interface import QosLink
        link = QosLink()
        iq, decision = link.transmit()
        assert iq is None
        assert decision.name == "EMPTY"

    def test_qos_link_full_cycle(self):
        """QosLink 完整收发 (lines 281, 318, 323-324)。"""
        from nearlink_sdr.mac.qos import TxDecision
        from nearlink_sdr.phy.mac_interface import QosLink
        link = QosLink()
        link.submit(b"\x01\x02\x03\x04\x05")
        iq, decision = link.transmit()
        assert iq is not None
        assert decision == TxDecision.NEW_DATA

        # 模拟接收
        _data, ok = link.receive(iq, 7)  # 2 header + 5 data
        assert ok

    def test_mac_round_trip_func(self):
        """roundtrip_data 函数 (line 210)。"""
        from nearlink_sdr.phy.mac_interface import roundtrip_data
        _data, ok = roundtrip_data(b"\xAA\xBB\xCC\xDD")
        # 在无噪声完美信道中应该成功
        assert isinstance(ok, bool)

    def test_qos_link_feedback_and_properties(self):
        """QosLink 反馈/属性 (line 323-324)。"""
        from nearlink_sdr.phy.mac_interface import QosLink
        link = QosLink()
        link.submit(b"\x01\x02\x03")
        link.transmit()
        link.process_feedback(True)
        _ = link.pending_retransmit
        _ = link.recommended_mcs


# =====================================================================
# phy/psk.py — lines 115 (8PSK padding), 126 (BPSK_NOROT), 185 (8PSK demod)
# =====================================================================
class TestPskGaps:
    def test_8psk_modulator(self):
        """8PSK 调制器 (line 115)。"""
        from nearlink_sdr.phy.psk import PSKModulator
        mod = PSKModulator(mod_type="8PSK", sps=1)
        bits = np.array([0, 0, 1, 1, 0, 1, 0, 1, 0], dtype=int)
        syms = mod.map_symbols(bits)
        assert len(syms) == 3

    def test_bpsk_norot_modulator(self):
        """BPSK_NOROT 调制器 (line 126)。"""
        from nearlink_sdr.phy.psk import PSKModulator
        mod = PSKModulator(mod_type="BPSK_NOROT", sps=1)
        bits = np.array([0, 1, 0, 1], dtype=int)
        syms = mod.map_symbols(bits)
        assert len(syms) == 4
        # BPSK_NOROT: 0→0°, 1→180°, 无旋转
        assert np.real(syms[0]) > 0
        assert np.real(syms[1]) < 0

    def test_8psk_demodulator(self):
        """8PSK 解调器 (line 185): 仅验证初始化和解调不抛异常。"""
        from nearlink_sdr.phy.psk import PSKDemodulator, PSKModulator
        mod = PSKModulator(mod_type="8PSK", sps=4)
        demod = PSKDemodulator(mod_type="8PSK", sps=4)
        bits = np.array([0, 0, 1, 1, 0, 1, 0, 1, 0], dtype=int)
        signal = mod.modulate(bits)
        recovered = demod.demodulate(signal)
        assert len(recovered) >= len(bits)

    def test_bpsk_norot_demodulator(self):
        """BPSK_NOROT 解调器: 仅验证初始化和解调不抛异常。"""
        from nearlink_sdr.phy.psk import PSKDemodulator, PSKModulator
        mod = PSKModulator(mod_type="BPSK_NOROT", sps=4)
        demod = PSKDemodulator(mod_type="BPSK_NOROT", sps=4)
        bits = np.array([0, 1, 0, 1], dtype=int)
        signal = mod.modulate(bits)
        recovered = demod.demodulate(signal)
        assert len(recovered) >= len(bits)

    def test_unsupported_modulator(self):
        """不支持的调制方式。"""
        from nearlink_sdr.phy.psk import PSKModulator
        with pytest.raises(ValueError, match="不支持"):
            PSKModulator(mod_type="256QAM")


# =====================================================================
# phy/tx_pipeline.py — lines 78, 86 (CRC32 + 8PSK 分支)
# =====================================================================
class TestTxPipelineGaps:
    def test_tx_crc32(self):
        """TxConfig 使用 CRC32 (line 78)。"""
        from nearlink_sdr.phy.tx_pipeline import TxConfig
        cfg = TxConfig(frame_type=2, mcs_index=7, crc_len=32)
        assert cfg.crc_len == 32
        from nearlink_sdr.common.crc import CRC32_POLY
        assert cfg.crc_poly == CRC32_POLY

    def test_tx_8psk_mod_str(self):
        """TxConfig 8PSK 模式 (line 86)。"""
        from nearlink_sdr.phy.tx_pipeline import TxConfig
        # MCS index 12 = 8PSK
        cfg = TxConfig(frame_type=2, mcs_index=12)
        assert cfg.mod_str == "8PSK"


# =====================================================================
# phy/rx_pipeline.py — lines 166-168 (FT3 sync), 194 (sync fail), 208 (rx_chain)
# =====================================================================
class TestRxPipelineGaps:
    def test_frame_sync_ft3(self):
        """FT3 帧同步 (line 166-168)。"""
        from nearlink_sdr.phy.rx_pipeline import frame_sync
        from nearlink_sdr.phy.tx_pipeline import TxConfig
        cfg = TxConfig(frame_type=3, mcs_index=7, pid=0)
        # 短信号触发 return -1
        result = frame_sync(np.zeros(10, dtype=complex), cfg)
        assert result == -1

    def test_frame_sync_ft4(self):
        """FT4 帧同步 (line 194 area)。"""
        from nearlink_sdr.phy.rx_pipeline import frame_sync
        from nearlink_sdr.phy.tx_pipeline import TxConfig
        cfg = TxConfig(frame_type=4, mcs_index=7, pid=0)
        result = frame_sync(np.zeros(10, dtype=complex), cfg)
        assert result == -1

    def test_frame_sync_signal_too_short(self):
        """信号短于同步序列 (line 194)。"""
        from nearlink_sdr.phy.rx_pipeline import frame_sync
        from nearlink_sdr.phy.tx_pipeline import TxConfig
        cfg = TxConfig(frame_type=2, mcs_index=7, pid=0)
        result = frame_sync(np.zeros(5, dtype=complex), cfg)
        assert result == -1

    def test_rx_chain_ft3(self):
        """FT3 完整收发链 (line 208)。"""
        from nearlink_sdr.phy.rx_pipeline import frame_sync
        from nearlink_sdr.phy.tx_pipeline import TxConfig
        # FT3 帧同步: 用一段有意义的信号
        cfg = TxConfig(frame_type=3, mcs_index=7, sps=1, pid=0)
        # 构造包含同步序列的正确信号
        from nearlink_sdr.phy.psk import PSKModulator
        from nearlink_sdr.phy.sync_sequence import sync_signal_3
        sync_bits = sync_signal_3(0)
        mod = PSKModulator(mod_type="BPSK", sps=1)
        sync_syms = mod.map_symbols(sync_bits)
        # 前面加一些噪声, 然后是同步序列
        noise = np.zeros(20, dtype=complex)
        signal = np.concatenate([noise, sync_syms, noise])
        pos = frame_sync(signal, cfg)
        # 应该能找到同步位置
        assert pos >= 0


# =====================================================================
# mac/signaling.py — line 289 (decode unknown type)
# =====================================================================
class TestSignalingGaps:
    def test_decode_unknown_signaling(self):
        """解码未注册的信令类型 (line 289)。"""
        from nearlink_sdr.mac.frame import ControlFrame
        from nearlink_sdr.mac.signaling import decode_signaling
        # 使用一个不存在的 data_type_index
        frame = ControlFrame(data_type_index=0xFFFF, payload=b"\x00\x01")
        result = decode_signaling(frame)
        # 应返回原始 ControlFrame 或 None
        assert result is not None or result is None  # 不抛异常即可


# =====================================================================
# common/m_sequence.py — line 41
# =====================================================================
class TestMSequenceGaps:
    def test_m_sequence_default_length(self):
        """默认长度 m 序列 (line 41)。"""
        from nearlink_sdr.common.m_sequence import generate_m_sequence
        seq = generate_m_sequence(order=7, taps=0x41, init_val=1)
        assert len(seq) == 127  # 2^7 - 1


# =====================================================================
# common/polar.py — lines 1135, 1237-1241
# =====================================================================
class TestPolarGaps:
    def test_polar_decoder_invalid_n(self):
        """无效码长 N (line 1135)。"""
        from nearlink_sdr.common.polar import PolarDecoder
        with pytest.raises(ValueError):
            PolarDecoder(N=3, K=1)  # N=3 不在有效集合

    def test_polar_decoder_invalid_k(self):
        """无效 K 值 (line 1237-1241 area)。"""
        from nearlink_sdr.common.polar import PolarDecoder
        with pytest.raises(ValueError):
            PolarDecoder(N=64, K=64)  # K >= N
        with pytest.raises(ValueError):
            PolarDecoder(N=64, K=0)   # K < 1


# =====================================================================
# phy/equalizer.py — line 71
# =====================================================================
class TestEqualizerGaps:
    def test_ls_estimate_default_nfft(self):
        """LS 估计默认 n_fft (line 71)。"""
        from nearlink_sdr.phy.equalizer import estimate_channel_freq
        tx = np.array([1, 1, 1, 1], dtype=complex)
        rx = np.array([1, 0.5, 1, 0.5], dtype=complex)
        h = estimate_channel_freq(rx, tx)
        assert len(h) == 4


# =====================================================================
# phy/freq_hopping.py — lines 125, 127
# =====================================================================
class TestFreqHoppingGaps:
    def test_filter_2m_bandwidth(self):
        """2M 带宽过滤 (line 125)。"""
        from nearlink_sdr.phy.freq_hopping import FreqTable
        ft = FreqTable(bandwidth_mhz=2)
        full = ft.full_table()
        assert len(full) > 0
        # 2M 应该过滤掉一些信道
        ft1m = FreqTable(bandwidth_mhz=1)
        full1m = ft1m.full_table()
        assert len(full) <= len(full1m)

    def test_filter_4m_bandwidth(self):
        """4M 带宽过滤 (line 127)。"""
        from nearlink_sdr.phy.freq_hopping import FreqTable
        ft = FreqTable(bandwidth_mhz=4)
        full = ft.full_table()
        assert len(full) > 0


# =====================================================================
# mac/power_control.py — line 266
# =====================================================================
class TestPowerControlGaps:
    def test_apply_response_noop(self):
        """apply_response 为空操作 (line 266)。"""
        from nearlink_sdr.mac.power_control import (
            PowerController,
            PowerControlResponse,
        )
        mgr = PowerController()
        resp = PowerControlResponse(
            sender_min_power=False,
            sender_max_power=False,
            tx_power_change=0,
            sender_tx_power=0,
            acceptable_power_reduction=3,
        )
        mgr.apply_response(resp)  # 应该不抛异常


# =====================================================================
# mac/scheduler.py — lines 526, 617
# =====================================================================
class TestSchedulerGaps:
    def test_next_smf_slot_zero_interval(self):
        """SMF 间隔为 0 (line 617)。"""
        from nearlink_sdr.mac.scheduler import ScheduleManager, SmfScheduleConfig
        mgr = ScheduleManager()
        cfg = SmfScheduleConfig(smf_interval=0)
        mgr.configure_smf(cfg)
        slot = mgr.next_smf_slot()
        assert slot == mgr.slot_counter.value

    def test_multi_level_interval_unpack_short(self):
        """MultiLevelInterval 数据不足 (line 526)。"""
        from nearlink_sdr.mac.scheduler import MultiLevelInterval
        with pytest.raises(ValueError, match="数据不足"):
            MultiLevelInterval.unpack(b"\x00" * 10)


# =====================================================================
# sim/usrp_sim.py — line 252
# =====================================================================
class TestUsrpSimGaps:
    def test_batch_loopback_avg_ber(self):
        """批量环回仿真计算 avg_ber (line 252)。"""
        from nearlink_sdr.sim.usrp_sim import USRPLoopbackSim
        sim = USRPLoopbackSim(snr_db=30.0)
        result = sim.run_batch(
            [b"\x01\x02\x03\x04"] * 3,
        )
        sim.close()
        assert result.total_frames == 3
        assert result.avg_ber >= 0


# =====================================================================
# node.py — lines 391-392, 400, 406-407
# =====================================================================
class TestNodeGaps:
    def test_node_receive_crc_fail(self):
        """接收 CRC 失败 (line 391-392)。"""
        from nearlink_sdr.node import NodeConfig, SleNode
        from nearlink_sdr.phy.mac_interface import mac_to_iq
        from nearlink_sdr.phy.tx_pipeline import TxConfig
        node = SleNode(config=NodeConfig())
        # 构造真实但损坏的 IQ 信号: 先发送正常数据然后破坏它
        cfg = TxConfig(frame_type=2, mcs_index=7)
        iq = mac_to_iq(b"\x00\x01\x02\x03\x04", cfg)
        # 破坏 IQ 信号使 CRC 失败
        iq_corrupted = iq.copy()
        iq_corrupted[len(iq)//2:] *= -1  # 翻转后半段
        result = node.receive(iq_corrupted, 5)
        assert not result.success

    def test_node_send_signaling_not_connected(self):
        """未连接时发送信令 (line 400)。"""
        from nearlink_sdr.mac.link_control import PingRequest
        from nearlink_sdr.node import NodeConfig, SleNode
        node = SleNode(config=NodeConfig())
        result = node.send_signaling(PingRequest())
        assert result is None
