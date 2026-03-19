"""TXS-10002-2025 链路仿真: GFSK/PSK 无编码 + Polar编码端到端仿真。"""

import numpy as np

from nearlink_sdr.common.polar import PolarDecoder, PolarEncoder, get_info_bit_count
from nearlink_sdr.phy.channel import ChannelModel
from nearlink_sdr.phy.gfsk import GFSKDemodulator, GFSKModulator
from nearlink_sdr.phy.preamble import generate_preamble
from nearlink_sdr.phy.psk import PSKDemodulator, PSKModulator
from nearlink_sdr.phy.sync_sequence import (
    sync_signal_1,
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
    for s, b in zip(gfsk_result["snr_db"], gfsk_result["ber"], strict=False):
        print(f"  SNR={s:2d} dB  BER={b:.5f}")

    # BPSK (帧类型3/4)
    print("[2/3] BPSK link simulation...")
    bpsk_result = sim_psk_link(num_data_bits=5000, mod_type="BPSK",
                               frame_type=3, snr_range_db=snr_range)
    for s, b in zip(bpsk_result["snr_db"], bpsk_result["ber"], strict=False):
        print(f"  SNR={s:2d} dB  BER={b:.5f}")

    # QPSK (帧类型2)
    print("[3/3] QPSK link simulation...")
    qpsk_result = sim_psk_link(num_data_bits=5000, mod_type="QPSK",
                               frame_type=2, snr_range_db=snr_range)
    for s, b in zip(qpsk_result["snr_db"], qpsk_result["ber"], strict=False):
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
    print("\nBER curve saved to ber_phase1.png")


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
        for s, b, f in zip(res["snr_db"][::4], res["ber"][::4], res["fer"][::4], strict=False):
            print(f"  Eb/N0={s:5.1f} dB  BER={b:.5f}  FER={f:.3f}")

    # 也运行无编码 BPSK 作为对比
    print(f"[{len(configs)+1}/{len(configs)+1}] Uncoded BPSK (reference)...")
    uncoded = sim_psk_link(num_data_bits=5000, mod_type="BPSK",
                           frame_type=3, snr_range_db=snr_range)

    # BER 曲线
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))

    markers = ["o-", "s-", "^-", "d-"]
    for (label, res), mk in zip(results, markers, strict=False):
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

    for (label, res), mk in zip(results, markers, strict=False):
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
    print("\nBER/FER curves saved to ber_phase2.png")


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
        FrameConfig,
        assemble_frame_bits,
        frame_to_symbols,
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
            data_syms = remove_pilots(data_rx, pilot_interval) if pilot_interval > 0 else data_rx

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
        for s, b, f in zip(res["snr_db"][::4], res["ber"][::4], res["fer"][::4], strict=False):
            print(f"  Eb/N0={s:5.1f} dB  BER={b:.5f}  FER={f:.3f}")

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))
    markers = ["o-", "s-", "^-", "d-"]

    for (label, res), mk in zip(results, markers, strict=False):
        ber_plot = [max(b, 1e-6) for b in res["ber"]]
        ax1.semilogy(res["snr_db"], ber_plot, mk, label=label, markersize=3)
    ax1.set_xlabel("Eb/N0 (dB)")
    ax1.set_ylabel("Bit Error Rate")
    ax1.set_title("SparkLink SLE - Phase 3 Frame-Level BER")
    ax1.legend(fontsize=7)
    ax1.grid(True, which="both", ls="--", alpha=0.5)
    ax1.set_ylim(bottom=1e-5)

    for (label, res), mk in zip(results, markers, strict=False):
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
    print("\nBER/FER curves saved to ber_phase3.png")


# ── Phase 4: 多径信道 + 均衡仿真 ──


