"""链路控制信令 -- TXS-10002-2025 标准 7.3.2.2-7.3.2.32

提供链路建立、参数协商、断开等核心控制面信令的编解码。
"""

from __future__ import annotations

import struct
from dataclasses import dataclass

# ---------------------------------------------------------------------------
# 7.3.2.2 收发间隔更新请求 (0x0000, 8 bits / 1 byte)
# ---------------------------------------------------------------------------

@dataclass
class IntervalUpdateRequest:
    """收发间隔更新请求。

    字段:
    - interval_type: 4 bits, 请求的收发间隔类型 (0-15)
    - reserved:      4 bits
    """
    interval_type: int  # 0-15

    DATA_TYPE_INDEX = 0x0000
    BYTE_LENGTH = 1

    def pack(self) -> bytes:
        return bytes([(self.interval_type & 0x0F) << 4])

    @classmethod
    def unpack(cls, data: bytes) -> IntervalUpdateRequest:
        if len(data) < cls.BYTE_LENGTH:
            raise ValueError(f"数据不足: 需要 {cls.BYTE_LENGTH} 字节")
        return cls(interval_type=(data[0] >> 4) & 0x0F)


# ---------------------------------------------------------------------------
# 7.3.2.3 收发间隔更新响应 (0x0001, 8 bits / 1 byte)
# ---------------------------------------------------------------------------

@dataclass
class IntervalUpdateResponse:
    """收发间隔更新响应。

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
    def unpack(cls, data: bytes) -> IntervalUpdateResponse:
        if len(data) < cls.BYTE_LENGTH:
            raise ValueError(f"数据不足: 需要 {cls.BYTE_LENGTH} 字节")
        return cls(interval_type=(data[0] >> 4) & 0x0F)


# ---------------------------------------------------------------------------
# 7.3.2.4 收发间隔更新指示 (0x0002, 64 bits / 8 bytes)
# ---------------------------------------------------------------------------

@dataclass
class IntervalUpdateIndication:
    """收发间隔更新指示。

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
    def unpack(cls, data: bytes) -> IntervalUpdateIndication:
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


# ---------------------------------------------------------------------------
# 7.3.2.6 安全请求 (0x0004, 104 bits / 13 bytes)
# ---------------------------------------------------------------------------

@dataclass
class SecurityRequest:
    """安全请求。

    字段:
    - g_node_iv:       32 bits, G节点初始化向量
    - g_node_skd:      64 bits, G节点连接密钥分散器
    - enc_indication:   8 bits, 加密和完整性保护指示
    """
    g_node_iv: int
    g_node_skd: int
    enc_indication: int

    DATA_TYPE_INDEX = 0x0004
    BYTE_LENGTH = 13

    def pack(self) -> bytes:
        return (self.g_node_iv.to_bytes(4, "big")
                + self.g_node_skd.to_bytes(8, "big")
                + bytes([self.enc_indication & 0xFF]))

    @classmethod
    def unpack(cls, data: bytes) -> SecurityRequest:
        if len(data) < cls.BYTE_LENGTH:
            raise ValueError(f"数据不足: 需要 {cls.BYTE_LENGTH} 字节")
        g_iv = int.from_bytes(data[0:4], "big")
        g_skd = int.from_bytes(data[4:12], "big")
        return cls(g_iv, g_skd, data[12])


# ---------------------------------------------------------------------------
# 7.3.2.7 安全响应 (0x0005, 96 bits / 12 bytes)
# ---------------------------------------------------------------------------

@dataclass
class SecurityResponse:
    """安全响应。

    字段:
    - t_node_iv:  32 bits, T节点初始化向量
    - t_node_skd: 64 bits, T节点连接密钥分散器
    """
    t_node_iv: int
    t_node_skd: int

    DATA_TYPE_INDEX = 0x0005
    BYTE_LENGTH = 12

    def pack(self) -> bytes:
        return (self.t_node_iv.to_bytes(4, "big")
                + self.t_node_skd.to_bytes(8, "big"))

    @classmethod
    def unpack(cls, data: bytes) -> SecurityResponse:
        if len(data) < cls.BYTE_LENGTH:
            raise ValueError(f"数据不足: 需要 {cls.BYTE_LENGTH} 字节")
        return cls(int.from_bytes(data[0:4], "big"),
                   int.from_bytes(data[4:12], "big"))


