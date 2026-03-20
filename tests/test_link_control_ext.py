"""扩展链路控制信令测试 -- TXS-10002-2025 标准 7.3.2"""

import pytest

from nearlink_sdr.mac.link_control import (
    AsyncLinkParamRequest,
    AsyncLinkParamResponse,
    AsyncMulticastReconfig,
    AsyncUnicastUpdate,
    BroadcastHopMapUpdate,
    BroadcastLinkDisconnect,
    BroadcastLinkParamUpdate,
    BroadcastLinkSetup,
    ChannelStatusIndication,
    HopMapUpdate,
    HopTableUpdate,
    IsochronousLinkSetup,
    IsochronousParamExchangeRequest,
    IsochronousParamExchangeResponse,
    IsochronousParamUpdateIndication,
    IsochronousParamUpdateRequest,
    MinAvailableChannels,
    MulticastDisconnect,
    PhyUpdateIndication,
    PhyUpdateRequest,
    PingRequest,
    PingResponse,
    RoleSwitchRequest,
    SecurityPauseRequest,
    SecurityPauseResponse,
    SecurityRequest,
    SecurityResponse,
    SecurityStartRequest,
    SecurityStartResponse,
    SMFParamUpdateIndication,
    SMFParamUpdateRequest,
    SMFSignalingTerminate,
    SMFTimeSlotUpdateRequest,
    SMFTimeSlotUpdateResponse,
    TimeOffsetIndication,
    TimeoutUpdateRequest,
    UnknownFeatureFeedback,
)
from nearlink_sdr.mac.signaling import decode_signaling, encode_signaling


class TestSecuritySignaling:
    """安全信令 (7.3.2.6 - 7.3.2.11)"""

    def test_security_request(self):
        msg = SecurityRequest(g_node_iv=0xDEADBEEF, g_node_skd=0x123456789ABCDEF0,
                              enc_indication=0x01)
        data = msg.pack()
        assert len(data) == 13
        restored = SecurityRequest.unpack(data)
        assert restored.g_node_iv == 0xDEADBEEF
        assert restored.g_node_skd == 0x123456789ABCDEF0
        assert restored.enc_indication == 0x01

    def test_security_response(self):
        msg = SecurityResponse(t_node_iv=0xCAFEBABE, t_node_skd=0xFEDCBA9876543210)
        data = msg.pack()
        assert len(data) == 12
        restored = SecurityResponse.unpack(data)
        assert restored.t_node_iv == 0xCAFEBABE
        assert restored.t_node_skd == 0xFEDCBA9876543210

    def test_security_start_request(self):
        msg = SecurityStartRequest()
        assert msg.pack() == b""
        restored = SecurityStartRequest.unpack(b"")
        assert isinstance(restored, SecurityStartRequest)

    def test_security_start_response(self):
        msg = SecurityStartResponse(enc_indication=0x03)
        assert len(msg.pack()) == 1
        restored = SecurityStartResponse.unpack(msg.pack())
        assert restored.enc_indication == 0x03

    def test_security_pause_request(self):
        msg = SecurityPauseRequest()
        assert msg.pack() == b""
        assert isinstance(SecurityPauseRequest.unpack(b""), SecurityPauseRequest)

    def test_security_pause_response(self):
        msg = SecurityPauseResponse()
        assert msg.pack() == b""
        assert isinstance(SecurityPauseResponse.unpack(b""), SecurityPauseResponse)

    def test_security_request_registry(self):
        msg = SecurityRequest(g_node_iv=1, g_node_skd=2, enc_indication=0)
        frame = encode_signaling(msg)
        assert frame.data_type_index == 0x0004
        decoded = decode_signaling(frame)
        assert isinstance(decoded, SecurityRequest)


class TestUnknownFeatureFeedback:
    """未知特性反馈 (7.3.2.14)"""

    def test_roundtrip(self):
        msg = UnknownFeatureFeedback(unknown_type=0x00FF)
        data = msg.pack()
        assert len(data) == 2
        restored = UnknownFeatureFeedback.unpack(data)
        assert restored.unknown_type == 0x00FF

    def test_registry(self):
        msg = UnknownFeatureFeedback(unknown_type=0x1234)
        frame = encode_signaling(msg)
        assert frame.data_type_index == 0x000C


