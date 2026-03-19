import numpy as np

from nearlink_sdr.common.bch import bch_31_26_encode, bch_63_24_encode
from nearlink_sdr.common.m_sequence import generate_m_sequence, m31_sequence, m63_sequence


# TXS-10002-2025 6.2.3 同步序列/同步信号

# ---- 广播帧固定同步序列 ----

# 同步信号1: 0x5A2BDA62, LSB first
SYNC1_BROADCAST = np.array([
    0, 1, 0, 0, 0, 1, 1, 0,  # 0x62
    0, 1, 0, 1, 1, 0, 1, 1,  # 0xDA
    1, 1, 0, 1, 0, 1, 0, 0,  # 0x2B
    0, 1, 0, 1, 1, 0, 1, 0,  # 0x5A
], dtype=int)

# 同步信号2: 0x7DE7585C6D226540, LSB first
SYNC2_BROADCAST = np.array([
    0, 0, 0, 0, 0, 0, 1, 0,  # 0x40
    1, 0, 1, 0, 0, 1, 1, 0,  # 0x65
    0, 1, 0, 0, 0, 1, 0, 0,  # 0x22
    1, 0, 1, 1, 0, 1, 1, 0,  # 0x6D
    0, 0, 1, 1, 1, 0, 1, 0,  # 0x5C
    0, 0, 0, 1, 1, 0, 1, 0,  # 0x58
    1, 1, 1, 0, 0, 1, 1, 1,  # 0xE7
    1, 0, 1, 1, 1, 1, 1, 0,  # 0x7D
], dtype=int)

# 同步信号1 m序列参数: 5阶LFSR, 初始值全1
# 反馈多项式 x^5 + x^2 + 1 (与BCH(31,26)生成多项式相同)
_SYNC1_M_TAPS = 0b100101
_SYNC1_M_INIT = 0b11111

# 同步信号2 m序列参数: 6阶LFSR, 初始值全1
# 反馈多项式 x^6 + x + 1
_SYNC2_M_TAPS = 0b1000011
_SYNC2_M_INIT = 0b111111


def _hex_to_bits_lsb(hex_val: int, n_bits: int) -> np.ndarray:
    """将整数转换为LSB优先的比特数组。"""
    bits = np.zeros(n_bits, dtype=int)
    for i in range(n_bits):
        bits[i] = (hex_val >> i) & 1
    return bits


def sync_signal_1(link_id_24: int | None = None) -> np.ndarray:
    """生成同步信号1的32比特序列。

    标准6.2.3.1:
    - 广播帧: 固定序列0x5A2BDA62
    - 其他帧: 24位逻辑链路标识 → 补"10" → BCH(31,26) → m31异或 → 补"0"

    参数:
        link_id_24: 24位逻辑链路标识，None表示广播帧

    返回:
        32比特同步序列
    """
    if link_id_24 is None:
        return SYNC1_BROADCAST.copy()

    # 24位逻辑链路标识 → LSB优先比特数组
    a = _hex_to_bits_lsb(link_id_24, 24)

    # 第一步: 前面补"10" → Ã(d) = 1 + d^2*A(d)
    a_tilde = np.zeros(26, dtype=int)
    a_tilde[0] = 1      # 常数项1
    a_tilde[1] = 0      # d^1项为0
    a_tilde[2:26] = a   # d^2*A(d)

    # 第二步: BCH(31,26)编码
    codeword_31 = bch_31_26_encode(a_tilde)

    # 第三步: 与31比特m序列异或
    m_seq = generate_m_sequence(5, _SYNC1_M_TAPS, _SYNC1_M_INIT, 31)
    scrambled = codeword_31 ^ m_seq

    # 第四步: 末尾补"0"
    sync_32 = np.zeros(32, dtype=int)
    sync_32[:31] = scrambled
    sync_32[31] = 0

    return sync_32


def sync_signal_2(link_id_24: int | None = None) -> np.ndarray:
    """生成同步信号2的64比特序列。

    标准6.2.3.2:
    - 广播帧: 固定序列0x7DE7585C6D226540
    - 其他帧: 24位逻辑链路标识 → BCH(63,24) → m63异或 → 补"0"

    参数:
        link_id_24: 24位逻辑链路标识，None表示广播帧

    返回:
        64比特同步序列
    """
    if link_id_24 is None:
        return SYNC2_BROADCAST.copy()

    # 24位逻辑链路标识 → LSB优先比特数组
    a = _hex_to_bits_lsb(link_id_24, 24)

    # 第一步: BCH(63,24)编码
    codeword_63 = bch_63_24_encode(a)

    # 第二步: 与63比特m序列异或
    m_seq = generate_m_sequence(6, _SYNC2_M_TAPS, _SYNC2_M_INIT, 63)
    scrambled = codeword_63 ^ m_seq

    # 第三步: 末尾补"0"
    sync_64 = np.zeros(64, dtype=int)
    sync_64[:63] = scrambled
    sync_64[63] = 0

    return sync_64


def sync_signal_3(m_seq_index: int = 0) -> np.ndarray:
    """生成同步信号3的62比特序列。

    标准6.2.3.3: 两个相同的31长m序列串联。
    经BPSK调制后产生62个符号。

    参数:
        m_seq_index: m31序列编号 0~5，基础广播信道为0

    返回:
        62比特序列
    """
    m31 = m31_sequence(m_seq_index, 31)
    return np.concatenate([m31, m31])


def sync_signal_4(m_seq_index: int = 0) -> np.ndarray:
    """生成同步信号4的126比特序列。

    标准6.2.3.4: 两个相同的63长m序列串联。
    经BPSK调制后产生126个符号。

    参数:
        m_seq_index: m63序列编号 0~5，基础广播信道为0

    返回:
        126比特序列
    """
    m63 = m63_sequence(m_seq_index, 63)
    return np.concatenate([m63, m63])


def sync_signal_1_validate(sync_32: np.ndarray) -> bool:
    """验证32比特同步序列是否满足标准约束条件。

    标准6.2.3.1要求:
    1. 不能出现7个或以上连续的0或1
    2. 不能出现26次或以上的0/1跳转
    3. 不能和广播帧同步序列相同
    """
    # 条件1: 连续0/1检查
    max_run = 1
    current_run = 1
    for i in range(1, len(sync_32)):
        if sync_32[i] == sync_32[i - 1]:
            current_run += 1
            max_run = max(max_run, current_run)
        else:
            current_run = 1
    if max_run >= 7:
        return False

    # 条件2: 跳转次数检查
    transitions = np.sum(np.abs(np.diff(sync_32)))
    if transitions >= 26:
        return False

    # 条件3: 不能和广播帧相同
    if np.array_equal(sync_32, SYNC1_BROADCAST):
        return False

    return True
