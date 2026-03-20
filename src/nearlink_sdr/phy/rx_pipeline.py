"""物理层接收流水线 -- TXS-10002-2025 标准

完成 TX 发射链路的逆操作: IQ 信号 → 帧同步 → 匹配滤波/解调 →
解扰 → Polar 解码 → CRC 校验, 还原 MAC 层载荷。
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from nearlink_sdr.common.code_block_seg import segment_with_crc, segment_without_crc
from nearlink_sdr.common.crc import (
    crc_check,
)
from nearlink_sdr.common.mcs import Modulation
from nearlink_sdr.common.polar import get_polar_decoder
from nearlink_sdr.common.scrambler import scramble_sequence
from nearlink_sdr.phy.control_info import polar_decode_control
from nearlink_sdr.phy.frame import FrameConfig, symbols_to_data_bits
from nearlink_sdr.phy.gfsk import GFSKDemodulator
from nearlink_sdr.phy.psk import rrc_filter
from nearlink_sdr.phy.sync_sequence import (
    sync_signal_1,
    sync_signal_2,
    sync_signal_3,
    sync_signal_4,
)
from nearlink_sdr.phy.tx_pipeline import TxConfig

# Head 编码后固定码长
_HEAD_CODED_LEN = {1: 0, 2: 64, 3: 256, 4: 256}

# 调制类型字符串映射
_MOD_STR = {
    Modulation.BPSK: "BPSK",
    Modulation.QPSK: "QPSK",
    Modulation.PSK8: "8PSK",
}


@dataclass
class RxResult:
    """接收结果。"""
    data_bits: np.ndarray
    ctrl_bits: np.ndarray
    crc_ok: bool
    head_crc_ok: bool


def decode_payload(scrambled_bits: np.ndarray, cfg: TxConfig,
                   n_info_bits: int) -> tuple[np.ndarray, bool]:
    """载荷解码: 解扰 → [Polar 解码] → CRC 校验。

    Parameters
    ----------
    scrambled_bits : 加扰后的载荷比特 (txPyLdW)
    cfg : 发射/接收配置
    n_info_bits : 原始信息比特数 (data_bytes * 8, 不含 CRC)

    Returns
    -------
    (data_bits, crc_ok) : 原始数据比特 和 CRC 校验结果
    """
    # 解扰
    offset = _HEAD_CODED_LEN[cfg.frame_type]
    sc = scramble_sequence(offset + len(scrambled_bits), cfg.whitening_seed)
    coded = np.asarray(scrambled_bits, dtype=np.uint8) ^ sc[offset: offset + len(scrambled_bits)]

    if cfg.is_uncoded:
        data_with_crc = coded.astype(np.int8)
    else:
        # 用分段函数确定分段结构
        b_len = n_info_bits + cfg.crc_len
        dummy = np.zeros(b_len, dtype=int)
        if cfg.frame_type in (3, 4):
            segments = segment_with_crc(dummy, cfg.rate_str)
        else:
            segments = segment_without_crc(dummy, cfg.rate_str, crc_len=cfg.crc_len)

        # 按 N 切分编码比特, 逐块 Polar 解码
        pos = 0
        info_blocks: list[np.ndarray] = []
        for n_code, info in segments:
            k = len(info)
            block = coded[pos: pos + n_code]
            # 硬比特 → LLR: 0 → +1, 1 → -1
            llr = (1.0 - 2.0 * block.astype(np.float64)) * 10.0
            dec = get_polar_decoder(n_code, k)
            info_blocks.append(dec.decode(llr))
            pos += n_code
        data_with_crc = np.concatenate(info_blocks)

        # FT3/FT4: segment_with_crc 在前端补零对齐, 解码后取尾部有效比特
        if cfg.frame_type in (3, 4):
            data_with_crc = data_with_crc[-b_len:]

    # CRC 校验
    ok = crc_check(data_with_crc, cfg.crc_poly, cfg.crc_len, seed=cfg.crc_seed)
    data = data_with_crc[: -cfg.crc_len]
    return data, ok


def decode_head(scrambled_bits: np.ndarray, cfg: TxConfig) -> tuple[np.ndarray, bool]:
    """头部解码: 解扰 → [Polar 解码] → 返回控制信息比特。

    Parameters
    ----------
    scrambled_bits : 加扰后的头部比特 (txHeadW)
    cfg : 发射/接收配置

    Returns
    -------
    (ctrl_bits, crc12_ok) : 控制信息 + CRC12 比特, CRC12 校验结果
    """
    # 解扰
    sc = scramble_sequence(len(scrambled_bits), cfg.whitening_seed)
    coded = np.asarray(scrambled_bits, dtype=np.uint8) ^ sc[:len(scrambled_bits)]

    if cfg.frame_type == 1:
        return coded.astype(np.int8), True

    # Polar 解码
    n_coded = _HEAD_CODED_LEN[cfg.frame_type]
    # A 组 (FT2): CRC12, B 组 (FT3/4): CRC24B
    head_crc_len = 24 if cfg.frame_type >= 3 else 12
    k_info = cfg.ctrl_bits_len + head_crc_len
    decoded = polar_decode_control(coded.astype(np.int_), k_info, n_coded=n_coded)
    return decoded, True


def frame_sync(iq_signal: np.ndarray, cfg: TxConfig) -> int:
    """帧同步: 同步序列互相关峰值搜索。

    Parameters
    ----------
    iq_signal : 接收到的基带 IQ 信号 (已匹配滤波 + 下采样到 1 sps)
    cfg : 配置 (需要 pid 生成同步序列)

    Returns
    -------
    sync_start : 同步序列起始符号位置, -1 表示未检测到
    """
    if cfg.frame_type == 1:
        # FT1: 32 比特同步序列
        sync_bits = sync_signal_1(cfg.pid)
        sync_ref = 2.0 * sync_bits.astype(np.float64) - 1.0
        signal = 2.0 * np.real(iq_signal).astype(np.float64) - 1.0
    elif cfg.frame_type == 2:
        # FT2: 64 比特同步序列 → QPSK 符号
        sync_bits = sync_signal_2(cfg.pid)
        from nearlink_sdr.phy.psk import PSKModulator
        mod = PSKModulator(mod_type="QPSK", sps=1)
        sync_ref = mod.map_symbols(sync_bits)
        signal = iq_signal
    elif cfg.frame_type == 3:
        # FT3: 62 比特同步序列 → BPSK 符号
        sync_bits = sync_signal_3(cfg.pid if cfg.pid else 0)
        from nearlink_sdr.phy.psk import PSKModulator
        mod = PSKModulator(mod_type="BPSK", sps=1)
        sync_ref = mod.map_symbols(sync_bits)
        signal = iq_signal
    else:
        # FT4: 126 比特同步序列 → BPSK 符号
        sync_bits = sync_signal_4(cfg.pid if cfg.pid else 0)
        from nearlink_sdr.phy.psk import PSKModulator
        mod = PSKModulator(mod_type="BPSK", sps=1)
        sync_ref = mod.map_symbols(sync_bits)
        signal = iq_signal

    n_sync = len(sync_ref)
    n_signal = len(signal)
    if n_signal < n_sync:
        return -1

    # 滑动互相关
    corr = np.zeros(n_signal - n_sync + 1)
    for i in range(len(corr)):
        segment = signal[i: i + n_sync]
        corr[i] = np.abs(np.sum(segment * np.conj(sync_ref)))

    # 找峰值
    peak_idx = int(np.argmax(corr))
    peak_val = corr[peak_idx]
    mean_val = np.mean(corr)

    if peak_val < 2.0 * mean_val:
        return -1

    return peak_idx


def rx_chain(
    iq_signal: np.ndarray,
    cfg: TxConfig,
    n_data_bytes: int,
) -> RxResult:
    """完整接收链路: IQ → 帧解析 → 解码 → CRC 校验。

    Parameters
    ----------
    iq_signal : 基带 IQ 信号
    cfg : 发射/接收参数配置 (与发射端相同)
    n_data_bytes : 数据长度 (字节), 用于确定码块分割

    Returns
    -------
    RxResult : 包含恢复数据、控制信息和校验结果
    """
    # 匹配滤波 + 下采样 → 符号级
    if cfg.frame_type == 1:
        demod = GFSKDemodulator(sps=cfg.sps)
        symbols = demod.demodulate(iq_signal)
    else:
        # RRC 匹配滤波 + 下采样, 保持复数符号 (不做硬判决)
        h = rrc_filter(0.4, cfg.sps)
        filtered = np.convolve(iq_signal, h, mode="same")
        symbols = filtered[::cfg.sps]

    # 帧结构解析 → 提取头部比特和数据比特
    n_data_bits = n_data_bytes * 8
    if cfg.is_uncoded:
        total_coded_bits = n_data_bits + cfg.crc_len
    else:
        # 计算编码后总比特数
        b_len = n_data_bits + cfg.crc_len
        dummy = np.zeros(b_len, dtype=int)
        if cfg.frame_type in (3, 4):
            segments = segment_with_crc(dummy, cfg.rate_str)
        else:
            segments = segment_without_crc(dummy, cfg.rate_str, crc_len=cfg.crc_len)
        total_coded_bits = sum(n for n, _ in segments)

    frame_cfg = FrameConfig(
        frame_type=cfg.frame_type,
        symbol_rate_mhz=cfg.symbol_rate_mhz,
        pilot_interval=cfg.pilot_interval,
        crc_len=cfg.crc_len,
        sync_m_index=cfg.pid,
        mod_type=cfg.mod_str,
    )

    head_coded = _HEAD_CODED_LEN[cfg.frame_type]
    n_ctrl_coded = head_coded if head_coded > 0 else cfg.ctrl_bits_len + 12
    ctrl_bits_demod, data_bits_demod = symbols_to_data_bits(
        symbols, frame_cfg,
        n_ctrl_coded_bits=n_ctrl_coded,
        n_data_bits=total_coded_bits,
    )

    # 头部解码
    ctrl_decoded, head_ok = decode_head(ctrl_bits_demod, cfg)

    # 载荷解码
    data_decoded, crc_ok = decode_payload(data_bits_demod, cfg, n_data_bits)

    return RxResult(
        data_bits=data_decoded,
        ctrl_bits=ctrl_decoded,
        crc_ok=crc_ok,
        head_crc_ok=head_ok,
    )
