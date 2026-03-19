"""链路控制信令 -- TXS-10002-2025 标准 7.3.2.2-7.3.2.32

提供链路建立、参数协商、断开等核心控制面信令的编解码。
"""

from __future__ import annotations

import struct
from dataclasses import dataclass

# ---------------------------------------------------------------------------
# 7.3.2.2 收发间隔更新请求 (0x0001, 8 bits / 1 byte)
# ---------------------------------------------------------------------------

@dataclass
class IntervalUpdateRequest:
    """收发间隔更新请求。

    字段:
    - interval_type: 4 bits, 响应的收发间隔类型 (0-15)
    - reserved:      4 bits
    """
    interval_type: int  # 0-15

    DATA_TYPE_INDEX = 0x0001
    BYTE_LENGTH = 1

    def pack(self) -> bytes:
        return bytes([(self.interval_type & 0x0F) << 4])

    @classmethod
    def unpack(cls, data: bytes) -> IntervalUpdateRequest:
        if len(data) < cls.BYTE_LENGTH:
            raise ValueError(f"数据不足: 需要 {cls.BYTE_LENGTH} 字节")
        return cls(interval_type=(data[0] >> 4) & 0x0F)


# ---------------------------------------------------------------------------
# 7.3.2.3 收发间隔更新响应 (0x0002, 64 bits / 8 bytes)
# ---------------------------------------------------------------------------

@dataclass
class IntervalUpdateResponse:
    """收发间隔更新响应。

    字段:
    - link_id:           24 bits, 逻辑链路标识
    - interval_type:     4 bits, 更新后的收发间隔类型
    - reserved:          4 bits
    - effective_slot:    32 bits, 信令生效时隙号
    """
    link_id: int           # 1 ~ 2^24-1
    interval_type: int     # 0-15
    effective_slot: int    # 0 ~ 2^30-1

    DATA_TYPE_INDEX = 0x0002
    BYTE_LENGTH = 8

    def pack(self) -> bytes:
        b = self.link_id.to_bytes(3, "big")
        b += bytes([(self.interval_type & 0x0F) << 4])
        b += self.effective_slot.to_bytes(4, "big")
        return b

    @classmethod
    def unpack(cls, data: bytes) -> IntervalUpdateResponse:
        if len(data) < cls.BYTE_LENGTH:
            raise ValueError(f"数据不足: 需要 {cls.BYTE_LENGTH} 字节")
        link_id = int.from_bytes(data[0:3], "big")
        interval_type = (data[3] >> 4) & 0x0F
        effective_slot = int.from_bytes(data[4:8], "big")
        return cls(link_id, interval_type, effective_slot)


# ---------------------------------------------------------------------------
# 7.3.2.5 信令被拒指示 (0x0003, 24 bits / 3 bytes)
# ---------------------------------------------------------------------------

@dataclass
class SignalingReject:
    """信令被拒指示。

    字段:
    - rejected_index: 16 bits, 被拒的数据类型索引
    - error_reason:    8 bits, 出错原因
    """
    rejected_index: int  # 0-65535
    error_reason: int    # 0-255

    DATA_TYPE_INDEX = 0x0003
    BYTE_LENGTH = 3

    def pack(self) -> bytes:
        return self.rejected_index.to_bytes(2, "big") + bytes([self.error_reason & 0xFF])

    @classmethod
    def unpack(cls, data: bytes) -> SignalingReject:
        if len(data) < cls.BYTE_LENGTH:
            raise ValueError(f"数据不足: 需要 {cls.BYTE_LENGTH} 字节")
        rejected_index = int.from_bytes(data[0:2], "big")
        return cls(rejected_index, data[2])


# ---------------------------------------------------------------------------
# 7.3.2.12 特性交互请求 (0x000A, 80 bits / 10 bytes)
# ---------------------------------------------------------------------------

