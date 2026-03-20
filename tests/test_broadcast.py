"""广播帧编解码测试 -- TXS-10002-2025 标准 7.1.4"""

import pytest

from nearlink_sdr.mac.broadcast import (
    AccessBasicInfo,
    AccessRequestInfo,
    AccessResponseEntry,
    AccessResponseInfo,
    AccessResponseType,
    AddrType,
    BroadcastDataType,
    BroadcastFrame,
    DiscoveryAccessEntry,
    DiscoveryAccessResourceConfig,
    ExtAdvResourceConfig,
    GTNegotiation,
    RequestType,
    SystemMgmtFrameInfo,
)


class TestExtAdvResourceConfig:
    """扩展广播帧资源配置信息 (7.1.4.1)"""

    def test_pack_unpack_roundtrip(self):
        cfg = ExtAdvResourceConfig(
            channel_index=37, offset=100, frame_type=2,
            bandwidth=1, pilot_density=0, clock_accuracy=3, offset_unit=0,
        )
        packed = cfg.pack()
        assert len(packed) == 4
        restored = ExtAdvResourceConfig.unpack(packed)
        assert restored.channel_index == 37
        assert restored.offset == 100
        assert restored.frame_type == 2
        assert restored.bandwidth == 1
        assert restored.pilot_density == 0
        assert restored.clock_accuracy == 3
        assert restored.offset_unit == 0

    def test_max_values(self):
        cfg = ExtAdvResourceConfig(
            channel_index=255, offset=4095, frame_type=15,
            bandwidth=3, pilot_density=3, clock_accuracy=7, offset_unit=1,
        )
        restored = ExtAdvResourceConfig.unpack(cfg.pack())
        assert restored.channel_index == 255
        assert restored.offset == 4095
        assert restored.frame_type == 15
        assert restored.bandwidth == 3
        assert restored.clock_accuracy == 7
        assert restored.offset_unit == 1

    def test_unpack_short_data(self):
        with pytest.raises(ValueError, match="数据不足"):
            ExtAdvResourceConfig.unpack(b"\x00\x00")


class TestDiscoveryAccessResourceConfig:
    """发现接入资源配置信息 (7.1.4.2)"""

    def test_pack_unpack_no_entries(self):
        cfg = DiscoveryAccessResourceConfig(
            request_offset=300, request_max_length=50,
            response_offset=600, gt_negotiation=GTNegotiation.NEGOTIATE_G,
            entry_count=0, entries=[],
        )
        packed = cfg.pack()
        restored = DiscoveryAccessResourceConfig.unpack(packed)
        assert restored.request_offset == 300
        assert restored.request_max_length == 50
        assert restored.response_offset == 600
        assert restored.gt_negotiation == GTNegotiation.NEGOTIATE_G
        assert restored.entry_count == 0

    def test_pack_unpack_with_entries(self):
        entry = DiscoveryAccessEntry(
            request_type=RequestType.ACCESS,
            carry_info_indication=1,
            peer_addr_type=AddrType.ALLIANCE_ASSIGNED,
            addr_present=1,
            peer_addr=b"\x01\x02\x03\x04\x05\x06",
        )
        cfg = DiscoveryAccessResourceConfig(
            request_offset=500, request_max_length=100,
            response_offset=1000, gt_negotiation=0,
            entry_count=1, entries=[entry],
        )
        packed = cfg.pack()
        restored = DiscoveryAccessResourceConfig.unpack(packed)
        assert restored.entry_count == 1
        assert len(restored.entries) == 1
        assert restored.entries[0].request_type == RequestType.ACCESS
        assert restored.entries[0].addr_present == 1
        assert restored.entries[0].peer_addr == b"\x01\x02\x03\x04\x05\x06"


