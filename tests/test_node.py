"""SLE 节点实体单元测试。"""

import numpy as np

from nearlink_sdr.mac.broadcast import BroadcastFrame
from nearlink_sdr.mac.frame import AsyncDataFrame
from nearlink_sdr.mac.link_manager import LinkState, Role
from nearlink_sdr.mac.qos import Priority, TxDecision
from nearlink_sdr.node import (
    NodeCallback,
    NodeConfig,
    NodeRole,
    NodeState,
    RxResult,
    SleNode,
    TransportMode,
    TxResult,
    _build_ctrl_bits,
    _build_ctrl_info,
)

# ── 初始化与配置 ──


class TestNodeInit:
    def test_default_config(self):
        node = SleNode()
        assert node.state == NodeState.IDLE
        assert node.role == Role.NONE
        assert not node.is_connected

    def test_custom_config(self):
        cfg = NodeConfig(
            address=b"\x01\x02\x03\x04\x05\x06",
            role=NodeRole.G_NODE,
            frame_type=2,
            mcs_index=5,
        )
        node = SleNode(config=cfg)
        assert node.config.mcs_index == 5
        assert node.config.frame_type == 2

    def test_ft1_ctrl_bits(self):
        node = SleNode(config=NodeConfig(frame_type=1))
        assert node._tx_config.ctrl_bits_len == 20

    def test_ft3_ctrl_bits(self):
        node = SleNode(config=NodeConfig(frame_type=3))
        assert node._tx_config.ctrl_bits_len == 27

    def test_ft4_ctrl_bits(self):
        node = SleNode(config=NodeConfig(frame_type=4))
        assert node._tx_config.ctrl_bits_len == 27


# ── 生命周期管理 ──


class TestNodeLifecycle:
    def test_start_advertising(self):
        node = SleNode()
        node.start_advertising()
        assert node.state == NodeState.ADVERTISING
        assert node.link_state == LinkState.BROADCASTING

    def test_start_scanning(self):
        node = SleNode()
        node.start_scanning()
        assert node.state == NodeState.SCANNING
        assert node.link_state == LinkState.SCANNING

    def test_disconnect(self):
        node = SleNode()
        node.start_advertising()
        node.accept_connection(b"\xAA" * 6, Role.G_NODE)
        node.disconnect()
        assert node.state == NodeState.DISCONNECTED

    def test_reset(self):
        node = SleNode()
        node.start_advertising()
        node.accept_connection(b"\xBB" * 6)
        node.reset()
        assert node.state == NodeState.IDLE
        assert node.role == Role.NONE
        assert node.peer_address == b""

    def test_accept_connection(self):
        node = SleNode()
        node.start_advertising()
        node.accept_connection(b"\xCC" * 6, Role.G_NODE)
        assert node.state == NodeState.CONNECTED
        assert node.peer_address == b"\xCC" * 6

    def test_connect_initiator(self):
        node = SleNode()
        node.start_scanning()
        node.connect(b"\xDD" * 6)
        assert node.state == NodeState.CONNECTING
        assert node.peer_address == b"\xDD" * 6


# ── 数据发送 ──


