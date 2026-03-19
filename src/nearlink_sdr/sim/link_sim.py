"""TXS-10002-2025 Phase 1 链路仿真: GFSK/PSK 无编码端到端仿真。"""

import numpy as np

from nearlink_sdr.phy.gfsk import GFSKModulator, GFSKDemodulator
from nearlink_sdr.phy.psk import PSKModulator, PSKDemodulator
from nearlink_sdr.phy.channel import ChannelModel
from nearlink_sdr.phy.preamble import generate_preamble
from nearlink_sdr.phy.sync_sequence import (
    sync_signal_1, sync_signal_2, sync_signal_3, sync_signal_4,
)


def _ber(tx: np.ndarray, rx: np.ndarray) -> float:
    n = min(len(tx), len(rx))
    if n == 0:
        return 0.0
    return float(np.sum(tx[:n] != rx[:n])) / n


def sim_gfsk_link(num_data_bits: int = 1000,
                  snr_range_db: np.ndarray | None = None,
                  sps: int = 8,
                  seed: int = 42) -> dict:
    """帧类型1 GFSK无编码链路仿真。

    流程: 前导码 + 同步信号1(广播) + 数据 → GFSK调制 → AWGN信道 → GFSK解调 → BER

    返回:
        {"snr_db": [...], "ber": [...]}
    """
    if snr_range_db is None:
        snr_range_db = np.arange(0, 18, 2)

    rng = np.random.default_rng(seed)
    mod = GFSKModulator(sps=sps)
    demod = GFSKDemodulator(sps=sps)

    # 构造帧比特: 前导 + 同步序列 + 数据
    preamble = generate_preamble(1, symbol_rate_mhz=1.0)
    sync = sync_signal_1(None)
    data_bits = rng.integers(0, 2, num_data_bits)
    frame_bits = np.concatenate([preamble, sync, data_bits])

    n_overhead = len(preamble) + len(sync)
    ber_list = []

    for snr in snr_range_db:
        ch = ChannelModel(snr_db=float(snr))
        tx_signal = mod.modulate(frame_bits)
        rx_signal = ch.apply_awgn(tx_signal)
        rx_bits = demod.demodulate(rx_signal)
        # 提取数据段
        rx_data = rx_bits[n_overhead:n_overhead + num_data_bits]
        ber_list.append(_ber(data_bits, rx_data))

    return {"snr_db": snr_range_db.tolist(), "ber": ber_list}


def sim_psk_link(num_data_bits: int = 1000,
                 mod_type: str = "QPSK",
                 frame_type: int = 2,
                 snr_range_db: np.ndarray | None = None,
                 sps: int = 4,
                 seed: int = 42) -> dict:
    """帧类型2/3/4 PSK无编码链路仿真。

    流程: 数据 → PSK调制 → AWGN信道 → PSK解调 → BER
    (前导和同步信号作为独立信号段，不影响数据BER)

    返回:
        {"snr_db": [...], "ber": [...]}
    """
    if snr_range_db is None:
        snr_range_db = np.arange(0, 18, 2)

    rng = np.random.default_rng(seed)
    mod = PSKModulator(mod_type=mod_type, sps=sps)
    demod = PSKDemodulator(mod_type=mod_type, sps=sps)

    data_bits = rng.integers(0, 2, num_data_bits)
    ber_list = []

    for snr in snr_range_db:
        ch = ChannelModel(snr_db=float(snr))
        tx_signal = mod.modulate(data_bits)
        rx_signal = ch.apply_awgn(tx_signal)
        rx_bits = demod.demodulate(rx_signal)
        ber_list.append(_ber(data_bits, rx_bits))

    return {"snr_db": snr_range_db.tolist(), "ber": ber_list}


def run_phase1_simulation():
    """Phase 1 综合仿真: GFSK + BPSK + QPSK BER曲线。"""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    snr_range = np.arange(0, 18, 2)

    print("=== Phase 1 Link Simulation ===")
    print()

    # GFSK (帧类型1)
    print("[1/3] GFSK link simulation...")
    gfsk_result = sim_gfsk_link(num_data_bits=5000, snr_range_db=snr_range)
    for s, b in zip(gfsk_result["snr_db"], gfsk_result["ber"]):
        print(f"  SNR={s:2d} dB  BER={b:.5f}")

    # BPSK (帧类型3/4)
    print("[2/3] BPSK link simulation...")
    bpsk_result = sim_psk_link(num_data_bits=5000, mod_type="BPSK",
                               frame_type=3, snr_range_db=snr_range)
    for s, b in zip(bpsk_result["snr_db"], bpsk_result["ber"]):
        print(f"  SNR={s:2d} dB  BER={b:.5f}")

    # QPSK (帧类型2)
    print("[3/3] QPSK link simulation...")
    qpsk_result = sim_psk_link(num_data_bits=5000, mod_type="QPSK",
                               frame_type=2, snr_range_db=snr_range)
    for s, b in zip(qpsk_result["snr_db"], qpsk_result["ber"]):
        print(f"  SNR={s:2d} dB  BER={b:.5f}")

    # BER曲线
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.semilogy(gfsk_result["snr_db"], gfsk_result["ber"],
                "o-", label="GFSK (Frame Type 1)")
    ax.semilogy(bpsk_result["snr_db"], bpsk_result["ber"],
                "s-", label="BPSK (Frame Type 3/4)")
    ax.semilogy(qpsk_result["snr_db"], qpsk_result["ber"],
                "^-", label="QPSK (Frame Type 2)")
    ax.set_xlabel("Eb/N0 (dB)")
    ax.set_ylabel("Bit Error Rate")
    ax.set_title("SparkLink SLE PHY - Phase 1 Uncoded BER")
    ax.legend()
    ax.grid(True, which="both", ls="--", alpha=0.5)
    ax.set_ylim(bottom=1e-5)
    fig.tight_layout()
    fig.savefig("ber_phase1.png", dpi=150)
    print(f"\nBER curve saved to ber_phase1.png")


if __name__ == "__main__":
    run_phase1_simulation()
