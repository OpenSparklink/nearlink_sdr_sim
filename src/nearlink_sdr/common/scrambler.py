"""信道比特加扰 -- TXS-10002-2025 标准 6.10.4

使用 7bit LFSR, 生成多项式 x^7 + x^4 + 1。
对编码后的比特序列进行异或加扰, 用于数据白化。
"""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray


def _lfsr_step(state: int) -> tuple[int, int]:
    """LFSR 单步: 输出 1bit, 返回 (output_bit, new_state)。

    多项式 x^7 + x^4 + 1, 寄存器位编号 0..6。
    输出位: 寄存器 0 (LSB)。
    反馈: 寄存器 0 XOR 寄存器 4, 写入寄存器 6。
    """
    output = state & 1
    feedback = ((state >> 0) ^ (state >> 4)) & 1
    new_state = (state >> 1) | (feedback << 6)
    return output, new_state


def scramble_sequence(length: int, seed: int) -> NDArray[np.uint8]:
    """生成指定长度的加扰序列。

    Parameters
    ----------
    length : int
        需要的加扰比特数。
    seed : int
        7bit 初始种子 (0 ~ 127)。

    Returns
    -------
    NDArray[np.uint8]
        加扰序列, 元素为 0 或 1。
    """
    if not 0 <= seed <= 127:
        raise ValueError(f"seed 必须在 0..127 范围内, 收到 {seed}")
    seq = np.empty(length, dtype=np.uint8)
    state = seed
    for i in range(length):
        bit, state = _lfsr_step(state)
        seq[i] = bit
    return seq


def scramble(bits: NDArray[np.uint8], seed: int) -> NDArray[np.uint8]:
    """对比特序列进行加扰 (XOR)。

    Parameters
    ----------
    bits : NDArray[np.uint8]
        待加扰比特, 元素为 0 或 1。
    seed : int
        7bit 初始种子。

    Returns
    -------
    NDArray[np.uint8]
        加扰后的比特序列。
    """
    seq = scramble_sequence(len(bits), seed)
    return (bits ^ seq).astype(np.uint8)


def descramble(bits: NDArray[np.uint8], seed: int) -> NDArray[np.uint8]:
    """解扰。加扰和解扰操作完全相同 (自逆性)。"""
    return scramble(bits, seed)


def broadcast_seed(physical_channel: int) -> int:
    """广播帧的加扰种子: 物理信道号。

    Parameters
    ----------
    physical_channel : int
        物理信道号 (0..397)。取低 7 位。

    Returns
    -------
    int
        7bit 种子。
    """
    return physical_channel & 0x7F


def data_link_seed(slot_number: int) -> int:
    """数据链路的加扰种子。

    将事件起始时刻调度时隙序号的低 6 位设为寄存器 0..5,
    寄存器 6 设为 1。

    Parameters
    ----------
    slot_number : int
        调度时隙序号。

    Returns
    -------
    int
        7bit 种子。
    """
    return (1 << 6) | (slot_number & 0x3F)