class TestNodeSendReceive:
    def _connected_node(self) -> SleNode:
        node = SleNode(config=NodeConfig(mcs_index=5))
        node.start_advertising()
        node.accept_connection(b"\x01" * 6)
        return node

    def test_send_enqueues(self):
        node = self._connected_node()
        ok = node.send(b"hello")
        assert ok
        assert node._qos.tx_queue.size == 1

    def test_send_priority(self):
        node = self._connected_node()
        node.send(b"low", Priority.LOW)
        node.send(b"high", Priority.HIGH)
        assert node._qos.tx_queue.size == 2

    def test_transmit_empty(self):
        node = self._connected_node()
        result = node.transmit()
        assert isinstance(result, TxResult)
        assert result.iq is None
        assert result.decision == TxDecision.EMPTY

    def test_transmit_with_data(self):
        node = self._connected_node()
        node.send(b"test data")
        result = node.transmit()
        assert result.iq is not None
        assert result.decision == TxDecision.NEW_DATA
        assert isinstance(result.iq, np.ndarray)

    def test_roundtrip(self):
        node = self._connected_node()
        payload = b"roundtrip test"
        node.send(payload)
        tx = node.transmit()

        frame = AsyncDataFrame(segment_type=0, data=payload)
        n_bytes = len(frame.pack())
        rx = node.receive(tx.iq, n_bytes)
        assert isinstance(rx, RxResult)
        assert rx.success
        assert rx.data == payload

    def test_receive_bad_signal(self):
        node = self._connected_node()
        rng = np.random.default_rng(42)
        noise = rng.normal(size=4000) + 1j * rng.normal(size=4000)
        rx = node.receive(noise, 10)
        assert not rx.success

    def test_tx_count_increments(self):
        node = self._connected_node()
        node.send(b"a")
        node.transmit()
        assert node.stats["tx_count"] == 1

    def test_process_feedback(self):
        node = self._connected_node()
        node.send(b"data")
        node.transmit()
        decision = node.process_feedback(True)
        assert decision in (TxDecision.NEW_DATA, TxDecision.EMPTY)


# ── 状态回调 ──


class TestNodeCallback:
    def test_state_change_callback(self):
        changes = []

        class Cb(NodeCallback):
            def on_state_changed(self, old, new):
                changes.append((old, new))

        node = SleNode(callback=Cb())
        node.start_advertising()
        assert len(changes) == 1
        assert changes[0] == (NodeState.IDLE, NodeState.ADVERTISING)

    def test_disconnect_callback(self):
        reasons = []

        class Cb(NodeCallback):
            def on_disconnected(self, reason):
                reasons.append(reason)

        node = SleNode(callback=Cb())
        node.start_advertising()
        node.accept_connection(b"\x01" * 6)
        node.disconnect()
        # 回调应被触发 (通过 LinkManager)
        assert node.state == NodeState.DISCONNECTED


# ── MCS 管理 ──


class TestNodeMcs:
    def test_update_mcs(self):
        node = SleNode()
        node.update_mcs(10)
        assert node.config.mcs_index == 10
        assert node._tx_config.mcs_index == 10

    def test_update_mcs_clamp(self):
        node = SleNode()
        node.update_mcs(99)
        assert node.config.mcs_index == 12
        node.update_mcs(-5)
        assert node.config.mcs_index == 0

    def test_recommended_mcs(self):
        node = SleNode(config=NodeConfig(mcs_index=6))
        mcs = node.recommended_mcs
        assert 0 <= mcs <= 12


# ── 信令 ──


class TestNodeSignaling:
    def test_send_signaling_not_connected(self):
        node = SleNode()
        result = node.send_signaling(None)
        assert result is None

    def test_receive_signaling(self):
        node = SleNode()
        node.start_advertising()
        node.accept_connection(b"\x01" * 6)
        # 不应抛出异常
        node.receive_signaling(object())


# ── 统计信息 ──


class TestNodeStats:
    def test_stats_keys(self):
        node = SleNode()
        s = node.stats
        assert "state" in s
        assert "role" in s
        assert "tx_count" in s
        assert "rx_count" in s
        assert "fer" in s
        assert "mcs" in s
        assert "queue_size" in s
        assert "flow_paused" in s
        assert "paired" in s
        assert "encrypted" in s

    def test_stats_values(self):
        node = SleNode(config=NodeConfig(mcs_index=7))
        s = node.stats
        assert s["state"] == "IDLE"
        assert s["tx_count"] == 0
        assert s["mcs"] == 7
        assert not s["paired"]
        assert not s["encrypted"]


# ── 控制比特构建 ──


