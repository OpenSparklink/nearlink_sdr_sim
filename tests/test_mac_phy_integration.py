"""MAC-PHY 集成联调测试。

验证 MAC 帧 → PHY IQ → MAC 帧的全链路数据完整性。
"""

import numpy as np

from nearlink_sdr.mac.frame import AsyncDataFrame
from nearlink_sdr.mac.link_control import PingRequest, PingResponse
from nearlink_sdr.mac.signaling import encode_signaling
from nearlink_sdr.phy.mac_interface import (
    bits_to_bytes,
    bytes_to_bits,
    iq_to_mac,
    mac_to_iq,
    roundtrip_data,
    roundtrip_signaling,
)
from nearlink_sdr.phy.tx_pipeline import TxConfig

# -----------------------------------------------------------------------
# 字节/比特转换
# -----------------------------------------------------------------------

class TestBitByteConversion:

    def test_roundtrip_simple(self):
        original = b"\xDE\xAD\xBE\xEF"
        bits = bytes_to_bits(original)
        assert len(bits) == 32
        assert bits_to_bytes(bits) == original

    def test_roundtrip_zeros(self):
        original = b"\x00\x00\x00"
        assert bits_to_bytes(bytes_to_bits(original)) == original

    def test_roundtrip_ones(self):
        original = b"\xFF\xFF"
        assert bits_to_bytes(bytes_to_bits(original)) == original

    def test_empty(self):
        assert bits_to_bytes(bytes_to_bits(b"")) == b""

    def test_single_byte(self):
        for val in [0x00, 0x55, 0xAA, 0xFF]:
            original = bytes([val])
            assert bits_to_bytes(bytes_to_bits(original)) == original

    def test_bits_padding(self):
        """不足 8 bit 的尾部补零。"""
        bits = np.array([1, 0, 1], dtype=np.uint8)
        result = bits_to_bytes(bits)
        assert result == bytes([0b10100000])


# -----------------------------------------------------------------------
# MAC → IQ 发射
# -----------------------------------------------------------------------

class TestMacToIq:

    def test_basic_transmit(self):
        """验证 mac_to_iq 产生非零 IQ 信号。"""
        payload = b"\x01\x02\x03\x04"
        cfg = TxConfig(frame_type=2, mcs_index=7)
        iq = mac_to_iq(payload, cfg)
        assert iq.dtype == np.complex128
        assert len(iq) > 0
        assert np.max(np.abs(iq)) > 0

    def test_control_frame_transmit(self):
        """验证 ControlFrame.pack() → mac_to_iq 成功。"""
        msg = PingRequest()
        frame = encode_signaling(msg)
        mac_bytes = frame.pack()
        cfg = TxConfig(frame_type=2, mcs_index=7)
        iq = mac_to_iq(mac_bytes, cfg)
        assert len(iq) > 0

    def test_async_data_transmit(self):
        """验证异步数据帧 → IQ 发射。"""
        data_frame = AsyncDataFrame(segment_type=0, data=b"hello world")
        mac_bytes = data_frame.pack()
        cfg = TxConfig(frame_type=2, mcs_index=7)
        iq = mac_to_iq(mac_bytes, cfg)
        assert len(iq) > 0

    def test_different_frame_types(self):
        """验证不同帧类型都能产生 IQ。"""
        payload = b"\xAA\xBB\xCC"
        for ft in [1, 2, 3, 4]:
            cfg = TxConfig(frame_type=ft, mcs_index=0 if ft == 1 else 7)
            iq = mac_to_iq(payload, cfg)
            assert len(iq) > 0, f"帧类型 {ft} 未产生 IQ 信号"


# -----------------------------------------------------------------------
# IQ → MAC 接收 (无信道直连)
# -----------------------------------------------------------------------

class TestIqToMac:

    def test_loopback_payload(self):
        """直连 roundtrip: MAC 字节 → IQ → MAC 字节 (无噪声)。"""
        payload = b"\x01\x02\x03\x04\x05\x06"
        cfg = TxConfig(frame_type=2, mcs_index=7, sps=4)
        iq = mac_to_iq(payload, cfg)
        rx = iq_to_mac(iq, cfg, len(payload))
        assert rx.crc_ok
        assert rx.mac_payload == payload


# -----------------------------------------------------------------------
# 全链路 roundtrip
# -----------------------------------------------------------------------

class TestRoundtripSignaling:

    def test_ping_roundtrip(self):
        """PingRequest 全链路: 编码 → IQ → 解码。"""
        msg = PingRequest()
        recovered, ok = roundtrip_signaling(msg)
        assert ok
        assert isinstance(recovered, PingRequest)

    def test_ping_response_roundtrip(self):
        """PingResponse 全链路。"""
        msg = PingResponse()
        recovered, ok = roundtrip_signaling(msg)
        assert ok
        assert isinstance(recovered, PingResponse)


class TestRoundtripData:

    def test_short_data(self):
        """短数据帧全链路。"""
        data = b"SLE"
        recovered, ok = roundtrip_data(data)
        assert ok
        assert recovered == data

    def test_longer_data(self):
        """较长数据帧全链路。"""
        data = bytes(range(27))
        recovered, ok = roundtrip_data(data)
        assert ok
        assert recovered == data
