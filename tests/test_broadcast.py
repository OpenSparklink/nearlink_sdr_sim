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
    NonLinkedBroadcastLinkInfo,
    QueryRequestFilterInfo,
    RequestType,
    SystemMgmtFrameInfo,
    TransportIndicationInfo,
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


# -----------------------------------------------------------------------
# 7.1.4.3 传输指示信息
# -----------------------------------------------------------------------


class TestTransportIndicationInfo:
    """TransportIndicationInfo 编解码测试"""

    def _make(self, *, is_5g: bool = False) -> TransportIndicationInfo:
        hop_len = 25 if is_5g else 10
        return TransportIndicationInfo(
            system_slot_seq=0xDEADBEEF,
            event_group_offset=0x123456,
            event_group_period=500,
            event_period=100,
            intra_event_interval=200,
            inter_event_interval=300,
            event_count=5,
            peer_addr=b"\x01\x02\x03\x04\x05\x06",
            peer_addr_type=3,
            sleep_clock_accuracy=2,
            first_last_indication=1,
            tx_frame_type=0x0A,
            rx_frame_type=0x05,
            tx_crc_type=1,
            rx_crc_type=0,
            tx_feedback_type=0x3F,
            rx_feedback_type=0x07,
            system_schedule_slot=0x05,
            tx_link_id=0xABCDEF,
            rx_link_id=0x112233,
            tx_bandwidth=3,
            rx_bandwidth=1,
            tx_pilot_density=2,
            rx_pilot_density=0,
            tx_pdu_max=0x7FF,
            rx_pdu_max=0x100,
            tx_max_time_offset=0x1FF,
            rx_max_time_offset=0x080,
            tx_crc_init=0xAABBCCDD,
            rx_crc_init=0x11223344,
            delay_period=1000,
            timeout=5000,
            hop_map=bytes(range(hop_len)),
            is_5g=is_5g,
        )

    def test_roundtrip_2_4ghz(self):
        original = self._make(is_5g=False)
        packed = original.pack()
        restored = TransportIndicationInfo.unpack(packed, is_5g=False)
        assert restored.system_slot_seq == original.system_slot_seq
        assert restored.event_group_offset == original.event_group_offset
        assert restored.event_count == original.event_count
        assert restored.peer_addr == original.peer_addr
        assert restored.peer_addr_type == original.peer_addr_type
        assert restored.tx_frame_type == original.tx_frame_type
        assert restored.rx_frame_type == original.rx_frame_type
        assert restored.tx_crc_init == original.tx_crc_init
        assert restored.rx_crc_init == original.rx_crc_init
        assert restored.hop_map == original.hop_map
        assert restored.delay_period == original.delay_period
        assert restored.timeout == original.timeout

    def test_roundtrip_5g(self):
        original = self._make(is_5g=True)
        packed = original.pack()
        restored = TransportIndicationInfo.unpack(packed, is_5g=True)
        assert restored.hop_map == original.hop_map
        assert len(restored.hop_map) == 25
        assert restored.system_slot_seq == original.system_slot_seq

    def test_pack_length_2_4ghz(self):
        info = self._make(is_5g=False)
        packed = info.pack()
        # 400 + 80 = 480 bits = 60 bytes
        assert len(packed) == 60

    def test_pack_length_5g(self):
        info = self._make(is_5g=True)
        packed = info.pack()
        # 400 + 200 = 600 bits = 75 bytes
        assert len(packed) == 75

    def test_unpack_short_data(self):
        with pytest.raises(ValueError, match="数据不足"):
            TransportIndicationInfo.unpack(b"\x00" * 10, is_5g=False)

    def test_all_fields_roundtrip(self):
        original = self._make()
        restored = TransportIndicationInfo.unpack(original.pack())
        assert restored.sleep_clock_accuracy == original.sleep_clock_accuracy
        assert restored.first_last_indication == original.first_last_indication
        assert restored.tx_crc_type == original.tx_crc_type
        assert restored.rx_crc_type == original.rx_crc_type
        assert restored.tx_feedback_type == original.tx_feedback_type
        assert restored.rx_feedback_type == original.rx_feedback_type
        assert restored.system_schedule_slot == original.system_schedule_slot
        assert restored.tx_link_id == original.tx_link_id
        assert restored.rx_link_id == original.rx_link_id
        assert restored.tx_bandwidth == original.tx_bandwidth
        assert restored.rx_bandwidth == original.rx_bandwidth
        assert restored.tx_pilot_density == original.tx_pilot_density
        assert restored.rx_pilot_density == original.rx_pilot_density
        assert restored.tx_pdu_max == original.tx_pdu_max
        assert restored.rx_pdu_max == original.rx_pdu_max
        assert restored.tx_max_time_offset == original.tx_max_time_offset
        assert restored.rx_max_time_offset == original.rx_max_time_offset
        assert restored.event_group_period == original.event_group_period
        assert restored.event_period == original.event_period
        assert restored.intra_event_interval == original.intra_event_interval
        assert restored.inter_event_interval == original.inter_event_interval


# -----------------------------------------------------------------------
# 7.1.4.8 非链接态广播链路信息
# -----------------------------------------------------------------------