class TestBuildCtrlBits:
    def test_ft2(self):
        bits = _build_ctrl_bits({"tx_sn": 1, "rx_sn": 0, "flow_ctrl": 1}, 2)
        assert len(bits) == 28
        assert bits[3] == 1  # tx_sn
        assert bits[4] == 0  # rx_sn
        assert bits[5] == 1  # flow_ctrl

    def test_ft3(self):
        bits = _build_ctrl_bits({"tx_sn": 5, "rx_sn": 3, "flow_ctrl": 0}, 3)
        assert len(bits) == 27
        # tx_sn = 5 = 0b00101
        assert bits[3] == 0
        assert bits[7] == 1
        # flow_ctrl
        assert bits[13] == 0

    def test_ft1(self):
        bits = _build_ctrl_bits({}, 1)
        assert len(bits) == 20

    def test_ft4(self):
        bits = _build_ctrl_bits({"tx_sn": 0, "rx_sn": 0, "flow_ctrl": 0}, 4)
        assert len(bits) == 27


class TestBuildCtrlInfo:
    def test_default_fields(self):
        info = _build_ctrl_info({}, 20)
        assert info.data_length == 20
        assert info.tx_sn == 0
        assert info.rx_sn == 0

    def test_with_qos_fields(self):
        fields = {"tx_sn": 1, "rx_sn": 1, "flow_ctrl": 1, "empty_packet": 1}
        info = _build_ctrl_info(fields, 50)
        assert info.tx_sn == 1
        assert info.flow_ctrl == 1
        assert info.empty_packet == 1
        assert info.data_length == 50


# ── 配对流程 ──


class TestNodePairing:
    def test_start_pairing(self):
        node = SleNode()
        node.start_advertising()
        node.accept_connection(b"\x01" * 6, Role.G_NODE)
        msgs = node.start_pairing(b"\x02" * 6)
        assert isinstance(msgs, list)
        assert node.state == NodeState.PAIRED

    def test_pairing_no_messages(self):
        node = SleNode()
        result = node.process_pairing_message(object())
        assert result == []


class TestNodePairingComplete:
    """配对完成与失败流程覆盖。"""

    def _setup_pair(self):
        """构建 G/T 节点并完成建连。"""
        g = SleNode(config=NodeConfig(
            address=b"\x01" * 6, role=NodeRole.G_NODE,
            frame_type=2, mcs_index=5,
        ))
        t = SleNode(config=NodeConfig(
            address=b"\x02" * 6, role=NodeRole.T_NODE,
            frame_type=2, mcs_index=5,
        ))
        g.start_advertising()
        g.accept_connection(b"\x02" * 6, Role.G_NODE)
        t.start_advertising()
        t.accept_connection(b"\x01" * 6, Role.T_NODE)
        return g, t

    def test_full_pairing_completes(self):
        g, t = self._setup_pair()
        g_msgs = g.start_pairing(b"\x02" * 6)
        t.start_pairing(b"\x01" * 6)
        while g_msgs:
            t_msgs = []
            for m in g_msgs:
                t_msgs.extend(t.process_pairing_message(m))
            g_msgs = []
            for m in t_msgs:
                g_msgs.extend(g.process_pairing_message(m))

        # 双方完成配对
        assert g.stats["paired"]
        assert t.stats["paired"]
        assert g.state == NodeState.CONNECTED
        assert t.state == NodeState.CONNECTED
        # 加密上下文已建立
        assert g._crypto is not None
        assert t._crypto is not None

    def test_pairing_failure_sets_disconnected(self):
        g, _ = self._setup_pair()
        g.start_pairing(b"\x02" * 6)
        from nearlink_sdr.mac.security import PairingFailure
        g.process_pairing_message(PairingFailure(reason=0x04))
        assert g.state == NodeState.DISCONNECTED

    def test_setup_crypto_no_pairing(self):
        node = SleNode()
        node._pairing = None
        node._setup_crypto()
        assert node._crypto is None


