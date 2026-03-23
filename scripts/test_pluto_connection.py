#!/usr/bin/env python3
"""ANTSDR E310 / PlutoSDR 连通性验证脚本。

用法::

    # 使用默认 IP 地址 (192.168.2.1)
    uv run python scripts/test_pluto_connection.py

    # 指定设备 URI
    uv run python scripts/test_pluto_connection.py ip:192.168.3.1

    # 使用 Mock 后端 (无硬件)
    uv run python scripts/test_pluto_connection.py --mock

验证内容:
    1. 设备连接
    2. 频率设置 (SLE 2.4 GHz 频段)
    3. 采样率配置
    4. 正弦波发射与接收 (环回)
    5. 频率切换 (信道跳转)
"""

from __future__ import annotations

import argparse
import sys
import time

import numpy as np

from nearlink_sdr.phy.sdr_backend import SDRConfig, create_device

SLE_CHANNEL_0_FREQ_MHZ = 2402.0
TEST_TONE_HZ = 50_000
NUM_TX_SAMPS = 8192
NUM_RX_SAMPS = 8192


def generate_tone(freq_hz: float, sample_rate_hz: float, n: int) -> np.ndarray:
    """生成单频正弦波 IQ 信号。"""
    t = np.arange(n) / sample_rate_hz
    return (0.8 * np.exp(2j * np.pi * freq_hz * t)).astype(np.complex64)


def run_test(uri: str, use_mock: bool) -> bool:
    """执行连通性测试, 返回是否全部通过。"""
    backend = "mock" if use_mock else "pluto"
    sample_rate = 1e6

    cfg = SDRConfig(
        backend=backend,
        device_args=uri,
        channel_num=0,
        band="2400",
        sample_rate_hz=sample_rate,
        rx_gain_db=30.0,
        tx_gain_db=20.0,
        rx_buffer_size=NUM_RX_SAMPS,
    )

    passed = 0
    total = 5

    # ── 测试 1: 设备连接 ──
    print(f"[1/{total}] 连接设备 ({backend}: {uri or 'default'}) ...", end=" ")
    try:
        dev = create_device(cfg)
        print("通过")
        passed += 1
    except Exception as e:
        print(f"失败: {e}")
        return False

    # ── 测试 2: 频率设置 ──
    print(f"[2/{total}] 设置频率 {SLE_CHANNEL_0_FREQ_MHZ} MHz ...", end=" ")
    try:
        dev.set_frequency(SLE_CHANNEL_0_FREQ_MHZ * 1e6)
        print("通过")
        passed += 1
    except Exception as e:
        print(f"失败: {e}")

    # ── 测试 3: 采样率 ──
    print(f"[3/{total}] 设置采样率 {sample_rate / 1e6:.1f} Msps ...", end=" ")
    try:
        dev.set_sample_rate(sample_rate)
        print("通过")
        passed += 1
    except Exception as e:
        print(f"失败: {e}")

    # ── 测试 4: 发射与接收 ──
    print(f"[4/{total}] 发射 {NUM_TX_SAMPS} 样本, 接收 {NUM_RX_SAMPS} 样本 ...", end=" ")
    try:
        tone = generate_tone(TEST_TONE_HZ, sample_rate, NUM_TX_SAMPS)
        n_sent = dev.transmit(tone)
        time.sleep(0.05)  # 给硬件缓冲延迟
        rx = dev.receive(NUM_RX_SAMPS)
        if n_sent > 0 and len(rx) == NUM_RX_SAMPS:
            rx_power = float(np.mean(np.abs(rx) ** 2))
            print(f"通过 (TX={n_sent}, RXlen={len(rx)}, RXpwr={rx_power:.4e})")
            passed += 1
        else:
            print(f"失败: TX={n_sent}, RXlen={len(rx)}")
    except Exception as e:
        print(f"失败: {e}")

    # ── 测试 5: 信道切换 ──
    print(f"[5/{total}] 切换到信道 20 ...", end=" ")
    try:
        dev.tune_channel(20)
        print("通过")
        passed += 1
    except Exception as e:
        print(f"失败: {e}")

    # ── 清理 ──
    dev.close()

    print(f"\n结果: {passed}/{total} 通过")
    print(f"设备状态: {dev.status_string()}")
    return passed == total


def main() -> None:
    parser = argparse.ArgumentParser(description="ANTSDR/PlutoSDR 连通性验证")
    parser.add_argument(
        "uri",
        nargs="?",
        default="ip:192.168.2.1",
        help="设备 URI (默认: ip:192.168.2.1)",
    )
    parser.add_argument(
        "--mock",
        action="store_true",
        help="使用 Mock 后端 (无需硬件)",
    )
    args = parser.parse_args()

    ok = run_test(args.uri, args.mock)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
