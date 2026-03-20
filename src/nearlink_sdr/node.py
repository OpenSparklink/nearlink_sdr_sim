"""SLE 节点实体 -- 统一收发接口。

将 MAC/PHY 各模块整合为单一 SLE 节点, 提供完整的链路生命周期管理
和数据收发能力。支持仿真模式和 USRP 硬件模式。
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import IntEnum, auto

import numpy as np

from nearlink_sdr.mac.frame import AsyncDataFrame, ControlFrame
from nearlink_sdr.mac.link_manager import (
    DisconnectReason,
    Event,
    EventType,
    LinkManager,
    LinkManagerCallback,
    LinkParams,
    LinkState,
    Role,
)
from nearlink_sdr.mac.qos import (
    ArqState,
    FlowController,
    HarqController,
    LinkQualityTracker,
    LinkType,
    Priority,
    QosManager,
    TxDecision,
    TxQueue,
)
from nearlink_sdr.mac.security_manager import (
    FrameCryptoContext,
    PairingManager,
    PairingState,
)
from nearlink_sdr.phy.control_info import ControlInfoA2
from nearlink_sdr.phy.mac_interface import (
    MacRxResult,
    iq_to_mac,
    mac_to_iq,
)
from nearlink_sdr.phy.tx_pipeline import TxConfig

log = logging.getLogger(__name__)


# ── 节点配置 ──


class NodeRole(IntEnum):
    """节点初始角色偏好。"""
    AUTO = 0
    G_NODE = 1
    T_NODE = 2


class TransportMode(IntEnum):
    """传输模式。"""
    SIMULATION = auto()
    USRP = auto()


@dataclass
class NodeConfig:
    """SLE 节点配置。

    Attributes:
        address: 6 字节设备地址。
        role: 角色偏好 (AUTO/G_NODE/T_NODE)。
        frame_type: 帧类型 (1-4)。
        mcs_index: MCS 索引 (0-12)。
        bandwidth_mhz: 信道带宽 (1/2/4 MHz)。
        pilot_interval: 导频插入间隔 (0/4/8/16)。
        max_pdu: 最大 PDU 长度 (字节)。
        max_retransmit: 最大重传次数。
        enable_encryption: 是否启用加密。
        transport: 传输模式。
    """
    address: bytes = b"\x00" * 6
    role: NodeRole = NodeRole.AUTO
    frame_type: int = 2
    mcs_index: int = 7
    bandwidth_mhz: int = 1
    pilot_interval: int = 8
    max_pdu: int = 256
    max_retransmit: int = 3
    enable_encryption: bool = False
    transport: TransportMode = TransportMode.SIMULATION


# ── 节点状态 ──


class NodeState(IntEnum):
    """节点高层状态, 简化自 LinkState。"""
    IDLE = 0
    ADVERTISING = auto()
    SCANNING = auto()
    CONNECTING = auto()
    PAIRED = auto()
    CONNECTED = auto()
    DISCONNECTED = auto()


# ── 节点回调 ──


class NodeCallback:
    """节点事件回调, 子类可覆盖。"""

    def on_state_changed(self, old: NodeState, new: NodeState) -> None:
        pass

    def on_connected(self, peer_address: bytes, role: Role) -> None:
        pass

    def on_data_received(self, data: bytes) -> None:
        pass

    def on_disconnected(self, reason: DisconnectReason) -> None:
        pass


# ── 收发结果 ──


@dataclass
class TxResult:
    """发射结果。"""
    iq: np.ndarray | None
    decision: TxDecision
    encrypted: bool = False


@dataclass
class RxResult:
    """接收结果。"""
    data: bytes | None
    success: bool
    decrypted: bool = False


# ── SLE 节点实体 ──


@dataclass
class SleNode:
    """SparkLink SLE 节点实体。

    整合链路管理、安全、QoS、PHY 流水线为统一收发接口。

    用法::

        node = SleNode(NodeConfig(address=b"\\x01\\x02\\x03\\x04\\x05\\x06"))
        node.send(b"hello", Priority.NORMAL)
        tx_result = node.transmit()
        # ... 通过信道传输 tx_result.iq ...
        rx_result = node.receive(rx_iq, n_bytes)
    """
    config: NodeConfig = field(default_factory=NodeConfig)
    callback: NodeCallback = field(default_factory=NodeCallback)

    # 内部组件 (延迟初始化)
    _link_mgr: LinkManager = field(init=False, repr=False)
    _qos: QosManager = field(init=False, repr=False)
    _tx_config: TxConfig = field(init=False, repr=False)
    _pairing: PairingManager | None = field(init=False, default=None, repr=False)
    _crypto: FrameCryptoContext | None = field(init=False, default=None, repr=False)
    _state: NodeState = field(init=False, default=NodeState.IDLE)
    _peer_address: bytes = field(init=False, default=b"")
    _tx_count: int = field(init=False, default=0)
    _rx_count: int = field(init=False, default=0)

    def __post_init__(self) -> None:
        cfg = self.config
        self._tx_config = TxConfig(
            frame_type=cfg.frame_type,
            mcs_index=cfg.mcs_index,
            pid=int.from_bytes(cfg.address[:3], "big") if len(cfg.address) >= 3 else 0,
            whitening_seed=0x52,
            crc_seed=0x555555,
            crc_len=24,
            ctrl_bits_len=self._ctrl_bits_len(),
            pilot_interval=cfg.pilot_interval,
        )
        link_type = LinkType.ASYNC if cfg.frame_type == 2 else LinkType.SYNC
        self._qos = QosManager(
            arq=ArqState(link_type=link_type, max_retransmit=cfg.max_retransmit),
            harq=HarqController(),
            flow=FlowController(),
            quality=LinkQualityTracker(),
            tx_queue=TxQueue(max_size=cfg.max_pdu),
        )
        self._link_mgr = LinkManager(
            local_address=cfg.address,
            params=LinkParams(frame_type=cfg.frame_type, bandwidth=cfg.bandwidth_mhz),
            callback=_InternalCallback(self),
        )

    def _ctrl_bits_len(self) -> int:
        ft = self.config.frame_type
        if ft == 1:
            return 20
        if ft == 2:
            return 28
        return 27

    # ── 生命周期管理 ──

    @property
    def state(self) -> NodeState:
        return self._state

    @property
    def link_state(self) -> LinkState:
        return self._link_mgr.state

    @property
    def role(self) -> Role:
        return self._link_mgr.role

    @property
    def peer_address(self) -> bytes:
        return self._peer_address

    @property
    def is_connected(self) -> bool:
        return self._state in (NodeState.CONNECTED, NodeState.PAIRED)

    def start_advertising(self) -> None:
        """进入广播态, 等待接入请求。"""
        self._link_mgr.process_event(Event(EventType.START_BROADCAST))
        self._set_state(NodeState.ADVERTISING)

    def start_scanning(self) -> None:
        """进入扫描态, 搜索广播节点。"""
        self._link_mgr.process_event(Event(EventType.START_SCAN))
        self._set_state(NodeState.SCANNING)

    def connect(self, peer_address: bytes) -> None:
        """发起接入请求。"""
        self._peer_address = peer_address
        self._link_mgr.process_event(Event(EventType.SEND_ACCESS_REQUEST))
        self._set_state(NodeState.CONNECTING)

    def accept_connection(self, peer_address: bytes, role: Role = Role.G_NODE) -> None:
        """接受接入请求, 直接进入链接态。"""
        self._peer_address = peer_address
        self._link_mgr.peer_address = peer_address
        self._link_mgr.process_event(
            Event(EventType.ACCESS_REQUEST_RECEIVED, {"accepted": True, "role": role})
        )
        self._set_state(NodeState.CONNECTED)

    def disconnect(self) -> None:
        """断开连接。"""
        self._link_mgr.process_event(Event(EventType.DISCONNECT_REQUEST))
        self._set_state(NodeState.DISCONNECTED)
        self._cleanup()

    def reset(self) -> None:
        """重置到初始状态。"""
        if self._link_mgr.state in (LinkState.CONNECTED, LinkState.PAIRING):
            self._link_mgr.process_event(Event(EventType.DISCONNECT_REQUEST))
        if self._link_mgr.state != LinkState.IDLE:
            self._link_mgr.reset()
        self._set_state(NodeState.IDLE)
        self._cleanup()
        self.__post_init__()

    # ── 安全配对 ──

    def start_pairing(self, peer_address: bytes) -> list:
        """发起配对流程。

        Returns:
            待发送给对端的配对信令列表。
        """
        is_g = self._link_mgr.role == Role.G_NODE
        self._pairing = PairingManager(
            is_g_node=is_g,
            local_address=self.config.address,
            peer_address=peer_address,
        )
        self._link_mgr.process_event(Event(EventType.START_PAIRING))
        self._set_state(NodeState.PAIRED)
        return self._pairing.start_pairing()

    def process_pairing_message(self, msg: object) -> list:
        """处理收到的配对信令。

        Returns:
            待发送的响应信令列表。
        """
        if self._pairing is None:
            return []
        responses = self._pairing.process_message(msg)
        if self._pairing.state == PairingState.COMPLETED:
            self._setup_crypto()
            self._link_mgr.process_event(Event(EventType.PAIRING_COMPLETE))
            self._set_state(NodeState.CONNECTED)
        elif self._pairing.state == PairingState.FAILED:
            self._link_mgr.process_event(Event(EventType.PAIRING_FAILED))
            self._set_state(NodeState.DISCONNECTED)
        return responses

    def _setup_crypto(self) -> None:
        if self._pairing is None or not self._pairing.is_paired:
            return
        is_g = self._link_mgr.role == Role.G_NODE
        ik = self._pairing.integrity_key
        iv_base = ik[:8] if ik else self._pairing.session_key[:8]
        self._crypto = FrameCryptoContext(
            session_key=self._pairing.session_key,
            iv_base=iv_base,
            direction=0 if is_g else 1,
            mic_len=4,
            frame_type=self.config.frame_type,
            link_id=0,
        )

    # ── 数据发送 ──

    def send(self, data: bytes, priority: Priority = Priority.NORMAL) -> bool:
        """提交数据到发送队列。

        Args:
            data: 待发送的数据负载。
            priority: 发送优先级。

        Returns:
            是否成功入队。
        """
        return self._qos.submit_data(data, priority)

    def transmit(self) -> TxResult:
        """从发送队列取出数据, 构建帧并生成 IQ 信号。

        Returns:
            TxResult, 包含 IQ 信号和发送决策。
        """
        decision, item = self._qos.prepare_tx()
        if item is None:
            return TxResult(iq=None, decision=decision)

        payload = item.data
        encrypted = False

        if self._crypto is not None and self.config.enable_encryption:
            aad = b""
            ciphertext, mic = self._crypto.encrypt(payload, aad)
            payload = ciphertext + mic
            encrypted = True

        frame = AsyncDataFrame(segment_type=0, data=payload)
        mac_bytes = frame.pack()

        ctrl_fields = self._qos.get_ctrl_fields()
        ctrl_info = _build_ctrl_info(ctrl_fields, len(mac_bytes))
        iq = mac_to_iq(mac_bytes, self._tx_config, ctrl_info=ctrl_info)

        self._tx_count += 1
        return TxResult(iq=iq, decision=decision, encrypted=encrypted)

    def receive(self, iq_signal: np.ndarray, n_mac_bytes: int) -> RxResult:
        """从 IQ 信号解码数据。

        Args:
            iq_signal: 接收到的 IQ 信号。
            n_mac_bytes: 预期 MAC 层 PDU 字节数。

        Returns:
            RxResult, 包含解码数据和成功标志。
        """
        rx: MacRxResult = iq_to_mac(iq_signal, self._tx_config, n_mac_bytes)

        if not rx.crc_ok:
            return RxResult(data=None, success=False)

        try:
            recovered = AsyncDataFrame.unpack(rx.mac_payload)
        except (ValueError, IndexError):
            return RxResult(data=None, success=False)

        data = recovered.data
        decrypted = False

        if self._crypto is not None and self.config.enable_encryption:
            mic_len = self._crypto.mic_len
            if len(data) < mic_len:
                return RxResult(data=None, success=False)
            ciphertext = data[:-mic_len]
            mic = data[-mic_len:]
            try:
                data = self._crypto.decrypt(ciphertext, mic, b"")
                decrypted = True
            except Exception:
                return RxResult(data=None, success=False)

        self._rx_count += 1
        return RxResult(data=data, success=True, decrypted=decrypted)

    def process_feedback(self, crc_ok: bool) -> TxDecision:
        """处理对端 ACK/NACK 反馈。"""
        return self._qos.on_tx_feedback(crc_ok)

    # ── 信令 ──

    def send_signaling(self, msg: object) -> ControlFrame | None:
        """通过链路管理器发送控制面信令。"""
        if not self.is_connected:
            return None
        return self._link_mgr.send_signaling(msg)

    def receive_signaling(self, msg: object) -> None:
        """处理收到的控制面信令。"""
        self._link_mgr.process_event(Event(EventType.SIGNALING_RECEIVED, msg))

    # ── 状态查询 ──

    @property
    def stats(self) -> dict:
        """返回节点统计信息。"""
        qos_fields = self._qos.get_ctrl_fields()
        return {
            "state": self._state.name,
            "role": self._link_mgr.role.name,
            "tx_count": self._tx_count,
            "rx_count": self._rx_count,
            "tx_sn": qos_fields.get("tx_sn", 0),
            "rx_sn": qos_fields.get("rx_sn", 0),
            "fer": self._qos.quality.fer,
            "mcs": self.config.mcs_index,
            "queue_size": self._qos.tx_queue.size,
            "flow_paused": self._qos.flow.is_paused,
            "paired": self._pairing is not None and self._pairing.is_paired,
            "encrypted": self._crypto is not None,
        }

    @property
    def recommended_mcs(self) -> int:
        """基于链路质量建议的 MCS 索引。"""
        adj = self._qos.quality.suggest_mcs_adjustment()
        return max(0, min(12, self.config.mcs_index + adj))

    def update_mcs(self, mcs_index: int) -> None:
        """更新 MCS 索引。"""
        self.config.mcs_index = max(0, min(12, mcs_index))
        self._tx_config = TxConfig(
            frame_type=self.config.frame_type,
            mcs_index=self.config.mcs_index,
            pid=self._tx_config.pid,
            whitening_seed=self._tx_config.whitening_seed,
            crc_seed=self._tx_config.crc_seed,
            crc_len=self._tx_config.crc_len,
            ctrl_bits_len=self._tx_config.ctrl_bits_len,
            pilot_interval=self._tx_config.pilot_interval,
        )

    # ── 内部方法 ──

    def _set_state(self, new: NodeState) -> None:
        old = self._state
        if old != new:
            self._state = new
            self.callback.on_state_changed(old, new)

    def _cleanup(self) -> None:
        self._peer_address = b""
        self._pairing = None
        self._crypto = None


class _InternalCallback(LinkManagerCallback):
    """将 LinkManager 回调转发到 SleNode。"""

    def __init__(self, node: SleNode) -> None:
        self._node = node

    def on_access_accepted(self, role: Role) -> None:
        self._node.callback.on_connected(self._node.peer_address, role)

    def on_disconnected(self, reason: DisconnectReason) -> None:
        self._node._set_state(NodeState.DISCONNECTED)
        self._node.callback.on_disconnected(reason)


def _build_ctrl_info(
    ctrl_fields: dict[str, int], data_length: int,
) -> ControlInfoA2:
    """从 QoS 控制字段构建 A2 控制信息。"""
    return ControlInfoA2(
        packet_type=0,
        empty_packet=ctrl_fields.get("empty_packet", 0) & 1,
        tx_sn=ctrl_fields.get("tx_sn", 0) & 1,
        rx_sn=ctrl_fields.get("rx_sn", 0) & 1,
        flow_ctrl=ctrl_fields.get("flow_ctrl", 0) & 1,
        sys_mgmt_rx=0,
        reserved=0,
        data_length=data_length,
    )


def _build_ctrl_bits(
    ctrl_fields: dict[str, int], frame_type: int,
) -> np.ndarray:
    """从 QoS 控制字段构建控制信息比特。"""
    if frame_type == 2:
        bits = np.zeros(28, dtype=np.int8)
        bits[3] = ctrl_fields.get("tx_sn", 0) & 1
        bits[4] = ctrl_fields.get("rx_sn", 0) & 1
        bits[5] = ctrl_fields.get("flow_ctrl", 0) & 1
    elif frame_type in (3, 4):
        bits = np.zeros(27, dtype=np.int8)
        tx_sn = ctrl_fields.get("tx_sn", 0) & 0x1F
        for i in range(5):
            bits[3 + i] = (tx_sn >> (4 - i)) & 1
        rx_sn = ctrl_fields.get("rx_sn", 0) & 0x1F
        for i in range(5):
            bits[8 + i] = (rx_sn >> (4 - i)) & 1
        bits[13] = ctrl_fields.get("flow_ctrl", 0) & 1
    else:
        bits = np.zeros(20, dtype=np.int8)
    return bits
