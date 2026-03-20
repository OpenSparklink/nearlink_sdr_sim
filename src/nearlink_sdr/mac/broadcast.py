"""广播帧编解码 -- TXS-10002-2025 标准 7.1.4

实现 SLE 广播、发现和接入所需的帧结构编解码:
- 广播帧通用结构 (BroadcastFrame)
- 扩展广播帧资源配置信息 (ExtAdvResourceConfig)
- 发现接入资源配置信息 (DiscoveryAccessResourceConfig)
- 接入基本信息 (AccessBasicInfo)
- 接入请求信息 (AccessRequestInfo)
- 接入响应信息 (AccessResponseInfo)
- 启动系统管理帧信息 (SystemMgmtFrameInfo)
"""

from __future__ import annotations

import struct
from dataclasses import dataclass, field
from enum import IntEnum

# ---------------------------------------------------------------------------
# 枚举定义
# ---------------------------------------------------------------------------


class AddrType(IntEnum):
    """媒体接入层标识类型 (7.1.4 表25)"""
    ALLIANCE_ASSIGNED = 0
    LOCAL_ORG = 2
    RESOLVABLE_RANDOM = 3
    NON_RESOLVABLE_RANDOM = 4
    ALLIANCE_RESERVED = 5
    PRIVATE = 6


class BroadcastDataType(IntEnum):
    """广播帧数据类型 (7.1.4 表26)"""
    DISCOVERY_ACCESS_RESOURCE = 0x00
    TRANSPORT_INDICATION = 0x01
    ACCESS_BASIC = 0x02
    ACCESS_REQUEST = 0x03
    ACCESS_RESPONSE = 0x04
    SYSTEM_MGMT_FRAME = 0x05
    UNLINKED_BROADCAST_LINK = 0x06
    QUERY_REQUEST_FILTER = 0x07
    NB_HOPPING_MEAS_CONFIG = 0x08
    UWB_PULSE_MEAS_CONFIG = 0x09
    UPPER_LAYER_DATA = 0xFF


class RequestType(IntEnum):
    """请求类型标志 (7.1.4.2)"""
    QUERY = 0
    ACCESS = 1
    UNRESTRICTED = 2


class GTNegotiation(IntEnum):
    """GT 角色协商结果 (7.1.4.2)"""
    NEGOTIATE_T = 0b00
    NEGOTIATE_G = 0b01
    FIXED_T = 0b10
    FIXED_G = 0b11


class AccessResponseType(IntEnum):
    """接入响应类型 (7.1.4.6)"""
    ACCEPT = 0
    GT_NEGOTIATION_FAIL = 1
    RESOURCE_LIMITED = 2
    USER_REJECT = 3


# ---------------------------------------------------------------------------
# 7.1.4.1 扩展广播帧资源配置信息 (4 字节)
# ---------------------------------------------------------------------------


@dataclass
class ExtAdvResourceConfig:
    """扩展广播帧资源配置信息 (7.1.4.1, 表27)

    4 字节结构:
    - 频点索引:       8 bits
    - 偏移量:        12 bits
    - 无线帧类型指示:  4 bits
    - 带宽指示:       2 bits
    - 导频密度指示:    2 bits
    - 时钟精度:       3 bits
    - 偏移量单位:     1 bit
    """
    channel_index: int        # 频点索引 (0-255)
    offset: int               # 偏移量 (0-4095)
    frame_type: int            # 无线帧类型 (0-15)
    bandwidth: int             # 带宽 (0=1M, 1=2M, 2=4M)
    pilot_density: int         # 导频密度 (0=4:1, 1=8:1, 2=16:1, 3=无)
    clock_accuracy: int        # 时钟精度 (0-7)
    offset_unit: int           # 偏移量单位 (0=1基础时隙, 1=10基础时隙)

    BYTE_LENGTH = 4

    def pack(self) -> bytes:
        b0 = self.channel_index & 0xFF
        b1 = (self.offset >> 4) & 0xFF
        b2 = ((self.offset & 0x0F) << 4) | (self.frame_type & 0x0F)
        b3 = (
            ((self.bandwidth & 0x03) << 6)
            | ((self.pilot_density & 0x03) << 4)
            | ((self.clock_accuracy & 0x07) << 1)
            | (self.offset_unit & 0x01)
        )
        return bytes([b0, b1, b2, b3])

    @classmethod
    def unpack(cls, data: bytes) -> ExtAdvResourceConfig:
        if len(data) < cls.BYTE_LENGTH:
            raise ValueError(f"数据不足: 需要 {cls.BYTE_LENGTH} 字节")
        channel_index = data[0]
        offset = (data[1] << 4) | ((data[2] >> 4) & 0x0F)
        frame_type = data[2] & 0x0F
        bandwidth = (data[3] >> 6) & 0x03
        pilot_density = (data[3] >> 4) & 0x03
        clock_accuracy = (data[3] >> 1) & 0x07
        offset_unit = data[3] & 0x01
        return cls(
            channel_index, offset, frame_type,
            bandwidth, pilot_density, clock_accuracy, offset_unit,
        )


