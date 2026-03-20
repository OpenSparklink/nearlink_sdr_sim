"""链路管理状态机测试 -- TXS-10002-2025 标准 7.1 / 7.2"""

import pytest

from nearlink_sdr.mac.link_control import (
    IntervalUpdateRequest,
    PingRequest,
)
from nearlink_sdr.mac.link_manager import (
    DisconnectReason,
    Event,
    EventType,
    InvalidState,
    LinkManager,
    LinkManagerCallback,
    LinkParams,
    LinkState,
    Role,
)

# -----------------------------------------------------------------------
# Callback 记录器
# -----------------------------------------------------------------------

class RecordingCallback(LinkManagerCallback):
    """记录所有回调调用供断言使用。"""

    def __init__(self):
        self.state_changes: list[tuple[LinkState, LinkState]] = []
        self.access_results: list[tuple[bool, Role | None]] = []
        self.signaling_msgs: list = []
        self.disconnect_reasons: list[DisconnectReason] = []
        self.dormant_count: int = 0
        self.wakeup_count: int = 0

    def on_state_changed(self, old, new):
        self.state_changes.append((old, new))

    def on_access_accepted(self, role):
        self.access_results.append((True, role))

    def on_access_rejected(self):
        self.access_results.append((False, None))

    def on_signaling(self, msg):
        self.signaling_msgs.append(msg)

    def on_disconnected(self, reason):
        self.disconnect_reasons.append(reason)

    def on_dormant(self):
        self.dormant_count += 1

    def on_wakeup(self):
        self.wakeup_count += 1


# -----------------------------------------------------------------------
# 辅助函数
# -----------------------------------------------------------------------

def make_manager() -> tuple[LinkManager, RecordingCallback]:
    cb = RecordingCallback()
    mgr = LinkManager(callback=cb)
    return mgr, cb


def connect_as_t_node(mgr: LinkManager) -> None:
    """快速将状态机推进到 CONNECTED / T_NODE。"""
    mgr.process_event(Event(EventType.START_SCAN))
    mgr.process_event(Event(
        EventType.SEND_ACCESS_REQUEST,
        {"peer_address": b"\x01\x02\x03", "role": Role.T_NODE},
    ))
    mgr.process_event(Event(
        EventType.ACCESS_RESPONSE_RECEIVED,
        {"accepted": True, "role": Role.T_NODE},
    ))


def connect_as_g_node(mgr: LinkManager) -> None:
    """快速将状态机推进到 CONNECTED / G_NODE（广播设备侧）。"""
    mgr.process_event(Event(EventType.START_BROADCAST))
    mgr.process_event(Event(
        EventType.ACCESS_REQUEST_RECEIVED,
        {"accepted": True, "role": Role.G_NODE},
    ))


# -----------------------------------------------------------------------
# 测试：基本状态转换
# -----------------------------------------------------------------------

class TestStateTransitions:

    def test_initial_state(self):
        mgr, _ = make_manager()
        assert mgr.state == LinkState.IDLE
        assert mgr.role == Role.NONE

    def test_start_broadcast(self):
        mgr, cb = make_manager()
        mgr.process_event(Event(EventType.START_BROADCAST))
        assert mgr.state == LinkState.BROADCASTING
        assert cb.state_changes == [(LinkState.IDLE, LinkState.BROADCASTING)]

    def test_stop_broadcast(self):
        mgr, _ = make_manager()
        mgr.process_event(Event(EventType.START_BROADCAST))
        mgr.process_event(Event(EventType.STOP_BROADCAST))
        assert mgr.state == LinkState.IDLE

    def test_start_scan(self):
        mgr, _ = make_manager()
        mgr.process_event(Event(EventType.START_SCAN))
        assert mgr.state == LinkState.SCANNING

    def test_stop_scan(self):
        mgr, _ = make_manager()
        mgr.process_event(Event(EventType.START_SCAN))
        mgr.process_event(Event(EventType.STOP_SCAN))
        assert mgr.state == LinkState.IDLE

    def test_invalid_transition_ignored(self):
        """IDLE 状态下收到 STOP_BROADCAST 应被忽略。"""
        mgr, cb = make_manager()
        mgr.process_event(Event(EventType.STOP_BROADCAST))
        assert mgr.state == LinkState.IDLE
        assert len(cb.state_changes) == 0