# ---------------------------------------------------------------------------
# 7.3.2.8 安全启动请求 (0x0006, 0 bytes)
# ---------------------------------------------------------------------------

@dataclass
class SecurityStartRequest:
    """安全启动请求 (无载荷)。"""

    DATA_TYPE_INDEX = 0x0006
    BYTE_LENGTH = 0

    def pack(self) -> bytes:
        return b""

    @classmethod
    def unpack(cls, data: bytes) -> SecurityStartRequest:
        return cls()


# ---------------------------------------------------------------------------
# 7.3.2.9 安全启动响应 (0x0007, 8 bits / 1 byte)
# ---------------------------------------------------------------------------

@dataclass
class SecurityStartResponse:
    """安全启动响应。

    字段:
    - enc_indication: 8 bits, 加密和完整性保护指示
    """
    enc_indication: int

    DATA_TYPE_INDEX = 0x0007
    BYTE_LENGTH = 1

    def pack(self) -> bytes:
        return bytes([self.enc_indication & 0xFF])

    @classmethod
    def unpack(cls, data: bytes) -> SecurityStartResponse:
        if len(data) < cls.BYTE_LENGTH:
            raise ValueError(f"数据不足: 需要 {cls.BYTE_LENGTH} 字节")
        return cls(data[0])


# ---------------------------------------------------------------------------
# 7.3.2.10 安全暂停请求 (0x0008, 0 bytes)
# ---------------------------------------------------------------------------

@dataclass
class SecurityPauseRequest:
    """安全暂停请求 (无载荷)。"""

    DATA_TYPE_INDEX = 0x0008
    BYTE_LENGTH = 0

    def pack(self) -> bytes:
        return b""

    @classmethod
    def unpack(cls, data: bytes) -> SecurityPauseRequest:
        return cls()


# ---------------------------------------------------------------------------
# 7.3.2.11 安全暂停响应 (0x0009, 0 bytes)
# ---------------------------------------------------------------------------

@dataclass
class SecurityPauseResponse:
    """安全暂停响应 (无载荷)。"""

    DATA_TYPE_INDEX = 0x0009
    BYTE_LENGTH = 0

    def pack(self) -> bytes:
        return b""

    @classmethod
    def unpack(cls, data: bytes) -> SecurityPauseResponse:
        return cls()


# ---------------------------------------------------------------------------
# 7.3.2.14 未知特性反馈 (0x000C, 16 bits / 2 bytes)
# ---------------------------------------------------------------------------

@dataclass
class UnknownFeatureFeedback:
    """未知特性反馈。

    字段:
    - unknown_type: 16 bits, 收到的未知数据类型索引
    """
    unknown_type: int

    DATA_TYPE_INDEX = 0x000C
    BYTE_LENGTH = 2

    def pack(self) -> bytes:
        return self.unknown_type.to_bytes(2, "big")

    @classmethod
    def unpack(cls, data: bytes) -> UnknownFeatureFeedback:
        if len(data) < cls.BYTE_LENGTH:
            raise ValueError(f"数据不足: 需要 {cls.BYTE_LENGTH} 字节")
        return cls(int.from_bytes(data[:2], "big"))


# ---------------------------------------------------------------------------
# 7.3.2.19 信道状态指示 (0x0011, 160 bits / 20 bytes)
# ---------------------------------------------------------------------------