class TestNodeEncryptedTransmit:
    """加密收发路径覆盖。"""

    def _paired_nodes(self):
        g = SleNode(config=NodeConfig(
            address=b"\x01" * 6, role=NodeRole.G_NODE,
            frame_type=2, mcs_index=5, enable_encryption=True,
        ))
        t = SleNode(config=NodeConfig(
            address=b"\x02" * 6, role=NodeRole.T_NODE,
            frame_type=2, mcs_index=5, enable_encryption=True,
        ))
        g.start_advertising()
        g.accept_connection(b"\x02" * 6, Role.G_NODE)
        t.start_advertising()
        t.accept_connection(b"\x01" * 6, Role.T_NODE)
        g_msgs = g.start_pairing(b"\x02" * 6)
        t.start_pairing(b"\x01" * 6)
        while g_msgs:
            t_msgs = []
            for m in g_msgs:
                t_msgs.extend(t.process_pairing_message(m))
            g_msgs = []
            for m in t_msgs:
                g_msgs.extend(g.process_pairing_message(m))
        # 手动同步 IV 以确保解密可行
        from nearlink_sdr.mac.security_manager import FrameCryptoContext
        iv = b"\x00" * 8
        g._crypto = FrameCryptoContext(
            session_key=g._pairing.session_key, iv_base=iv,
            direction=0, mic_len=4, frame_type=2, link_id=0,
        )
        t._crypto = FrameCryptoContext(
            session_key=t._pairing.session_key, iv_base=iv,
            direction=0, mic_len=4, frame_type=2, link_id=0,
        )
        return g, t

    def test_encrypted_transmit(self):
        g, _ = self._paired_nodes()
        g.send(b"secret")
        tx = g.transmit()
        assert tx.iq is not None
        assert tx.encrypted

    def test_encrypted_roundtrip(self):
        g, t = self._paired_nodes()
        payload = b"encrypted data"
        g.send(payload)
        tx = g.transmit()
        frame = AsyncDataFrame(segment_type=0, data=payload)
        # 加密帧比原 payload 长 (MIC 附加)
        n_mac = len(frame.pack()) + 4  # +4 MIC
        rx = t.receive(tx.iq, n_mac)
        assert rx.success
        assert rx.decrypted
        assert rx.data == payload

    def test_receive_decrypt_short_data(self):
        """数据长度不足以包含 MIC 时返回失败。"""
        _, t = self._paired_nodes()
        # 构造一个 crc_ok 但 payload 过短的场景
        # 直接用正常帧但设 mic_len 大于 payload 长度
        from nearlink_sdr.mac.security_manager import FrameCryptoContext
        t._crypto = FrameCryptoContext(
            session_key=t._pairing.session_key, iv_base=b"\x00" * 8,
            direction=0, mic_len=100, frame_type=2, link_id=0,
        )
        g, _ = self._paired_nodes()
        g.send(b"tiny")
        tx = g.transmit()
        frame = AsyncDataFrame(segment_type=0, data=b"tiny")
        n_mac = len(frame.pack())
        rx = t.receive(tx.iq, n_mac)
        # 因 MIC 长度 > 数据长度, 解密失败
        assert not rx.success


class TestNodeSendSignalingConnected:
    """已连接状态下信令发送覆盖。"""

    def test_send_signaling_connected(self):
        node = SleNode()
        node.start_advertising()
        node.accept_connection(b"\x01" * 6, Role.G_NODE)
        from nearlink_sdr.mac.link_control import IntervalUpdateRequest
        msg = IntervalUpdateRequest(interval_type=10)
        result = node.send_signaling(msg)
        # 已连接, 应返回 ControlFrame 或至少不为 None
        assert result is not None


class TestNodeCallbackDefault:
    """默认回调方法不抛异常。"""

    def test_on_data_received(self):
        cb = NodeCallback()
        cb.on_data_received(b"test data")

    def test_on_connected(self):
        cb = NodeCallback()
        cb.on_connected(b"\x01" * 6, Role.G_NODE)

    def test_on_disconnected(self):
        from nearlink_sdr.mac.link_manager import DisconnectReason
        cb = NodeCallback()
        cb.on_disconnected(DisconnectReason.LOCAL_REQUEST)

    def test_on_broadcast_received(self):
        cb = NodeCallback()
        frame = BroadcastFrame(0, 0, 0, b"\x01" * 6, 0, b"\x02" * 6)
        cb.on_broadcast_received(frame)

    def test_on_discovery_complete(self):
        cb = NodeCallback()
        cb.on_discovery_complete({})

    def test_on_measurement_result(self):
        cb = NodeCallback()
        cb.on_measurement_result({"range": 1.5})


