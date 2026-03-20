"""SLE 物理层回环测试脚本。

在 E310 硬件或 MockUSRP 上执行 PHY 全链路回环:
  mac_to_iq → SLETransceiver TX → 信道/线缆 → RX → iq_to_mac

支持多种帧类型和 MCS, 统计 BER/FER。

用法:
  # Mock 模式快速验证
  uv run python scripts/phy_loopback.py --mock

  # 真实硬件, FT2 MCS 0-7 各 10 帧
  uv run python scripts/phy_loopback.py --frames 10

  # 指定帧类型和 MCS
  uv run python scripts/phy_loopback.py --mock --ft 1 --mcs 0 --frames 20
"""

from __future__ import annotations

import argparse
import sys
import time

import numpy as np

from nearlink_sdr.phy.channel import ChannelConfig, ChannelModel
from nearlink_sdr.phy.rx_pipeline import rx_chain
from nearlink_sdr.phy.tx_pipeline import TxConfig, tx_chain
from nearlink_sdr.phy.usrp import (
    LoopbackBuffer,
    SLETransceiver,
    USRPConfig,
    USRPDevice,
    uhd_available,
)


def _make_cfg(frame_type: int, mcs_index: int) -> TxConfig:
    """根据帧类型创建合适的 TxConfig。"""
    if frame_type in (3, 4):
        return TxConfig(
            frame_type=frame_type,
            mcs_index=mcs_index,
            ctrl_bits_len=27,  # B 组控制信息
        )
    return TxConfig(frame_type=frame_type, mcs_index=mcs_index)


def run_loopback_test(
    xcvr: SLETransceiver,
    loopback: LoopbackBuffer | None,
    frame_type: int,
    mcs_index: int,
    num_frames: int,
    payload_size: int,
    snr_db: float,
) -> dict:
    """执行单组回环测试。

    Returns:
        包含 total/success/ber_avg/elapsed_s 的统计字典。
    """
    cfg = _make_cfg(frame_type, mcs_index)
    rng = np.random.default_rng(42)

    total = 0
    success = 0
    ber_sum = 0.0
    t0 = time.perf_counter()

    for _ in range(num_frames):
        data_bits = rng.integers(0, 2, size=payload_size * 8, dtype=np.int8)
        # 头部比特: FT2 = A组(28 info + 12 CRC = 40), FT3/4 = B组(27 info + 24 CRC = 51)
        if frame_type in (3, 4):
            head_bits = np.zeros(51, dtype=np.int8)
        else:
            head_bits = np.zeros(cfg.ctrl_bits_len, dtype=np.int8)
        iq = tx_chain(head_bits, data_bits, cfg)

        if loopback is not None:
            loopback.clear()
        n_sent = xcvr.transmit_iq(iq)
        rx_iq = xcvr.receive_iq(n_sent)
        result = rx_chain(rx_iq, cfg, payload_size)

        total += 1
        if result.crc_ok:
            success += 1
            n_cmp = min(len(data_bits), len(result.data_bits))
            errs = int(np.sum(data_bits[:n_cmp] != result.data_bits[:n_cmp]))
            ber_sum += errs / max(n_cmp, 1)

    elapsed = time.perf_counter() - t0
    return {
        "total": total,
        "success": success,
        "fer": (total - success) / max(total, 1),
        "ber_avg": ber_sum / max(success, 1) if success > 0 else 1.0,
        "elapsed_s": elapsed,
    }


def main():
    parser = argparse.ArgumentParser(description="SLE PHY 回环测试")
    parser.add_argument("--mock", action="store_true", help="使用 MockUSRP")
    parser.add_argument("--addr", type=str, default="", help="UHD 设备地址")
    parser.add_argument("--ft", type=int, default=0, help="帧类型 (1/2/3/4, 0=全部)")
    parser.add_argument("--mcs", type=int, default=-1, help="MCS 索引 (-1=全部)")
    parser.add_argument("--frames", type=int, default=5, help="每组帧数")
    parser.add_argument("--size", type=int, default=32, help="载荷字节数")
    parser.add_argument("--snr", type=float, default=50.0, help="信噪比 (dB)")
    args = parser.parse_args()

    use_mock = args.mock or not uhd_available()

    # 构建测试矩阵
    # FT1 容量有限 (GFSK, uncoded ctrl), 使用较小载荷
    # FT3/FT4 按标准使用 MCS0
    ft_mcs_list: list[tuple[int, int, int]] = []  # (ft, mcs, payload_size)
    if args.ft > 0 and args.mcs >= 0:
        ft_mcs_list.append((args.ft, args.mcs, args.size))
    elif args.ft > 0:
        mcs_range = {1: [0], 2: list(range(8)), 3: [0], 4: [0]}
        sz = 4 if args.ft == 1 else args.size
        for m in mcs_range.get(args.ft, [0]):
            ft_mcs_list.append((args.ft, m, sz))
    else:
        ft_mcs_list = [
            (2, 0, args.size), (2, 3, args.size), (2, 7, args.size),
            (3, 0, args.size),
            (4, 0, args.size),
        ]

    # 初始化设备
    ch_cfg = ChannelConfig(snr_db=args.snr, channel_type="awgn", seed=0)
    ch_model = ChannelModel(config=ch_cfg)
    loopback = LoopbackBuffer(channel_model=ch_model, seed=0) if use_mock else None

    usrp_cfg = USRPConfig(sample_rate_hz=1e6)
    dev = USRPDevice(config=usrp_cfg, use_mock=use_mock, loopback=loopback)
    xcvr = SLETransceiver(dev)
    xcvr.open()

    mode = "MockUSRP" if use_mock else "USRP E310"
    print(f"SLE PHY 回环测试 -- 模式: {mode}, SNR: {args.snr} dB")
    print(f"载荷: {args.size} bytes, 每组: {args.frames} 帧")
    print("=" * 70)
    print(f"{'FT':>4} {'MCS':>4} {'Frames':>8} {'Success':>8} "
          f"{'FER':>8} {'BER':>10} {'Time(s)':>8}")
    print("-" * 70)

    all_pass = True
    for ft, mcs, payload_sz in ft_mcs_list:
        result = run_loopback_test(
            xcvr, loopback, ft, mcs, args.frames, payload_sz, args.snr,
        )
        print(
            f"{ft:>4} {mcs:>4} {result['total']:>8} {result['success']:>8} "
            f"{result['fer']:>8.4f} {result['ber_avg']:>10.6f} "
            f"{result['elapsed_s']:>8.3f}"
        )
        if result["fer"] > 0:
            all_pass = False

    print("=" * 70)
    verdict = "ALL PASS" if all_pass else "SOME FAILURES"
    print(f"结果: {verdict}")

    xcvr.close()
    sys.exit(0 if all_pass else 1)


if __name__ == "__main__":
    main()
