"""数据链路层帧结构与信令注册表测试 -- 7.3.2, 7.3.3, 7.3.4"""

import pytest

from nearlink_sdr.mac.frame import (
    AsyncDataFrame,
    ControlFrame,
    MuxFrame,
    SegmentType,
    SyncDataFrame,
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