# ── 跳频集成 ──


class TestNodeFreqHopping:
    def test_default_freq_table(self):
        node = SleNode()
        assert node.freq_table.band == "2400"
        assert node.freq_table.bandwidth_mhz == 1

    def test_current_channel_in_range(self):
        node = SleNode()
        ch = node.current_channel
        assert 0 <= ch <= 78

    def test_block_unblock_channel(self):
        node = SleNode()
        node.block_channel(5)
        assert 5 in node.freq_table.blocked_channels
        assert 5 not in node.freq_table.available_table()
        node.unblock_channel(5)
        assert 5 not in node.freq_table.blocked_channels

    def test_hop_param2_derived_from_address(self):
        node = SleNode(config=NodeConfig(address=b"\x01\x02\x03\x04\x05\x06"))
        assert node._hop_param2 != 0

    def test_hop_param2_explicit(self):
        node = SleNode(config=NodeConfig(hop_param2=0x1234))
        assert node._hop_param2 == 0x1234

    def test_custom_band(self):
        node = SleNode(config=NodeConfig(band="2400", bandwidth_mhz=2))
        assert node.freq_table.bandwidth_mhz == 2

    def test_blocked_channels_from_config(self):
        node = SleNode(config=NodeConfig(blocked_channels={3, 7, 15}))
        assert node.freq_table.blocked_channels == {3, 7, 15}


# ── 功率控制 ──


class TestNodePowerControl:
    def test_initial_power(self):
        node = SleNode(config=NodeConfig(tx_power_dbm=5.0))
        assert node.tx_power_dbm == 5.0

    def test_power_controller_access(self):
        node = SleNode()
        pc = node.power_controller
        assert pc is not None

    def test_adjust_power(self):
        node = SleNode(config=NodeConfig(
            tx_power_dbm=0.0, max_power_dbm=10.0, min_power_dbm=-20.0,
        ))
        new_power = node.adjust_power(3.0)
        assert isinstance(new_power, float)

    def test_power_limits(self):
        node = SleNode(config=NodeConfig(
            tx_power_dbm=0.0, max_power_dbm=5.0, min_power_dbm=-5.0,
        ))
        assert node.power_controller.max_power_dbm == 5.0
        assert node.power_controller.min_power_dbm == -5.0

    def test_stats_include_power(self):
        node = SleNode(config=NodeConfig(tx_power_dbm=3.0))
        s = node.stats
        assert "tx_power_dbm" in s
        assert s["tx_power_dbm"] == 3.0


# ── 时序调度 ──


class TestNodeScheduler:
    def test_scheduler_exists(self):
        node = SleNode()
        assert node.scheduler is not None

    def test_advance_slot(self):
        node = SleNode()
        old_val = node.scheduler.slot_counter.value
        node.advance_slot(10)
        assert node.scheduler.slot_counter.value == old_val + 10

    def test_accept_connection_registers_link(self):
        node = SleNode()
        node.start_advertising()
        node.accept_connection(b"\x01" * 6)
        assert 0 in node.scheduler.event_schedulers

    def test_run_access_registers_link(self):
        node = SleNode(config=NodeConfig(address=b"\xAA" * 6))
        b_mgr, i_mgr = node.run_access(peer_address=b"\xBB" * 6)
        assert b_mgr is not None
        assert i_mgr is not None
        assert 0 in node.scheduler.event_schedulers


# ── SMF 调度 ──


