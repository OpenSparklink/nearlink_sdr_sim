"""数据链路层帧结构与信令注册表测试 -- 7.3.2, 7.3.3, 7.3.4"""

import pytest

from nearlink_sdr.mac.frame import (
    AsyncDataFrame,
    ControlFrame,
    MuxFrame,
    SegmentType,
    SyncDataFrame,
)
from nearlink_sdr.mac.link_control import (
    ChannelReportConfig,
    ClockAccuracyRequest,
    ClockAccuracyResponse,
    CrcSwitchIndication,
    CrcSwitchRequest,
    DataLengthRequest,
    DataLengthResponse,
    FeatureExchangeRequest,
    FeatureExchangeResponse,
    IntervalUpdateIndication,
    IntervalUpdateRequest,
    IntervalUpdateResponse,
    LinkDisconnect,
    SignalingReject,
    VersionExchange,
)
from nearlink_sdr.mac.power_control import (
    Bandwidth,
    FreqDensity,
    PowerChangeIndication,
    PowerControlRequest,
    PowerControlResponse,
)
from nearlink_sdr.mac.signaling import (
    decode_signaling,
    encode_signaling,
    get_signaling_name,
    list_registered,
)

# ============================================================================
# 7.3.2.1 控制面帧
# ============================================================================

class TestControlFrame:
    def test_pack_unpack_roundtrip(self):
        cf = ControlFrame(0x0019, bytes([0x24, 0x05, 0xF6]))
        data = cf.pack()
        decoded, consumed = ControlFrame.unpack(data)
        assert consumed == len(data)
        assert decoded.data_type_index == 0x0019
        assert decoded.payload == bytes([0x24, 0x05, 0xF6])

    def test_pack_format(self):
        cf = ControlFrame(0x001A, bytes([0x80, 0xFF, 0x00, 0xC8]))
        data = cf.pack()
        # 2B index + 1B length + 4B payload = 7B
        assert len(data) == 7
        assert data[0:2] == b"\x00\x1A"
        assert data[2] == 4
        assert data[3:7] == bytes([0x80, 0xFF, 0x00, 0xC8])

    def test_empty_payload(self):
        cf = ControlFrame(0x0006, b"")
        data = cf.pack()
        decoded, consumed = ControlFrame.unpack(data)
        assert consumed == 3
        assert decoded.payload == b""

    def test_unpack_insufficient_header(self):
        with pytest.raises(ValueError, match="控制面帧头部不足"):
            ControlFrame.unpack(b"\x00\x19")

    def test_unpack_insufficient_payload(self):
        with pytest.raises(ValueError, match="控制面帧数据不足"):
            ControlFrame.unpack(b"\x00\x19\x03\x24\x05")

    def test_multiple_frames_sequential(self):
        cf1 = ControlFrame(0x0019, bytes(3))
        cf2 = ControlFrame(0x001A, bytes(4))
        buf = cf1.pack() + cf2.pack()
        d1, n1 = ControlFrame.unpack(buf)
        d2, n2 = ControlFrame.unpack(buf[n1:])
        assert d1.data_type_index == 0x0019
        assert d2.data_type_index == 0x001A
        assert n1 + n2 == len(buf)


# ============================================================================
# 7.3.3.2 异步数据帧
# ============================================================================

class TestAsyncDataFrame:
    def test_pack_unpack_roundtrip(self):
        payload = b"hello SLE"
        frame = AsyncDataFrame(SegmentType.COMPLETE, payload)
        data = frame.pack()
        decoded = AsyncDataFrame.unpack(data)
        assert decoded.segment_type == SegmentType.COMPLETE
        assert decoded.data == payload

    def test_segment_types(self):
        for seg in (SegmentType.FIRST, SegmentType.MIDDLE, SegmentType.LAST):
            frame = AsyncDataFrame(seg, b"\x01\x02\x03")
            decoded = AsyncDataFrame.unpack(frame.pack())
            assert decoded.segment_type == seg

    def test_max_length(self):
        frame = AsyncDataFrame(0, bytes(2047))
        decoded = AsyncDataFrame.unpack(frame.pack())
        assert len(decoded.data) == 2047

    def test_overflow_length(self):
        with pytest.raises(ValueError, match="数据长度超过 2047"):
            AsyncDataFrame(0, bytes(2048)).pack()

    def test_empty_data(self):
        frame = AsyncDataFrame(0, b"")
        decoded = AsyncDataFrame.unpack(frame.pack())
        assert decoded.data == b""

    def test_unpack_insufficient(self):
        with pytest.raises(ValueError, match="异步数据帧头部不足"):
            AsyncDataFrame.unpack(b"\x00")


# ============================================================================
# 7.3.3.3 同步数据帧
# ============================================================================

