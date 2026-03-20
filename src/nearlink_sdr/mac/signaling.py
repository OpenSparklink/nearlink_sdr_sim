"""控制面信令注册表 -- TXS-10002-2025 标准 7.3.2 / 附录 G

维护 data_type_index 到信令类型的映射, 支持自动编解码。
"""

from __future__ import annotations

from typing import Any

from nearlink_sdr.mac.frame import ControlFrame
from nearlink_sdr.mac.link_control import (
    AsyncLinkParamRequest,
    AsyncLinkParamResponse,
    AsyncMulticastReconfig,
    AsyncUnicastUpdate,
    BroadcastHopMapUpdate,
    BroadcastLinkDisconnect,
    BroadcastLinkParamUpdate,
    BroadcastLinkSetup,
    ChannelReportConfig,
    ChannelStatusIndication,
    ClockAccuracyRequest,
    ClockAccuracyResponse,
    CrcSwitchIndication,
    CrcSwitchRequest,
    DataLengthRequest,
    DataLengthResponse,
    FeatureExchangeRequest,
    FeatureExchangeResponse,
    HopMapUpdate,
    HopTableUpdate,
    IntervalUpdateIndication,
    IntervalUpdateRequest,
    IntervalUpdateResponse,
    IsochronousLinkSetup,
    IsochronousParamExchangeRequest,
    IsochronousParamExchangeResponse,
    IsochronousParamUpdateIndication,
    IsochronousParamUpdateRequest,
    LinkDisconnect,
    MinAvailableChannels,
    MulticastDisconnect,
    PhyUpdateIndication,
    PhyUpdateRequest,
    PingRequest,
    PingResponse,
    RoleSwitchRequest,
    SecurityPauseRequest,
    SecurityPauseResponse,
    SecurityRequest,
    SecurityResponse,
    SecurityStartRequest,
    SecurityStartResponse,
    SignalingReject,
    SMFParamUpdateIndication,
    SMFParamUpdateRequest,
    SMFSignalingTerminate,
    SMFTimeSlotUpdateRequest,
    SMFTimeSlotUpdateResponse,
    TimeOffsetIndication,
    TimeoutUpdateRequest,
    UnknownFeatureFeedback,
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
    0x0000: ("收发间隔更新请求", IntervalUpdateRequest, 1),
    0x0001: ("收发间隔更新响应", IntervalUpdateResponse, 1),
    0x0002: ("收发间隔更新指示", IntervalUpdateIndication, 8),
    0x0003: ("信令被拒指示", SignalingReject, 3),
    0x0004: ("安全请求", SecurityRequest, 13),
    0x0005: ("安全响应", SecurityResponse, 12),
    0x0006: ("安全启动请求", SecurityStartRequest, 0),
    0x0007: ("安全启动响应", SecurityStartResponse, 1),
    0x0008: ("安全暂停请求", SecurityPauseRequest, 0),
    0x0009: ("安全暂停响应", SecurityPauseResponse, 0),
    0x000A: ("特性交互请求", FeatureExchangeRequest, 10),
    0x000B: ("特性交互响应", FeatureExchangeResponse, 10),
    0x000C: ("未知特性反馈", UnknownFeatureFeedback, 2),
    0x000D: ("版本交互指示", VersionExchange, 5),
    0x000E: ("数据长度请求", DataLengthRequest, 8),
    0x000F: ("数据长度响应", DataLengthResponse, 8),
    0x0010: ("信道上报指示", ChannelReportConfig, 3),
    0x0011: ("信道状态指示", ChannelStatusIndication, 20),
    0x0012: ("跳频表更新指示", HopTableUpdate, 5),
    0x0013: ("跳频地图更新指示", HopMapUpdate, 14),
    0x0014: ("最少可用信道指示", MinAvailableChannels, 2),
    0x0015: ("CRC切换请求", CrcSwitchRequest, 12),
    0x0016: ("CRC切换指示", CrcSwitchIndication, 16),
    0x0017: ("物理层更新请求", PhyUpdateRequest, 4),
    0x0018: ("物理层更新指示", PhyUpdateIndication, 8),
    0x0019: ("功率控制请求", PowerControlRequest, 3),
    0x001A: ("功率控制响应", PowerControlResponse, 4),
    0x001B: ("功率变化指示", PowerChangeIndication, 4),
    0x001C: ("时钟精度请求", ClockAccuracyRequest, 1),
    0x001D: ("时钟精度响应", ClockAccuracyResponse, 1),
    0x001E: ("链路断开指示", LinkDisconnect, 4),
    0x001F: ("异步组播链路参数重配置指示", AsyncMulticastReconfig, 31),
    0x0020: ("链接态异步链路参数更新请求", AsyncLinkParamRequest, 27),
    0x0021: ("链接态异步链路参数更新响应", AsyncLinkParamResponse, 27),
    0x0022: ("同步等时链路建链指示", IsochronousLinkSetup, 56),
    0x0023: ("同步等时链路参数交互请求", IsochronousParamExchangeRequest, 52),
    0x0024: ("同步等时链路参数交互响应", IsochronousParamExchangeResponse, 52),
    0x0025: ("同步等时链路参数更新请求", IsochronousParamUpdateRequest, 3),
    0x0026: ("同步等时链路参数更新指示", IsochronousParamUpdateIndication, 9),
    0x0027: ("链接态广播链路建立指示", BroadcastLinkSetup, 44),
    0x0028: ("广播链路参数更新指示", BroadcastLinkParamUpdate, 32),
    0x0029: ("广播链路跳频地图更新指示", BroadcastHopMapUpdate, 14),
    0x002A: ("广播链路断开指示", BroadcastLinkDisconnect, 5),
    0x002B: ("系统管理帧参数更新请求", SMFParamUpdateRequest, 8),
    0x002C: ("系统管理帧参数更新指示", SMFParamUpdateIndication, 12),
    0x002D: ("系统管理帧时间片更新请求", SMFTimeSlotUpdateRequest, 13),
    0x002E: ("系统管理帧时间片更新响应", SMFTimeSlotUpdateResponse, 9),
    0x0030: ("系统管理帧信令传输终止", SMFSignalingTerminate, 1),
    0x0031: ("角色切换请求", RoleSwitchRequest, 4),
    0x0032: ("时间偏移指示", TimeOffsetIndication, 8),
    0x0033: ("PING请求", PingRequest, 0),
    0x0034: ("PING响应", PingResponse, 0),
    0x003A: ("链接态单播异步链路参数更新指示", AsyncUnicastUpdate, 15),
    0x003C: ("超时时间更新请求", TimeoutUpdateRequest, 2),
    0x003D: ("组播链路断开指示", MulticastDisconnect, 3),
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