# -----------------------------------------------------------------------
# 测试：接入流程 (7.1.3)
# -----------------------------------------------------------------------

class TestAccessFlow:

    def test_scan_to_access(self):
        mgr, _ = make_manager()
        mgr.process_event(Event(EventType.START_SCAN))
        mgr.process_event(Event(
            EventType.SEND_ACCESS_REQUEST,
            {"peer_address": b"\xAA\xBB", "role": Role.T_NODE},
        ))
        assert mgr.state == LinkState.ACCESSING
        assert mgr.peer_address == b"\xAA\xBB"
        assert mgr.role == Role.T_NODE

    def test_access_accepted(self):
        mgr, cb = make_manager()
        connect_as_t_node(mgr)
        assert mgr.state == LinkState.CONNECTED
        assert mgr.role == Role.T_NODE
        assert cb.access_results == [(True, Role.T_NODE)]

    def test_access_rejected(self):
        mgr, cb = make_manager()
        mgr.process_event(Event(EventType.START_SCAN))
        mgr.process_event(Event(EventType.SEND_ACCESS_REQUEST, {}))
        mgr.process_event(Event(
            EventType.ACCESS_RESPONSE_RECEIVED, {"accepted": False},
        ))
        assert mgr.state == LinkState.SCANNING
        assert cb.access_results == [(False, None)]

    def test_broadcast_side_access(self):
        mgr, cb = make_manager()
        connect_as_g_node(mgr)
        assert mgr.state == LinkState.CONNECTED
        assert mgr.role == Role.G_NODE
        assert cb.access_results == [(True, Role.G_NODE)]


# -----------------------------------------------------------------------
# 测试：链接态控制面 (7.2)
# -----------------------------------------------------------------------

class TestConnectedSignaling:

    def test_signaling_received(self):
        mgr, cb = make_manager()
        connect_as_t_node(mgr)
        msg = IntervalUpdateRequest(interval_type=3)
        mgr.process_event(Event(EventType.SIGNALING_RECEIVED, msg))
        assert len(cb.signaling_msgs) == 1

    def test_send_signaling(self):
        mgr, _ = make_manager()
        connect_as_t_node(mgr)
        msg = PingRequest()
        frame = mgr.send_signaling(msg)
        assert frame is not None
        assert frame.data_type_index == 0x0033

    def test_send_signaling_not_connected(self):
        mgr, _ = make_manager()
        with pytest.raises(InvalidState):
            mgr.send_signaling(PingRequest())


# -----------------------------------------------------------------------
# 测试：断开流程 (7.2.17)
# -----------------------------------------------------------------------

class TestDisconnect:

    def test_local_disconnect(self):
        mgr, cb = make_manager()
        connect_as_t_node(mgr)
        mgr.process_event(Event(EventType.DISCONNECT_REQUEST))
        assert mgr.state == LinkState.DISCONNECTED
        assert cb.disconnect_reasons == [DisconnectReason.LOCAL_REQUEST]

    def test_remote_disconnect(self):
        mgr, cb = make_manager()
        connect_as_t_node(mgr)
        mgr.process_event(Event(EventType.DISCONNECT_RECEIVED))
        assert mgr.state == LinkState.DISCONNECTED
        assert cb.disconnect_reasons == [DisconnectReason.REMOTE_REQUEST]

    def test_supervision_timeout(self):
        mgr, cb = make_manager()
        connect_as_t_node(mgr)
        mgr.process_event(Event(EventType.SUPERVISION_TIMEOUT))
        assert mgr.state == LinkState.DISCONNECTED
        assert cb.disconnect_reasons == [DisconnectReason.TIMEOUT]

    def test_reset_after_disconnect(self):
        mgr, _ = make_manager()
        connect_as_t_node(mgr)
        mgr.process_event(Event(EventType.DISCONNECT_REQUEST))
        mgr.reset()
        assert mgr.state == LinkState.IDLE
        assert mgr.role == Role.NONE


# -----------------------------------------------------------------------
# 测试：角色切换 (7.2.15)
# -----------------------------------------------------------------------

class TestRoleSwitch:

    def test_switch_g_to_t(self):
        mgr, _ = make_manager()
        connect_as_g_node(mgr)
        assert mgr.role == Role.G_NODE
        mgr.switch_role()
        assert mgr.role == Role.T_NODE

    def test_switch_t_to_g(self):
        mgr, _ = make_manager()
        connect_as_t_node(mgr)
        assert mgr.role == Role.T_NODE
        mgr.switch_role()
        assert mgr.role == Role.G_NODE

    def test_switch_not_connected(self):
        mgr, _ = make_manager()
        with pytest.raises(InvalidState):
            mgr.switch_role()