@dataclass
class ChannelStatusIndication:
    """信道状态指示。

    字段:
    - channel_map: 160 bits, 每信道 2 bit 质量指示 (0=未知, 1=好, 3=差)
    """
    channel_map: bytes  # 20 bytes

    DATA_TYPE_INDEX = 0x0011
    BYTE_LENGTH = 20

    def pack(self) -> bytes:
        return self.channel_map[:20].ljust(20, b"\x00")

    @classmethod
    def unpack(cls, data: bytes) -> ChannelStatusIndication:
        if len(data) < cls.BYTE_LENGTH:
            raise ValueError(f"数据不足: 需要 {cls.BYTE_LENGTH} 字节")
        return cls(bytes(data[:20]))


# ---------------------------------------------------------------------------
# 7.3.2.20 跳频表更新指示 (0x0012, 可变长度)
# ---------------------------------------------------------------------------

@dataclass
class HopTableUpdate:
    """跳频表更新指示 (系统管理帧)。

    字段:
    - effective_slot: 32 bits, 信令生效时隙号
    - channel_count:   8 bits, 跳频表频点个数
    - channel_table:  可变,  跳频表频点列表
    """
    effective_slot: int
    channel_count: int
    channel_table: bytes

    DATA_TYPE_INDEX = 0x0012
    BYTE_LENGTH = 5  # 最小长度

    def pack(self) -> bytes:
        return (self.effective_slot.to_bytes(4, "big")
                + bytes([self.channel_count & 0xFF])
                + self.channel_table)

    @classmethod
    def unpack(cls, data: bytes) -> HopTableUpdate:
        if len(data) < 5:
            raise ValueError("数据不足: 至少需要 5 字节")
        slot = int.from_bytes(data[0:4], "big")
        count = data[4]
        table = bytes(data[5:5 + count])
        return cls(slot, count, table)


# ---------------------------------------------------------------------------
# 7.3.2.21 跳频地图更新指示 (0x0013, 112 bits / 14 bytes)
# ---------------------------------------------------------------------------

@dataclass
class HopMapUpdate:
    """跳频地图更新指示 (数据链路)。

    字段:
    - hop_map:        80 bits, 跳频地图位图
    - effective_slot: 32 bits, 信令生效时隙号
    """
    hop_map: bytes         # 10 bytes
    effective_slot: int

    DATA_TYPE_INDEX = 0x0013
    BYTE_LENGTH = 14

    def pack(self) -> bytes:
        return self.hop_map[:10].ljust(10, b"\x00") + self.effective_slot.to_bytes(4, "big")

    @classmethod
    def unpack(cls, data: bytes) -> HopMapUpdate:
        if len(data) < cls.BYTE_LENGTH:
            raise ValueError(f"数据不足: 需要 {cls.BYTE_LENGTH} 字节")
        return cls(bytes(data[:10]), int.from_bytes(data[10:14], "big"))


# ---------------------------------------------------------------------------
# 7.3.2.22 最少可用信道指示 (0x0014, 16 bits / 2 bytes)
# ---------------------------------------------------------------------------

@dataclass
class MinAvailableChannels:
    """最少可用信道指示。

    字段:
    - frame_type:     4 bits, 无线帧类型
    - bandwidth:      2 bits, 带宽指示
    - pilot_density:  2 bits, 导频密度指示
    - min_channels:   8 bits, 最小信道数 (2-76)
    """
    frame_type: int
    bandwidth: int
    pilot_density: int
    min_channels: int

    DATA_TYPE_INDEX = 0x0014
    BYTE_LENGTH = 2

    def pack(self) -> bytes:
        b0 = ((self.frame_type & 0x0F) << 4
              | (self.bandwidth & 0x03) << 2
              | (self.pilot_density & 0x03))
        return bytes([b0, self.min_channels & 0xFF])

    @classmethod
    def unpack(cls, data: bytes) -> MinAvailableChannels:
        if len(data) < cls.BYTE_LENGTH:
            raise ValueError(f"数据不足: 需要 {cls.BYTE_LENGTH} 字节")
        ft = (data[0] >> 4) & 0x0F
        bw = (data[0] >> 2) & 0x03
        pd = data[0] & 0x03
        return cls(ft, bw, pd, data[1])