def sim_channel_eq_link(
    channel_type: str = "rayleigh",
    rician_k_db: float = 6.0,
    eq_method: str = "mmse",
    rate_str: str = "1/2",
    code_length: int = 256,
    snr_range_db: np.ndarray | None = None,
    n_frames: int = 20,
    seed: int = 42,
) -> dict:
    """多径信道 + 均衡器 + Polar编码 BPSK 链路仿真。

    流程: 信息比特 → Polar编码 → BPSK调制 → 信道(衰落+AWGN) → 均衡 → LLR → 解码

    Args:
        channel_type: "awgn" / "rayleigh" / "rician" / "multipath"。
        rician_k_db: Rician K 因子。
        eq_method: "zf" / "mmse" / "none" (不均衡)。
        rate_str: Polar 码率。
        code_length: Polar 码长。
        snr_range_db: SNR 范围。
        n_frames: 每个 SNR 点的帧数。
        seed: 随机种子。

    Returns:
        {"snr_db": [...], "ber": [...], "fer": [...]}
    """
    from nearlink_sdr.phy.channel import PDP_2TAP, ChannelConfig
    from nearlink_sdr.phy.equalizer import equalize_1tap, equalize_mmse_freq

    if snr_range_db is None:
        snr_range_db = np.arange(-2, 12, 1)

    K = get_info_bit_count(rate_str, code_length)
    enc = PolarEncoder(code_length, K)
    dec = PolarDecoder(code_length, K)

    rng = np.random.default_rng(seed)
    ber_list, fer_list = [], []

    for snr in snr_range_db:
        total_errors, total_bits, frame_errors = 0, 0, 0

        for _ in range(n_frames):
            info = rng.integers(0, 2, size=K, dtype=np.int8)
            coded = enc.encode(info)

            # BPSK 调制: 0 → +1, 1 → -1
            tx = (1 - 2 * coded.astype(np.float64)).astype(complex)

            # 信道
            frame_seed = int(rng.integers(0, 2**31))
            cfg = ChannelConfig(
                snr_db=float(snr),
                channel_type=channel_type,
                rician_k_db=rician_k_db,
                pdp=list(PDP_2TAP),
                seed=frame_seed,
            )
            ch = ChannelModel(config=cfg)
            noise_var = ch.noise_variance

            if channel_type == "multipath":
                taps = ch.get_channel_taps(len(tx))
                # 手动应用多径: 对每条路径做延迟卷积
                n_sig = len(tx)
                faded = np.zeros(n_sig, dtype=complex)
                for tap_i, (delay, _) in enumerate(PDP_2TAP):
                    if delay < n_sig and tap_i < taps.shape[0]:
                        shifted = np.zeros(n_sig, dtype=complex)
                        shifted[delay:] = tx[:n_sig - delay]
                        faded += taps[tap_i, :n_sig] * shifted
                # 手动加噪
                sig_power = np.mean(np.abs(faded) ** 2) if np.mean(np.abs(faded) ** 2) > 1e-20 else 1.0
                n_power = sig_power / (10.0 ** (float(snr) / 10.0)) if snr > -50 else sig_power * 100
                noise = np.sqrt(n_power / 2) * (ch._rng.standard_normal(n_sig) + 1j * ch._rng.standard_normal(n_sig))
                rx = faded + noise

                if eq_method == "none":
                    eq = rx
                else:
                    h_time = taps[:, 0]
                    h_freq = np.fft.fft(h_time, len(rx))
                    if eq_method == "mmse":
                        eq = equalize_mmse_freq(rx, h_freq, noise_var)
                    else:
                        from nearlink_sdr.phy.equalizer import equalize_zf
                        eq = equalize_zf(rx, h_freq)
            elif channel_type in ("rayleigh", "rician"):
                taps = ch.get_channel_taps(len(tx))
                h = taps[0, :]
                # 手动应用平坦衰落 + 加噪
                faded = tx * h
                sig_power = np.mean(np.abs(faded) ** 2) if np.mean(np.abs(faded) ** 2) > 1e-20 else 1.0
                n_power = sig_power / (10.0 ** (float(snr) / 10.0)) if snr > -50 else sig_power * 100
                noise = np.sqrt(n_power / 2) * (ch._rng.standard_normal(len(tx)) + 1j * ch._rng.standard_normal(len(tx)))
                rx = faded + noise

                if eq_method == "none":
                    eq = rx
                else:
                    eq = equalize_1tap(rx, h, noise_var=noise_var, method=eq_method)
            else:
                rx = ch.apply_fading(tx)
                eq = rx

            # 软 LLR: BPSK +1→bit0, -1→bit1, LLR = 2*real(y)/sigma^2
            noise_var = ch.noise_variance
            if noise_var < 1e-10:
                noise_var = 1e-10
            llr = np.real(eq) * 2.0 / noise_var
            llr = llr[:code_length]
            if len(llr) < code_length:
                llr = np.concatenate([llr, np.zeros(code_length - len(llr))])

            decoded = dec.decode(llr.real)
            errors = int(np.sum(decoded != info))
            total_errors += errors
            total_bits += K
            if errors > 0:
                frame_errors += 1

        ber = total_errors / total_bits if total_bits > 0 else 0.0
        fer = frame_errors / n_frames
        ber_list.append(ber)
        fer_list.append(fer)

    return {"snr_db": snr_range_db.tolist(), "ber": ber_list, "fer": fer_list}