# -----------------------------------------------------------------------
# 测试：参数更新
# -----------------------------------------------------------------------

class TestParamsUpdate:

    def test_update_interval(self):
        mgr, _ = make_manager()
        mgr.update_params(tx_rx_interval=50)
        assert mgr.params.tx_rx_interval == 50

    def test_update_multiple(self):
        mgr, _ = make_manager()
        mgr.update_params(tx_max_octets=100, rx_max_octets=200)
        assert mgr.params.tx_max_octets == 100
        assert mgr.params.rx_max_octets == 200

    def test_default_params(self):
        params = LinkParams()
        assert params.supervision_timeout == 5000


# -----------------------------------------------------------------------
# 测试：事件日志
# -----------------------------------------------------------------------

class TestEventLog:

    def test_log_records_transitions(self):
        mgr, _ = make_manager()
        mgr.process_event(Event(EventType.START_SCAN))
        assert len(mgr.event_log) == 1
        _, _, old, new = mgr.event_log[0]
        assert old == LinkState.IDLE
        assert new == LinkState.SCANNING

    def test_is_connected_property(self):
        mgr, _ = make_manager()
        assert not mgr.is_connected
        connect_as_t_node(mgr)
        assert mgr.is_connected


# -----------------------------------------------------------------------
# 测试：完整生命周期
# -----------------------------------------------------------------------

class TestFullLifecycle:

    def test_scan_access_connect_disconnect(self):
        """扫描 → 接入 → 链接 → 断开 完整流程。"""
        mgr, _cb = make_manager()
        # 扫描
        mgr.process_event(Event(EventType.START_SCAN))
        assert mgr.state == LinkState.SCANNING
        # 接入请求
        mgr.process_event(Event(
            EventType.SEND_ACCESS_REQUEST,
            {"peer_address": b"\x01", "role": Role.T_NODE},
        ))
        assert mgr.state == LinkState.ACCESSING
        # 接入响应
        mgr.process_event(Event(
            EventType.ACCESS_RESPONSE_RECEIVED,
            {"accepted": True, "role": Role.T_NODE},
        ))
        assert mgr.state == LinkState.CONNECTED
        # 发送信令
        frame = mgr.send_signaling(PingRequest())
        assert frame.data_type_index == 0x0033
        # 断开
        mgr.process_event(Event(EventType.DISCONNECT_REQUEST))
        assert mgr.state == LinkState.DISCONNECTED
        # 重置
        mgr.reset()
        assert mgr.state == LinkState.IDLE

    def test_broadcast_access_connect(self):
        """广播 → 收到接入请求 → 链接 完整流程（广播设备侧）。"""
        mgr, _cb = make_manager()
        mgr.process_event(Event(EventType.START_BROADCAST))
        mgr.process_event(Event(
            EventType.ACCESS_REQUEST_RECEIVED,
            {"accepted": True, "role": Role.G_NODE},
        ))
        assert mgr.state == LinkState.CONNECTED
        assert mgr.role == Role.G_NODE
        mgr.process_event(Event(EventType.DISCONNECT_RECEIVED))
        assert mgr.state == LinkState.DISCONNECTED


# -----------------------------------------------------------------------
# 测试: 配对状态转换 (9.2)
# -----------------------------------------------------------------------

class TestPairingTransitions:

    def test_connected_to_pairing(self):
        mgr, _ = make_manager()
        connect_as_t_node(mgr)
        mgr.process_event(Event(EventType.START_PAIRING))
        assert mgr.state == LinkState.PAIRING

    def test_pairing_complete(self):
        mgr, _ = make_manager()
        connect_as_t_node(mgr)
        mgr.process_event(Event(EventType.START_PAIRING))
        mgr.process_event(Event(EventType.PAIRING_COMPLETE))
        assert mgr.state == LinkState.CONNECTED

    def test_pairing_failed(self):
        mgr, cb = make_manager()
        connect_as_t_node(mgr)
        mgr.process_event(Event(EventType.START_PAIRING))
        mgr.process_event(Event(EventType.PAIRING_FAILED))
        assert mgr.state == LinkState.DISCONNECTED
        assert cb.disconnect_reasons == [DisconnectReason.LOCAL_REQUEST]

    def test_full_pairing_lifecycle(self):
        """CONNECTED → PAIRING → CONNECTED 完整流程。"""
        mgr, _cb = make_manager()
        connect_as_g_node(mgr)
        mgr.process_event(Event(EventType.START_PAIRING))
        assert mgr.state == LinkState.PAIRING
        mgr.process_event(Event(EventType.PAIRING_COMPLETE))
        assert mgr.state == LinkState.CONNECTED
        assert mgr.role == Role.G_NODE