class TestAccessBasicInfo:
    """接入基本信息 (7.1.4.4)"""

    def test_pack_unpack_2_4ghz(self):
        hop_map = bytes(10)
        info = AccessBasicInfo(
            smf_baseline_slot=1000, smf_offset=500,
            smf_link_id=0x123456, smf_period=800,
            smf_frame_type=2, smf_bandwidth=1, smf_pilot_density=0,
            access_link_id=0xABCDEF, access_period=400,
            access_timeout=30, sleep_clock_accuracy=5,
            access_crc_type=0, access_crc_init=0xDEADBEEF,
            hop_map=hop_map, smf_channel_count=3,
            smf_channel_table=b"\x25\x26\x27",
        )
        packed = info.pack()
        restored = AccessBasicInfo.unpack(packed)
        assert restored.smf_baseline_slot == 1000
        assert restored.smf_offset == 500
        assert restored.smf_link_id == 0x123456
        assert restored.smf_period == 800
        assert restored.smf_frame_type == 2
        assert restored.smf_bandwidth == 1
        assert restored.access_link_id == 0xABCDEF
        assert restored.access_crc_init == 0xDEADBEEF
        assert restored.smf_channel_count == 3


class TestAccessRequestInfo:
    """接入请求信息 (7.1.4.5)"""

    def test_minimal(self):
        info = AccessRequestInfo(structure_indication=0x00)
        packed = info.pack()
        restored = AccessRequestInfo.unpack(packed)
        assert restored.structure_indication == 0x00
        assert restored.gt_role is None

    def test_full_fields(self):
        info = AccessRequestInfo(
            structure_indication=0xFF,
            gt_role=0b01,
            frame_support=0b1111,
            bandwidth_support=0b111,
            mcs_support=0x1FFF,
            pilot_support=0b1111,
            slot_support=0b11111,
            switch_delay=0x04,
            crc_support=0b11,
        )
        packed = info.pack()
        restored = AccessRequestInfo.unpack(packed)
        assert restored.structure_indication == 0xFF
        assert restored.gt_role == 0b01
        assert restored.frame_support == 0b1111
        assert restored.bandwidth_support == 0b111
        assert restored.mcs_support == 0x1FFF
        assert restored.pilot_support == 0b1111
        assert restored.slot_support == 0b11111
        assert restored.switch_delay == 0x04
        assert restored.crc_support == 0b11


class TestAccessResponseInfo:
    """接入响应信息 (7.1.4.6)"""

    def test_accept_response(self):
        entry = AccessResponseEntry(
            peer_addr=b"\xAA\xBB\xCC\xDD\xEE\xFF",
            response_type=AccessResponseType.ACCEPT,
            peer_addr_type=AddrType.ALLIANCE_ASSIGNED,
            repeat_indication=0,
        )
        info = AccessResponseInfo(entries=[entry])
        packed = info.pack()
        restored = AccessResponseInfo.unpack(packed)
        assert len(restored.entries) == 1
        assert restored.entries[0].response_type == AccessResponseType.ACCEPT
        assert restored.entries[0].peer_addr == b"\xAA\xBB\xCC\xDD\xEE\xFF"

    def test_reject_response(self):
        entry = AccessResponseEntry(
            peer_addr=b"\x01" * 6,
            response_type=AccessResponseType.USER_REJECT,
            peer_addr_type=AddrType.PRIVATE,
            repeat_indication=0,
        )
        info = AccessResponseInfo(entries=[entry])
        restored = AccessResponseInfo.unpack(info.pack())
        assert restored.entries[0].response_type == AccessResponseType.USER_REJECT


class TestSystemMgmtFrameInfo:
    """启动系统管理帧信息 (7.1.4.7)"""

    def test_pack_unpack(self):
        info = SystemMgmtFrameInfo(
            baseline_slot=5000, offset=1500,
            access_addr=0x123456, period=2400,
            frame_type=2, bandwidth=1, pilot_density=0,
            channel_count=3, channel_table=b"\x25\x26\x27",
        )
        packed = info.pack()
        restored = SystemMgmtFrameInfo.unpack(packed)
        assert restored.baseline_slot == 5000
        assert restored.offset == 1500
        assert restored.access_addr == 0x123456
        assert restored.period == 2400
        assert restored.frame_type == 2
        assert restored.bandwidth == 1
        assert restored.channel_count == 3
        assert restored.channel_table == b"\x25\x26\x27"