# ---------------------------------------------------------------------------
# 7.3.2.25 物理层更新请求 (0x0017, 32 bits / 4 bytes)
# ---------------------------------------------------------------------------

@dataclass
class PhyUpdateRequest:
    """物理层更新请求。

    字段:
    - tx_frame_type:      4 bits, 先发链路无线帧类型
    - rx_frame_type:      4 bits, 后发链路无线帧类型
    - tx_bandwidth:       2 bits, 先发链路带宽
    - rx_bandwidth:       2 bits, 后发链路带宽
    - tx_pilot_density:   2 bits, 先发链路导频密度
    - rx_pilot_density:   2 bits, 后发链路导频密度
    - tx_feedback_type:   6 bits, 先发链路反馈类型
    - rx_feedback_type:   3 bits, 后发链路反馈类型
    - reserved:           7 bits
    """
    tx_frame_type: int
    rx_frame_type: int
    tx_bandwidth: int
    rx_bandwidth: int
    tx_pilot_density: int
    rx_pilot_density: int
    tx_feedback_type: int
    rx_feedback_type: int

    DATA_TYPE_INDEX = 0x0017
    BYTE_LENGTH = 4

    def pack(self) -> bytes:
        b0 = ((self.tx_frame_type & 0x0F) << 4) | (self.rx_frame_type & 0x0F)
        b1 = ((self.tx_bandwidth & 0x03) << 6
              | (self.rx_bandwidth & 0x03) << 4
              | (self.tx_pilot_density & 0x03) << 2
              | (self.rx_pilot_density & 0x03))
        b2 = ((self.tx_feedback_type & 0x3F) << 2
              | (self.rx_feedback_type >> 1) & 0x03)
        b3 = ((self.rx_feedback_type & 0x01) << 7)
        return bytes([b0, b1, b2, b3])

    @classmethod
    def unpack(cls, data: bytes) -> PhyUpdateRequest:
        if len(data) < cls.BYTE_LENGTH:
            raise ValueError(f"数据不足: 需要 {cls.BYTE_LENGTH} 字节")
        tx_ft = (data[0] >> 4) & 0x0F
        rx_ft = data[0] & 0x0F
        tx_bw = (data[1] >> 6) & 0x03
        rx_bw = (data[1] >> 4) & 0x03
        tx_pd = (data[1] >> 2) & 0x03
        rx_pd = data[1] & 0x03
        tx_fb = (data[2] >> 2) & 0x3F
        rx_fb = ((data[2] & 0x03) << 1) | ((data[3] >> 7) & 0x01)
        return cls(tx_ft, rx_ft, tx_bw, rx_bw, tx_pd, rx_pd, tx_fb, rx_fb)


# ---------------------------------------------------------------------------
# 7.3.2.26 物理层更新指示 (0x0018, 64 bits / 8 bytes)
# ---------------------------------------------------------------------------

@dataclass
class PhyUpdateIndication:
    """物理层更新指示 (含生效时隙)。"""
    tx_frame_type: int
    rx_frame_type: int
    tx_bandwidth: int
    rx_bandwidth: int
    tx_pilot_density: int
    rx_pilot_density: int
    tx_feedback_type: int
    rx_feedback_type: int
    effective_slot: int

    DATA_TYPE_INDEX = 0x0018
    BYTE_LENGTH = 8

    def pack(self) -> bytes:
        phy_req = PhyUpdateRequest(
            self.tx_frame_type, self.rx_frame_type,
            self.tx_bandwidth, self.rx_bandwidth,
            self.tx_pilot_density, self.rx_pilot_density,
            self.tx_feedback_type, self.rx_feedback_type,
        )
        return phy_req.pack() + self.effective_slot.to_bytes(4, "big")

    @classmethod
    def unpack(cls, data: bytes) -> PhyUpdateIndication:
        if len(data) < cls.BYTE_LENGTH:
            raise ValueError(f"数据不足: 需要 {cls.BYTE_LENGTH} 字节")
        req = PhyUpdateRequest.unpack(data[:4])
        slot = int.from_bytes(data[4:8], "big")
        return cls(
            req.tx_frame_type, req.rx_frame_type,
            req.tx_bandwidth, req.rx_bandwidth,
            req.tx_pilot_density, req.rx_pilot_density,
            req.tx_feedback_type, req.rx_feedback_type, slot,
        )