# ---------------------------------------------------------------------------
# 7.1.4.2 发现接入资源配置信息
# ---------------------------------------------------------------------------


@dataclass
class DiscoveryAccessEntry:
    """单个发现接入资源条目"""
    request_type: int         # 请求类型标志 (2 bits)
    carry_info_indication: int  # 请求携带信息指示 (2 bits)
    peer_addr_type: int       # 对端标识类型 (3 bits)
    addr_present: int         # 标识指示 (1 bit)
    peer_addr: bytes          # 对端标识 (6字节, 仅当 addr_present=1 时有效)


@dataclass
class DiscoveryAccessResourceConfig:
    """发现接入资源配置信息 (7.1.4.2, 表28)"""
    request_offset: int            # 请求偏移量 (2字节, us)
    request_max_length: int        # 请求最大长度 (1字节)
    response_offset: int           # 请求响应偏移量 (2字节, us)
    gt_negotiation: int            # GT 协商指示 (2 bits)
    entry_count: int               # 请求/响应个数 (6 bits)
    entries: list[DiscoveryAccessEntry] = field(default_factory=list)

    def pack(self) -> bytes:
        buf = struct.pack(">HBH", self.request_offset,
                          self.request_max_length, self.response_offset)
        buf += bytes([
            ((self.gt_negotiation & 0x03) << 6) | (self.entry_count & 0x3F)
        ])
        for entry in self.entries:
            flag = (
                ((entry.request_type & 0x03) << 6)
                | ((entry.carry_info_indication & 0x03) << 4)
                | ((entry.peer_addr_type & 0x07) << 1)
                | (entry.addr_present & 0x01)
            )
            buf += bytes([flag])
            if entry.addr_present:
                buf += entry.peer_addr[:6].ljust(6, b"\x00")
        return buf

    @classmethod
    def unpack(cls, data: bytes) -> DiscoveryAccessResourceConfig:
        if len(data) < 6:
            raise ValueError("数据不足: 至少需要 6 字节")
        req_offset, req_max_len, resp_offset = struct.unpack(">HBH", data[:5])
        gt_neg = (data[5] >> 6) & 0x03
        count = data[5] & 0x3F
        entries: list[DiscoveryAccessEntry] = []
        pos = 6
        for _ in range(count):
            if pos >= len(data):
                break
            flag = data[pos]
            pos += 1
            req_type = (flag >> 6) & 0x03
            carry_info = (flag >> 4) & 0x03
            peer_type = (flag >> 1) & 0x07
            addr_present = flag & 0x01
            peer_addr = b""
            if addr_present and pos + 6 <= len(data):
                peer_addr = bytes(data[pos:pos + 6])
                pos += 6
            entries.append(DiscoveryAccessEntry(
                req_type, carry_info, peer_type, addr_present, peer_addr,
            ))
        return cls(req_offset, req_max_len, resp_offset, gt_neg, count, entries)


# ---------------------------------------------------------------------------
# 7.1.4.4 接入基本信息 (可变长)
# ---------------------------------------------------------------------------