def run_phase4_simulation():
    """Phase 4: 不同信道模型 + 均衡器的 BER/FER 比较。"""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    snr_range = np.arange(-2, 12, 1)

    print("=== Phase 4 Channel & Equalizer Simulation ===")
    print()

    configs = [
        {"channel_type": "awgn", "eq_method": "none", "label": "AWGN (baseline)"},
        {"channel_type": "rayleigh", "eq_method": "none", "label": "Rayleigh (no eq)"},
        {"channel_type": "rayleigh", "eq_method": "mmse", "label": "Rayleigh + MMSE eq"},
        {"channel_type": "rician", "eq_method": "none", "label": "Rician K=6dB (no eq)"},
        {"channel_type": "rician", "eq_method": "mmse", "label": "Rician K=6dB + MMSE eq"},
        {"channel_type": "multipath", "eq_method": "none", "label": "Multipath (no eq)"},
        {"channel_type": "multipath", "eq_method": "mmse", "label": "Multipath + MMSE eq"},
    ]

    results = []
    for i, cfg in enumerate(configs):
        print(f"[{i+1}/{len(configs)}] {cfg['label']}...")
        res = sim_channel_eq_link(
            channel_type=cfg["channel_type"],
            eq_method=cfg["eq_method"],
            rate_str="1/2",
            code_length=256,
            snr_range_db=snr_range,
            n_frames=30,
        )
        results.append((cfg["label"], res))
        for s, b, f in zip(res["snr_db"][::3], res["ber"][::3], res["fer"][::3], strict=False):
            print(f"  Eb/N0={s:5.1f} dB  BER={b:.5f}  FER={f:.3f}")

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))
    markers = ["o-", "s--", "s-", "^--", "^-", "d--", "d-"]

    for (label, res), mk in zip(results, markers, strict=False):
        ber_plot = [max(b, 1e-6) for b in res["ber"]]
        ax1.semilogy(res["snr_db"], ber_plot, mk, label=label, markersize=3)
    ax1.set_xlabel("Eb/N0 (dB)")
    ax1.set_ylabel("Bit Error Rate")
    ax1.set_title("SparkLink SLE - Phase 4 Channel BER")
    ax1.legend(fontsize=6)
    ax1.grid(True, which="both", ls="--", alpha=0.5)
    ax1.set_ylim(bottom=1e-5)

    for (label, res), mk in zip(results, markers, strict=False):
        fer_plot = [max(f, 1e-4) for f in res["fer"]]
        ax2.semilogy(res["snr_db"], fer_plot, mk, label=label, markersize=3)
    ax2.set_xlabel("Eb/N0 (dB)")
    ax2.set_ylabel("Frame Error Rate")
    ax2.set_title("SparkLink SLE - Phase 4 Channel FER")
    ax2.legend(fontsize=6)
    ax2.grid(True, which="both", ls="--", alpha=0.5)
    ax2.set_ylim(bottom=1e-4)

    fig.tight_layout()
    fig.savefig("ber_phase4.png", dpi=150)
    print("\nBER/FER curves saved to ber_phase4.png")


# ── Phase 5: 跳频链路仿真 ──