class TestBroadcastFrame:
    """广播帧通用结构 (7.1.4)"""

    def test_minimal_frame(self):
        frame = BroadcastFrame(
            structure_indication=0x00,
            local_addr_type=0, peer_addr_type=0,
            local_addr=b"\x00" * 6, irk_id=0,
            peer_addr=b"\x00" * 6,
        )
        packed = frame.pack()
        assert len(packed) == 2
        restored = BroadcastFrame.unpack(packed)
        assert restored.structure_indication == 0x00

    def test_with_local_addr(self):
        addr = b"\x11\x22\x33\x44\x55\x66"
        frame = BroadcastFrame(
            structure_indication=0x01,
            local_addr_type=AddrType.ALLIANCE_ASSIGNED,
            peer_addr_type=0, local_addr=addr,
            irk_id=0, peer_addr=b"\x00" * 6,
        )
        packed = frame.pack()
        restored = BroadcastFrame.unpack(packed)
        assert restored.structure_indication == 0x01
        assert restored.local_addr == addr
        assert restored.local_addr_type == AddrType.ALLIANCE_ASSIGNED

    def test_full_frame_with_data(self):
        ext_cfg = ExtAdvResourceConfig(
            channel_index=10, offset=200, frame_type=2,
            bandwidth=1, pilot_density=0, clock_accuracy=3, offset_unit=0,
        )
        data_payload = b"\xDE\xAD\xBE\xEF"
        frame = BroadcastFrame(
            structure_indication=0x1F,
            local_addr_type=AddrType.ALLIANCE_ASSIGNED,
            peer_addr_type=AddrType.RESOLVABLE_RANDOM,
            local_addr=b"\x01\x02\x03\x04\x05\x06",
            irk_id=0x42,
            peer_addr=b"\xA1\xA2\xA3\xA4\xA5\xA6",
            ext_adv_config=ext_cfg,
            data_items=[
                (BroadcastDataType.ACCESS_BASIC, data_payload),
            ],
        )
        packed = frame.pack()
        restored = BroadcastFrame.unpack(packed)
        assert restored.structure_indication == 0x1F
        assert restored.local_addr == b"\x01\x02\x03\x04\x05\x06"
        assert restored.irk_id == 0x42
        assert restored.peer_addr == b"\xA1\xA2\xA3\xA4\xA5\xA6"
        assert restored.ext_adv_config is not None
        assert restored.ext_adv_config.channel_index == 10
        assert len(restored.data_items) == 1
        assert restored.data_items[0][0] == BroadcastDataType.ACCESS_BASIC
        assert restored.data_items[0][1] == data_payload

    def test_multiple_data_items(self):
        frame = BroadcastFrame(
            structure_indication=0x10,
            local_addr_type=0, peer_addr_type=0,
            local_addr=b"\x00" * 6, irk_id=0,
            peer_addr=b"\x00" * 6,
            data_items=[
                (BroadcastDataType.DISCOVERY_ACCESS_RESOURCE, b"\x01\x02"),
                (BroadcastDataType.UPPER_LAYER_DATA, b"\xFF\xFE\xFD"),
            ],
        )
        restored = BroadcastFrame.unpack(frame.pack())
        assert len(restored.data_items) == 2
        assert restored.data_items[0][0] == 0x00
        assert restored.data_items[1][0] == 0xFF

    def test_unpack_short_data(self):
        with pytest.raises(ValueError, match="数据不足"):
            BroadcastFrame.unpack(b"\x00")


class TestEnums:
    """枚举值验证"""

    def test_addr_type_values(self):
        assert AddrType.ALLIANCE_ASSIGNED == 0
        assert AddrType.RESOLVABLE_RANDOM == 3
        assert AddrType.PRIVATE == 6

    def test_broadcast_data_type(self):
        assert BroadcastDataType.DISCOVERY_ACCESS_RESOURCE == 0x00
        assert BroadcastDataType.UPPER_LAYER_DATA == 0xFF

    def test_request_type(self):
        assert RequestType.QUERY == 0
        assert RequestType.ACCESS == 1

    def test_access_response_type(self):
        assert AccessResponseType.ACCEPT == 0
        assert AccessResponseType.USER_REJECT == 3