# ---------------------------------------------------------------------------
# 7.3.2.33 异步组播链路参数重配置指示 (0x001F, 248 bits / 31 bytes)
# ---------------------------------------------------------------------------

@dataclass
class AsyncMulticastReconfig:
    """异步组播链路参数重配置指示。"""
    effective_ref_slot: int      # 32 bits
    event_group_offset: int      # 16 bits
    event_group_period: int      # 16 bits
    event_period: int            # 16 bits
    delay_period: int            # 16 bits
    timeout: int                 # 16 bits
    intra_event_interval: int    # 16 bits
    inter_event_interval: int    # 16 bits
    event_count: int             # 8 bits
    payload_count: int           # 39 bits
    scheduling_slot: int         # 3 bits
    tx_rx_indication: int        # 1 bit
    tx_max_pdu: int              # 11 bits
    rx_max_pdu: int              # 11 bits
    tx_max_time_offset: int      # 9 bits
    rx_max_time_offset: int      # 9 bits

    DATA_TYPE_INDEX = 0x001F
    BYTE_LENGTH = 30

    def pack(self) -> bytes:
        buf = self.effective_ref_slot.to_bytes(4, "big")
        buf += struct.pack(">HHHHHHHB",
                           self.event_group_offset, self.event_group_period,
                           self.event_period, self.delay_period,
                           self.timeout, self.intra_event_interval,
                           self.inter_event_interval, self.event_count)
        # payload_count(39) + reserved(5) + scheduling_slot(3) +
        # tx_rx_indication(1) + tx_max_pdu(11) + rx_max_pdu(11) +
        # tx_max_time_offset(9) + rx_max_time_offset(9) = 88 bits = 11 bytes
        pc = self.payload_count & 0x7FFFFFFFFF
        bits = (pc << 49
                | (self.scheduling_slot & 0x07) << 41
                | (self.tx_rx_indication & 0x01) << 40
                | (self.tx_max_pdu & 0x7FF) << 29
                | (self.rx_max_pdu & 0x7FF) << 18
                | (self.tx_max_time_offset & 0x1FF) << 9
                | (self.rx_max_time_offset & 0x1FF))
        buf += bits.to_bytes(11, "big")
        return buf

    @classmethod
    def unpack(cls, data: bytes) -> AsyncMulticastReconfig:
        if len(data) < cls.BYTE_LENGTH:
            raise ValueError(f"数据不足: 需要 {cls.BYTE_LENGTH} 字节")
        efs = int.from_bytes(data[0:4], "big")
        ego, egp, ep, dp, to, iei, iei2, ec = struct.unpack(
            ">HHHHHHHB", data[4:19])
        tail = int.from_bytes(data[19:30], "big")
        pc = (tail >> 49) & 0x7FFFFFFFFF
        ss = (tail >> 41) & 0x07
        tri = (tail >> 40) & 0x01
        tmp = (tail >> 29) & 0x7FF
        rmp = (tail >> 18) & 0x7FF
        tmto = (tail >> 9) & 0x1FF
        rmto = tail & 0x1FF
        return cls(efs, ego, egp, ep, dp, to, iei, iei2, ec,
                   pc, ss, tri, tmp, rmp, tmto, rmto)


# ---------------------------------------------------------------------------
# 7.3.2.34 链接态异步链路参数更新指示 (0x003A, 120 bits / 15 bytes)
# ---------------------------------------------------------------------------