def sim_hopping_link(
    hop_param2: int = 0xABCD,
    n_hops: int = 20,
    rate_str: str = "1/2",
    code_length: int = 256,
    snr_range_db: np.ndarray | None = None,
    bandwidth_mhz: int = 1,
    blocked_ratio: float = 0.0,
    seed: int = 42,
) -> dict:
    """跳频链路仿真: 数据帧在多个跳频信道间传输, 每跳独立衰落。

    流程: 生成跳频序列 → 每跳: Polar编码 → BPSK调制 → 独立 Rayleigh 信道 → 均衡 → 解码

    Args:
        hop_param2: 跳频参数 2。
        n_hops: 每个 SNR 点的跳频次数 (帧数)。
        rate_str: Polar 码率。
        code_length: Polar 码长。
        snr_range_db: SNR 范围。
        bandwidth_mhz: 信道带宽 1/2/4 MHz。
        blocked_ratio: 被阻塞信道占比 (0~1)。
        seed: 随机种子。

    Returns:
        {"snr_db": [...], "ber": [...], "fer": [...], "channels_used": [...]}
    """
    from nearlink_sdr.phy.channel import ChannelConfig
    from nearlink_sdr.phy.equalizer import equalize_1tap
    from nearlink_sdr.phy.freq_hopping import (
        FreqTable,
        generate_hopping_sequence,
    )

    if snr_range_db is None:
        snr_range_db = np.arange(-2, 14, 2)

    rng = np.random.default_rng(seed)
    K = get_info_bit_count(rate_str, code_length)
    enc = PolarEncoder(code_length, K)
    dec = PolarDecoder(code_length, K)

    # 频率表: 按比例阻塞部分信道
    ft = FreqTable(band="2400", bandwidth_mhz=bandwidth_mhz)
    all_ch = ft.full_table()
    n_blocked = int(len(all_ch) * blocked_ratio)
    if n_blocked > 0:
        blocked_idx = rng.choice(len(all_ch), n_blocked, replace=False)
        ft.blocked_channels = {all_ch[i] for i in blocked_idx}

    # 生成跳频序列
    hop_seq = generate_hopping_sequence(
        n_hops, hop_param2, ft, link_type="data", start_slot=0,
    )

    ber_list, fer_list = [], []
    channels_used = sorted(set(hop_seq))

    for snr in snr_range_db:
        total_errors, total_bits, frame_errors = 0, 0, 0

        for _hop_i, _ch_num in enumerate(hop_seq):
            info = rng.integers(0, 2, size=K, dtype=np.int8)
            coded = enc.encode(info)
            tx = (1 - 2 * coded.astype(np.float64)).astype(complex)

            # 每跳独立 Rayleigh 衰落 (模拟跳频分集效果)
            frame_seed = int(rng.integers(0, 2**31))
            cfg = ChannelConfig(
                snr_db=float(snr),
                channel_type="rayleigh",
                seed=frame_seed,
            )
            ch = ChannelModel(config=cfg)
            noise_var = ch.noise_variance

            taps = ch.get_channel_taps(len(tx))
            h = taps[0, :]
            faded = tx * h
            sig_power = max(np.mean(np.abs(faded) ** 2), 1e-20)
            n_power = sig_power / (10.0 ** (float(snr) / 10.0))
            noise = np.sqrt(n_power / 2) * (
                ch._rng.standard_normal(len(tx))
                + 1j * ch._rng.standard_normal(len(tx))
            )
            rx = faded + noise

            eq = equalize_1tap(rx, h, noise_var=noise_var, method="mmse")

            llr = np.real(eq) * 2.0 / max(noise_var, 1e-10)
            llr = llr[:code_length]
            decoded = dec.decode(llr.real)
            errors = int(np.sum(decoded != info))
            total_errors += errors
            total_bits += K
            if errors > 0:
                frame_errors += 1

        ber = total_errors / total_bits if total_bits > 0 else 0.0
        fer = frame_errors / n_hops
        ber_list.append(ber)
        fer_list.append(fer)

    return {
        "snr_db": snr_range_db.tolist(),
        "ber": ber_list,
        "fer": fer_list,
        "channels_used": channels_used,
    }