@dataclass
class AccessBasicInfo:
    """接入基本信息 (7.1.4.4, 表31)"""
    smf_baseline_slot: int         # 系统管理帧基线时隙 (4字节)
    smf_offset: int                # 启动系统管理帧偏移量 (2字节, us)
    smf_link_id: int               # 系统管理帧逻辑链路标识 (4字节)
    smf_period: int                # 系统管理帧周期间隔 (3字节, 基础时隙)
    smf_frame_type: int            # 系统管理帧无线帧类型 (4 bits)
    smf_bandwidth: int             # 系统管理帧带宽 (2 bits)
    smf_pilot_density: int         # 系统管理帧导频密度 (2 bits)
    access_link_id: int            # 接入逻辑链路标识 (3字节)
    access_period: int             # 接入周期间隔 (2字节, 基础时隙)
    access_timeout: int            # 接入超时时间 (1字节)
    sleep_clock_accuracy: int      # 睡眠时钟精度 (3 bits)
    access_crc_type: int           # 接入CRC类型 (1 bit, 0=CRC24, 1=CRC32)
    access_crc_init: int           # 接入CRC初始值 (4字节)
    hop_map: bytes                 # 数据传输可用跳频地图 (10或25字节)
    smf_channel_count: int         # 系统管理帧可用频点个数 (1字节)
    smf_channel_table: bytes       # 系统管理帧频点表 (可变长)

    def pack(self) -> bytes:
        buf = self.smf_baseline_slot.to_bytes(4, "big")
        buf += self.smf_offset.to_bytes(2, "big")
        buf += self.smf_link_id.to_bytes(4, "big")
        buf += self.smf_period.to_bytes(3, "big")
        b_config = (
            ((self.smf_frame_type & 0x0F) << 4)
            | ((self.smf_bandwidth & 0x03) << 2)
            | (self.smf_pilot_density & 0x03)
        )
        buf += bytes([b_config])
        buf += self.access_link_id.to_bytes(3, "big")
        buf += self.access_period.to_bytes(2, "big")
        buf += bytes([self.access_timeout & 0xFF])
        b_flags = (
            ((self.sleep_clock_accuracy & 0x07) << 5)
            | (self.access_crc_type & 0x01)
        )
        buf += bytes([b_flags])
        buf += self.access_crc_init.to_bytes(4, "big")
        buf += self.hop_map
        buf += bytes([self.smf_channel_count & 0xFF])
        buf += self.smf_channel_table
        return buf

    @classmethod
    def unpack(cls, data: bytes) -> AccessBasicInfo:
        if len(data) < 25:
            raise ValueError("数据不足: 至少需要 25 字节")
        smf_baseline = int.from_bytes(data[0:4], "big")
        smf_offset = int.from_bytes(data[4:6], "big")
        smf_link_id = int.from_bytes(data[6:10], "big")
        smf_period = int.from_bytes(data[10:13], "big")
        config = data[13]
        smf_ft = (config >> 4) & 0x0F
        smf_bw = (config >> 2) & 0x03
        smf_pd = config & 0x03
        access_lid = int.from_bytes(data[14:17], "big")
        access_period = int.from_bytes(data[17:19], "big")
        access_timeout = data[19]
        flags = data[20]
        sca = (flags >> 5) & 0x07
        crc_type = flags & 0x01
        crc_init = int.from_bytes(data[21:25], "big")
        # 根据跳频地图长度判断: 2.4GHz = 10字节, 5.xGHz = 25字节
        remaining = len(data) - 25
        if remaining >= 25 + 1:
            hop_map = bytes(data[25:50])
            pos = 50
        else:
            hop_map = bytes(data[25:35])
            pos = 35
        smf_ch_count = data[pos] if pos < len(data) else 0
        pos += 1
        smf_ch_table = bytes(data[pos:pos + smf_ch_count])
        return cls(
            smf_baseline, smf_offset, smf_link_id, smf_period,
            smf_ft, smf_bw, smf_pd, access_lid, access_period,
            access_timeout, sca, crc_type, crc_init, hop_map,
            smf_ch_count, smf_ch_table,
        )