class TestChannelStatusIndication:
    """信道状态指示 (7.3.2.19)"""

    def test_roundtrip(self):
        ch_map = bytes(range(20))
        msg = ChannelStatusIndication(channel_map=ch_map)
        data = msg.pack()
        assert len(data) == 20
        restored = ChannelStatusIndication.unpack(data)
        assert restored.channel_map == ch_map


class TestHopTableUpdate:
    """跳频表更新指示 (7.3.2.20)"""

    def test_roundtrip(self):
        table = bytes([37, 38, 39, 40, 41])
        msg = HopTableUpdate(effective_slot=5000, channel_count=5,
                              channel_table=table)
        data = msg.pack()
        assert len(data) == 10
        restored = HopTableUpdate.unpack(data)
        assert restored.effective_slot == 5000
        assert restored.channel_count == 5
        assert restored.channel_table == table


class TestHopMapUpdate:
    """跳频地图更新指示 (7.3.2.21)"""

    def test_roundtrip(self):
        hop_map = bytes(10)
        msg = HopMapUpdate(hop_map=hop_map, effective_slot=12345)
        data = msg.pack()
        assert len(data) == 14
        restored = HopMapUpdate.unpack(data)
        assert restored.hop_map == hop_map
        assert restored.effective_slot == 12345


class TestMinAvailableChannels:
    """最少可用信道指示 (7.3.2.22)"""

    def test_roundtrip(self):
        msg = MinAvailableChannels(frame_type=2, bandwidth=1,
                                   pilot_density=0, min_channels=37)
        data = msg.pack()
        assert len(data) == 2
        restored = MinAvailableChannels.unpack(data)
        assert restored.frame_type == 2
        assert restored.bandwidth == 1
        assert restored.pilot_density == 0
        assert restored.min_channels == 37


class TestPhyUpdate:
    """物理层更新 (7.3.2.25 - 7.3.2.26)"""

    def test_request_roundtrip(self):
        msg = PhyUpdateRequest(
            tx_frame_type=2, rx_frame_type=3,
            tx_bandwidth=1, rx_bandwidth=2,
            tx_pilot_density=0, rx_pilot_density=1,
            tx_feedback_type=26, rx_feedback_type=7,
        )
        data = msg.pack()
        assert len(data) == 4
        restored = PhyUpdateRequest.unpack(data)
        assert restored.tx_frame_type == 2
        assert restored.rx_frame_type == 3
        assert restored.tx_bandwidth == 1
        assert restored.rx_bandwidth == 2
        assert restored.tx_pilot_density == 0
        assert restored.rx_pilot_density == 1
        assert restored.tx_feedback_type == 26
        assert restored.rx_feedback_type == 7

    def test_indication_roundtrip(self):
        msg = PhyUpdateIndication(
            tx_frame_type=1, rx_frame_type=2,
            tx_bandwidth=0, rx_bandwidth=1,
            tx_pilot_density=2, rx_pilot_density=3,
            tx_feedback_type=0, rx_feedback_type=6,
            effective_slot=999999,
        )
        data = msg.pack()
        assert len(data) == 8
        restored = PhyUpdateIndication.unpack(data)
        assert restored.tx_frame_type == 1
        assert restored.rx_frame_type == 2
        assert restored.effective_slot == 999999

    def test_request_registry(self):
        msg = PhyUpdateRequest(0, 0, 0, 0, 0, 0, 0, 0)
        frame = encode_signaling(msg)
        assert frame.data_type_index == 0x0017


class TestRoleSwitchRequest:
    """角色切换请求 (7.3.2.52)"""

    def test_roundtrip(self):
        msg = RoleSwitchRequest(effective_slot=0x12345678)
        data = msg.pack()
        assert len(data) == 4
        restored = RoleSwitchRequest.unpack(data)
        assert restored.effective_slot == 0x12345678


class TestTimeOffsetIndication:
    """时间偏移指示 (7.3.2.53)"""

    def test_roundtrip(self):
        msg = TimeOffsetIndication(time_offset=0xDEADBEEFCAFEBABE)
        data = msg.pack()
        assert len(data) == 8
        restored = TimeOffsetIndication.unpack(data)
        assert restored.time_offset == 0xDEADBEEFCAFEBABE