class TestSyncDataFrame:
    def test_nonperiodic_complete_roundtrip(self):
        frame = SyncDataFrame(
            pdu_seq=7, event_group=100, frame_format=1,
            segment_type=SegmentType.COMPLETE,
            data=b"\xAB\xCD", time_offset=5000,
        )
        data = frame.pack()
        decoded = SyncDataFrame.unpack(data)
        assert decoded.pdu_seq == 7
        assert decoded.event_group == 100
        assert decoded.frame_format == 1
        assert decoded.segment_type == SegmentType.COMPLETE
        assert decoded.time_offset == 5000
        assert decoded.data == b"\xAB\xCD"

    def test_periodic_roundtrip(self):
        frame = SyncDataFrame(
            pdu_seq=3, event_group=50, frame_format=0,
            segment_type=SegmentType.FIRST,
            data=b"\x01\x02\x03", sdu_seq=15,
        )
        data = frame.pack()
        decoded = SyncDataFrame.unpack(data)
        assert decoded.pdu_seq == 3
        assert decoded.event_group == 50
        assert decoded.frame_format == 0
        assert decoded.sdu_seq == 15
        assert decoded.data == b"\x01\x02\x03"

    def test_nonperiodic_middle_no_offset(self):
        frame = SyncDataFrame(
            pdu_seq=1, event_group=10, frame_format=1,
            segment_type=SegmentType.MIDDLE,
            data=b"\xFF",
        )
        data = frame.pack()
        decoded = SyncDataFrame.unpack(data)
        assert decoded.time_offset is None
        assert decoded.data == b"\xFF"

    def test_unpack_insufficient(self):
        with pytest.raises(ValueError, match="同步数据帧头部不足"):
            SyncDataFrame.unpack(b"\x00\x01\x02")


# ============================================================================
# 信令注册表
# ============================================================================

class TestSignalingRegistry:
    def test_encode_decode_power_request(self):
        req = PowerControlRequest(2, Bandwidth.BW_2MHZ, FreqDensity.RATIO_4_1, 5, -10)
        frame = encode_signaling(req)
        assert frame.data_type_index == 0x0019
        decoded = decode_signaling(frame)
        assert isinstance(decoded, PowerControlRequest)
        assert decoded.frame_type == 2
        assert decoded.tx_power_change == 5

    def test_encode_decode_power_response(self):
        resp = PowerControlResponse(True, False, -1, 0, 200)
        frame = encode_signaling(resp)
        assert frame.data_type_index == 0x001A
        decoded = decode_signaling(frame)
        assert isinstance(decoded, PowerControlResponse)
        assert decoded.sender_min_power is True
        assert decoded.acceptable_power_reduction == 200

    def test_encode_decode_power_indication(self):
        ind = PowerChangeIndication(7, 0, 3, False, True, 10, -20)
        frame = encode_signaling(ind)
        assert frame.data_type_index == 0x001B
        decoded = decode_signaling(frame)
        assert isinstance(decoded, PowerChangeIndication)
        assert decoded.frame_type == 7

    def test_unknown_signaling_passthrough(self):
        cf = ControlFrame(0x9999, b"\x01\x02")
        result = decode_signaling(cf)
        assert isinstance(result, ControlFrame)
        assert result.data_type_index == 0x9999

    def test_get_signaling_name(self):
        assert get_signaling_name(0x0019) == "功率控制请求"
        assert get_signaling_name(0x001A) == "功率控制响应"
        assert get_signaling_name(0x001B) == "功率变化指示"
        assert get_signaling_name(0xFFFF) == "未知"

    def test_list_registered(self):
        items = list_registered()
        assert len(items) >= 3
        indices = [idx for idx, _, _ in items]
        assert 0x0019 in indices
        assert 0x001A in indices
        assert 0x001B in indices


# ============================================================================
# 7.3.4 复用帧
# ============================================================================

class TestMuxFrame:
    def test_pack_control_only(self):
        cf1 = ControlFrame(0x0019, bytes(3))
        cf2 = ControlFrame(0x001A, bytes(4))
        mux = MuxFrame(control_frames=[cf1, cf2])
        data = mux.pack()
        assert len(data) == (3 + 3) + (3 + 4)

    def test_pack_with_async_data(self):
        cf = ControlFrame(0x0019, bytes(3))
        adf = AsyncDataFrame(SegmentType.COMPLETE, b"payload")
        mux = MuxFrame(control_frames=[cf], data_frame=adf)
        data = mux.pack()
        # control: 3+3=6, async: 2+7=9 => 15
        assert len(data) == 15

    def test_pack_empty(self):
        mux = MuxFrame(control_frames=[])
        assert mux.pack() == b""

    def test_end_to_end_signaling_in_mux(self):
        req = PowerControlRequest(2, 1, 0, 5, -10)
        frame = encode_signaling(req)
        mux = MuxFrame(control_frames=[frame])
        packed = mux.pack()
        # 解析回来
        restored, _ = ControlFrame.unpack(packed)
        msg = decode_signaling(restored)
        assert isinstance(msg, PowerControlRequest)
        assert msg.tx_power_change == 5


