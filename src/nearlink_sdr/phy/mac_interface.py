"""MAC-PHY 集成适配层。

将 MAC 层帧对象与 PHY 层发射/接收流水线打通，
提供字节级到比特级的转换和完整的发收链路。
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from nearlink_sdr.mac.frame import (
    AsyncDataFrame,
    ControlFrame,
)
from nearlink_sdr.mac.signaling import decode_signaling, encode_signaling
from nearlink_sdr.phy.control_info import ControlInfoA2
from nearlink_sdr.phy.rx_pipeline import rx_chain
from nearlink_sdr.phy.tx_pipeline import TxConfig, tx_chain

# -----------------------------------------------------------------------
# 字节 / 比特转换
# -----------------------------------------------------------------------

def bytes_to_bits(data: bytes) -> np.ndarray:
    """字节序列 → 比特数组 (MSB first)。"""
    return np.unpackbits(np.frombuffer(data, dtype=np.uint8))


def bits_to_bytes(bits: np.ndarray) -> bytes:
    """比特数组 → 字节序列 (长度向上对齐到 8 的倍数)。"""
    n = len(bits)
    padded = bits
    if n % 8 != 0:
        padded = np.concatenate([bits, np.zeros(8 - n % 8, dtype=np.uint8)])
    return np.packbits(padded.astype(np.uint8)).tobytes()


# -----------------------------------------------------------------------
# 发射端适配
# -----------------------------------------------------------------------

def mac_to_iq(
    mac_payload: bytes,
    cfg: TxConfig,
    ctrl_info: ControlInfoA2 | None = None,
) -> np.ndarray:
    """MAC 层载荷 → 基带 IQ 信号。

    Parameters
    ----------
    mac_payload : MAC 帧 pack() 产生的字节流
    cfg : 发射参数配置
    ctrl_info : 物理层控制信息。若为 None 则使用默认 A2 配置。

    Returns
    -------
    IQ 采样数组 (complex128)
    """
    data_bits = bytes_to_bits(mac_payload)

    if ctrl_info is None:
        ctrl_info = ControlInfoA2(
            packet_type=0,
            empty_packet=0,
            tx_sn=0,
            rx_sn=0,
            flow_ctrl=0,
            sys_mgmt_rx=0,
            reserved=0,
            data_length=len(mac_payload),
        )

    ctrl_bits = ctrl_info.pack(sync_seed=cfg.pid)

    return tx_chain(ctrl_bits, data_bits, cfg)


def signaling_to_iq(msg: object, cfg: TxConfig) -> np.ndarray:
    """信令对象 → 基带 IQ 信号。

    将一条 MAC 信令消息编码为 ControlFrame -> bytes -> bits -> tx_chain。
    """
    frame = encode_signaling(msg)
    mac_bytes = frame.pack()
    return mac_to_iq(mac_bytes, cfg)


# -----------------------------------------------------------------------
# 接收端适配
# -----------------------------------------------------------------------

@dataclass
class MacRxResult:
    """MAC 层接收结果。"""
    mac_payload: bytes
    ctrl_bits: np.ndarray
    crc_ok: bool
    head_crc_ok: bool


def iq_to_mac(
    iq_signal: np.ndarray,
    cfg: TxConfig,
    n_mac_bytes: int,
) -> MacRxResult:
    """基带 IQ 信号 → MAC 层载荷字节。

    Parameters
    ----------
    iq_signal : IQ 采样数组
    cfg : 与发射端相同的配置
    n_mac_bytes : MAC 层载荷字节数（需要预先知道）

    Returns
    -------
    MacRxResult
    """
    result = rx_chain(iq_signal, cfg, n_mac_bytes)
    mac_payload = bits_to_bytes(result.data_bits[:n_mac_bytes * 8])
    return MacRxResult(
        mac_payload=mac_payload,
        ctrl_bits=result.ctrl_bits,
        crc_ok=result.crc_ok,
        head_crc_ok=result.head_crc_ok,
    )


def iq_to_signaling(
    iq_signal: np.ndarray,
    cfg: TxConfig,
    n_mac_bytes: int,
) -> tuple[object, bool]:
    """基带 IQ 信号 → 信令对象。

    Returns
    -------
    (信令对象, CRC是否通过)
    """
    rx = iq_to_mac(iq_signal, cfg, n_mac_bytes)
    if not rx.crc_ok:
        return None, False
    frame, _ = ControlFrame.unpack(rx.mac_payload)
    msg = decode_signaling(frame)
    return msg, True


# -----------------------------------------------------------------------
# 全链路 roundtrip (用于测试/仿真)
# -----------------------------------------------------------------------

def roundtrip_signaling(
    msg: object,
    cfg: TxConfig | None = None,
) -> tuple[object | None, bool]:
    """信令编码 → IQ → 解码全链路测试。

    无信道（直连），验证 MAC → PHY → MAC 数据完整性。

    Returns
    -------
    (恢复的信令对象, CRC是否通过)
    """
    if cfg is None:
        cfg = TxConfig(frame_type=2, mcs_index=7)

    frame = encode_signaling(msg)
    mac_bytes = frame.pack()
    n_mac_bytes = len(mac_bytes)

    iq = mac_to_iq(mac_bytes, cfg)
    return iq_to_signaling(iq, cfg, n_mac_bytes)


def roundtrip_data(
    data: bytes,
    cfg: TxConfig | None = None,
    segment_type: int = 0,
) -> tuple[bytes, bool]:
    """异步数据帧编码 → IQ → 解码全链路测试。

    Returns
    -------
    (恢复的数据, CRC是否通过)
    """
    if cfg is None:
        cfg = TxConfig(frame_type=2, mcs_index=7)

    frame = AsyncDataFrame(segment_type=segment_type, data=data)
    mac_bytes = frame.pack()
    n_mac_bytes = len(mac_bytes)

    iq = mac_to_iq(mac_bytes, cfg)
    rx = iq_to_mac(iq, cfg, n_mac_bytes)

    if not rx.crc_ok:
        return b"", False

    recovered = AsyncDataFrame.unpack(rx.mac_payload)
    return recovered.data, True