class TestPing:
    """PING (7.3.2.54 - 7.3.2.55)"""

    def test_ping_request(self):
        msg = PingRequest()
        assert msg.pack() == b""
        frame = encode_signaling(msg)
        assert frame.data_type_index == 0x0033

    def test_ping_response(self):
        msg = PingResponse()
        assert msg.pack() == b""
        frame = encode_signaling(msg)
        assert frame.data_type_index == 0x0034


class TestTimeoutUpdateRequest:
    """超时时间更新请求 (7.3.2.62)"""

    def test_roundtrip(self):
        msg = TimeoutUpdateRequest(timeout=3000)
        data = msg.pack()
        assert len(data) == 2
        restored = TimeoutUpdateRequest.unpack(data)
        assert restored.timeout == 3000


class TestBroadcastLinkDisconnect:
    """广播链路断开指示 (7.3.2.45)"""

    def test_roundtrip(self):
        msg = BroadcastLinkDisconnect(link_id=0xABCDEF, error_reason=7)
        data = msg.pack()
        assert len(data) == 5
        restored = BroadcastLinkDisconnect.unpack(data)
        assert restored.link_id == 0xABCDEF
        assert restored.error_reason == 7


class TestSMFSignalingTerminate:
    """系统管理帧信令传输终止 (7.3.2.51)"""

    def test_roundtrip(self):
        msg = SMFSignalingTerminate(terminate_type=2)
        data = msg.pack()
        assert len(data) == 1
        restored = SMFSignalingTerminate.unpack(data)
        assert restored.terminate_type == 2


class TestMulticastDisconnect:
    """组播链路断开指示 (7.3.2.63)"""

    def test_roundtrip(self):
        msg = MulticastDisconnect(link_id=0x123456)
        data = msg.pack()
        assert len(data) == 3
        restored = MulticastDisconnect.unpack(data)
        assert restored.link_id == 0x123456


class TestAsyncMulticastReconfig:
    """异步组播链路参数重配置指示 (7.3.2.33)"""

    def test_roundtrip(self):
        msg = AsyncMulticastReconfig(
            effective_ref_slot=100000, event_group_offset=500,
            event_group_period=1000, event_period=200,
            delay_period=10, timeout=300, intra_event_interval=50,
            inter_event_interval=100, event_count=5,
            payload_count=12345, scheduling_slot=4,
            tx_rx_indication=1, tx_max_pdu=512, rx_max_pdu=256,
            tx_max_time_offset=100, rx_max_time_offset=80,
        )
        data = msg.pack()
        assert len(data) == 30
        restored = AsyncMulticastReconfig.unpack(data)
        assert restored.effective_ref_slot == 100000
        assert restored.event_group_offset == 500
        assert restored.event_group_period == 1000
        assert restored.event_period == 200
        assert restored.event_count == 5
        assert restored.payload_count == 12345
        assert restored.scheduling_slot == 4
        assert restored.tx_rx_indication == 1
        assert restored.tx_max_pdu == 512
        assert restored.rx_max_pdu == 256
        assert restored.tx_max_time_offset == 100
        assert restored.rx_max_time_offset == 80


class TestAsyncUnicastUpdate:
    """链接态单播异步链路参数更新指示 (7.3.2.34)"""

    def test_pack_min_fields(self):
        msg = AsyncUnicastUpdate(
            effective_ref_slot=50000, event_group_offset=200,
            event_group_period=400, intra_event_interval=50,
            inter_event_interval=100, delay_period=5,
            scheduling_slot=4, tx_rx_indication=1,
        )
        data = msg.pack()
        assert len(data) == 15
        restored = AsyncUnicastUpdate.unpack(data)
        assert restored.effective_ref_slot == 50000
        assert restored.event_group_offset == 200
        assert restored.scheduling_slot == 4
        assert restored.tx_rx_indication == 1


# ====================================================================
# 0x0020-0x002E 链路控制信令往返测试
# ====================================================================