class TestNonLinkedBroadcastLinkInfo:
    """NonLinkedBroadcastLinkInfo 编解码测试"""

    def _make(self, *, is_5g: bool = False) -> NonLinkedBroadcastLinkInfo:
        hop_len = 25 if is_5g else 10
        return NonLinkedBroadcastLinkInfo(
            transmission_type=1,
            service_adapt_mode=0,
            system_slot_seq=0x12345678,
            event_group_offset=0xABCDEF,
            event_group_set_id=0x42,
            event_group_count=3,
            event_group_interval=10,
            event_group_period=200,
            event_period=50,
            event_count=8,
            sync_anchor_delay=0x001234,
            sync_ref_delay=0x005678,
            base_link_id=0xFEDCBA,
            frame_type=0x0F,
            bandwidth=2,
            pilot_density=1,
            sdu_max=0xFFF,
            sdu_period=0xFFFFF,
            pdu_max=0x7FF,
            new_packet_count=0x0A,
            crc_type=1,
            crc_base_init=0xDEADFACE,
            hop_map=bytes(range(hop_len)),
            giv=b"\xA1\xA2\xA3\xA4\xA5\xA6\xA7\xA8",
            gskd=bytes(range(0x10, 0x20)),
            is_5g=is_5g,
        )

    def test_roundtrip_2_4ghz(self):
        original = self._make(is_5g=False)
        packed = original.pack()
        restored = NonLinkedBroadcastLinkInfo.unpack(packed, is_5g=False)
        assert restored.transmission_type == original.transmission_type
        assert restored.service_adapt_mode == original.service_adapt_mode
        assert restored.system_slot_seq == original.system_slot_seq
        assert restored.event_group_offset == original.event_group_offset
        assert restored.base_link_id == original.base_link_id
        assert restored.crc_base_init == original.crc_base_init
        assert restored.hop_map == original.hop_map
        assert restored.giv == original.giv
        assert restored.gskd == original.gskd

    def test_roundtrip_5g(self):
        original = self._make(is_5g=True)
        packed = original.pack()
        restored = NonLinkedBroadcastLinkInfo.unpack(packed, is_5g=True)
        assert len(restored.hop_map) == 25
        assert restored.hop_map == original.hop_map
        assert restored.giv == original.giv
        assert restored.gskd == original.gskd

    def test_pack_length_2_4ghz(self):
        info = self._make(is_5g=False)
        packed = info.pack()
        # 288 + 80 + 64 + 128 = 560 bits = 70 bytes
        assert len(packed) == 70

    def test_pack_length_5g(self):
        info = self._make(is_5g=True)
        packed = info.pack()
        # 288 + 200 + 64 + 128 = 680 bits = 85 bytes
        assert len(packed) == 85

    def test_unpack_short_data(self):
        with pytest.raises(ValueError, match="数据不足"):
            NonLinkedBroadcastLinkInfo.unpack(b"\x00" * 5, is_5g=False)

    def test_all_fields_roundtrip(self):
        original = self._make()
        restored = NonLinkedBroadcastLinkInfo.unpack(original.pack())
        assert restored.event_group_set_id == original.event_group_set_id
        assert restored.event_group_count == original.event_group_count
        assert restored.event_group_interval == original.event_group_interval
        assert restored.event_group_period == original.event_group_period
        assert restored.event_period == original.event_period
        assert restored.event_count == original.event_count
        assert restored.sync_anchor_delay == original.sync_anchor_delay
        assert restored.sync_ref_delay == original.sync_ref_delay
        assert restored.frame_type == original.frame_type
        assert restored.bandwidth == original.bandwidth
        assert restored.pilot_density == original.pilot_density
        assert restored.sdu_max == original.sdu_max
        assert restored.sdu_period == original.sdu_period
        assert restored.pdu_max == original.pdu_max
        assert restored.new_packet_count == original.new_packet_count
        assert restored.crc_type == original.crc_type


# -----------------------------------------------------------------------
# 7.1.4.9 查询请求过滤信息
# -----------------------------------------------------------------------


class TestQueryRequestFilterInfo:
    """QueryRequestFilterInfo 编解码测试"""

    def test_roundtrip_16bit_only(self):
        info = QueryRequestFilterInfo(
            uuid_16_list=[0x1800, 0x1801, 0xFFEE],
        )
        packed = info.pack()
        restored = QueryRequestFilterInfo.unpack(packed)
        assert restored.uuid_16_list == info.uuid_16_list
        assert restored.uuid_128_list == []

    def test_roundtrip_128bit_only(self):
        uuid_a = bytes(range(16))
        uuid_b = bytes(range(0xF0, 0x100))
        info = QueryRequestFilterInfo(
            uuid_128_list=[uuid_a, uuid_b],
        )
        packed = info.pack()
        restored = QueryRequestFilterInfo.unpack(packed)
        assert restored.uuid_16_list == []
        assert restored.uuid_128_list == [uuid_a, uuid_b]

    def test_roundtrip_mixed(self):
        uuid_128 = b"\xAA" * 16
        info = QueryRequestFilterInfo(
            uuid_16_list=[0x0001, 0xABCD],
            uuid_128_list=[uuid_128],
        )
        packed = info.pack()
        restored = QueryRequestFilterInfo.unpack(packed)
        assert restored.uuid_16_list == [0x0001, 0xABCD]
        assert restored.uuid_128_list == [uuid_128]

    def test_empty(self):
        info = QueryRequestFilterInfo()
        packed = info.pack()
        restored = QueryRequestFilterInfo.unpack(packed)
        assert restored.uuid_16_list == []
        assert restored.uuid_128_list == []

    def test_unpack_short_data(self):
        with pytest.raises(ValueError, match="数据不足"):
            QueryRequestFilterInfo.unpack(b"")

    def test_pack_length(self):
        info = QueryRequestFilterInfo(
            uuid_16_list=[0x1234],
            uuid_128_list=[b"\x00" * 16],
        )
        packed = info.pack()
        # 1 (count_16) + 2 (uuid16) + 1 (count_128) + 16 (uuid128) = 20
        assert len(packed) == 20