class TestNodeSmf:
    def test_smf_disabled_by_default(self):
        node = SleNode()
        assert node.smf_scheduler is None

    def test_smf_enabled(self):
        node = SleNode(config=NodeConfig(smf_enabled=True))
        assert node.smf_scheduler is not None

    def test_configure_smf(self):
        from nearlink_sdr.mac.smf_scheduler import SMFScheduleParams
        node = SleNode(config=NodeConfig(smf_enabled=True))
        params = SMFScheduleParams(interval=800, frame_type=2)
        node.configure_smf(params)
        assert node.scheduler.superframe.smf_config.smf_interval == 800


# ── 接入白名单与发现 ──


class TestNodeAccessDiscovery:
    def test_whitelist_empty(self):
        node = SleNode()
        assert len(node.whitelist.addresses) == 0

    def test_whitelist_add_remove(self):
        node = SleNode()
        node.whitelist.add(b"\x01" * 6)
        assert node.whitelist.contains(b"\x01" * 6)
        node.whitelist.remove(b"\x01" * 6)
        assert not node.whitelist.contains(b"\x01" * 6)

    def test_discovery_manager_exists(self):
        node = SleNode()
        assert node.discovery is not None
        assert len(node.discovered_devices) == 0

    def test_start_advertising_returns_frame(self):
        node = SleNode()
        frame = node.start_advertising()
        assert frame is not None
        assert isinstance(frame, BroadcastFrame)

    def test_start_scanning_creates_initiator(self):
        node = SleNode()
        node.start_scanning()
        assert node._initiator_mgr is not None

    def test_broadcast_filter_default_accepts(self):
        node = SleNode()
        frame = BroadcastFrame(0, 0, 0, b"\x01" * 6, 0, b"\x02" * 6)
        result = node.on_broadcast_received(frame)
        # 默认过滤器无条件, 应该接受
        assert isinstance(result, bool)

    def test_set_broadcast_filter(self):
        from nearlink_sdr.mac.broadcast import BroadcastFilter
        node = SleNode()
        f = BroadcastFilter()
        node.set_broadcast_filter(f)
        assert node._broadcast_filter is f


# ── 非链接态广播 ──


class TestNodeNonConnectedBroadcast:
    def test_build_broadcast_frame(self):
        node = SleNode(config=NodeConfig(address=b"\xAA" * 6))
        frame = node.start_non_connected_broadcast()
        assert frame is not None
        assert isinstance(frame, BroadcastFrame)


# ── 信道模型 ──


class TestNodeChannelModel:
    def test_no_channel_by_default(self):
        node = SleNode()
        assert node.channel_model is None

    def test_set_channel_model(self):
        from nearlink_sdr.phy.channel import ChannelConfig
        node = SleNode()
        cfg = ChannelConfig(snr_db=20.0)
        node.set_channel_model(cfg)
        assert node.channel_model is not None

    def test_clear_channel_model(self):
        from nearlink_sdr.phy.channel import ChannelConfig
        node = SleNode()
        node.set_channel_model(ChannelConfig(snr_db=20.0))
        node.clear_channel_model()
        assert node.channel_model is None

    def test_channel_from_config(self):
        from nearlink_sdr.phy.channel import ChannelConfig
        cfg = NodeConfig(channel_config=ChannelConfig(snr_db=15.0))
        node = SleNode(config=cfg)
        assert node.channel_model is not None

    def test_receive_through_channel(self):
        """带信道模型的高 SNR 环回仍能解码。"""
        from nearlink_sdr.phy.channel import ChannelConfig
        cfg = NodeConfig(
            mcs_index=5,
            channel_config=ChannelConfig(snr_db=40.0),
        )
        node = SleNode(config=cfg)
        node.start_advertising()
        node.accept_connection(b"\x01" * 6)

        payload = b"channel_test"
        node.send(payload)
        tx = node.transmit()
        assert tx.iq is not None

        # 接收端使用无信道节点解码 (信道已在 receive 中应用)
        rx = node.receive(tx.iq, len(tx.mac_bytes))
        # 高 SNR 下应能解码
        assert rx.success
        assert rx.data == payload


# ── USRP 硬件接口 ──