# ============================================================================
# 7.3.2 链路控制信令编解码
# ============================================================================


class TestIntervalUpdate:
    def test_request_roundtrip(self):
        req = IntervalUpdateRequest(interval_type=5)
        data = req.pack()
        assert len(data) == 1
        restored = IntervalUpdateRequest.unpack(data)
        assert restored.interval_type == 5

    def test_response_roundtrip(self):
        resp = IntervalUpdateResponse(interval_type=3)
        data = resp.pack()
        assert len(data) == 1
        restored = IntervalUpdateResponse.unpack(data)
        assert restored.interval_type == 3

    def test_indication_roundtrip(self):
        ind = IntervalUpdateIndication(link_id=0xABCDEF, interval_type=3,
                                       effective_slot=1000)
        data = ind.pack()
        assert len(data) == 8
        restored = IntervalUpdateIndication.unpack(data)
        assert restored.link_id == 0xABCDEF
        assert restored.interval_type == 3
        assert restored.effective_slot == 1000

    def test_request_signaling_registry(self):
        req = IntervalUpdateRequest(interval_type=0)
        frame = encode_signaling(req)
        assert frame.data_type_index == 0x0000
        decoded = decode_signaling(frame)
        assert isinstance(decoded, IntervalUpdateRequest)
        assert decoded.interval_type == 0

    def test_response_signaling_registry(self):
        resp = IntervalUpdateResponse(interval_type=15)
        frame = encode_signaling(resp)
        assert frame.data_type_index == 0x0001
        decoded = decode_signaling(frame)
        assert isinstance(decoded, IntervalUpdateResponse)
        assert decoded.interval_type == 15

    def test_indication_signaling_registry(self):
        ind = IntervalUpdateIndication(link_id=1, interval_type=15,
                                       effective_slot=0)
        frame = encode_signaling(ind)
        assert frame.data_type_index == 0x0002
        decoded = decode_signaling(frame)
        assert isinstance(decoded, IntervalUpdateIndication)
        assert decoded.interval_type == 15


class TestSignalingRejectMsg:
    def test_roundtrip(self):
        msg = SignalingReject(rejected_index=0x0019, error_reason=42)
        data = msg.pack()
        assert len(data) == 3
        restored = SignalingReject.unpack(data)
        assert restored.rejected_index == 0x0019
        assert restored.error_reason == 42

    def test_signaling_registry(self):
        msg = SignalingReject(rejected_index=0x000E, error_reason=1)
        frame = encode_signaling(msg)
        decoded = decode_signaling(frame)
        assert isinstance(decoded, SignalingReject)
        assert decoded.rejected_index == 0x000E


class TestFeatureExchange:
    def test_request_roundtrip(self):
        features = (1 << 79) | (1 << 0)
        req = FeatureExchangeRequest(feature_set=features)
        data = req.pack()
        assert len(data) == 10
        restored = FeatureExchangeRequest.unpack(data)
        assert restored.feature_set == features

    def test_response_roundtrip(self):
        resp = FeatureExchangeResponse(feature_set=0xFF00FF00FF)
        data = resp.pack()
        restored = FeatureExchangeResponse.unpack(data)
        assert restored.feature_set == 0xFF00FF00FF

    def test_signaling_registry(self):
        req = FeatureExchangeRequest(feature_set=0)
        frame = encode_signaling(req)
        decoded = decode_signaling(frame)
        assert isinstance(decoded, FeatureExchangeRequest)
        assert decoded.feature_set == 0


class TestVersionExchange:
    def test_roundtrip(self):
        msg = VersionExchange(spec_version=2, company_id=0x1234,
                              sub_version=0x5678)
        data = msg.pack()
        assert len(data) == 5
        restored = VersionExchange.unpack(data)
        assert restored.spec_version == 2
        assert restored.company_id == 0x1234
        assert restored.sub_version == 0x5678

    def test_signaling_registry(self):
        msg = VersionExchange(spec_version=1, company_id=0,
                              sub_version=0)
        frame = encode_signaling(msg)
        decoded = decode_signaling(frame)
        assert isinstance(decoded, VersionExchange)
        assert decoded.spec_version == 1


