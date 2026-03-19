"""TXS-10002-2025 链路仿真: GFSK/PSK 无编码 + Polar编码端到端仿真。"""

import numpy as np

from nearlink_sdr.phy.gfsk import GFSKModulator, GFSKDemodulator
from nearlink_sdr.phy.psk import PSKModulator, PSKDemodulator
from nearlink_sdr.phy.channel import ChannelModel
from nearlink_sdr.phy.preamble import generate_preamble
from nearlink_sdr.phy.sync_sequence import (
    sync_signal_1, sync_signal_2, sync_signal_3, sync_signal_4,
)
from nearlink_sdr.common.polar import PolarEncoder, PolarDecoder, get_info_bit_count


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


# ── Phase 2: Polar编码链路仿真 ──


def sim_polar_coded_psk_link(
    num_info_bits: int = 1000,
    mod_type: str = "BPSK",
    rate_str: str = "1/2",
    code_length: int = 256,
    snr_range_db: np.ndarray | None = None,
    sps: int = 4,
    seed: int = 42,
) -> dict:
    """Polar编码PSK链路仿真。

    流程: 信息比特 → Polar编码 → BPSK/QPSK调制 → AWGN信道 → 解调(软判决LLR) → SC解码 → BER

    返回:
        {"snr_db": [...], "ber": [...], "fer": [...]}
    """
    if snr_range_db is None:
        snr_range_db = np.arange(-2, 12, 1)

    K = get_info_bit_count(rate_str, code_length)
    enc = PolarEncoder(code_length, K)
    dec = PolarDecoder(code_length, K)

    rng = np.random.default_rng(seed)

    # 将总信息比特分成多个码块
    n_blocks = max(1, num_info_bits // K)

    ber_list = []
    fer_list = []

    for snr in snr_range_db:
        total_bit_errors = 0
        total_bits = 0
        frame_errors = 0

        for _ in range(n_blocks):
            info = rng.integers(0, 2, size=K, dtype=np.int8)
            coded = enc.encode(info)

            # BPSK映射: 0 → +1, 1 → -1
            bpsk = 1.0 - 2.0 * coded.astype(np.float64)

            # AWGN信道
            snr_linear = 10.0 ** (float(snr) / 10.0)
            # 对于码率R的编码, Eb/N0 = SNR / R
            R_val = K / code_length
            noise_var = 1.0 / (2.0 * R_val * snr_linear) if snr_linear > 0 else 1e10
            noise = rng.normal(0, np.sqrt(noise_var), size=code_length)
            received = bpsk + noise

            # LLR计算: LLR = 2*y/sigma^2
            llr = 2.0 * received / noise_var

            # SC解码
            decoded = dec.decode(llr)

            # 统计
            bit_errors = int(np.sum(decoded != info))
            total_bit_errors += bit_errors
            total_bits += K
            if bit_errors > 0:
                frame_errors += 1

        ber = total_bit_errors / total_bits if total_bits > 0 else 0.0
        fer = frame_errors / n_blocks
        ber_list.append(ber)
        fer_list.append(fer)

    return {
        "snr_db": snr_range_db.tolist(),
        "ber": ber_list,
        "fer": fer_list,
        "code_params": f"N={code_length}, K={K}, R={rate_str}",
    }


def run_phase2_simulation():
    """Phase 2 综合仿真: Polar编码 BPSK/QPSK BER/FER 曲线。"""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    snr_range = np.arange(-2, 10, 0.5)

    print("=== Phase 2 Polar Coded Link Simulation ===")
    print()

    configs = [
        {"rate_str": "1/2", "code_length": 256, "mod_type": "BPSK", "label": "Polar(256,112) R=1/2 BPSK"},
        {"rate_str": "1/2", "code_length": 512, "mod_type": "BPSK", "label": "Polar(512,224) R=1/2 BPSK"},
        {"rate_str": "3/4", "code_length": 256, "mod_type": "BPSK", "label": "Polar(256,176) R=3/4 BPSK"},
        {"rate_str": "1/4", "code_length": 256, "mod_type": "BPSK", "label": "Polar(256,48) R=1/4 BPSK"},
    ]

    results = []
    for i, cfg in enumerate(configs):
        print(f"[{i+1}/{len(configs)}] {cfg['label']}...")
        res = sim_polar_coded_psk_link(
            num_info_bits=5000,
            snr_range_db=snr_range,
            **{k: v for k, v in cfg.items() if k != "label"},
        )
        results.append((cfg["label"], res))
        # 打印部分结果
        for s, b, f in zip(res["snr_db"][::4], res["ber"][::4], res["fer"][::4]):
            print(f"  Eb/N0={s:5.1f} dB  BER={b:.5f}  FER={f:.3f}")

    # 也运行无编码 BPSK 作为对比
    print(f"[{len(configs)+1}/{len(configs)+1}] Uncoded BPSK (reference)...")
    uncoded = sim_psk_link(num_data_bits=5000, mod_type="BPSK",
                           frame_type=3, snr_range_db=snr_range)

    # BER 曲线
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))

    markers = ["o-", "s-", "^-", "d-"]
    for (label, res), mk in zip(results, markers):
        ber_plot = [max(b, 1e-6) for b in res["ber"]]
        ax1.semilogy(res["snr_db"], ber_plot, mk, label=label, markersize=3)

    uncoded_ber = [max(b, 1e-6) for b in uncoded["ber"]]
    ax1.semilogy(uncoded["snr_db"], uncoded_ber, "x--", label="Uncoded BPSK", markersize=3)
    ax1.set_xlabel("Eb/N0 (dB)")
    ax1.set_ylabel("Bit Error Rate")
    ax1.set_title("SparkLink SLE PHY - Phase 2 BER")
    ax1.legend(fontsize=7)
    ax1.grid(True, which="both", ls="--", alpha=0.5)
    ax1.set_ylim(bottom=1e-5)

    for (label, res), mk in zip(results, markers):
        fer_plot = [max(f, 1e-4) for f in res["fer"]]
        ax2.semilogy(res["snr_db"], fer_plot, mk, label=label, markersize=3)
    ax2.set_xlabel("Eb/N0 (dB)")
    ax2.set_ylabel("Frame Error Rate")
    ax2.set_title("SparkLink SLE PHY - Phase 2 FER")
    ax2.legend(fontsize=7)
    ax2.grid(True, which="both", ls="--", alpha=0.5)
    ax2.set_ylim(bottom=1e-4)

    fig.tight_layout()
    fig.savefig("ber_phase2.png", dpi=150)
    print(f"\nBER/FER curves saved to ber_phase2.png")


