"""控制面信令注册表 -- TXS-10002-2025 标准 7.3.2 / 附录 G

维护 data_type_index 到信令类型的映射, 支持自动编解码。
"""

from __future__ import annotations

from typing import Any

from nearlink_sdr.mac.frame import ControlFrame
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
    0x0019: ("功率控制请求", PowerControlRequest, 3),
    0x001A: ("功率控制响应", PowerControlResponse, 4),
    0x001B: ("功率变化指示", PowerChangeIndication, 4),
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