def run_phase5_simulation():
    """Phase 5: 跳频链路仿真 — 比较不同跳频配置的 BER/FER。"""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    from nearlink_sdr.phy.freq_hopping import derive_hop_param2

    snr_range = np.arange(-2, 14, 2)

    print("=== Phase 5 Frequency Hopping Link Simulation ===")
    print()

    hp2 = derive_hop_param2(0xDEADBEEF, 32)

    configs = [
        {"bandwidth_mhz": 1, "blocked_ratio": 0.0,
         "label": "1 MHz, no blocking"},
        {"bandwidth_mhz": 1, "blocked_ratio": 0.3,
         "label": "1 MHz, 30% blocked"},
        {"bandwidth_mhz": 2, "blocked_ratio": 0.0,
         "label": "2 MHz, no blocking"},
        {"bandwidth_mhz": 4, "blocked_ratio": 0.0,
         "label": "4 MHz, no blocking"},
    ]

    results = []
    for i, cfg in enumerate(configs):
        print(f"[{i + 1}/{len(configs)}] {cfg['label']}...")
        res = sim_hopping_link(
            hop_param2=hp2,
            n_hops=30,
            rate_str="1/2",
            code_length=256,
            snr_range_db=snr_range,
            bandwidth_mhz=cfg["bandwidth_mhz"],
            blocked_ratio=cfg["blocked_ratio"],
        )
        results.append((cfg["label"], res))
        print(f"  Channels used: {len(res['channels_used'])}")
        for s, b, f in zip(res["snr_db"][::2], res["ber"][::2], res["fer"][::2], strict=False):
            print(f"  Eb/N0={s:5.1f} dB  BER={b:.5f}  FER={f:.3f}")

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))
    markers = ["o-", "s--", "^-", "d-"]

    for (label, res), mk in zip(results, markers, strict=False):
        ber_plot = [max(b, 1e-6) for b in res["ber"]]
        ax1.semilogy(res["snr_db"], ber_plot, mk, label=label, markersize=4)
    ax1.set_xlabel("Eb/N0 (dB)")
    ax1.set_ylabel("Bit Error Rate")
    ax1.set_title("SparkLink SLE - Phase 5 Hopping BER")
    ax1.legend(fontsize=7)
    ax1.grid(True, which="both", ls="--", alpha=0.5)
    ax1.set_ylim(bottom=1e-5)

    for (label, res), mk in zip(results, markers, strict=False):
        fer_plot = [max(f, 1e-4) for f in res["fer"]]
        ax2.semilogy(res["snr_db"], fer_plot, mk, label=label, markersize=4)
    ax2.set_xlabel("Eb/N0 (dB)")
    ax2.set_ylabel("Frame Error Rate")
    ax2.set_title("SparkLink SLE - Phase 5 Hopping FER")
    ax2.legend(fontsize=7)
    ax2.grid(True, which="both", ls="--", alpha=0.5)
    ax2.set_ylim(bottom=1e-4)

    fig.tight_layout()
    fig.savefig("ber_phase5.png", dpi=150)
    print("\nBER/FER curves saved to ber_phase5.png")


# ── Phase 6: 全链路 Pipeline 仿真 ──


def sim_pipeline_link(
    frame_type: int = 2,
    mcs_index: int = 7,
    n_data_bytes: int = 10,
    snr_range_db: np.ndarray | None = None,
    n_frames: int = 20,
    sps: int = 4,
    seed: int = 42,
) -> dict:
    """使用 tx_chain / rx_chain 的全链路端到端仿真。

    Args:
        frame_type: 帧类型 (1-4)
        mcs_index: MCS 索引
        n_data_bytes: 数据长度 (字节)
        snr_range_db: Eb/N0 扫描范围 (dB)
        n_frames: 每个 SNR 点的仿真帧数
        sps: 每符号采样数
        seed: 随机种子

    Returns:
        {"snr_db": [...], "ber": [...], "fer": [...]}
    """
    from nearlink_sdr.phy.rx_pipeline import rx_chain
    from nearlink_sdr.phy.tx_pipeline import TxConfig, tx_chain

    if snr_range_db is None:
        snr_range_db = np.arange(0, 16, 2)

    rng = np.random.default_rng(seed)

    # 根据帧类型确定配置
    if frame_type == 1:
        ctrl_bits_len = 20
        crc_len = 24
        head_crc_len = 12
        pilot_interval = 0
    elif frame_type == 2:
        ctrl_bits_len = 28
        crc_len = 24
        head_crc_len = 12
        pilot_interval = 8
    else:  # FT3/FT4
        ctrl_bits_len = 27
        crc_len = 24
        head_crc_len = 24
        pilot_interval = 4

    cfg = TxConfig(
        frame_type=frame_type,
        mcs_index=mcs_index,
        pid=0x123456 if frame_type <= 2 else 0,  # FT3/4 用 m_seq_index
        whitening_seed=0x52,
        crc_seed=0x555555,
        crc_len=crc_len,
        ctrl_bits_len=ctrl_bits_len,
        pilot_interval=pilot_interval,
        sps=sps,
    )

    n_data_bits = n_data_bytes * 8
    ber_list, fer_list = [], []

    for snr in snr_range_db:
        total_errors, total_bits, frame_errors = 0, 0, 0
        ch = ChannelModel(snr_db=float(snr))

        for _ in range(n_frames):
            # 生成随机控制信息和数据
            head_bits = rng.integers(0, 2, ctrl_bits_len + head_crc_len, dtype=np.int8)
            data_bits = rng.integers(0, 2, n_data_bits, dtype=int)

            # TX
            iq = tx_chain(head_bits, data_bits, cfg)

            # AWGN 信道
            rx_iq = ch.apply_awgn(iq)

            # RX
            result = rx_chain(rx_iq, cfg, n_data_bytes)

            # 统计
            errors = int(np.sum(result.data_bits[:n_data_bits] != data_bits))
            total_errors += errors
            total_bits += n_data_bits
            if not result.crc_ok:
                frame_errors += 1

        ber = total_errors / total_bits if total_bits > 0 else 0.0
        fer = frame_errors / n_frames
        ber_list.append(ber)
        fer_list.append(fer)

    return {"snr_db": snr_range_db.tolist(), "ber": ber_list, "fer": fer_list}


