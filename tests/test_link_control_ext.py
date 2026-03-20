"""扩展链路控制信令测试 -- TXS-10002-2025 标准 7.3.2"""

import pytest

from nearlink_sdr.mac.link_control import (
    AsyncLinkParamRequest,
    AsyncLinkParamResponse,
    AsyncMulticastLinkSetup,
    AsyncMulticastParamExchangeRequest,
    AsyncMulticastParamExchangeResponse,
    AsyncMulticastParamUpdateIndication,
    AsyncMulticastParamUpdateRequest,
    AsyncMulticastReconfig,
    AsyncTTLinkSetup,
    AsyncUnicastUpdate,
    BroadcastHopMap5GUpdate,
    BroadcastHopMapUpdate,
    BroadcastLinkDisconnect,
    BroadcastLinkParamUpdate,
    BroadcastLinkSetup,
    Channel5GStatusIndication,
    ChannelStatusIndication,
    CoordinateConfig,
    CoordinateReport,
    CoordinateRequest,
    HopMap5GUpdate,
    HopMapUpdate,
    HopTableUpdate,
    IsochronousLinkSetup,
    IsochronousParamExchangeRequest,
    IsochronousParamExchangeResponse,
    IsochronousParamUpdateIndication,
    IsochronousParamUpdateRequest,
    MinAvailableChannels,
    MulticastDisconnect,
    MultiIntervalUpdateIndication,
    MultiIntervalUpdateRequest,
    MultiIntervalUpdateResponse,
    NarrowbandDelayRequest,
    NarrowbandDelayResponse,
    NarrowbandFreqTable24Update,
    NarrowbandFreqTable51Update,
    NarrowbandFreqTable58Update,
    NarrowbandMeasAction,
    NarrowbandMeasCapRequest,
    NarrowbandMeasCapResponse,
    NarrowbandMeasConfig,
    NarrowbandMeasConfigUpdateIndication,
    NarrowbandMeasConfigUpdateRequest,
    NarrowbandMeasReport,
    NarrowbandProxySensingFeedback,
    NarrowbandProxySensingRequest,
    NarrowbandSensingAction,
    NarrowbandSensingCapRequest,
    NarrowbandSensingCapResponse,
    NarrowbandSensingConfig,
    NarrowbandSensingConfigFeedback,
    NarrowbandSensingFeedback,
    NarrowbandSensingReport,
    NarrowbandSensingRequest,
    PhyUpdateIndication,
    PhyUpdateRequest,
    PingRequest,
    PingResponse,
    ResourceReservation,
    ResourceReservationTerminate,
    RoleSwitchRequest,
    SecurityPauseRequest,
    SecurityPauseResponse,
    SecurityRequest,
    SecurityResponse,
    SecurityStartRequest,
    SecurityStartResponse,
    SensingDeviceStatusReport,
    SMFParamUpdateIndication,
    SMFParamUpdateRequest,
    SMFSignalingTerminate,
    SMFTimeSlotUpdateRequest,
    SMFTimeSlotUpdateResponse,
    SystemTimeIndication,
    TimeOffsetIndication,
    TimeoutUpdateRequest,
    UnknownFeatureFeedback,
    UWBMeasAction,
    UWBMeasCapRequest,
    UWBMeasCapResponse,
    UWBMeasConfig,
    UWBMeasConfigFeedback,
    UWBMeasReport,
    UWBProxySensingFeedback,
    UWBProxySensingRequest,
    UWBSensingAction,
    UWBSensingCapRequest,
    UWBSensingCapResponse,
    UWBSensingConfig,
    UWBSensingConfigFeedback,
    UWBSensingProcessFeedback,
    UWBSensingProcessRequest,
    UWBSensingReport,
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


# ====================================================================
# 0x0035-0x0070 扩展链路控制信令往返测试
# ====================================================================

class TestChannel5GAndHopMap:
    """5GHz 信道状态 / 跳频地图 (0x0035, 0x0036, 0x003B)"""

    def test_channel_5g_status(self):
        ch = bytes(range(50))
        msg = Channel5GStatusIndication(channel_classification=ch)
        _roundtrip(msg)

    def test_hop_map_5g_update(self):
        hm = bytes(range(25))
        msg = HopMap5GUpdate(hop_map=hm, effective_slot=0xABCD1234)
        _roundtrip(msg)

    def test_broadcast_hop_map_5g_update(self):
        hm = bytes(range(25))
        msg = BroadcastHopMap5GUpdate(
            hop_map=hm, effective_slot=0x12345678,
        )
        packed = msg.pack()
        assert len(packed) == 29
        restored = BroadcastHopMap5GUpdate.unpack(packed)
        assert restored.hop_map == hm
        assert restored.effective_slot == 0x12345678
        assert isinstance(restored, BroadcastHopMap5GUpdate)


class TestMultiIntervalUpdate:
    """多级收发间隔更新 (0x0037, 0x0038, 0x0039)"""

    def test_request_roundtrip(self):
        intervals = bytes(range(31))
        msg = MultiIntervalUpdateRequest(intervals=intervals)
        _roundtrip(msg)

    def test_response_roundtrip(self):
        intervals = bytes([0xFF] * 31)
        msg = MultiIntervalUpdateResponse(intervals=intervals)
        packed = msg.pack()
        assert len(packed) == 31
        restored = MultiIntervalUpdateResponse.unpack(packed)
        assert restored.intervals == intervals
        assert isinstance(restored, MultiIntervalUpdateResponse)

    def test_indication_roundtrip(self):
        intervals = bytes(range(31))
        msg = MultiIntervalUpdateIndication(
            intervals=intervals,
            update_flags=0x2A,
            effective_slot=0xDEADBEEF,
        )
        _roundtrip(msg)


class TestSystemTimeAndMulticast:
    """系统时间 / 异步组播 (0x003E-0x0043)"""

    def test_system_time_indication(self):
        payload = b"\x01\x02\x03\x04\x05"
        msg = SystemTimeIndication(payload=payload)
        packed = msg.pack()
        assert packed == payload
        restored = SystemTimeIndication.unpack(packed)
        assert restored.payload == payload

    def test_async_multicast_link_setup(self):
        msg = AsyncMulticastLinkSetup(
            event_group_set_id=1,
            event_group_id=2,
            effective_slot=0x12345678,
            event_group_period=100,
            event_period=50,
            intra_event_interval=10,
            inter_event_interval=20,
            scheduling_slot=5,
            tx_rx_indication=1,
            tx_link_id=0xAAAAAA,
            rx_link_id=0xBBBBBB,
            tx_frame_type=3,
            rx_frame_type=7,
            tx_bandwidth=2,
            rx_bandwidth=1,
            tx_pilot_density=3,
            rx_pilot_density=0,
            tx_sdu_max=1024,
            rx_sdu_max=512,
            tx_sdu_period=0x12345,
            rx_sdu_period=0xABCDE,
            tx_pdu_max=500,
            rx_pdu_max=300,
            tx_max_time_offset=100,
            rx_max_time_offset=200,
            tx_crc_init=0xDEADBEEF,
            rx_crc_init=0xCAFEBABE,
            tx_crc_type=1,
            rx_crc_type=0,
            tx_feedback_type=0x1F,
            rx_feedback_type=5,
        )
        packed = msg.pack()
        assert len(packed) == 45
        restored = AsyncMulticastLinkSetup.unpack(packed)
        assert restored.event_group_set_id == 1
        assert restored.event_group_id == 2
        assert restored.effective_slot == 0x12345678
        assert restored.event_group_period == 100
        assert restored.scheduling_slot == 5
        assert restored.tx_link_id == 0xAAAAAA
        assert restored.rx_link_id == 0xBBBBBB
        assert restored.tx_crc_init == 0xDEADBEEF
        assert restored.rx_crc_init == 0xCAFEBABE
        assert restored.tx_crc_type == 1
        assert restored.tx_feedback_type == 0x1F
        assert restored.rx_feedback_type == 5

    def test_async_multicast_param_exchange_request(self):
        payload = bytes(range(41))
        msg = AsyncMulticastParamExchangeRequest(payload=payload)
        _roundtrip(msg)

    def test_async_multicast_param_exchange_response(self):
        payload = bytes([0xAB] * 41)
        msg = AsyncMulticastParamExchangeResponse(payload=payload)
        _roundtrip(msg)

    def test_async_multicast_param_update_request(self):
        msg = AsyncMulticastParamUpdateRequest(
            param_tag_id=0x0A,
            event_group_set_id=0xBB,
            event_group_id=0xCC,
        )
        _roundtrip(msg)

    def test_async_multicast_param_update_indication(self):
        msg = AsyncMulticastParamUpdateIndication(
            param_tag_id=0x0F,
            event_group_set_id=0x12,
            event_group_id=0x34,
            effective_ref_slot=0xDEADBEEF,
            event_group_offset=0x1234,
        )
        _roundtrip(msg)


class TestNarrowbandMeasurement:
    """窄带跳频测量 (0x0044-0x004B)"""

    def test_meas_cap_request_zero(self):
        msg = NarrowbandMeasCapRequest()
        assert msg.pack() == b""
        restored = NarrowbandMeasCapRequest.unpack(b"")
        assert isinstance(restored, NarrowbandMeasCapRequest)

    def test_meas_cap_response(self):
        payload = bytes(range(32))
        msg = NarrowbandMeasCapResponse(payload=payload)
        _roundtrip(msg)

    def test_freq_table_24_update(self):
        ft = bytes(range(10))
        msg = NarrowbandFreqTable24Update(
            config_index=0x42, freq_table=ft,
        )
        _roundtrip(msg)

    def test_freq_table_51_update(self):
        ft = bytes(range(25))
        msg = NarrowbandFreqTable51Update(
            config_index=0x13, freq_table=ft,
        )
        _roundtrip(msg)

    def test_freq_table_58_update(self):
        ft = bytes(range(16))
        msg = NarrowbandFreqTable58Update(
            config_index=0xAA, freq_table=ft,
        )
        _roundtrip(msg)

    def test_meas_config_variable(self):
        payload = b"\xDE\xAD\xBE\xEF"
        msg = NarrowbandMeasConfig(payload=payload)
        packed = msg.pack()
        assert packed == payload
        restored = NarrowbandMeasConfig.unpack(packed)
        assert restored.payload == payload

    def test_meas_report_variable(self):
        payload = b"\xCA\xFE\xBA\xBE\x00\x01"
        msg = NarrowbandMeasReport(payload=payload)
        packed = msg.pack()
        assert packed == payload
        restored = NarrowbandMeasReport.unpack(packed)
        assert restored.payload == payload

    def test_meas_action(self):
        msg = NarrowbandMeasAction(
            config_index=0x05,
            start_slot=0xABCDEF01,
            action_config=0x7F,
        )
        _roundtrip(msg)


class TestCoordinateAndDelay:
    """坐标 / 时延 (0x004C-0x0050)"""

    def test_coordinate_request_zero(self):
        msg = CoordinateRequest()
        assert msg.pack() == b""
        restored = CoordinateRequest.unpack(b"")
        assert isinstance(restored, CoordinateRequest)

    def test_coordinate_report(self):
        msg = CoordinateReport(
            rel_x=100, rel_y=-200, rel_z=300,
            abs_lon=1160000, abs_lat=400000, abs_alt=50,
        )
        _roundtrip(msg)

    def test_coordinate_config(self):
        msg = CoordinateConfig(
            rel_x=-1, rel_y=-2, rel_z=-3,
            abs_lon=0, abs_lat=0, abs_alt=0,
        )
        _roundtrip(msg)

    def test_narrowband_delay_request_zero(self):
        msg = NarrowbandDelayRequest()
        assert msg.pack() == b""
        restored = NarrowbandDelayRequest.unpack(b"")
        assert isinstance(restored, NarrowbandDelayRequest)

    def test_narrowband_delay_response_variable(self):
        payload = b"\x01\x02\x03\x04\x05\x06\x07\x08"
        msg = NarrowbandDelayResponse(payload=payload)
        packed = msg.pack()
        assert packed == payload
        restored = NarrowbandDelayResponse.unpack(packed)
        assert restored.payload == payload


class TestAsyncTTLinkSetupExt:
    """异步 TT 链路建链指示 (0x0051)"""

    def test_variable_payload(self):
        payload = bytes(range(20))
        msg = AsyncTTLinkSetup(payload=payload)
        packed = msg.pack()
        assert packed == payload
        restored = AsyncTTLinkSetup.unpack(packed)
        assert restored.payload == payload


class TestUWBMeasurement:
    """超宽带脉冲测量 (0x0052-0x0056)"""

    def test_meas_cap_request_zero(self):
        msg = UWBMeasCapRequest()
        assert msg.pack() == b""
        restored = UWBMeasCapRequest.unpack(b"")
        assert isinstance(restored, UWBMeasCapRequest)

    def test_meas_cap_response(self):
        payload = bytes(range(50))
        msg = UWBMeasCapResponse(payload=payload)
        _roundtrip(msg)

    def test_meas_config_variable(self):
        payload = b"\x11\x22\x33\x44\x55"
        msg = UWBMeasConfig(payload=payload)
        packed = msg.pack()
        assert packed == payload
        restored = UWBMeasConfig.unpack(packed)
        assert restored.payload == payload

    def test_meas_config_feedback(self):
        msg = UWBMeasConfigFeedback(
            config_index=0x0A, status=0x01,
        )
        _roundtrip(msg)

    def test_meas_report_variable(self):
        payload = b"\xAA\xBB\xCC"
        msg = UWBMeasReport(payload=payload)
        packed = msg.pack()
        assert packed == payload
        restored = UWBMeasReport.unpack(packed)
        assert restored.payload == payload


class TestUWBSensing:
    """超宽带脉冲感知 (0x0057-0x005C)"""

    def test_sensing_cap_request_zero(self):
        msg = UWBSensingCapRequest()
        assert msg.pack() == b""
        restored = UWBSensingCapRequest.unpack(b"")
        assert isinstance(restored, UWBSensingCapRequest)

    def test_sensing_cap_response(self):
        payload = bytes(range(51))
        msg = UWBSensingCapResponse(payload=payload)
        _roundtrip(msg)

    def test_sensing_config_variable(self):
        payload = b"\x01\x02\x03"
        msg = UWBSensingConfig(payload=payload)
        packed = msg.pack()
        assert packed == payload
        restored = UWBSensingConfig.unpack(packed)
        assert restored.payload == payload

    def test_sensing_config_feedback(self):
        msg = UWBSensingConfigFeedback(
            config_index=0xFF, status=0x02,
        )
        _roundtrip(msg)

    def test_sensing_report_variable(self):
        payload = b"\xDE\xAD"
        msg = UWBSensingReport(payload=payload)
        packed = msg.pack()
        assert packed == payload
        restored = UWBSensingReport.unpack(packed)
        assert restored.payload == payload

    def test_sensing_action(self):
        msg = UWBSensingAction(
            config_index=0x03,
            start_slot=0x12345678,
            action_config=0xAB,
        )
        _roundtrip(msg)


class TestResourceReservation:
    """资源预留 (0x005D-0x005E)"""

    def test_reservation_roundtrip(self):
        msg = ResourceReservation(
            config_index=0x07,
            effective_slot=0xCAFEBABE,
            event_group_period=1000,
            event_period=200,
            event_length=50,
            event_count=8,
            scheduling_slot=5,
        )
        _roundtrip(msg)

    def test_reservation_terminate(self):
        msg = ResourceReservationTerminate(
            config_index=0x0A, reason=0x03,
        )
        _roundtrip(msg)


class TestNarrowbandSensing:
    """窄带跳频感知 (0x005F-0x0069)"""

    def test_sensing_request(self):
        payload = bytes(range(16))
        msg = NarrowbandSensingRequest(payload=payload)
        _roundtrip(msg)

    def test_sensing_feedback(self):
        msg = NarrowbandSensingFeedback(
            process_index=0x05, status=0x01,
        )
        _roundtrip(msg)

    def test_proxy_sensing_request(self):
        msg = NarrowbandProxySensingRequest(
            proxy_index=0x0A,
            sensing_index=0x0B,
            meas_quantity=0x12345678,
            report_period=0xABCDEF01,
            bandwidth=0x03,
        )
        _roundtrip(msg)

    def test_proxy_sensing_feedback(self):
        msg = NarrowbandProxySensingFeedback(
            proxy_index=0x01,
            sensing_index=0x0234,
            status=0x05,
            meas_quantity1=0x11111111,
            meas_quantity2=0x22222222,
            bandwidth1=0x0A,
            bandwidth2=0x0B,
        )
        _roundtrip(msg)

    def test_sensing_cap_request_zero(self):
        msg = NarrowbandSensingCapRequest()
        assert msg.pack() == b""
        restored = NarrowbandSensingCapRequest.unpack(b"")
        assert isinstance(restored, NarrowbandSensingCapRequest)

    def test_sensing_cap_response(self):
        payload = bytes(range(50))
        msg = NarrowbandSensingCapResponse(payload=payload)
        _roundtrip(msg)

    def test_sensing_config_variable(self):
        payload = b"\xAA\xBB\xCC\xDD"
        msg = NarrowbandSensingConfig(payload=payload)
        packed = msg.pack()
        assert packed == payload
        restored = NarrowbandSensingConfig.unpack(packed)
        assert restored.payload == payload

    def test_sensing_config_feedback(self):
        msg = NarrowbandSensingConfigFeedback(
            config_index=0x0C, status=0x07,
        )
        _roundtrip(msg)

    def test_device_status_report(self):
        msg = SensingDeviceStatusReport(
            config_index=0x42, stability=1,
        )
        _roundtrip(msg)

    def test_sensing_report_variable(self):
        payload = b"\x01\x02\x03\x04\x05\x06"
        msg = NarrowbandSensingReport(payload=payload)
        packed = msg.pack()
        assert packed == payload
        restored = NarrowbandSensingReport.unpack(packed)
        assert restored.payload == payload

    def test_sensing_action(self):
        msg = NarrowbandSensingAction(
            config_index=0x09,
            start_slot=0xDEADBEEF,
            action_config=0x55,
        )
        _roundtrip(msg)


class TestConfigUpdateAndUWBExtended:
    """配置更新 / UWB 扩展 (0x006A-0x0070)"""

    def test_meas_config_update_request(self):
        payload = bytes(range(32))
        msg = NarrowbandMeasConfigUpdateRequest(payload=payload)
        _roundtrip(msg)

    def test_meas_config_update_indication(self):
        payload = bytes([0xFF] * 32)
        msg = NarrowbandMeasConfigUpdateIndication(
            payload=payload,
        )
        _roundtrip(msg)

    def test_uwb_sensing_process_request(self):
        payload = bytes(range(16))
        msg = UWBSensingProcessRequest(payload=payload)
        _roundtrip(msg)

    def test_uwb_sensing_process_feedback(self):
        msg = UWBSensingProcessFeedback(
            process_index=0x04, status=0x02,
        )
        _roundtrip(msg)

    def test_uwb_proxy_sensing_request(self):
        msg = UWBProxySensingRequest(
            proxy_index=0x0A,
            sensing_index=0x0B,
            meas_quantity=0x12345678,
            report_period=0xABCDEF01,
            bandwidth=0x03,
        )
        _roundtrip(msg)

    def test_uwb_proxy_sensing_feedback(self):
        msg = UWBProxySensingFeedback(
            proxy_index=0x01,
            sensing_index=0x0234,
            status=0x05,
            meas_quantity1=0x11111111,
            meas_quantity2=0x22222222,
            bandwidth1=0x0A,
            bandwidth2=0x0B,
        )
        _roundtrip(msg)

    def test_uwb_meas_action(self):
        msg = UWBMeasAction(
            config_index=0x0F,
            start_slot=0xCAFEBABE,
            action_config=0x77,
        )
        _roundtrip(msg)


class TestDataTypeIndexExtended:
    """扩展信令 DATA_TYPE_INDEX 验证 (0x0035-0x0070)"""

    @pytest.mark.parametrize("cls,expected_idx", [
        (Channel5GStatusIndication, 0x0035),
        (HopMap5GUpdate, 0x0036),
        (MultiIntervalUpdateRequest, 0x0037),
        (MultiIntervalUpdateResponse, 0x0038),
        (MultiIntervalUpdateIndication, 0x0039),
        (BroadcastHopMap5GUpdate, 0x003B),
        (SystemTimeIndication, 0x003E),
        (AsyncMulticastLinkSetup, 0x003F),
        (AsyncMulticastParamExchangeRequest, 0x0040),
        (AsyncMulticastParamExchangeResponse, 0x0041),
        (AsyncMulticastParamUpdateRequest, 0x0042),
        (AsyncMulticastParamUpdateIndication, 0x0043),
        (NarrowbandMeasCapRequest, 0x0044),
        (NarrowbandMeasCapResponse, 0x0045),
        (NarrowbandFreqTable24Update, 0x0046),
        (NarrowbandFreqTable51Update, 0x0047),
        (NarrowbandFreqTable58Update, 0x0048),
        (NarrowbandMeasConfig, 0x0049),
        (NarrowbandMeasReport, 0x004A),
        (NarrowbandMeasAction, 0x004B),
        (CoordinateRequest, 0x004C),
        (CoordinateReport, 0x004D),
        (CoordinateConfig, 0x004E),
        (NarrowbandDelayRequest, 0x004F),
        (NarrowbandDelayResponse, 0x0050),
        (AsyncTTLinkSetup, 0x0051),
        (UWBMeasCapRequest, 0x0052),
        (UWBMeasCapResponse, 0x0053),
        (UWBMeasConfig, 0x0054),
        (UWBMeasConfigFeedback, 0x0055),
        (UWBMeasReport, 0x0056),
        (UWBSensingCapRequest, 0x0057),
        (UWBSensingCapResponse, 0x0058),
        (UWBSensingConfig, 0x0059),
        (UWBSensingConfigFeedback, 0x005A),
        (UWBSensingReport, 0x005B),
        (UWBSensingAction, 0x005C),
        (ResourceReservation, 0x005D),
        (ResourceReservationTerminate, 0x005E),
        (NarrowbandSensingRequest, 0x005F),
        (NarrowbandSensingFeedback, 0x0060),
        (NarrowbandProxySensingRequest, 0x0061),
        (NarrowbandProxySensingFeedback, 0x0062),
        (NarrowbandSensingCapRequest, 0x0063),
        (NarrowbandSensingCapResponse, 0x0064),
        (NarrowbandSensingConfig, 0x0065),
        (NarrowbandSensingConfigFeedback, 0x0066),
        (SensingDeviceStatusReport, 0x0067),
        (NarrowbandSensingReport, 0x0068),
        (NarrowbandSensingAction, 0x0069),
        (NarrowbandMeasConfigUpdateRequest, 0x006A),
        (NarrowbandMeasConfigUpdateIndication, 0x006B),
        (UWBSensingProcessRequest, 0x006C),
        (UWBSensingProcessFeedback, 0x006D),
        (UWBProxySensingRequest, 0x006E),
        (UWBProxySensingFeedback, 0x006F),
        (UWBMeasAction, 0x0070),
    ])
    def test_data_type_index(self, cls, expected_idx):
        assert expected_idx == cls.DATA_TYPE_INDEX
