"""链路管理状态机 -- TXS-10002-2025 标准 7.1 / 7.2。

实现 SparkLink SLE 的链路生命周期管理，包括广播、发现、接入、
链接态控制面流程和链路断开。
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any

from nearlink_sdr.mac.broadcast import BroadcastFrame
from nearlink_sdr.mac.frame import ControlFrame
from nearlink_sdr.mac.signaling import decode_signaling, encode_signaling

log = logging.getLogger(__name__)


# -----------------------------------------------------------------------
# 角色与状态枚举
# -----------------------------------------------------------------------

class Role(Enum):
    """G/T 节点角色（标准 7.1.3 / 7.1.7.1）。"""
    NONE = auto()
    G_NODE = auto()
    T_NODE = auto()


class LinkState(Enum):
    """链路状态。

    IDLE        -- 初始待机
    BROADCASTING -- 广播态，周期发送基础/扩展广播帧（7.1.1）
    SCANNING    -- 发现态，接收广播帧（7.1.2）
    ACCESSING   -- 接入态，发送接入请求/等待响应（7.1.3）
    CONNECTED   -- 链接态，异步数据链路已建立
    PAIRING     -- 配对态，执行安全流程（9.2）
    DORMANT     -- 休眠态，保持链路但停止数据传输（7.2.14）
    DISCONNECTED -- 链路已断开
    """
    IDLE = auto()
    BROADCASTING = auto()
    SCANNING = auto()
    ACCESSING = auto()
    CONNECTED = auto()
    PAIRING = auto()
    DORMANT = auto()
    DISCONNECTED = auto()


class DisconnectReason(Enum):
    """断开原因。"""
    LOCAL_REQUEST = 0
    REMOTE_REQUEST = 1
    TIMEOUT = 2
    ACCESS_REJECTED = 3


# -----------------------------------------------------------------------
# 链路参数
# -----------------------------------------------------------------------

@dataclass
class LinkParams:
    """链路运行参数集合。"""
    # 收发间隔 (7.2.1)
    tx_rx_interval: int = 20  # 单位 ms
    # 数据长度 (7.2.6)
    tx_max_octets: int = 27
    rx_max_octets: int = 27
    # 跳频信道表
    channel_table: bytes = b""
    # 帧类型
    frame_type: int = 2
    # 带宽
    bandwidth: int = 0
    # CRC 类型
    crc_type: int = 0
    # 超时 (单位 ms)
    supervision_timeout: int = 5000


# -----------------------------------------------------------------------
# 事件
# -----------------------------------------------------------------------

class EventType(Enum):
    """状态机输入事件类型。"""
    # 广播/发现/接入
    START_BROADCAST = auto()
    STOP_BROADCAST = auto()
    START_SCAN = auto()
    STOP_SCAN = auto()
    BROADCAST_RECEIVED = auto()
    SEND_ACCESS_REQUEST = auto()
    ACCESS_RESPONSE_RECEIVED = auto()
    ACCESS_REQUEST_RECEIVED = auto()
    # 链接态控制面 (7.2)
    SIGNALING_RECEIVED = auto()
    SIGNALING_SEND = auto()
    # 配对（9.2）
    START_PAIRING = auto()
    PAIRING_COMPLETE = auto()
    PAIRING_FAILED = auto()
    # 断开
    DISCONNECT_REQUEST = auto()
    DISCONNECT_RECEIVED = auto()
    SUPERVISION_TIMEOUT = auto()
    # 休眠/唤醒（7.2.14）
    SLEEP_REQUEST = auto()
    WAKE_REQUEST = auto()
    WAKE_RECEIVED = auto()


@dataclass
class Event:
    """状态机事件。"""
    type: EventType
    data: Any = None


# -----------------------------------------------------------------------
# 回调协议
# -----------------------------------------------------------------------

class LinkManagerCallback:
    """链路管理回调接口。子类可覆盖需要的方法。"""

    def on_state_changed(self, old: LinkState, new: LinkState) -> None:
        """状态变迁通知。"""

    def on_broadcast_frame(self, frame: BroadcastFrame) -> None:
        """接收到广播帧。"""

    def on_access_accepted(self, role: Role) -> None:
        """接入成功，角色已确定。"""

    def on_access_rejected(self) -> None:
        """接入被拒绝。"""

    def on_signaling(self, msg: Any) -> None:
        """收到控制面信令。"""

    def on_disconnected(self, reason: DisconnectReason) -> None:
        """链路断开。"""

    def on_dormant(self) -> None:
        """进入休眠态（7.2.14）。"""

    def on_wakeup(self) -> None:
        """从休眠态唤醒（7.2.14）。"""


# -----------------------------------------------------------------------
# 链路管理器
# -----------------------------------------------------------------------

_VALID_TRANSITIONS: dict[LinkState, set[LinkState]] = {
    LinkState.IDLE: {
        LinkState.BROADCASTING,
        LinkState.SCANNING,
    },
    LinkState.BROADCASTING: {
        LinkState.IDLE,
        LinkState.CONNECTED,
    },
    LinkState.SCANNING: {
        LinkState.IDLE,
        LinkState.ACCESSING,
    },
    LinkState.ACCESSING: {
        LinkState.CONNECTED,
        LinkState.SCANNING,
        LinkState.DISCONNECTED,
    },
    LinkState.CONNECTED: {
        LinkState.PAIRING,
        LinkState.DORMANT,
        LinkState.DISCONNECTED,
    },
    LinkState.PAIRING: {
        LinkState.CONNECTED,
        LinkState.DISCONNECTED,
    },
    LinkState.DORMANT: {
        LinkState.CONNECTED,
        LinkState.DISCONNECTED,
    },
    LinkState.DISCONNECTED: {
        LinkState.IDLE,
    },
}


@dataclass
class LinkManager:
    """SparkLink SLE 链路管理状态机。

    以事件驱动方式管理链路生命周期：
    IDLE → BROADCASTING / SCANNING → ACCESSING → CONNECTED → DISCONNECTED。
    """
    state: LinkState = LinkState.IDLE
    role: Role = Role.NONE
    params: LinkParams = field(default_factory=LinkParams)
    callback: LinkManagerCallback = field(default_factory=LinkManagerCallback)
    peer_address: bytes = b""
    local_address: bytes = b""
    # 内部计数
    _slot_counter: int = 0
    _last_rx_time: float = 0.0
    _event_log: list[tuple[float, EventType, LinkState, LinkState]] = field(
        default_factory=list
    )

    # ---------------------------------------------------------------
    # 公共接口
    # ---------------------------------------------------------------

    def process_event(self, event: Event) -> None:
        """处理一个事件，驱动状态转换。"""
        handler = _HANDLERS.get((self.state, event.type))
        if handler is None:
            log.warning(
                "忽略事件 %s (当前状态 %s)", event.type.name, self.state.name
            )
            return
        handler(self, event)

    def reset(self) -> None:
        """重置到 IDLE 状态。"""
        self._transition(LinkState.IDLE)
        self.role = Role.NONE
        self.peer_address = b""

    @property
    def is_connected(self) -> bool:
        return self.state == LinkState.CONNECTED

    @property
    def is_dormant(self) -> bool:
        return self.state == LinkState.DORMANT

    @property
    def event_log(self) -> list[tuple[float, EventType, LinkState, LinkState]]:
        return list(self._event_log)

    # ---------------------------------------------------------------
    # 状态转换
    # ---------------------------------------------------------------

    def _transition(self, new_state: LinkState) -> None:
        old = self.state
        if new_state not in _VALID_TRANSITIONS.get(old, set()):
            if old == new_state:
                return
            raise InvalidTransition(
                f"非法转换: {old.name} → {new_state.name}"
            )
        self.state = new_state
        ts = time.monotonic()
        self._event_log.append((ts, EventType.START_BROADCAST, old, new_state))
        log.info("状态转换 %s → %s", old.name, new_state.name)
        self.callback.on_state_changed(old, new_state)

    # ---------------------------------------------------------------
    # 事件处理器
    # ---------------------------------------------------------------

    def _handle_start_broadcast(self, event: Event) -> None:
        self._transition(LinkState.BROADCASTING)

    def _handle_stop_broadcast(self, event: Event) -> None:
        self._transition(LinkState.IDLE)

    def _handle_start_scan(self, event: Event) -> None:
        self._transition(LinkState.SCANNING)

    def _handle_stop_scan(self, event: Event) -> None:
        self._transition(LinkState.IDLE)

    def _handle_broadcast_received(self, event: Event) -> None:
        """发现态收到广播帧（7.1.2）。"""
        if isinstance(event.data, BroadcastFrame):
            self.callback.on_broadcast_frame(event.data)

    def _handle_send_access_request(self, event: Event) -> None:
        """发现态发起接入请求（7.1.3）。"""
        self._transition(LinkState.ACCESSING)
        if isinstance(event.data, dict):
            self.peer_address = event.data.get("peer_address", b"")
            requested_role = event.data.get("role", Role.T_NODE)
            self.role = requested_role

    def _handle_access_response_received(self, event: Event) -> None:
        """接入态收到接入响应（7.1.3d）。"""
        if isinstance(event.data, dict) and event.data.get("accepted", False):
            role = event.data.get("role")
            if isinstance(role, Role):
                self.role = role
            self._transition(LinkState.CONNECTED)
            self._last_rx_time = time.monotonic()
            self.callback.on_access_accepted(self.role)
        else:
            self._transition(LinkState.SCANNING)
            self.callback.on_access_rejected()

    def _handle_access_request_received(self, event: Event) -> None:
        """广播态收到接入请求（7.1.3c），广播设备侧。"""
        if isinstance(event.data, dict) and event.data.get("accepted", False):
            role = event.data.get("role", Role.G_NODE)
            if isinstance(role, Role):
                self.role = role
            self._transition(LinkState.CONNECTED)
            self._last_rx_time = time.monotonic()
            self.callback.on_access_accepted(self.role)

    def _handle_signaling_received(self, event: Event) -> None:
        """链接态收到控制面信令（7.2）。"""
        self._last_rx_time = time.monotonic()
        if isinstance(event.data, ControlFrame):
            msg = decode_signaling(event.data)
            self.callback.on_signaling(msg)
        else:
            self.callback.on_signaling(event.data)

    def _handle_signaling_send(self, event: Event) -> None:
        """链接态发送控制面信令。

        实际发送由上层完成，此处仅编码并返回 ControlFrame。
        """
        if event.data is not None:
            frame = encode_signaling(event.data)
            return frame
        return None

    def _handle_disconnect_request(self, event: Event) -> None:
        """本端请求断开（7.2.17）。"""
        self._transition(LinkState.DISCONNECTED)
        self.callback.on_disconnected(DisconnectReason.LOCAL_REQUEST)

    def _handle_disconnect_received(self, event: Event) -> None:
        """收到对端断开指示（7.2.17）。"""
        self._transition(LinkState.DISCONNECTED)
        self.callback.on_disconnected(DisconnectReason.REMOTE_REQUEST)

    def _handle_supervision_timeout(self, event: Event) -> None:
        """监督超时（链接态）。"""
        self._transition(LinkState.DISCONNECTED)
        self.callback.on_disconnected(DisconnectReason.TIMEOUT)

    def _handle_start_pairing(self, event: Event) -> None:
        """链接态发起配对流程（9.2）。"""
        self._transition(LinkState.PAIRING)

    def _handle_pairing_complete(self, event: Event) -> None:
        """配对完成，返回链接态（加密）。"""
        self._transition(LinkState.CONNECTED)

    def _handle_pairing_failed(self, event: Event) -> None:
        """配对失败，断开链路。"""
        self._transition(LinkState.DISCONNECTED)
        self.callback.on_disconnected(DisconnectReason.LOCAL_REQUEST)

    def _handle_sleep_request(self, event: Event) -> None:
        """链接态发起休眠（7.2.14）。"""
        self._transition(LinkState.DORMANT)
        self.callback.on_dormant()

    def _handle_wake_request(self, event: Event) -> None:
        """本端请求唤醒（7.2.14）。"""
        self._transition(LinkState.CONNECTED)
        self._last_rx_time = time.monotonic()
        self.callback.on_wakeup()

    def _handle_wake_received(self, event: Event) -> None:
        """收到对端唤醒指示（7.2.14）。"""
        self._transition(LinkState.CONNECTED)
        self._last_rx_time = time.monotonic()
        self.callback.on_wakeup()

    def _handle_dormant_disconnect(self, event: Event) -> None:
        """休眠态断开链路。"""
        self._transition(LinkState.DISCONNECTED)
        self.callback.on_disconnected(DisconnectReason.LOCAL_REQUEST)

    # ---------------------------------------------------------------
    # 链接态便利方法 (7.2.x)
    # ---------------------------------------------------------------

    def send_signaling(self, msg: Any) -> ControlFrame | None:
        """在链接态发送一条控制面信令，返回编码后的 ControlFrame。"""
        if self.state != LinkState.CONNECTED:
            raise InvalidState(
                f"仅链接态可发送信令 (当前 {self.state.name})"
            )
        return encode_signaling(msg)

    def update_params(self, **kwargs: Any) -> None:
        """更新链路参数。"""
        for k, v in kwargs.items():
            if hasattr(self.params, k):
                setattr(self.params, k, v)

    def switch_role(self) -> None:
        """角色切换（7.2.15），仅交换本地角色标记。"""
        if self.state != LinkState.CONNECTED:
            raise InvalidState("角色切换仅在链接态可用")
        if self.role == Role.G_NODE:
            self.role = Role.T_NODE
        elif self.role == Role.T_NODE:
            self.role = Role.G_NODE

    def check_supervision_timeout(self) -> bool:
        """检查监督定时器是否超时。返回 True 表示已超时并触发断开。"""
        if self.state != LinkState.CONNECTED:
            return False
        if self._last_rx_time == 0:
            return False
        elapsed_ms = (time.monotonic() - self._last_rx_time) * 1000
        if elapsed_ms > self.params.supervision_timeout:
            self.process_event(Event(EventType.SUPERVISION_TIMEOUT))
            return True
        return False


# -----------------------------------------------------------------------
# 异常
# -----------------------------------------------------------------------

class InvalidTransition(Exception):
    """非法状态转换。"""


class InvalidState(Exception):
    """当前状态不允许此操作。"""


# -----------------------------------------------------------------------
# 事件分发表
# -----------------------------------------------------------------------

_HandlerFunc = type(LinkManager._handle_start_broadcast)

_HANDLERS: dict[tuple[LinkState, EventType], _HandlerFunc] = {
    # IDLE
    (LinkState.IDLE, EventType.START_BROADCAST):
        LinkManager._handle_start_broadcast,
    (LinkState.IDLE, EventType.START_SCAN):
        LinkManager._handle_start_scan,
    # BROADCASTING
    (LinkState.BROADCASTING, EventType.STOP_BROADCAST):
        LinkManager._handle_stop_broadcast,
    (LinkState.BROADCASTING, EventType.ACCESS_REQUEST_RECEIVED):
        LinkManager._handle_access_request_received,
    # SCANNING
    (LinkState.SCANNING, EventType.STOP_SCAN):
        LinkManager._handle_stop_scan,
    (LinkState.SCANNING, EventType.BROADCAST_RECEIVED):
        LinkManager._handle_broadcast_received,
    (LinkState.SCANNING, EventType.SEND_ACCESS_REQUEST):
        LinkManager._handle_send_access_request,
    # ACCESSING
    (LinkState.ACCESSING, EventType.ACCESS_RESPONSE_RECEIVED):
        LinkManager._handle_access_response_received,
    # CONNECTED
    (LinkState.CONNECTED, EventType.SIGNALING_RECEIVED):
        LinkManager._handle_signaling_received,
    (LinkState.CONNECTED, EventType.SIGNALING_SEND):
        LinkManager._handle_signaling_send,
    (LinkState.CONNECTED, EventType.DISCONNECT_REQUEST):
        LinkManager._handle_disconnect_request,
    (LinkState.CONNECTED, EventType.DISCONNECT_RECEIVED):
        LinkManager._handle_disconnect_received,
    (LinkState.CONNECTED, EventType.SUPERVISION_TIMEOUT):
        LinkManager._handle_supervision_timeout,
    # CONNECTED → PAIRING
    (LinkState.CONNECTED, EventType.START_PAIRING):
        LinkManager._handle_start_pairing,
    # CONNECTED → DORMANT (7.2.14)
    (LinkState.CONNECTED, EventType.SLEEP_REQUEST):
        LinkManager._handle_sleep_request,
    # PAIRING
    (LinkState.PAIRING, EventType.PAIRING_COMPLETE):
        LinkManager._handle_pairing_complete,
    (LinkState.PAIRING, EventType.PAIRING_FAILED):
        LinkManager._handle_pairing_failed,
    # DORMANT (7.2.14)
    (LinkState.DORMANT, EventType.WAKE_REQUEST):
        LinkManager._handle_wake_request,
    (LinkState.DORMANT, EventType.WAKE_RECEIVED):
        LinkManager._handle_wake_received,
    (LinkState.DORMANT, EventType.DISCONNECT_REQUEST):
        LinkManager._handle_dormant_disconnect,
}
