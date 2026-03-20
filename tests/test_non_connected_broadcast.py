"""非链接态广播传输测试 -- TXS-10002-2025 标准 7.1.7.2。

验证非链接态广播帧的构建、序列化/反序列化以及端到端流程。
"""

from __future__ import annotations

from nearlink_sdr.mac.access import (
    NonConnectedBroadcastConfig,
    NonConnectedBroadcastManager,
    NonConnectedBroadcastResult,
    parse_non_connected_broadcast,
)
from nearlink_sdr.mac.broadcast import (
    BroadcastDataType,
    BroadcastFrame,
    NonLinkedBroadcastLinkInfo,
    SystemMgmtFrameInfo,
)


class TestNonConnectedBroadcastConfig:
    """非链接态广播配置测试。"""

    def test_default_config(self):
        cfg = NonConnectedBroadcastConfig()
        assert cfg.transmission_type == 0
        assert cfg.service_adapt_mode == 0
        assert cfg.encrypted is False
        assert cfg.is_5g is False
        assert cfg.sdu_max == 128
        assert cfg.smf_period == 800

    def test_encrypted_config(self):
        giv = b"\x01" * 8
        gskd = b"\x02" * 16
        cfg = NonConnectedBroadcastConfig(
            encrypted=True,
            giv=giv,
            gskd=gskd,
        )
        assert cfg.encrypted is True
        assert cfg.giv == giv
        assert cfg.gskd == gskd

    def test_5g_config(self):
        cfg = NonConnectedBroadcastConfig(
            is_5g=True,
            hop_map=b"\xFF" * 25,
        )
        assert cfg.is_5g is True
        assert len(cfg.hop_map) == 25


class TestNonConnectedBroadcastManager:
    """非链接态广播管理器测试。"""

    def test_build_frame_default(self):
        mgr = NonConnectedBroadcastManager(
            local_address=b"\x01\x02\x03\x04\x05\x06",
        )
        frame = mgr.build_non_connected_broadcast_frame()
        assert isinstance(frame, BroadcastFrame)
        assert frame.local_addr == b"\x01\x02\x03\x04\x05\x06"

        types = [dt for dt, _ in frame.data_items]
        assert BroadcastDataType.UNLINKED_BROADCAST_LINK in types
        assert BroadcastDataType.SYSTEM_MGMT_FRAME in types

    def test_build_frame_has_two_data_items(self):
        mgr = NonConnectedBroadcastManager()
        frame = mgr.build_non_connected_broadcast_frame()
        assert len(frame.data_items) == 2

    def test_frame_link_info_roundtrip(self):
        cfg = NonConnectedBroadcastConfig(
            transmission_type=1,
            service_adapt_mode=1,
            base_link_id=0x123456,
            frame_type=3,
            bandwidth=1,
            pilot_density=2,
            sdu_max=256,
            event_count=5,
        )
        mgr = NonConnectedBroadcastManager(config=cfg)
        frame = mgr.build_non_connected_broadcast_frame()

        for dt, data in frame.data_items:
            if dt == BroadcastDataType.UNLINKED_BROADCAST_LINK:
                info = NonLinkedBroadcastLinkInfo.unpack(data)
                assert info.transmission_type == 1
                assert info.service_adapt_mode == 1
                assert info.base_link_id == 0x123456
                assert info.frame_type == 3
                assert info.bandwidth == 1
                assert info.pilot_density == 2
                assert info.sdu_max == 256
                assert info.event_count == 5
                break
        else:
            raise AssertionError("UNLINKED_BROADCAST_LINK 未找到")

    def test_frame_smf_info_roundtrip(self):
        cfg = NonConnectedBroadcastConfig(
            smf_baseline_slot=100,
            smf_offset=500,
            smf_access_addr=0xABCDEF,
            smf_period=1600,
            smf_frame_type=3,
            smf_bandwidth=1,
            smf_pilot_density=2,
            smf_channel_table=b"\x00\x05\x0A\x0F",
        )
        mgr = NonConnectedBroadcastManager(config=cfg)
        frame = mgr.build_non_connected_broadcast_frame()

        for dt, data in frame.data_items:
            if dt == BroadcastDataType.SYSTEM_MGMT_FRAME:
                info = SystemMgmtFrameInfo.unpack(data)
                assert info.baseline_slot == 100
                assert info.offset == 500
                assert info.access_addr == 0xABCDEF
                assert info.period == 1600
                assert info.frame_type == 3
                assert info.bandwidth == 1
                assert info.pilot_density == 2
                assert info.channel_count == 4
                assert info.channel_table == b"\x00\x05\x0A\x0F"
                break
        else:
            raise AssertionError("SYSTEM_MGMT_FRAME 未找到")

    def test_encrypted_frame_includes_giv_gskd(self):
        giv = b"\xAA" * 8
        gskd = b"\xBB" * 16
        cfg = NonConnectedBroadcastConfig(
            encrypted=True,
            giv=giv,
            gskd=gskd,
        )
        mgr = NonConnectedBroadcastManager(config=cfg)
        frame = mgr.build_non_connected_broadcast_frame()

        for dt, data in frame.data_items:
            if dt == BroadcastDataType.UNLINKED_BROADCAST_LINK:
                info = NonLinkedBroadcastLinkInfo.unpack(data)
                assert info.giv == giv
                assert info.gskd == gskd
                break

    def test_unencrypted_frame_empty_giv_gskd(self):
        cfg = NonConnectedBroadcastConfig(encrypted=False)
        mgr = NonConnectedBroadcastManager(config=cfg)
        frame = mgr.build_non_connected_broadcast_frame()

        for dt, data in frame.data_items:
            if dt == BroadcastDataType.UNLINKED_BROADCAST_LINK:
                info = NonLinkedBroadcastLinkInfo.unpack(data)
                assert info.giv == b"\x00" * 8
                assert info.gskd == b"\x00" * 16
                break

    def test_5g_hop_map(self):
        hop_map = b"\xFF" * 25
        cfg = NonConnectedBroadcastConfig(is_5g=True, hop_map=hop_map)
        mgr = NonConnectedBroadcastManager(config=cfg)
        frame = mgr.build_non_connected_broadcast_frame()

        for dt, data in frame.data_items:
            if dt == BroadcastDataType.UNLINKED_BROADCAST_LINK:
                info = NonLinkedBroadcastLinkInfo.unpack(data, is_5g=True)
                assert len(info.hop_map) == 25
                break