def run_phase6_simulation():
    """Phase 6: 全链路 Pipeline BER/FER 仿真 — 不同 MCS + 帧类型。"""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    snr_range = np.arange(0, 16, 1)

    print("=== Phase 6 Full Pipeline Link Simulation ===")
    print()

    configs = [
        {"frame_type": 2, "mcs_index": 5, "label": "FT2 MCS5 QPSK R=5/8"},
        {"frame_type": 2, "mcs_index": 7, "label": "FT2 MCS7 QPSK R=7/8"},
        {"frame_type": 2, "mcs_index": 8, "label": "FT2 MCS8 QPSK R=1/1"},
        {"frame_type": 4, "mcs_index": 0, "label": "FT4 MCS0 BPSK R=1/4"},
        {"frame_type": 1, "mcs_index": 8, "label": "FT1 GFSK uncoded"},
    ]

    results = []
    for i, cfg in enumerate(configs):
        print(f"[{i+1}/{len(configs)}] {cfg['label']}...")
        res = sim_pipeline_link(
            frame_type=cfg["frame_type"],
            mcs_index=cfg["mcs_index"],
            n_data_bytes=10,
            snr_range_db=snr_range,
            n_frames=50,
        )
        results.append((cfg["label"], res))
        for s, b, f in zip(res["snr_db"][::4], res["ber"][::4], res["fer"][::4], strict=False):
            print(f"  Eb/N0={s:5.1f} dB  BER={b:.5f}  FER={f:.3f}")

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))
    markers = ["o-", "s-", "^-", "d-", "x-"]

    for (label, res), mk in zip(results, markers, strict=False):
        ber_plot = [max(b, 1e-6) for b in res["ber"]]
        ax1.semilogy(res["snr_db"], ber_plot, mk, label=label, markersize=4)
    ax1.set_xlabel("Eb/N0 (dB)")
    ax1.set_ylabel("Bit Error Rate")
    ax1.set_title("SparkLink SLE - Phase 6 Pipeline BER")
    ax1.legend(fontsize=7)
    ax1.grid(True, which="both", ls="--", alpha=0.5)
    ax1.set_ylim(bottom=1e-5)

    for (label, res), mk in zip(results, markers, strict=False):
        fer_plot = [max(f, 1e-4) for f in res["fer"]]
        ax2.semilogy(res["snr_db"], fer_plot, mk, label=label, markersize=4)
    ax2.set_xlabel("Eb/N0 (dB)")
    ax2.set_ylabel("Frame Error Rate")
    ax2.set_title("SparkLink SLE - Phase 6 Pipeline FER")
    ax2.legend(fontsize=7)
    ax2.grid(True, which="both", ls="--", alpha=0.5)
    ax2.set_ylim(bottom=1e-4)

    fig.tight_layout()
    fig.savefig("ber_phase6.png", dpi=150)
    print("\nBER/FER curves saved to ber_phase6.png")


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "phase2":
        run_phase2_simulation()
    elif len(sys.argv) > 1 and sys.argv[1] == "phase3":
        run_phase3_simulation()
    elif len(sys.argv) > 1 and sys.argv[1] == "phase4":
        run_phase4_simulation()
    elif len(sys.argv) > 1 and sys.argv[1] == "phase5":
        run_phase5_simulation()
    elif len(sys.argv) > 1 and sys.argv[1] == "phase6":
        run_phase6_simulation()
    else:
        run_phase1_simulation()
