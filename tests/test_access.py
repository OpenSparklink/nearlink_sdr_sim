"""接入流程测试 -- TXS-10002-2025 标准 7.1.3。

验证广播方/发起方接入管理器和端到端接入流程。
"""

from __future__ import annotations

from nearlink_sdr.mac.access import (
    AccessConfig,
    AccessPhase,
    AccessWhitelist,
    BroadcasterAccessManager,
    DiscoveryManager,
    InitiatorAccessManager,
    negotiate_gt_role,
    run_access_procedure,
)
from nearlink_sdr.mac.broadcast import (
    AccessRequestInfo,
    AccessResponseType,
    BroadcastDataType,
    BroadcastFrame,
    DiscoveryAccessEntry,
    DiscoveryAccessResourceConfig,
    QueryRequestFilterInfo,
)
from nearlink_sdr.mac.link_manager import LinkState, Role

# -----------------------------------------------------------------------
# GT 角色协商
# -----------------------------------------------------------------------


class TestNegotiateGTRole:
    """GT 角色协商逻辑测试。"""

    def test_complementary_preferences(self):
        """双方偏好互补: 广播方=T, 发起方=G → 各取所好。"""
        result = negotiate_gt_role(
            broadcaster_pref=0, broadcaster_negotiable=True,
            initiator_pref=1, initiator_negotiable=True,
        )
        assert result.local_role == Role.G_NODE
        assert result.peer_role == Role.T_NODE
        assert result.negotiated is True

    def test_complementary_reversed(self):
        """双方偏好互补: 广播方=G, 发起方=T → 各取所好。"""
        result = negotiate_gt_role(
            broadcaster_pref=1, broadcaster_negotiable=True,
            initiator_pref=0, initiator_negotiable=True,
        )
        assert result.local_role == Role.T_NODE
        assert result.peer_role == Role.G_NODE

    def test_conflict_both_want_g_both_negotiable(self):
        """冲突: 双方都想 G, 广播方可协商 → 发起方保持 G。"""
        result = negotiate_gt_role(
            broadcaster_pref=1, broadcaster_negotiable=True,
            initiator_pref=1, initiator_negotiable=True,
        )
        assert result.local_role == Role.G_NODE
        assert result.peer_role == Role.T_NODE

    def test_conflict_both_want_t_both_negotiable(self):
        """冲突: 双方都想 T, 广播方可协商 → 发起方保持 T。"""
        result = negotiate_gt_role(
            broadcaster_pref=0, broadcaster_negotiable=True,
            initiator_pref=0, initiator_negotiable=True,
        )
        assert result.local_role == Role.T_NODE
        assert result.peer_role == Role.G_NODE

    def test_conflict_both_fixed(self):
        """冲突: 双方偏好相同且均不可协商 → 默认发起方=G。"""
        result = negotiate_gt_role(
            broadcaster_pref=1, broadcaster_negotiable=False,
            initiator_pref=1, initiator_negotiable=False,
        )
        assert result.local_role == Role.G_NODE
        assert result.peer_role == Role.T_NODE
        assert result.negotiated is False

    def test_conflict_initiator_flexible(self):
        """冲突: 双方都想 G，发起方可协商 → 广播方保持 G, 发起方让步。"""
        result = negotiate_gt_role(
            broadcaster_pref=1, broadcaster_negotiable=False,
            initiator_pref=1, initiator_negotiable=True,
        )
        assert result.local_role == Role.T_NODE  # 发起方让步
        assert result.peer_role == Role.G_NODE


# -----------------------------------------------------------------------
# 广播方接入管理器
# -----------------------------------------------------------------------