class TestParseNonConnectedBroadcast:
    """解析非链接态广播帧测试。"""

    def _build_frame(self, **overrides) -> BroadcastFrame:
        cfg = NonConnectedBroadcastConfig(**overrides)
        mgr = NonConnectedBroadcastManager(
            config=cfg,
            local_address=b"\x11\x22\x33\x44\x55\x66",
        )
        return mgr.build_non_connected_broadcast_frame()

    def test_parse_success(self):
        frame = self._build_frame()
        result = parse_non_connected_broadcast(frame)
        assert result is not None
        assert isinstance(result, NonConnectedBroadcastResult)
        assert result.broadcaster_addr == b"\x11\x22\x33\x44\x55\x66"

    def test_parse_extracts_link_info(self):
        frame = self._build_frame(
            base_link_id=0xCAFE01,
            sdu_max=512,
        )
        result = parse_non_connected_broadcast(frame)
        assert result is not None
        assert result.link_info.base_link_id == 0xCAFE01
        assert result.link_info.sdu_max == 512

    def test_parse_extracts_smf_info(self):
        frame = self._build_frame(
            smf_period=2400,
            smf_access_addr=0x112233,
        )
        result = parse_non_connected_broadcast(frame)
        assert result is not None
        assert result.smf_info.period == 2400
        assert result.smf_info.access_addr == 0x112233

    def test_parse_returns_none_without_link_info(self):
        frame = BroadcastFrame(
            structure_indication=0x11,
            local_addr_type=0,
            peer_addr_type=0,
            local_addr=b"\x00" * 6,
            irk_id=0,
            peer_addr=b"\x00" * 6,
            data_items=[
                (BroadcastDataType.SYSTEM_MGMT_FRAME,
                 SystemMgmtFrameInfo(0, 0, 0, 0, 0, 0, 0, 0, b"").pack()),
            ],
        )
        assert parse_non_connected_broadcast(frame) is None

    def test_parse_returns_none_without_smf_info(self):
        link_info = NonLinkedBroadcastLinkInfo(
            transmission_type=0,
            service_adapt_mode=0,
        )
        frame = BroadcastFrame(
            structure_indication=0x11,
            local_addr_type=0,
            peer_addr_type=0,
            local_addr=b"\x00" * 6,
            irk_id=0,
            peer_addr=b"\x00" * 6,
            data_items=[
                (BroadcastDataType.UNLINKED_BROADCAST_LINK, link_info.pack()),
            ],
        )
        assert parse_non_connected_broadcast(frame) is None

    def test_parse_returns_none_for_empty_frame(self):
        frame = BroadcastFrame(
            structure_indication=0x11,
            local_addr_type=0,
            peer_addr_type=0,
            local_addr=b"\x00" * 6,
            irk_id=0,
            peer_addr=b"\x00" * 6,
            data_items=[],
        )
        assert parse_non_connected_broadcast(frame) is None