# -----------------------------------------------------------------------
# 测试: 监督超时检测
# -----------------------------------------------------------------------

class TestSupervisionCheck:

    def test_check_not_connected(self):
        mgr, _ = make_manager()
        assert mgr.check_supervision_timeout() is False

    def test_check_no_rx_time(self):
        mgr, _ = make_manager()
        connect_as_t_node(mgr)
        mgr._last_rx_time = 0
        assert mgr.check_supervision_timeout() is False

    def test_check_within_timeout(self):
        import time
        mgr, _ = make_manager()
        connect_as_t_node(mgr)
        mgr._last_rx_time = time.monotonic()
        assert mgr.check_supervision_timeout() is False

    def test_check_exceeds_timeout(self):
        import time
        mgr, _cb = make_manager()
        connect_as_t_node(mgr)
        mgr.params.supervision_timeout = 1  # 1ms
        mgr._last_rx_time = time.monotonic() - 1.0  # 1 秒前
        assert mgr.check_supervision_timeout() is True
        assert mgr.state == LinkState.DISCONNECTED


# -----------------------------------------------------------------------
# 测试：休眠与唤醒 (7.2.14)
# -----------------------------------------------------------------------

class TestDormantTransitions:

    def test_connected_to_dormant(self):
        mgr, cb = make_manager()
        connect_as_t_node(mgr)
        mgr.process_event(Event(EventType.SLEEP_REQUEST))
        assert mgr.state == LinkState.DORMANT
        assert mgr.is_dormant
        assert cb.dormant_count == 1

    def test_dormant_to_connected_local_wake(self):
        mgr, cb = make_manager()
        connect_as_t_node(mgr)
        mgr.process_event(Event(EventType.SLEEP_REQUEST))
        mgr.process_event(Event(EventType.WAKE_REQUEST))
        assert mgr.state == LinkState.CONNECTED
        assert not mgr.is_dormant
        assert cb.wakeup_count == 1

    def test_dormant_to_connected_remote_wake(self):
        mgr, cb = make_manager()
        connect_as_t_node(mgr)
        mgr.process_event(Event(EventType.SLEEP_REQUEST))
        mgr.process_event(Event(EventType.WAKE_RECEIVED))
        assert mgr.state == LinkState.CONNECTED
        assert cb.wakeup_count == 1

    def test_dormant_disconnect(self):
        mgr, cb = make_manager()
        connect_as_t_node(mgr)
        mgr.process_event(Event(EventType.SLEEP_REQUEST))
        mgr.process_event(Event(EventType.DISCONNECT_REQUEST))
        assert mgr.state == LinkState.DISCONNECTED
        assert len(cb.disconnect_reasons) == 1

    def test_sleep_not_connected_ignored(self):
        mgr, cb = make_manager()
        # IDLE 态发 SLEEP_REQUEST 应被忽略
        mgr.process_event(Event(EventType.SLEEP_REQUEST))
        assert mgr.state == LinkState.IDLE
        assert cb.dormant_count == 0

    def test_full_dormant_lifecycle(self):
        mgr, cb = make_manager()
        connect_as_t_node(mgr)
        # 进入休眠
        mgr.process_event(Event(EventType.SLEEP_REQUEST))
        assert mgr.state == LinkState.DORMANT
        # 唤醒
        mgr.process_event(Event(EventType.WAKE_REQUEST))
        assert mgr.state == LinkState.CONNECTED
        # 再次休眠
        mgr.process_event(Event(EventType.SLEEP_REQUEST))
        assert mgr.state == LinkState.DORMANT
        # 远端唤醒
        mgr.process_event(Event(EventType.WAKE_RECEIVED))
        assert mgr.state == LinkState.CONNECTED
        assert cb.dormant_count == 2
        assert cb.wakeup_count == 2