@dataclass
class FeatureExchangeRequest:
    """特性交互请求: 80-bit 特性集位图。"""
    feature_set: int  # 0 ~ 2^80-1

    DATA_TYPE_INDEX = 0x000A
    BYTE_LENGTH = 10

    def pack(self) -> bytes:
        return self.feature_set.to_bytes(10, "big")

    @classmethod
    def unpack(cls, data: bytes) -> FeatureExchangeRequest:
        if len(data) < cls.BYTE_LENGTH:
            raise ValueError(f"数据不足: 需要 {cls.BYTE_LENGTH} 字节")
        return cls(int.from_bytes(data[:10], "big"))


# ---------------------------------------------------------------------------
# 7.3.2.13 特性交互响应 (0x000B, 80 bits / 10 bytes)
# ---------------------------------------------------------------------------

@dataclass
class FeatureExchangeResponse:
    """特性交互响应: 80-bit 特性集位图。"""
    feature_set: int  # 0 ~ 2^80-1

    DATA_TYPE_INDEX = 0x000B
    BYTE_LENGTH = 10

    def pack(self) -> bytes:
        return self.feature_set.to_bytes(10, "big")

    @classmethod
    def unpack(cls, data: bytes) -> FeatureExchangeResponse:
        if len(data) < cls.BYTE_LENGTH:
            raise ValueError(f"数据不足: 需要 {cls.BYTE_LENGTH} 字节")
        return cls(int.from_bytes(data[:10], "big"))


# ---------------------------------------------------------------------------
# 7.3.2.15 版本交互指示 (0x000D, 40 bits / 5 bytes)
# ---------------------------------------------------------------------------

@dataclass
class VersionExchange:
    """版本交互指示。

    字段:
    - spec_version:     8 bits, 规格版本
    - company_id:      16 bits, 公司标识符
    - sub_version:     16 bits, 子规格版本
    """
    spec_version: int   # 0-255
    company_id: int     # 0-65535
    sub_version: int    # 0-65535

    DATA_TYPE_INDEX = 0x000D
    BYTE_LENGTH = 5

    def pack(self) -> bytes:
        return (bytes([self.spec_version & 0xFF])
                + self.company_id.to_bytes(2, "big")
                + self.sub_version.to_bytes(2, "big"))

    @classmethod
    def unpack(cls, data: bytes) -> VersionExchange:
        if len(data) < cls.BYTE_LENGTH:
            raise ValueError(f"数据不足: 需要 {cls.BYTE_LENGTH} 字节")
        return cls(data[0], int.from_bytes(data[1:3], "big"),
                   int.from_bytes(data[3:5], "big"))


# ---------------------------------------------------------------------------
# 7.3.2.16 数据长度请求 (0x000E, 64 bits / 8 bytes)
# ---------------------------------------------------------------------------

@dataclass
class DataLengthRequest:
    """数据长度请求 (MTU 协商)。

    字段:
    - max_rx_bytes: 16 bits, 最大接收字节数 (31-2047)
    - max_rx_time:  16 bits, 最大接收时间 (346-65535 us)
    - max_tx_bytes: 16 bits, 最大发送字节数 (31-2047)
    - max_tx_time:  16 bits, 最大发送时间 (346-65535 us)
    """
    max_rx_bytes: int
    max_rx_time: int
    max_tx_bytes: int
    max_tx_time: int

    DATA_TYPE_INDEX = 0x000E
    BYTE_LENGTH = 8

    def pack(self) -> bytes:
        return struct.pack(">HHHH", self.max_rx_bytes, self.max_rx_time,
                           self.max_tx_bytes, self.max_tx_time)

    @classmethod
    def unpack(cls, data: bytes) -> DataLengthRequest:
        if len(data) < cls.BYTE_LENGTH:
            raise ValueError(f"数据不足: 需要 {cls.BYTE_LENGTH} 字节")
        vals = struct.unpack(">HHHH", data[:8])
        return cls(*vals)


# ---------------------------------------------------------------------------
# 7.3.2.17 数据长度响应 (0x000F, 64 bits / 8 bytes)
# ---------------------------------------------------------------------------