class TestNonConnectedBroadcastEndToEnd:
    """端到端流程测试。"""

    def test_build_serialize_parse(self):
        cfg = NonConnectedBroadcastConfig(
            transmission_type=1,
            base_link_id=0x0A0B0C,
            sdu_max=64,
            smf_period=400,
            smf_access_addr=0x112233,
        )
        mgr = NonConnectedBroadcastManager(
            config=cfg,
            local_address=b"\xAA\xBB\xCC\xDD\xEE\xFF",
        )

        frame = mgr.build_non_connected_broadcast_frame()
        raw = frame.pack()
        restored = BroadcastFrame.unpack(raw)
        result = parse_non_connected_broadcast(restored)

        assert result is not None
        assert result.broadcaster_addr == b"\xAA\xBB\xCC\xDD\xEE\xFF"
        assert result.link_info.transmission_type == 1
        assert result.link_info.base_link_id == 0x0A0B0C
        assert result.link_info.sdu_max == 64
        assert result.smf_info.period == 400
        assert result.smf_info.access_addr == 0x112233

    def test_encrypted_roundtrip(self):
        giv = bytes(range(8))
        gskd = bytes(range(16))
        cfg = NonConnectedBroadcastConfig(
            encrypted=True,
            giv=giv,
            gskd=gskd,
            base_link_id=0xDEAD01,
        )
        mgr = NonConnectedBroadcastManager(config=cfg)
        frame = mgr.build_non_connected_broadcast_frame()
        raw = frame.pack()
        restored = BroadcastFrame.unpack(raw)
        result = parse_non_connected_broadcast(restored)

        assert result is not None
        assert result.link_info.giv == giv
        assert result.link_info.gskd == gskd
        assert result.link_info.base_link_id == 0xDEAD01

    def test_sync_broadcast_params(self):
        cfg = NonConnectedBroadcastConfig(
            transmission_type=1,
            service_adapt_mode=0,
            event_group_period=320,
            event_period=80,
            event_count=4,
            sync_anchor_delay=100,
            sync_ref_delay=200,
        )
        mgr = NonConnectedBroadcastManager(config=cfg)
        frame = mgr.build_non_connected_broadcast_frame()
        result = parse_non_connected_broadcast(frame)

        assert result is not None
        assert result.link_info.transmission_type == 1
        assert result.link_info.event_group_period == 320
        assert result.link_info.event_period == 80
        assert result.link_info.event_count == 4
        assert result.link_info.sync_anchor_delay == 100
        assert result.link_info.sync_ref_delay == 200

    def test_multiple_channels(self):
        channels = bytes(range(20))
        cfg = NonConnectedBroadcastConfig(
            smf_channel_table=channels,
        )
        mgr = NonConnectedBroadcastManager(config=cfg)
        frame = mgr.build_non_connected_broadcast_frame()
        result = parse_non_connected_broadcast(frame)

        assert result is not None
        assert result.smf_info.channel_count == 20
        assert result.smf_info.channel_table == channels