@dataclass
class AsyncUnicastUpdate:
    """链接态单播异步链路参数更新指示。

    标准定义 120 bits = 15 bytes。timeout 字段不包含在标准序列化中。
    """
    effective_ref_slot: int      # 32 bits
    event_group_offset: int      # 16 bits
    event_group_period: int      # 16 bits
    intra_event_interval: int    # 16 bits
    inter_event_interval: int    # 16 bits
    delay_period: int            # 16 bits
    timeout: int = 0             # 不参与序列化
    scheduling_slot: int = 0     # 3 bits
    tx_rx_indication: int = 0    # 1 bit

    DATA_TYPE_INDEX = 0x003A
    BYTE_LENGTH = 15

    def pack(self) -> bytes:
        buf = self.effective_ref_slot.to_bytes(4, "big")
        buf += struct.pack(">HHHHH",
                           self.event_group_offset, self.event_group_period,
                           self.intra_event_interval, self.inter_event_interval,
                           self.delay_period)
        tail = ((self.scheduling_slot & 0x07) << 5
                | (self.tx_rx_indication & 0x01) << 4)
        buf += bytes([tail])
        return buf

    @classmethod
    def unpack(cls, data: bytes) -> AsyncUnicastUpdate:
        if len(data) < cls.BYTE_LENGTH:
            raise ValueError(f"数据不足: 需要 {cls.BYTE_LENGTH} 字节")
        efs = int.from_bytes(data[0:4], "big")
        ego = int.from_bytes(data[4:6], "big")
        egp = int.from_bytes(data[6:8], "big")
        iei = int.from_bytes(data[8:10], "big")
        iei2 = int.from_bytes(data[10:12], "big")
        dp = int.from_bytes(data[12:14], "big")
        tail = data[14]
        ss = (tail >> 5) & 0x07
        tri = (tail >> 4) & 0x01
        return cls(efs, ego, egp, iei, iei2, dp, 0, ss, tri)


# ---------------------------------------------------------------------------
# 7.3.2.45 广播链路断开指示 (0x002A, 40 bits / 5 bytes)
# ---------------------------------------------------------------------------

@dataclass
class BroadcastLinkDisconnect:
    """广播链路断开指示。

    字段:
    - link_id:      24 bits, 逻辑链路标识
    - error_reason:  8 bits, 出错原因
    - reserved:      8 bits
    """
    link_id: int
    error_reason: int

    DATA_TYPE_INDEX = 0x002A
    BYTE_LENGTH = 5

    def pack(self) -> bytes:
        return self.link_id.to_bytes(3, "big") + bytes([self.error_reason & 0xFF, 0])

    @classmethod
    def unpack(cls, data: bytes) -> BroadcastLinkDisconnect:
        if len(data) < cls.BYTE_LENGTH:
            raise ValueError(f"数据不足: 需要 {cls.BYTE_LENGTH} 字节")
        return cls(int.from_bytes(data[0:3], "big"), data[3])


# ---------------------------------------------------------------------------
# 7.3.2.51 系统管理帧信令传输终止 (0x0030, 8 bits / 1 byte)
# ---------------------------------------------------------------------------

@dataclass
class SMFSignalingTerminate:
    """系统管理帧信令传输终止。"""
    terminate_type: int  # 8 bits

    DATA_TYPE_INDEX = 0x0030
    BYTE_LENGTH = 1

    def pack(self) -> bytes:
        return bytes([self.terminate_type & 0xFF])

    @classmethod
    def unpack(cls, data: bytes) -> SMFSignalingTerminate:
        if len(data) < cls.BYTE_LENGTH:
            raise ValueError(f"数据不足: 需要 {cls.BYTE_LENGTH} 字节")
        return cls(data[0])


# ---------------------------------------------------------------------------
# 7.3.2.52 角色切换请求 (0x0031, 32 bits / 4 bytes)
# ---------------------------------------------------------------------------