@dataclass
class DataLengthResponse:
    """数据长度响应。字段与 DataLengthRequest 相同。"""
    max_rx_bytes: int
    max_rx_time: int
    max_tx_bytes: int
    max_tx_time: int

    DATA_TYPE_INDEX = 0x000F
    BYTE_LENGTH = 8

    def pack(self) -> bytes:
        return struct.pack(">HHHH", self.max_rx_bytes, self.max_rx_time,
                           self.max_tx_bytes, self.max_tx_time)

    @classmethod
    def unpack(cls, data: bytes) -> DataLengthResponse:
        if len(data) < cls.BYTE_LENGTH:
            raise ValueError(f"数据不足: 需要 {cls.BYTE_LENGTH} 字节")
        vals = struct.unpack(">HHHH", data[:8])
        return cls(*vals)


# ---------------------------------------------------------------------------
# 7.3.2.18 信道上报指示 (0x0010, 24 bits / 3 bytes)
# ---------------------------------------------------------------------------

@dataclass
class ChannelReportConfig:
    """信道上报指示。

    字段:
    - enable:       8 bits, 使能信道上报 (0 或 1)
    - min_interval: 8 bits, 最小时间间隔 (5-150, 单位 200ms)
    - max_delay:    8 bits, 最大时延 (5-150, 单位 200ms)
    """
    enable: int        # 0 或 1
    min_interval: int  # 5-150
    max_delay: int     # 5-150

    DATA_TYPE_INDEX = 0x0010
    BYTE_LENGTH = 3

    def pack(self) -> bytes:
        return bytes([self.enable & 0xFF, self.min_interval & 0xFF,
                      self.max_delay & 0xFF])

    @classmethod
    def unpack(cls, data: bytes) -> ChannelReportConfig:
        if len(data) < cls.BYTE_LENGTH:
            raise ValueError(f"数据不足: 需要 {cls.BYTE_LENGTH} 字节")
        return cls(data[0], data[1], data[2])


# ---------------------------------------------------------------------------
# 7.3.2.23 CRC 切换请求 (0x0015, 96 bits / 12 bytes)
# ---------------------------------------------------------------------------

@dataclass
class CrcSwitchRequest:
    """CRC 切换请求。

    字段:
    - link_id:         24 bits, 逻辑链路标识
    - tx_crc_type:      1 bit, 先发链路 CRC 类型 (0=CRC24, 1=CRC32)
    - rx_crc_type:      1 bit, 后发链路 CRC 类型
    - reserved:         6 bits
    - tx_crc_init:     32 bits, 先发链路 CRC 初始值
    - rx_crc_init:     32 bits, 后发链路 CRC 初始值
    """
    link_id: int
    tx_crc_type: int     # 0=CRC24, 1=CRC32
    rx_crc_type: int     # 0=CRC24, 1=CRC32
    tx_crc_init: int     # CRC 初始值
    rx_crc_init: int     # CRC 初始值

    DATA_TYPE_INDEX = 0x0015
    BYTE_LENGTH = 12

    def pack(self) -> bytes:
        b = self.link_id.to_bytes(3, "big")
        flags = ((self.tx_crc_type & 1) << 7) | ((self.rx_crc_type & 1) << 6)
        b += bytes([flags])
        b += self.tx_crc_init.to_bytes(4, "big")
        b += self.rx_crc_init.to_bytes(4, "big")
        return b

    @classmethod
    def unpack(cls, data: bytes) -> CrcSwitchRequest:
        if len(data) < cls.BYTE_LENGTH:
            raise ValueError(f"数据不足: 需要 {cls.BYTE_LENGTH} 字节")
        link_id = int.from_bytes(data[0:3], "big")
        tx_crc_type = (data[3] >> 7) & 1
        rx_crc_type = (data[3] >> 6) & 1
        tx_crc_init = int.from_bytes(data[4:8], "big")
        rx_crc_init = int.from_bytes(data[8:12], "big")
        return cls(link_id, tx_crc_type, rx_crc_type, tx_crc_init, rx_crc_init)


# ---------------------------------------------------------------------------
# 7.3.2.24 CRC 切换指示 (0x0016, 128 bits / 16 bytes)
# ---------------------------------------------------------------------------