# ── Phase 3: 帧级端到端仿真 ──


def sim_frame_link(
    frame_type: int = 2,
    num_data_bits: int = 200,
    rate_str: str = "1/2",
    code_length: int = 256,
    pilot_interval: int = 4,
    snr_range_db: np.ndarray | None = None,
    seed: int = 42,
) -> dict:
    """完整帧级仿真: 帧组装 → Polar编码 → PSK调制(含导频) → AWGN → 解调 → 解码 → BER。

    Args:
        frame_type: 2, 3, or 4.
        num_data_bits: 数据负载比特数.
        rate_str: Polar码率.
        code_length: Polar码长.
        pilot_interval: 导频插入间隔 (0, 4, 8, 16).
        snr_range_db: SNR扫描范围.
        seed: 随机种子.

    Returns:
        {"snr_db": [...], "ber": [...], "fer": [...]}
    """
    from nearlink_sdr.phy.frame import (
        FrameConfig, assemble_frame_bits, frame_to_symbols,
    )
    from nearlink_sdr.phy.pilot import remove_pilots

    if snr_range_db is None:
        snr_range_db = np.arange(-2, 10, 1)

    K = get_info_bit_count(rate_str, code_length)
    enc = PolarEncoder(code_length, K)
    dec = PolarDecoder(code_length, K)

    rng = np.random.default_rng(seed)

    # 每帧的数据比特分成码块
    n_blocks = max(1, num_data_bits // K)

    mod_type = {2: "QPSK", 3: "QPSK", 4: "BPSK"}[frame_type]
    config = FrameConfig(
        frame_type=frame_type,
        pilot_interval=pilot_interval,
        mod_type=mod_type,
    )

    ber_list = []
    fer_list = []

    for snr in snr_range_db:
        total_bit_errors = 0
        total_bits = 0
        frame_errors = 0

        for _ in range(n_blocks):
            info = rng.integers(0, 2, size=K, dtype=np.int8)

            # Polar编码
            coded = enc.encode(info)

            # 调制 + 帧组装
            ctrl_bits = np.zeros(64 if frame_type == 2 else 256, dtype=np.int8)
            fields = assemble_frame_bits(ctrl_bits, coded, config)
            tx_symbols = frame_to_symbols(fields, config)

            # AWGN信道
            snr_linear = 10.0 ** (float(snr) / 10.0)
            R_val = K / code_length
            noise_var = 1.0 / (2.0 * R_val * snr_linear) if snr_linear > 0 else 1e10
            noise = rng.normal(0, np.sqrt(noise_var), size=len(tx_symbols)) + \
                    1j * rng.normal(0, np.sqrt(noise_var), size=len(tx_symbols))
            rx_symbols = tx_symbols + noise

            # 提取数据段(从末尾反推)
            data_syms_count = code_length // (2 if mod_type == "QPSK" else 1)
            if pilot_interval > 0:
                n_data_pilots = data_syms_count // pilot_interval
                if data_syms_count % pilot_interval == 0 and n_data_pilots > 0:
                    n_data_pilots -= 1  # 末尾导频省略
                data_section_len = data_syms_count + n_data_pilots
            else:
                data_section_len = data_syms_count
            data_start = len(tx_symbols) - data_section_len

            # 提取数据符号并去除导频
            data_rx = rx_symbols[data_start:]
            if pilot_interval > 0:
                data_syms = remove_pilots(data_rx, pilot_interval)
            else:
                data_syms = data_rx

            # 解调为LLR (BPSK/QPSK)
            if mod_type == "BPSK":
                # 取虚部 (bit 0→90°→imag=1, bit 1→-90°→imag=-1)
                llr = np.zeros(min(code_length, len(data_syms)))
                for i in range(len(llr)):
                    sym = data_syms[i]
                    if i % 2 == 1:
                        sym *= np.exp(1j * np.pi / 2)
                    llr[i] = np.imag(sym) * 2.0 / noise_var
            else:
                # QPSK: 2 bits per symbol
                llr = np.zeros(min(code_length, len(data_syms) * 2))
                for i in range(min(len(data_syms), code_length // 2)):
                    sym = data_syms[i]
                    if i % 2 == 1:
                        sym *= np.exp(1j * np.deg2rad(45.0))
                    # I/Q to LLR: b0→imag, b1→real
                    llr[2*i] = np.imag(sym) * 2.0 / noise_var
                    llr[2*i+1] = np.real(sym) * 2.0 / noise_var

            # 补齐到码长
            if len(llr) < code_length:
                llr = np.concatenate([llr, np.zeros(code_length - len(llr))])
            llr = llr[:code_length]

            # SC解码
            decoded = dec.decode(llr)

            bit_errors = int(np.sum(decoded != info))
            total_bit_errors += bit_errors
            total_bits += K
            if bit_errors > 0:
                frame_errors += 1

        ber = total_bit_errors / total_bits if total_bits > 0 else 0.0
        fer = frame_errors / n_blocks
        ber_list.append(ber)
        fer_list.append(fer)

    return {
        "snr_db": snr_range_db.tolist(),
        "ber": ber_list,
        "fer": fer_list,
    }


def run_phase3_simulation():
    """Phase 3 帧级仿真: 不同帧类型、导频配置的 BER/FER。"""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    snr_range = np.arange(-2, 8, 0.5)

    print("=== Phase 3 Frame-Level Simulation ===")
    print()

    configs = [
        {"frame_type": 2, "pilot_interval": 0, "label": "Type2 QPSK no-pilot"},
        {"frame_type": 2, "pilot_interval": 4, "label": "Type2 QPSK pilot=4"},
        {"frame_type": 3, "pilot_interval": 4, "label": "Type3 QPSK pilot=4"},
        {"frame_type": 4, "pilot_interval": 4, "label": "Type4 BPSK pilot=4"},
    ]

    results = []
    for i, cfg in enumerate(configs):
        print(f"[{i+1}/{len(configs)}] {cfg['label']}...")
        res = sim_frame_link(
            frame_type=cfg["frame_type"],
            num_data_bits=3000,
            rate_str="1/2",
            code_length=256,
            pilot_interval=cfg["pilot_interval"],
            snr_range_db=snr_range,
        )
        results.append((cfg["label"], res))
        for s, b, f in zip(res["snr_db"][::4], res["ber"][::4], res["fer"][::4]):
            print(f"  Eb/N0={s:5.1f} dB  BER={b:.5f}  FER={f:.3f}")

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))
    markers = ["o-", "s-", "^-", "d-"]

    for (label, res), mk in zip(results, markers):
        ber_plot = [max(b, 1e-6) for b in res["ber"]]
        ax1.semilogy(res["snr_db"], ber_plot, mk, label=label, markersize=3)
    ax1.set_xlabel("Eb/N0 (dB)")
    ax1.set_ylabel("Bit Error Rate")
    ax1.set_title("SparkLink SLE - Phase 3 Frame-Level BER")
    ax1.legend(fontsize=7)
    ax1.grid(True, which="both", ls="--", alpha=0.5)
    ax1.set_ylim(bottom=1e-5)

    for (label, res), mk in zip(results, markers):
        fer_plot = [max(f, 1e-4) for f in res["fer"]]
        ax2.semilogy(res["snr_db"], fer_plot, mk, label=label, markersize=3)
    ax2.set_xlabel("Eb/N0 (dB)")
    ax2.set_ylabel("Frame Error Rate")
    ax2.set_title("SparkLink SLE - Phase 3 Frame-Level FER")
    ax2.legend(fontsize=7)
    ax2.grid(True, which="both", ls="--", alpha=0.5)
    ax2.set_ylim(bottom=1e-4)

    fig.tight_layout()
    fig.savefig("ber_phase3.png", dpi=150)
    print(f"\nBER/FER curves saved to ber_phase3.png")


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "phase2":
        run_phase2_simulation()
    elif len(sys.argv) > 1 and sys.argv[1] == "phase3":
        run_phase3_simulation()
    else:
        run_phase1_simulation()