class TestBroadcasterAccessManager:
    """广播方接入管理器测试。"""

    ADDR = b"\x01\x02\x03\x04\x05\x06"

    def _make_mgr(self, **kwargs):
        config = AccessConfig(**kwargs)
        mgr = BroadcasterAccessManager(
            config=config,
            local_address=self.ADDR,
        )
        mgr.link_manager.process_event(
            __import__("nearlink_sdr.mac.link_manager", fromlist=["Event"])
            .Event(
                __import__("nearlink_sdr.mac.link_manager", fromlist=["EventType"])
                .EventType.START_BROADCAST
            )
        )
        return mgr

    def test_build_ext_adv_frame(self):
        """构造可接入扩展广播帧。"""
        mgr = self._make_mgr()
        frame = mgr.build_ext_adv_frame()
        assert isinstance(frame, BroadcastFrame)
        assert len(frame.data_items) >= 1
        data_types = [dt for dt, _ in frame.data_items]
        assert BroadcastDataType.DISCOVERY_ACCESS_RESOURCE in data_types
        assert mgr._phase == AccessPhase.ADV_SENDING

    def test_ext_adv_roundtrip(self):
        """广播帧可序列化/反序列化。"""
        mgr = self._make_mgr()
        frame = mgr.build_ext_adv_frame()
        packed = frame.pack()
        restored = BroadcastFrame.unpack(packed)
        assert len(restored.data_items) == len(frame.data_items)

    def test_handle_access_request_accept(self):
        """处理接入请求并接受。"""
        from nearlink_sdr.mac.broadcast import AccessRequestInfo

        mgr = self._make_mgr()
        mgr.build_ext_adv_frame()

        req = AccessRequestInfo(
            structure_indication=0x01,
            gt_role=0x00,  # 偏好 T 节点
        )
        resp_frame, accepted = mgr.handle_access_request(
            req.pack(), peer_address=b"\x0A" * 6,
        )
        assert accepted is True
        assert resp_frame is not None
        assert mgr.link_manager.state == LinkState.CONNECTED

    def test_reject_access_request(self):
        """拒绝接入请求。"""
        mgr = self._make_mgr()
        frame = mgr.reject_access_request(
            peer_address=b"\x0B" * 6,
            reason=AccessResponseType.RESOURCE_LIMITED,
        )
        assert isinstance(frame, BroadcastFrame)


# -----------------------------------------------------------------------
# 接入发起方管理器
# -----------------------------------------------------------------------


class TestInitiatorAccessManager:
    """接入发起方管理器测试。"""

    ADDR = b"\x0A\x0B\x0C\x0D\x0E\x0F"

    def _make_mgr(self, **kwargs):
        from nearlink_sdr.mac.link_manager import Event, EventType

        config = AccessConfig(**kwargs)
        mgr = InitiatorAccessManager(
            config=config,
            local_address=self.ADDR,
        )
        mgr.link_manager.process_event(
            Event(EventType.START_SCAN)
        )
        return mgr

    def _make_adv_frame(self):
        b_mgr = BroadcasterAccessManager(
            local_address=b"\x01" * 6,
        )
        return b_mgr.build_ext_adv_frame()

    def test_process_ext_adv(self):
        """解析扩展广播帧。"""
        mgr = self._make_mgr()
        frame = self._make_adv_frame()
        result = mgr.process_ext_adv(frame)
        assert result is True
        assert mgr.discovery_config is not None
        assert mgr.phase == AccessPhase.REQ_WINDOW

    def test_process_ext_adv_no_resource(self):
        """无接入资源配置的广播帧返回 False。"""
        mgr = self._make_mgr()
        frame = BroadcastFrame(
            structure_indication=0x00,
            local_addr_type=0,
            peer_addr_type=0,
            local_addr=b"\x00" * 6,
            irk_id=0,
            peer_addr=b"\x00" * 6,
            data_items=[],
        )
        result = mgr.process_ext_adv(frame)
        assert result is False

    def test_build_access_request(self):
        """构造接入请求。"""
        mgr = self._make_mgr()
        frame = self._make_adv_frame()
        mgr.process_ext_adv(frame)
        req_data = mgr.build_access_request()
        assert isinstance(req_data, bytes)
        assert len(req_data) > 0
        assert mgr.link_manager.state == LinkState.ACCESSING

    def test_handle_accept_response(self):
        """处理接受响应。"""
        from nearlink_sdr.mac.broadcast import (
            AccessBasicInfo,
            AccessResponseEntry,
            AccessResponseInfo,
        )

        mgr = self._make_mgr()
        frame = self._make_adv_frame()
        mgr.process_ext_adv(frame)
        mgr.build_access_request()

        # 构造响应帧
        resp_entry = AccessResponseEntry(
            peer_addr=b"\x01" * 6,
            response_type=AccessResponseType.ACCEPT,
            peer_addr_type=0,
            repeat_indication=0,
        )
        resp_info = AccessResponseInfo(
            entries=[resp_entry],
        )
        access_basic = AccessBasicInfo(
            smf_baseline_slot=100,
            smf_offset=300,
            smf_link_id=1,
            smf_period=800,
            smf_frame_type=2,
            smf_bandwidth=0,
            smf_pilot_density=0,
            access_link_id=1,
            access_period=40,
            access_timeout=50,
            sleep_clock_accuracy=7,
            access_crc_type=0,
            access_crc_init=0,
            hop_map=b"\xFF" * 10,
            smf_channel_count=3,
            smf_channel_table=b"\x00\x01\x02",
        )
        resp_frame = BroadcastFrame(
            structure_indication=0x10,
            local_addr_type=0,
            peer_addr_type=0,
            local_addr=b"\x00" * 6,
            irk_id=0,
            peer_addr=b"\x00" * 6,
            data_items=[
                (BroadcastDataType.ACCESS_RESPONSE, resp_info.pack()),
                (BroadcastDataType.ACCESS_BASIC, access_basic.pack()),
            ],
        )

        role, _params = mgr.handle_access_response(resp_frame.pack())
        assert role == Role.T_NODE  # 对端携带 AccessBasicInfo → 对端是 G
        assert mgr.link_manager.state == LinkState.CONNECTED
        assert "smf_baseline_slot" in _params

    def test_handle_reject_response(self):
        """处理拒绝响应。"""
        from nearlink_sdr.mac.broadcast import (
            AccessResponseEntry,
            AccessResponseInfo,
        )

        mgr = self._make_mgr()
        frame = self._make_adv_frame()
        mgr.process_ext_adv(frame)
        mgr.build_access_request()

        resp_entry = AccessResponseEntry(
            peer_addr=b"\x01" * 6,
            response_type=AccessResponseType.USER_REJECT,
            peer_addr_type=0,
            repeat_indication=0,
        )
        resp_info = AccessResponseInfo(
            entries=[resp_entry],
        )
        resp_frame = BroadcastFrame(
            structure_indication=0x10,
            local_addr_type=0,
            peer_addr_type=0,
            local_addr=b"\x00" * 6,
            irk_id=0,
            peer_addr=b"\x00" * 6,
            data_items=[
                (BroadcastDataType.ACCESS_RESPONSE, resp_info.pack()),
            ],
        )

        role, _params = mgr.handle_access_response(resp_frame.pack())
        assert role is None
        assert mgr.link_manager.state == LinkState.SCANNING
        assert mgr.can_retry is True

    def test_retry_limit(self):
        """重试次数达到上限。"""
        from nearlink_sdr.mac.broadcast import (
            AccessResponseEntry,
            AccessResponseInfo,
        )

        mgr = self._make_mgr(max_retries=2)
        frame = self._make_adv_frame()

        for _i in range(2):
            mgr.process_ext_adv(frame)
            mgr.build_access_request()

            resp_entry = AccessResponseEntry(
                peer_addr=b"\x01" * 6,
                response_type=AccessResponseType.USER_REJECT,
                peer_addr_type=0,
                repeat_indication=0,
            )
            resp_info = AccessResponseInfo(
                entries=[resp_entry],
            )
            resp_frame = BroadcastFrame(
                structure_indication=0x10,
                local_addr_type=0,
                peer_addr_type=0,
                local_addr=b"\x00" * 6,
                irk_id=0,
                peer_addr=b"\x00" * 6,
                data_items=[
                    (BroadcastDataType.ACCESS_RESPONSE, resp_info.pack()),
                ],
            )
            mgr.handle_access_response(resp_frame.pack())

        assert mgr.can_retry is False