@dataclass
class CrcSwitchIndication:
    """CRC 切换指示。增加生效时隙号。"""
    link_id: int
    tx_crc_type: int
    rx_crc_type: int
    tx_crc_init: int
    rx_crc_init: int
    effective_slot: int  # 32 bits

    DATA_TYPE_INDEX = 0x0016
    BYTE_LENGTH = 16

    def pack(self) -> bytes:
        b = self.link_id.to_bytes(3, "big")
        flags = ((self.tx_crc_type & 1) << 7) | ((self.rx_crc_type & 1) << 6)
        b += bytes([flags])
        b += self.tx_crc_init.to_bytes(4, "big")
        b += self.rx_crc_init.to_bytes(4, "big")
        b += self.effective_slot.to_bytes(4, "big")
        return b

    @classmethod
    def unpack(cls, data: bytes) -> CrcSwitchIndication:
        if len(data) < cls.BYTE_LENGTH:
            raise ValueError(f"数据不足: 需要 {cls.BYTE_LENGTH} 字节")
        link_id = int.from_bytes(data[0:3], "big")
        tx_crc_type = (data[3] >> 7) & 1
        rx_crc_type = (data[3] >> 6) & 1
        tx_crc_init = int.from_bytes(data[4:8], "big")
        rx_crc_init = int.from_bytes(data[8:12], "big")
        effective_slot = int.from_bytes(data[12:16], "big")
        return cls(link_id, tx_crc_type, rx_crc_type,
                   tx_crc_init, rx_crc_init, effective_slot)


# ---------------------------------------------------------------------------
# 7.3.2.30 时钟精度请求 (0x001C, 8 bits / 1 byte)
# ---------------------------------------------------------------------------

@dataclass
class ClockAccuracyRequest:
    """时钟精度请求。"""
    accuracy: int  # 0-255, 枚举

    DATA_TYPE_INDEX = 0x001C
    BYTE_LENGTH = 1

    def pack(self) -> bytes:
        return bytes([self.accuracy & 0xFF])

    @classmethod
    def unpack(cls, data: bytes) -> ClockAccuracyRequest:
        if len(data) < cls.BYTE_LENGTH:
            raise ValueError(f"数据不足: 需要 {cls.BYTE_LENGTH} 字节")
        return cls(data[0])


# ---------------------------------------------------------------------------
# 7.3.2.31 时钟精度响应 (0x001D, 8 bits / 1 byte)
# ---------------------------------------------------------------------------

@dataclass
class ClockAccuracyResponse:
    """时钟精度响应。"""
    accuracy: int  # 0-255

    DATA_TYPE_INDEX = 0x001D
    BYTE_LENGTH = 1

    def pack(self) -> bytes:
        return bytes([self.accuracy & 0xFF])

    @classmethod
    def unpack(cls, data: bytes) -> ClockAccuracyResponse:
        if len(data) < cls.BYTE_LENGTH:
            raise ValueError(f"数据不足: 需要 {cls.BYTE_LENGTH} 字节")
        return cls(data[0])


# ---------------------------------------------------------------------------
# 7.3.2.32 链路断开指示 (0x001E, 32 bits / 4 bytes)
# ---------------------------------------------------------------------------

@dataclass
class LinkDisconnect:
    """链路断开指示。

    字段:
    - link_id:      24 bits, 逻辑链路标识
    - error_reason:  8 bits, 出错原因
    """
    link_id: int      # 0 ~ 2^24-1
    error_reason: int  # 0-255

    DATA_TYPE_INDEX = 0x001E
    BYTE_LENGTH = 4

    def pack(self) -> bytes:
        return self.link_id.to_bytes(3, "big") + bytes([self.error_reason & 0xFF])

    @classmethod
    def unpack(cls, data: bytes) -> LinkDisconnect:
        if len(data) < cls.BYTE_LENGTH:
            raise ValueError(f"数据不足: 需要 {cls.BYTE_LENGTH} 字节")
        link_id = int.from_bytes(data[0:3], "big")
        return cls(link_id, data[3])