def _roundtrip(msg):
    """打包再解包, 验证字段一致。"""
    packed = msg.pack()
    assert len(packed) == msg.BYTE_LENGTH, f"长度不符: {len(packed)} != {msg.BYTE_LENGTH}"
    recovered = type(msg).unpack(packed)
    for attr in vars(msg):
        if attr.startswith("_"):
            continue
        orig = getattr(msg, attr)
        rec = getattr(recovered, attr)
        assert orig == rec, f"字段 {attr} 不一致: {orig!r} != {rec!r}"
    return recovered


class TestAsyncLinkParam:
    def test_request_roundtrip(self):
        msg = AsyncLinkParamRequest(
            event_group_period_min=100,
            event_group_period_max=500,
            delay_period=20,
            timeout=300,
            expected_period_unit=3,
            effective_ref_slot=0xABCD1234,
            offsets=(10, 20, 30, 40, 50, 60),
            time_slot_length=8,
            time_slot_count=4,
        )
        _roundtrip(msg)

    def test_response_roundtrip(self):
        msg = AsyncLinkParamResponse(
            event_group_period_min=0,
            event_group_period_max=0xFFFF,
            delay_period=0xFFFF,
            timeout=0,
            expected_period_unit=255,
            effective_ref_slot=0,
            offsets=(0, 0, 0, 0, 0, 0),
            time_slot_length=0,
            time_slot_count=0,
        )
        _roundtrip(msg)


class TestIsochronousLinkSetup:
    def test_roundtrip(self):
        msg = IsochronousLinkSetup(
            event_group_set_id=1, event_group_id=2,
            effective_slot=0x12345678,
            event_group_period=100, event_period=50,
            intra_event_interval=10, inter_event_interval=20,
            event_count=3, sync_anchor_delay=0x0A0B0C,
            sync_ref_delay=0x0D0E0F, scheduling_slot=5,
            tx_rx_indication=1, tx_adapt_mode=0, rx_adapt_mode=1,
            tx_link_id=0xAAAAAA, rx_link_id=0xBBBBBB,
            tx_frame_type=3, rx_frame_type=7,
            tx_bandwidth=2, rx_bandwidth=1,
            tx_pilot_density=3, rx_pilot_density=0,
            tx_sdu_max=1024, rx_sdu_max=512,
            tx_sdu_period=0x12345, rx_sdu_period=0xABCDE,
            tx_pdu_max=500, rx_pdu_max=300,
            tx_max_time_offset=100, rx_max_time_offset=200,
            tx_new_pkt_count=5, rx_new_pkt_count=3,
            tx_crc_init=0xDEADBEEF, rx_crc_init=0xCAFEBABE,
            tx_discard_period=10, rx_discard_period=20,
            tx_crc_type=1, rx_crc_type=0,
            tx_feedback_type=0x1F, rx_feedback_type=0x05,
        )
        _roundtrip(msg)

    def test_pack_length(self):
        msg = IsochronousLinkSetup(
            0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
            0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
            0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
            0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
        )
        assert len(msg.pack()) == 56


class TestIsochronousParamExchange:
    def test_request_roundtrip(self):
        msg = IsochronousParamExchangeRequest(
            event_group_set_id=5, event_group_id=10,
            event_group_period=200, event_period=100,
            intra_event_interval=30, inter_event_interval=50,
            event_count=4, sync_anchor_delay=0x010203,
            sync_ref_delay=0x040506, param_tag_id=0x0A,
            tx_rx_indication=1, tx_adapt_mode=1, rx_adapt_mode=0,
            tx_link_id=0x112233, rx_link_id=0x445566,
            tx_frame_type=2, rx_frame_type=5,
            tx_bandwidth=1, rx_bandwidth=3,
            tx_pilot_density=2, rx_pilot_density=1,
            tx_sdu_max=2048, rx_sdu_max=1024,
            tx_sdu_period=0x54321, rx_sdu_period=0xFEDCB,
            tx_pdu_max=700, rx_pdu_max=400,
            tx_max_time_offset=50, rx_max_time_offset=150,
            tx_new_pkt_count=8, rx_new_pkt_count=2,
            tx_crc_init=0x11223344, rx_crc_init=0x55667788,
            tx_discard_period=5, rx_discard_period=15,
            tx_crc_type=0, rx_crc_type=1,
            tx_feedback_type=0x3F, rx_feedback_type=0x07,
        )
        _roundtrip(msg)

    def test_response_inherits(self):
        msg = IsochronousParamExchangeResponse(
            0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
            0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
            0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
            0, 0, 0, 0, 0, 0, 0, 0, 0,
        )
        rec = _roundtrip(msg)
        assert isinstance(rec, IsochronousParamExchangeResponse)
        assert msg.DATA_TYPE_INDEX == 0x0024