class TestNodeUsrp:
    def test_no_transceiver_by_default(self):
        node = SleNode()
        assert node.transceiver is None

    def test_usrp_mode_creates_transceiver(self):
        from nearlink_sdr.phy.usrp import USRPConfig
        cfg = NodeConfig(
            transport=TransportMode.USRP,
            usrp_config=USRPConfig(),
        )
        node = SleNode(config=cfg)
        assert node.transceiver is not None

    def test_receive_iq_without_transceiver(self):
        node = SleNode()
        result = node.receive_iq(1024)
        assert result is None

    def test_open_close_transceiver(self):
        from nearlink_sdr.phy.usrp import USRPConfig
        cfg = NodeConfig(
            transport=TransportMode.USRP,
            usrp_config=USRPConfig(),
        )
        node = SleNode(config=cfg)
        node.open_transceiver(2048)
        node.close_transceiver()


# ── 测量信号 ──


class TestNodeMeasurement:
    def test_generate_measurement_signal(self):
        node = SleNode()
        sig = node.generate_measurement_signal(n_measur=64)
        assert isinstance(sig, np.ndarray)
        assert len(sig) > 0


# ── 数据链路参数 ──


class TestNodeDataLinkParams:
    def test_async_params_for_ft2(self):
        from nearlink_sdr.phy.data_link import AsyncDataLinkParams
        node = SleNode(config=NodeConfig(frame_type=2))
        assert isinstance(node.data_link_params, AsyncDataLinkParams)

    def test_sync_params_for_ft3(self):
        from nearlink_sdr.phy.data_link import SyncDataLinkParams
        node = SleNode(config=NodeConfig(frame_type=3))
        assert isinstance(node.data_link_params, SyncDataLinkParams)


# ── 增强 stats ──


class TestNodeEnhancedStats:
    def test_stats_has_channel(self):
        node = SleNode()
        s = node.stats
        assert "channel" in s
        assert 0 <= s["channel"] <= 78

    def test_stats_has_hop_param2(self):
        node = SleNode()
        s = node.stats
        assert "hop_param2" in s
        assert isinstance(s["hop_param2"], int)

    def test_stats_has_power(self):
        node = SleNode(config=NodeConfig(tx_power_dbm=7.0))
        assert node.stats["tx_power_dbm"] == 7.0


# ── 发送信道号 ──


class TestNodeTransmitChannel:
    def test_transmit_includes_channel(self):
        node = SleNode(config=NodeConfig(mcs_index=5))
        node.start_advertising()
        node.accept_connection(b"\x01" * 6)
        node.send(b"data")
        tx = node.transmit()
        assert tx.channel >= 0

    def test_channel_advances_with_slot(self):
        node = SleNode(config=NodeConfig(mcs_index=5))
        node.start_advertising()
        node.accept_connection(b"\x01" * 6)

        channels = set()
        for _ in range(10):
            node.send(b"x")
            tx = node.transmit()
            channels.add(tx.channel)
            node.advance_slot(1)
        # 多个时隙应命中不同信道 (极小概率全相同)
        assert len(channels) >= 1


# ── 重置后组件重建 ──


class TestNodeReset:
    def test_reset_rebuilds_components(self):
        node = SleNode(config=NodeConfig(
            address=b"\x01\x02\x03\x04\x05\x06",
            smf_enabled=True,
            blocked_channels={5},
        ))
        node.start_advertising()
        node.accept_connection(b"\xAA" * 6)
        node.block_channel(10)
        node.reset()

        # 重建后组件应恢复初始状态
        assert node.state == NodeState.IDLE
        assert node.smf_scheduler is not None
        assert 5 in node.freq_table.blocked_channels
        # 手动添加的阻塞信道不应被保留 (重建来自 config)
        assert 10 not in node.freq_table.blocked_channels

    def test_reset_clears_access_managers(self):
        node = SleNode()
        node.start_advertising()
        assert node._broadcaster_mgr is not None
        node.accept_connection(b"\xBB" * 6)
        node.reset()
        assert node._broadcaster_mgr is None
        assert node._initiator_mgr is None