@dataclass
class RoleSwitchRequest:
    """角色切换请求。

    字段:
    - effective_slot: 32 bits, 信令生效时隙号
    """
    effective_slot: int

    DATA_TYPE_INDEX = 0x0031
    BYTE_LENGTH = 4

    def pack(self) -> bytes:
        return self.effective_slot.to_bytes(4, "big")

    @classmethod
    def unpack(cls, data: bytes) -> RoleSwitchRequest:
        if len(data) < cls.BYTE_LENGTH:
            raise ValueError(f"数据不足: 需要 {cls.BYTE_LENGTH} 字节")
        return cls(int.from_bytes(data[:4], "big"))


# ---------------------------------------------------------------------------
# 7.3.2.53 时间偏移指示 (0x0032, 64 bits / 8 bytes)
# ---------------------------------------------------------------------------

@dataclass
class TimeOffsetIndication:
    """时间偏移指示。"""
    time_offset: int  # 64 bits

    DATA_TYPE_INDEX = 0x0032
    BYTE_LENGTH = 8

    def pack(self) -> bytes:
        return self.time_offset.to_bytes(8, "big")

    @classmethod
    def unpack(cls, data: bytes) -> TimeOffsetIndication:
        if len(data) < cls.BYTE_LENGTH:
            raise ValueError(f"数据不足: 需要 {cls.BYTE_LENGTH} 字节")
        return cls(int.from_bytes(data[:8], "big"))


# ---------------------------------------------------------------------------
# 7.3.2.54 PING 请求 (0x0033, 0 bytes)
# ---------------------------------------------------------------------------

@dataclass
class PingRequest:
    """PING 请求 (无载荷)。"""

    DATA_TYPE_INDEX = 0x0033
    BYTE_LENGTH = 0

    def pack(self) -> bytes:
        return b""

    @classmethod
    def unpack(cls, data: bytes) -> PingRequest:
        return cls()


# ---------------------------------------------------------------------------
# 7.3.2.55 PING 响应 (0x0034, 0 bytes)
# ---------------------------------------------------------------------------

@dataclass
class PingResponse:
    """PING 响应 (无载荷)。"""

    DATA_TYPE_INDEX = 0x0034
    BYTE_LENGTH = 0

    def pack(self) -> bytes:
        return b""

    @classmethod
    def unpack(cls, data: bytes) -> PingResponse:
        return cls()


# ---------------------------------------------------------------------------
# 7.3.2.62 超时时间更新请求 (0x003C, 16 bits / 2 bytes)
# ---------------------------------------------------------------------------

@dataclass
class TimeoutUpdateRequest:
    """超时时间更新请求。"""
    timeout: int  # 16 bits, 单位 10ms

    DATA_TYPE_INDEX = 0x003C
    BYTE_LENGTH = 2

    def pack(self) -> bytes:
        return self.timeout.to_bytes(2, "big")

    @classmethod
    def unpack(cls, data: bytes) -> TimeoutUpdateRequest:
        if len(data) < cls.BYTE_LENGTH:
            raise ValueError(f"数据不足: 需要 {cls.BYTE_LENGTH} 字节")
        return cls(int.from_bytes(data[:2], "big"))


# ---------------------------------------------------------------------------
# 7.3.2.63 组播链路断开指示 (0x003D, 24 bits / 3 bytes)
# ---------------------------------------------------------------------------

@dataclass
class MulticastDisconnect:
    """组播链路断开指示。"""
    link_id: int       # 24 bits
    # 注: 标准定义 3 字节 (link_id 仅 24 bits, 无额外字段)

    DATA_TYPE_INDEX = 0x003D
    BYTE_LENGTH = 3

    def pack(self) -> bytes:
        return self.link_id.to_bytes(3, "big")

    @classmethod
    def unpack(cls, data: bytes) -> MulticastDisconnect:
        if len(data) < cls.BYTE_LENGTH:
            raise ValueError(f"数据不足: 需要 {cls.BYTE_LENGTH} 字节")
        return cls(int.from_bytes(data[:3], "big"))