# ---------------------------------------------------------------------------
# 7.1.4.5 接入请求信息 (可变长)
# ---------------------------------------------------------------------------


@dataclass
class AccessRequestInfo:
    """接入请求信息 (7.1.4.5, 表32/33)"""
    structure_indication: int   # 结构指示字段 (8 bits 位图)
    gt_role: int | None = None         # GT角色标志 (2 bits)
    frame_support: int | None = None   # 无线帧结构指示 (4 bits 位图)
    bandwidth_support: int | None = None  # 带宽指示 (3 bits 位图)
    mcs_support: int | None = None     # MCS指示 (13 bits 位图)
    pilot_support: int | None = None   # 导频指示 (4 bits 位图)
    slot_support: int | None = None    # 调度时隙指示 (5 bits 位图)
    switch_delay: int | None = None    # 收发切换时延 (4 bits)
    crc_support: int | None = None     # CRC指示 (2 bits 位图)

    def pack(self) -> bytes:
        # 按位收集存在的字段, 组成比特流后按字节对齐
        bits: list[int] = []
        bits.extend(_int_to_bits(self.structure_indication, 8))
        if self.structure_indication & 0x01 and self.gt_role is not None:
            bits.extend(_int_to_bits(self.gt_role, 2))
        if self.structure_indication & 0x02 and self.frame_support is not None:
            bits.extend(_int_to_bits(self.frame_support, 4))
        if self.structure_indication & 0x04 and self.bandwidth_support is not None:
            bits.extend(_int_to_bits(self.bandwidth_support, 3))
        if self.structure_indication & 0x08 and self.mcs_support is not None:
            bits.extend(_int_to_bits(self.mcs_support, 13))
        if self.structure_indication & 0x10 and self.pilot_support is not None:
            bits.extend(_int_to_bits(self.pilot_support, 4))
        if self.structure_indication & 0x20 and self.slot_support is not None:
            bits.extend(_int_to_bits(self.slot_support, 5))
        if self.structure_indication & 0x40 and self.switch_delay is not None:
            bits.extend(_int_to_bits(self.switch_delay, 4))
        if self.structure_indication & 0x80 and self.crc_support is not None:
            bits.extend(_int_to_bits(self.crc_support, 2))
        # 高位补零对齐到字节
        pad = (8 - len(bits) % 8) % 8
        bits.extend([0] * pad)
        return _bits_to_bytes(bits)

    @classmethod
    def unpack(cls, data: bytes) -> AccessRequestInfo:
        if len(data) < 1:
            raise ValueError("数据不足: 至少需要 1 字节")
        bits = _bytes_to_bits(data)
        pos = 0
        si = _bits_to_int(bits, pos, 8)
        pos += 8
        gt = frame = bw = mcs = pilot = slot = switch = crc = None
        if si & 0x01:
            gt = _bits_to_int(bits, pos, 2)
            pos += 2
        if si & 0x02:
            frame = _bits_to_int(bits, pos, 4)
            pos += 4
        if si & 0x04:
            bw = _bits_to_int(bits, pos, 3)
            pos += 3
        if si & 0x08:
            mcs = _bits_to_int(bits, pos, 13)
            pos += 13
        if si & 0x10:
            pilot = _bits_to_int(bits, pos, 4)
            pos += 4
        if si & 0x20:
            slot = _bits_to_int(bits, pos, 5)
            pos += 5
        if si & 0x40:
            switch = _bits_to_int(bits, pos, 4)
            pos += 4
        if si & 0x80:
            crc = _bits_to_int(bits, pos, 2)
            pos += 2
        return cls(si, gt, frame, bw, mcs, pilot, slot, switch, crc)


# ---------------------------------------------------------------------------
# 7.1.4.6 接入响应信息 (可变长)
# ---------------------------------------------------------------------------


@dataclass
class AccessResponseEntry:
    """单个接入响应条目"""
    peer_addr: bytes               # 对端标识 (6字节)
    response_type: int             # 请求响应类型 (3 bits)
    peer_addr_type: int            # 对端标识类型 (3 bits)
    repeat_indication: int         # 重复指示 (2 bits)
    capability: bytes | None = None  # 广播节点能力指示 (6字节, 可选)