class TestDataLength:
    def test_request_roundtrip(self):
        req = DataLengthRequest(max_rx_bytes=251, max_rx_time=2120,
                                max_tx_bytes=251, max_tx_time=2120)
        data = req.pack()
        assert len(data) == 8
        restored = DataLengthRequest.unpack(data)
        assert restored.max_rx_bytes == 251
        assert restored.max_tx_time == 2120

    def test_response_roundtrip(self):
        resp = DataLengthResponse(max_rx_bytes=2047, max_rx_time=65535,
                                  max_tx_bytes=31, max_tx_time=346)
        data = resp.pack()
        restored = DataLengthResponse.unpack(data)
        assert restored.max_rx_bytes == 2047
        assert restored.max_tx_bytes == 31

    def test_signaling_registry(self):
        req = DataLengthRequest(100, 500, 100, 500)
        frame = encode_signaling(req)
        assert frame.data_type_index == 0x000E
        decoded = decode_signaling(frame)
        assert isinstance(decoded, DataLengthRequest)
        assert decoded.max_rx_bytes == 100


class TestChannelReport:
    def test_roundtrip(self):
        msg = ChannelReportConfig(enable=1, min_interval=10,
                                  max_delay=30)
        data = msg.pack()
        assert len(data) == 3
        restored = ChannelReportConfig.unpack(data)
        assert restored.enable == 1
        assert restored.min_interval == 10
        assert restored.max_delay == 30


class TestCrcSwitch:
    def test_request_roundtrip(self):
        req = CrcSwitchRequest(link_id=0x123456, tx_crc_type=1,
                               rx_crc_type=0, tx_crc_init=0x87654321,
                               rx_crc_init=0x12345678)
        data = req.pack()
        assert len(data) == 12
        restored = CrcSwitchRequest.unpack(data)
        assert restored.link_id == 0x123456
        assert restored.tx_crc_type == 1
        assert restored.rx_crc_type == 0
        assert restored.tx_crc_init == 0x87654321
        assert restored.rx_crc_init == 0x12345678

    def test_indication_roundtrip(self):
        ind = CrcSwitchIndication(link_id=0xABC, tx_crc_type=0,
                                  rx_crc_type=1, tx_crc_init=0,
                                  rx_crc_init=0xFFFFFFFF,
                                  effective_slot=999)
        data = ind.pack()
        assert len(data) == 16
        restored = CrcSwitchIndication.unpack(data)
        assert restored.link_id == 0xABC
        assert restored.rx_crc_type == 1
        assert restored.rx_crc_init == 0xFFFFFFFF
        assert restored.effective_slot == 999


class TestClockAccuracy:
    def test_request_roundtrip(self):
        req = ClockAccuracyRequest(accuracy=50)
        data = req.pack()
        assert len(data) == 1
        restored = ClockAccuracyRequest.unpack(data)
        assert restored.accuracy == 50

    def test_response_roundtrip(self):
        resp = ClockAccuracyResponse(accuracy=100)
        data = resp.pack()
        restored = ClockAccuracyResponse.unpack(data)
        assert restored.accuracy == 100


class TestLinkDisconnect:
    def test_roundtrip(self):
        msg = LinkDisconnect(link_id=0x654321, error_reason=0x13)
        data = msg.pack()
        assert len(data) == 4
        restored = LinkDisconnect.unpack(data)
        assert restored.link_id == 0x654321
        assert restored.error_reason == 0x13

    def test_signaling_registry(self):
        msg = LinkDisconnect(link_id=1, error_reason=0)
        frame = encode_signaling(msg)
        assert frame.data_type_index == 0x001E
        decoded = decode_signaling(frame)
        assert isinstance(decoded, LinkDisconnect)
        assert decoded.link_id == 1


class TestSignalingRegistryExpanded:
    """验证扩展后的信令注册表覆盖 38 种信令类型。"""

    def test_total_registered_count(self):
        items = list_registered()
        assert len(items) >= 38

    def test_all_indices_present(self):
        items = list_registered()
        indices = {idx for idx, _, _ in items}
        expected = {0x0000, 0x0001, 0x0002, 0x0003, 0x0004, 0x0005,
                    0x0006, 0x0007, 0x0008, 0x0009,
                    0x000A, 0x000B, 0x000C, 0x000D,
                    0x000E, 0x000F, 0x0010, 0x0011,
                    0x0012, 0x0013, 0x0014,
                    0x0015, 0x0016, 0x0017, 0x0018,
                    0x0019, 0x001A, 0x001B, 0x001C, 0x001D, 0x001E,
                    0x001F, 0x002A, 0x0030, 0x0031, 0x0032,
                    0x0033, 0x0034, 0x003A, 0x003C, 0x003D}
        assert expected.issubset(indices)

    def test_names_lookup(self):
        assert get_signaling_name(0x0000) == "收发间隔更新请求"
        assert get_signaling_name(0x0003) == "信令被拒指示"
        assert get_signaling_name(0x000D) == "版本交互指示"
        assert get_signaling_name(0x001E) == "链路断开指示"
