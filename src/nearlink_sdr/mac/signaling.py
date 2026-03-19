"""控制面信令注册表 -- TXS-10002-2025 标准 7.3.2 / 附录 G

维护 data_type_index 到信令类型的映射, 支持自动编解码。
"""

from __future__ import annotations

from typing import Any

from nearlink_sdr.mac.frame import ControlFrame
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
    IntervalUpdateRequest,
    IntervalUpdateResponse,
    LinkDisconnect,
    SignalingReject,
    VersionExchange,
)
from nearlink_sdr.mac.power_control import (
    PowerChangeIndication,
    PowerControlRequest,
    PowerControlResponse,
)

# ---------------------------------------------------------------------------
# 信令注册表
# ---------------------------------------------------------------------------

# data_type_index -> (名称, 信令类, 字节长度)
_SIGNALING_REGISTRY: dict[int, tuple[str, type, int]] = {
    0x0001: ("收发间隔更新请求", IntervalUpdateRequest, 1),
    0x0002: ("收发间隔更新响应", IntervalUpdateResponse, 8),
    0x0003: ("信令被拒指示", SignalingReject, 3),
    0x000A: ("特性交互请求", FeatureExchangeRequest, 10),
    0x000B: ("特性交互响应", FeatureExchangeResponse, 10),
    0x000D: ("版本交互指示", VersionExchange, 5),
    0x000E: ("数据长度请求", DataLengthRequest, 8),
    0x000F: ("数据长度响应", DataLengthResponse, 8),
    0x0010: ("信道上报指示", ChannelReportConfig, 3),
    0x0015: ("CRC切换请求", CrcSwitchRequest, 12),
    0x0016: ("CRC切换指示", CrcSwitchIndication, 16),
    0x0019: ("功率控制请求", PowerControlRequest, 3),
    0x001A: ("功率控制响应", PowerControlResponse, 4),
    0x001B: ("功率变化指示", PowerChangeIndication, 4),
    0x001C: ("时钟精度请求", ClockAccuracyRequest, 1),
    0x001D: ("时钟精度响应", ClockAccuracyResponse, 1),
    0x001E: ("链路断开指示", LinkDisconnect, 4),
}


def register_signaling(data_type_index: int, name: str, cls: type, byte_length: int) -> None:
    """注册一个新的信令类型。

    信令类必须实现 pack() -> bytes 和 unpack(bytes) -> Self 方法。
    """
    _SIGNALING_REGISTRY[data_type_index] = (name, cls, byte_length)


def encode_signaling(msg: Any) -> ControlFrame:
    """将信令消息编码为控制面帧。"""
    data_type_index = msg.DATA_TYPE_INDEX
    payload = msg.pack()
    return ControlFrame(data_type_index, payload)


def decode_signaling(frame: ControlFrame) -> Any:
    """将控制面帧解码为信令消息。

    如果 data_type_index 未注册, 返回原始 ControlFrame。
    """
    entry = _SIGNALING_REGISTRY.get(frame.data_type_index)
    if entry is None:
        return frame
    _name, cls, _byte_len = entry
    return cls.unpack(frame.payload)


def get_signaling_name(data_type_index: int) -> str:
    """获取信令名称, 未注册则返回 '未知'。"""
    entry = _SIGNALING_REGISTRY.get(data_type_index)
    return entry[0] if entry else "未知"


def list_registered() -> list[tuple[int, str, int]]:
    """列出所有已注册的信令类型: [(index, name, byte_length), ...]"""
    return [(idx, name, blen) for idx, (name, _cls, blen) in sorted(_SIGNALING_REGISTRY.items())]