# -----------------------------------------------------------------------
# 端到端接入流程
# -----------------------------------------------------------------------


class TestAccessProcedure:
    """端到端接入流程测试。"""

    def test_default_procedure(self):
        """默认配置端到端接入。"""
        b_mgr, i_mgr = run_access_procedure()
        assert b_mgr.link_manager.state == LinkState.CONNECTED
        assert i_mgr.link_manager.state == LinkState.CONNECTED

    def test_roles_assigned(self):
        """角色正确分配。"""
        b_mgr, i_mgr = run_access_procedure()
        # 双方角色互补
        roles = {b_mgr.link_manager.role, i_mgr.link_manager.role}
        assert Role.G_NODE in roles
        assert Role.T_NODE in roles

    def test_initiator_wants_g(self):
        """发起方偏好 G 节点。"""
        i_config = AccessConfig(gt_preference=1)
        _b_mgr, i_mgr = run_access_procedure(
            initiator_config=i_config,
        )
        assert i_mgr.link_manager.state == LinkState.CONNECTED

    def test_broadcaster_wants_g(self):
        """广播方偏好 G 节点。"""
        b_config = AccessConfig(gt_preference=1)
        b_mgr, _i_mgr = run_access_procedure(
            broadcaster_config=b_config,
        )
        assert b_mgr.link_manager.state == LinkState.CONNECTED

    def test_both_want_g(self):
        """双方都偏好 G, 冲突协商。"""
        b_config = AccessConfig(gt_preference=1)
        i_config = AccessConfig(gt_preference=1)
        b_mgr, i_mgr = run_access_procedure(
            broadcaster_config=b_config,
            initiator_config=i_config,
        )
        assert b_mgr.link_manager.state == LinkState.CONNECTED
        assert i_mgr.link_manager.state == LinkState.CONNECTED

    def test_custom_addresses(self):
        """自定义 MAC 地址。"""
        b_addr = b"\xAA\xBB\xCC\xDD\xEE\xFF"
        i_addr = b"\x11\x22\x33\x44\x55\x66"
        b_mgr, i_mgr = run_access_procedure(
            broadcaster_addr=b_addr,
            initiator_addr=i_addr,
        )
        assert b_mgr.local_address == b_addr
        assert i_mgr.local_address == i_addr

    def test_no_smf_mode(self):
        """不使用系统管理帧模式。"""
        b_mgr, i_mgr = run_access_procedure(
            broadcaster_use_smf=False,
        )
        assert b_mgr.link_manager.state == LinkState.CONNECTED
        assert i_mgr.link_manager.state == LinkState.CONNECTED

    def test_event_log_records(self):
        """事件日志记录完整。"""
        b_mgr, i_mgr = run_access_procedure()
        # 广播方: IDLE→BROADCASTING→CONNECTED
        b_log = b_mgr.link_manager.event_log
        assert len(b_log) >= 2

        # 发起方: IDLE→SCANNING→ACCESSING→CONNECTED
        i_log = i_mgr.link_manager.event_log
        assert len(i_log) >= 3