@dataclass
class AccessResponseInfo:
    """接入响应信息 (7.1.4.6, 表34)"""
    entries: list[AccessResponseEntry] = field(default_factory=list)

    def pack(self) -> bytes:
        count = len(self.entries)
        buf = bytes([(count & 0x3F) << 2])
        for entry in self.entries:
            buf += entry.peer_addr[:6].ljust(6, b"\x00")
            flag = (
                ((entry.response_type & 0x07) << 5)
                | ((entry.peer_addr_type & 0x07) << 2)
                | (entry.repeat_indication & 0x03)
            )
            buf += bytes([flag])
            if entry.repeat_indication in (1, 2) and entry.capability:
                buf += entry.capability[:6].ljust(6, b"\x00")
        return buf

    @classmethod
    def unpack(cls, data: bytes) -> AccessResponseInfo:
        if len(data) < 1:
            raise ValueError("数据不足")
        count = (data[0] >> 2) & 0x3F
        entries: list[AccessResponseEntry] = []
        pos = 1
        for _ in range(count):
            if pos + 7 > len(data):
                break
            peer_addr = bytes(data[pos:pos + 6])
            pos += 6
            flag = data[pos]
            pos += 1
            resp_type = (flag >> 5) & 0x07
            peer_type = (flag >> 2) & 0x07
            repeat = flag & 0x03
            cap = None
            if repeat in (1, 2) and pos + 6 <= len(data):
                cap = bytes(data[pos:pos + 6])
                pos += 6
            entries.append(AccessResponseEntry(
                peer_addr, resp_type, peer_type, repeat, cap,
            ))
        return cls(entries)


# ---------------------------------------------------------------------------
# 7.1.4.7 启动系统管理帧信息
# ---------------------------------------------------------------------------


@dataclass
class SystemMgmtFrameInfo:
    """启动系统管理帧信息 (7.1.4.7, 表35)"""
    baseline_slot: int           # 系统管理帧基线时隙 (4字节)
    offset: int                  # 偏移量 (2字节, us)
    access_addr: int             # 系统管理帧接入地址 (3字节)
    period: int                  # 周期间隔 (3字节, 基础时隙)
    frame_type: int              # 无线帧类型 (4 bits)
    bandwidth: int               # 带宽 (2 bits)
    pilot_density: int           # 导频密度 (2 bits)
    channel_count: int           # 可用频点个数 (1字节)
    channel_table: bytes         # 频点表 (可变长)

    def pack(self) -> bytes:
        buf = self.baseline_slot.to_bytes(4, "big")
        buf += self.offset.to_bytes(2, "big")
        buf += self.access_addr.to_bytes(3, "big")
        buf += self.period.to_bytes(3, "big")
        config = (
            ((self.frame_type & 0x0F) << 4)
            | ((self.bandwidth & 0x03) << 2)
            | (self.pilot_density & 0x03)
        )
        buf += bytes([config])
        buf += bytes([self.channel_count & 0xFF])
        buf += self.channel_table
        return buf

    @classmethod
    def unpack(cls, data: bytes) -> SystemMgmtFrameInfo:
        if len(data) < 14:
            raise ValueError("数据不足: 至少需要 14 字节")
        baseline = int.from_bytes(data[0:4], "big")
        offset = int.from_bytes(data[4:6], "big")
        access_addr = int.from_bytes(data[6:9], "big")
        period = int.from_bytes(data[9:12], "big")
        config = data[12]
        ft = (config >> 4) & 0x0F
        bw = (config >> 2) & 0x03
        pd = config & 0x03
        ch_count = data[13]
        ch_table = bytes(data[14:14 + ch_count])
        return cls(baseline, offset, access_addr, period, ft, bw, pd,
                   ch_count, ch_table)


# ---------------------------------------------------------------------------
# 7.1.4 广播帧通用结构
# ---------------------------------------------------------------------------