class TestIsochronousParamUpdate:
    def test_request_roundtrip(self):
        msg = IsochronousParamUpdateRequest(0x0F, 0xAB, 0xCD)
        _roundtrip(msg)

    def test_indication_roundtrip(self):
        msg = IsochronousParamUpdateIndication(0x0A, 0x12, 0x34, 0xDEADBEEF, 0x1234)
        _roundtrip(msg)


class TestBroadcastLinkSetupNew:
    def test_roundtrip(self):
        msg = BroadcastLinkSetup(
            transmission_type=1, adapt_mode=0,
            event_group_set_id=3, event_group_count=5,
            event_group_id=2, effective_slot=0x87654321,
            event_group_interval=10, event_group_period=200,
            event_period=50, event_count=8,
            base_link_id=0xABCDEF, frame_type=7,
            bandwidth=2, pilot_density=1,
            sdu_max=0xFFF, sdu_period=0xFFFFF,
            pdu_max=0x7FF, new_pkt_count=0x0F,
            crc_type=1, crc_base_init=0xCAFEBABE,
            hop_map=bytes(range(10)),
            sync_anchor_delay=0x112233,
            sync_ref_delay=0x445566,
        )
        _roundtrip(msg)

    def test_pack_length(self):
        msg = BroadcastLinkSetup(
            0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
            0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
            b"\x00" * 10, 0, 0,
        )
        assert len(msg.pack()) == 44


class TestBroadcastLinkParamUpdateNew:
    def test_pack_length(self):
        msg = BroadcastLinkParamUpdate(
            1, 2, 3, 100, 50, 4, 5, 2, 1,
            1000, 7, 1, 50000, 800, 0, 0x12345678,
            0xAABBCC, 0xDDEEFF, 0x11223344, 0x5566,
        )
        assert len(msg.pack()) == 32


class TestBroadcastHopMapUpdateNew:
    def test_roundtrip(self):
        msg = BroadcastHopMapUpdate(b"\xFF" * 10, 0xABCDEF01)
        _roundtrip(msg)


class TestSMFParamUpdateNew:
    def test_request_roundtrip(self):
        msg = SMFParamUpdateRequest(1000, 50, 0x123456, 3, 1, 2, 1)
        _roundtrip(msg)

    def test_indication_roundtrip(self):
        msg = SMFParamUpdateIndication(2000, 100, 0xABCDEF, 7, 2, 3, 0, 0xDEADBEEF)
        _roundtrip(msg)


class TestSMFTimeSlotUpdateNew:
    def test_request_roundtrip(self):
        msg = SMFTimeSlotUpdateRequest(0x0A0B0C, 5000, (100, 200, 300, 400))
        _roundtrip(msg)

    def test_response_roundtrip(self):
        msg = SMFTimeSlotUpdateResponse(0xFEDCBA, 12345, 0xABCDEF01)
        _roundtrip(msg)


class TestDataTypeIndexNew:
    @pytest.mark.parametrize("cls,expected_idx", [
        (AsyncLinkParamRequest, 0x0020),
        (AsyncLinkParamResponse, 0x0021),
        (IsochronousLinkSetup, 0x0022),
        (IsochronousParamExchangeRequest, 0x0023),
        (IsochronousParamExchangeResponse, 0x0024),
        (IsochronousParamUpdateRequest, 0x0025),
        (IsochronousParamUpdateIndication, 0x0026),
        (BroadcastLinkSetup, 0x0027),
        (BroadcastLinkParamUpdate, 0x0028),
        (BroadcastHopMapUpdate, 0x0029),
        (SMFParamUpdateRequest, 0x002B),
        (SMFParamUpdateIndication, 0x002C),
        (SMFTimeSlotUpdateRequest, 0x002D),
        (SMFTimeSlotUpdateResponse, 0x002E),
    ])
    def test_data_type_index(self, cls, expected_idx):
        assert expected_idx == cls.DATA_TYPE_INDEX