# -----------------------------------------------------------------------
# 接入白名单 (7.1.6)
# -----------------------------------------------------------------------

class TestAccessWhitelist:
    """白名单功能测试。"""

    def test_disabled_allows_all(self):
        wl = AccessWhitelist()
        assert wl.check(b"\x01\x02\x03\x04\x05\x06") is True
        assert wl.check(b"\xFF" * 6) is True

    def test_enabled_empty_blocks_all(self):
        wl = AccessWhitelist(enabled=True)
        assert wl.check(b"\x01\x02\x03\x04\x05\x06") is False

    def test_add_and_check(self):
        wl = AccessWhitelist(enabled=True)
        addr = b"\x01\x02\x03\x04\x05\x06"
        wl.add(addr)
        assert wl.check(addr) is True
        assert wl.check(b"\xFF" * 6) is False

    def test_remove(self):
        wl = AccessWhitelist(enabled=True)
        addr = b"\x01\x02\x03\x04\x05\x06"
        wl.add(addr)
        wl.remove(addr)
        assert wl.check(addr) is False

    def test_clear(self):
        wl = AccessWhitelist(enabled=True)
        wl.add(b"\x01" * 6)
        wl.add(b"\x02" * 6)
        wl.clear()
        assert wl.addresses == []

    def test_contains(self):
        wl = AccessWhitelist()
        addr = b"\xAA\xBB\xCC\xDD\xEE\xFF"
        wl.add(addr)
        assert wl.contains(addr) is True
        assert wl.contains(b"\x00" * 6) is False

    def test_addresses_sorted(self):
        wl = AccessWhitelist()
        wl.add(b"\x02" * 6)
        wl.add(b"\x01" * 6)
        assert wl.addresses == [b"\x01" * 6, b"\x02" * 6]

    def test_truncates_to_6_bytes(self):
        wl = AccessWhitelist(enabled=True)
        long_addr = b"\x01\x02\x03\x04\x05\x06\x07\x08"
        wl.add(long_addr)
        assert wl.contains(b"\x01\x02\x03\x04\x05\x06") is True

    def test_broadcaster_whitelist_rejects(self):
        """广播方白名单拒绝非白名单地址的接入请求。"""
        mgr = BroadcasterAccessManager(local_address=b"\xAA" * 6)
        mgr.whitelist.enabled = True
        mgr.whitelist.add(b"\x11" * 6)
        req_info = AccessRequestInfo(structure_indication=0x00)
        resp, accepted = mgr.handle_access_request(
            req_info.pack(), b"\x22" * 6,
        )
        assert accepted is False
        assert resp is None

    def test_broadcaster_whitelist_accepts(self):
        """广播方白名单接受白名单内地址。"""
        mgr = BroadcasterAccessManager(local_address=b"\xAA" * 6)
        mgr.whitelist.enabled = True
        mgr.whitelist.add(b"\x22" * 6)
        req_info = AccessRequestInfo(structure_indication=0x00)
        _resp, accepted = mgr.handle_access_request(
            req_info.pack(), b"\x22" * 6,
        )
        assert accepted is True


# -----------------------------------------------------------------------
# 发现流程 (7.1.2)
# -----------------------------------------------------------------------