@dataclass
class BroadcastFrame:
    """广播帧通用结构 (7.1.4, 表25)

    结构指示 (5 bits) 控制可选字段:
    - bit 0: 本端标识存在
    - bit 1: 解析密钥标识存在
    - bit 2: 对端标识存在
    - bit 3: 扩展广播帧资源配置存在
    - bit 4: 数据部分存在
    """
    structure_indication: int       # 广播帧结构指示 (5 bits)
    local_addr_type: int            # 本端标识类型 (3 bits)
    peer_addr_type: int             # 对端标识类型 (3 bits)
    local_addr: bytes               # 本端标识 (6字节)
    irk_id: int                     # 解析密钥标识 (1字节)
    peer_addr: bytes                # 对端标识 (6字节)
    ext_adv_config: ExtAdvResourceConfig | None = None
    data_items: list[tuple[int, bytes]] = field(default_factory=list)

    def pack(self) -> bytes:
        si = self.structure_indication & 0x1F
        b0 = (si << 3)
        b1 = (
            ((self.local_addr_type & 0x07) << 5)
            | ((self.peer_addr_type & 0x07) << 2)
        )
        buf = bytes([b0, b1])
        if si & 0x01:
            buf += self.local_addr[:6].ljust(6, b"\x00")
        if si & 0x02:
            buf += bytes([self.irk_id & 0xFF])
        if si & 0x04:
            buf += self.peer_addr[:6].ljust(6, b"\x00")
        if si & 0x08 and self.ext_adv_config:
            buf += self.ext_adv_config.pack()
        if si & 0x10:
            for dtype, content in self.data_items:
                buf += bytes([dtype & 0xFF, len(content) & 0xFF])
                buf += content
        return buf

    @classmethod
    def unpack(cls, data: bytes) -> BroadcastFrame:
        if len(data) < 2:
            raise ValueError("数据不足: 至少需要 2 字节")
        si = (data[0] >> 3) & 0x1F
        local_type = (data[1] >> 5) & 0x07
        peer_type = (data[1] >> 2) & 0x07
        pos = 2
        local_addr = b"\x00" * 6
        irk_id = 0
        peer_addr = b"\x00" * 6
        ext_config = None
        items: list[tuple[int, bytes]] = []

        if si & 0x01:
            local_addr = bytes(data[pos:pos + 6])
            pos += 6
        if si & 0x02:
            irk_id = data[pos]
            pos += 1
        if si & 0x04:
            peer_addr = bytes(data[pos:pos + 6])
            pos += 6
        if si & 0x08:
            ext_config = ExtAdvResourceConfig.unpack(data[pos:pos + 4])
            pos += 4
        if si & 0x10:
            while pos + 2 <= len(data):
                dtype = data[pos]
                dlen = data[pos + 1]
                pos += 2
                if pos + dlen > len(data):
                    break
                content = bytes(data[pos:pos + dlen])
                pos += dlen
                items.append((dtype, content))

        return cls(si, local_type, peer_type, local_addr,
                   irk_id, peer_addr, ext_config, items)


# ---------------------------------------------------------------------------
# 比特操作辅助函数
# ---------------------------------------------------------------------------


def _int_to_bits(val: int, width: int) -> list[int]:
    """整数转比特列表 (高位在前)"""
    return [(val >> (width - 1 - i)) & 1 for i in range(width)]


def _bits_to_int(bits: list[int], start: int, width: int) -> int:
    """比特列表转整数"""
    val = 0
    for i in range(width):
        if start + i < len(bits):
            val = (val << 1) | (bits[start + i] & 1)
        else:
            val <<= 1
    return val


def _bits_to_bytes(bits: list[int]) -> bytes:
    """比特列表转字节序列"""
    result = []
    for i in range(0, len(bits), 8):
        byte_val = 0
        for j in range(8):
            if i + j < len(bits):
                byte_val = (byte_val << 1) | (bits[i + j] & 1)
            else:
                byte_val <<= 1
        result.append(byte_val)
    return bytes(result)


def _bytes_to_bits(data: bytes) -> list[int]:
    """字节序列转比特列表"""
    bits: list[int] = []
    for b in data:
        for i in range(7, -1, -1):
            bits.append((b >> i) & 1)
    return bits