class TestDiscoveryManager:
    """发现流程测试。"""

    def _make_queryable_frame(
        self, addr: bytes = b"\x01\x02\x03\x04\x05\x06",
    ) -> BroadcastFrame:
        """构造一个包含可查询发现接入资源配置的广播帧。"""
        config = DiscoveryAccessResourceConfig(
            request_offset=600,
            request_max_length=64,
            response_offset=1200,
            gt_negotiation=0,
            entry_count=1,
            entries=[
                DiscoveryAccessEntry(
                    request_type=1,  # 可查询
                    carry_info_indication=0,
                    peer_addr_type=0,
                    addr_present=0,
                    peer_addr=b"",
                ),
            ],
        )
        return BroadcastFrame(
            structure_indication=0x10,
            local_addr_type=0,
            peer_addr_type=0,
            local_addr=addr,
            irk_id=0,
            peer_addr=b"\x00" * 6,
            data_items=[
                (BroadcastDataType.DISCOVERY_ACCESS_RESOURCE,
                 config.pack()),
            ],
        )

    def test_broadcast_received_queryable(self):
        mgr = DiscoveryManager(local_address=b"\xAA" * 6)
        frame = self._make_queryable_frame()
        assert mgr.on_broadcast_received(frame) is True
        assert frame.local_addr in mgr.discovered_devices

    def test_broadcast_received_not_queryable(self):
        mgr = DiscoveryManager()
        frame = BroadcastFrame(
            structure_indication=0x00,
            local_addr_type=0,
            peer_addr_type=0,
            local_addr=b"\x01" * 6,
            irk_id=0, peer_addr=b"\x00" * 6,
            data_items=[],
        )
        assert mgr.on_broadcast_received(frame) is False

    def test_whitelist_blocks(self):
        mgr = DiscoveryManager()
        mgr.whitelist.enabled = True
        frame = self._make_queryable_frame()
        assert mgr.on_broadcast_received(frame) is False

    def test_build_query_request(self):
        mgr = DiscoveryManager(local_address=b"\xAA" * 6)
        req = mgr.build_query_request(
            target_addr=b"\x01" * 6,
            upper_layer_data=b"\x42",
        )
        assert req.local_addr == b"\xAA" * 6
        assert req.peer_addr == b"\x01" * 6
        assert len(req.data_items) == 1

    def test_build_query_request_with_filter(self):
        mgr = DiscoveryManager(local_address=b"\xBB" * 6)
        filter_info = QueryRequestFilterInfo(
            uuid_16_list=[0x1234],
        )
        req = mgr.build_query_request(
            target_addr=b"\x01" * 6,
            filter_info=filter_info,
        )
        assert len(req.data_items) == 1
        assert req.data_items[0][0] == BroadcastDataType.QUERY_REQUEST_FILTER

    def test_handle_query_response(self):
        mgr = DiscoveryManager()
        broadcast_frame = self._make_queryable_frame()
        mgr.on_broadcast_received(broadcast_frame)

        response = BroadcastFrame(
            structure_indication=0x10,
            local_addr_type=0, peer_addr_type=0,
            local_addr=broadcast_frame.local_addr,
            irk_id=0, peer_addr=b"\x00" * 6,
            data_items=[(BroadcastDataType.UPPER_LAYER_DATA, b"\x99")],
        )
        assert mgr.handle_query_response(response) is True
        _, resp = mgr.discovered_devices[broadcast_frame.local_addr]
        assert resp is not None

    def test_handle_query_request_and_response(self):
        """广播设备端处理查询请求。"""
        b_mgr = DiscoveryManager(local_address=b"\x01" * 6)
        d_mgr = DiscoveryManager(local_address=b"\x02" * 6)

        # 发现设备收到广播帧
        adv_frame = self._make_queryable_frame(addr=b"\x01" * 6)
        d_mgr.on_broadcast_received(adv_frame)

        # 发现设备构造查询请求
        query_req = d_mgr.build_query_request(b"\x01" * 6)

        # 广播设备处理查询请求并返回响应
        query_resp = b_mgr.handle_query_request(
            query_req, all_services_data=b"\xAB\xCD",
        )
        assert query_resp.local_addr == b"\x01" * 6

        # 发现设备收到响应
        assert d_mgr.handle_query_response(query_resp) is True

    def test_clear(self):
        mgr = DiscoveryManager()
        frame = self._make_queryable_frame()
        mgr.on_broadcast_received(frame)
        assert len(mgr.discovered_devices) == 1
        mgr.clear()
        assert len(mgr.discovered_devices) == 0
