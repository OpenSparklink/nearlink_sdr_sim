"""USRP E310 硬件验证脚本。

用于在真实 E310 硬件或 MockUSRP 上执行分步验证:
1. 设备初始化与基本参数检查
2. 频率设置与信道切换 (2402-2480 MHz)
3. 增益控制 (TX / RX)
4. 单载波发射与回环接收
5. PHY 帧级环回 (FT2 GFSK)
6. 跳频序列验证

用法:
  # Mock 模式 (无硬件)
  uv run python scripts/hw_verify.py --mock

  # 真实硬件 (自动发现)
  uv run python scripts/hw_verify.py

  # 指定设备地址
  uv run python scripts/hw_verify.py --addr "addr=192.168.10.2"
"""

from __future__ import annotations

import argparse
import sys
import time

import numpy as np

from nearlink_sdr.phy.channel import ChannelConfig, ChannelModel
from nearlink_sdr.phy.freq_hopping import BAND_2400, channel_to_freq
from nearlink_sdr.phy.mac_interface import iq_to_mac, mac_to_iq
from nearlink_sdr.phy.tx_pipeline import TxConfig
from nearlink_sdr.phy.usrp import (
    E310_RX_GAIN_MAX,
    E310_TX_GAIN_MAX,
    LoopbackBuffer,
    SLETransceiver,
    USRPConfig,
    USRPDevice,
    uhd_available,
)


class HWVerifier:
    """硬件验证执行器。"""

    def __init__(self, use_mock: bool, device_args: str = ""):
        self._use_mock = use_mock
        self._device_args = device_args
        self._pass_count = 0
        self._fail_count = 0
        self._loopback: LoopbackBuffer | None = None

    def _report(self, name: str, ok: bool, detail: str = ""):
        tag = "PASS" if ok else "FAIL"
        msg = f"  [{tag}] {name}"
        if detail:
            msg += f" -- {detail}"
        print(msg)
        if ok:
            self._pass_count += 1
        else:
            self._fail_count += 1

    def _make_device(self, **kwargs) -> USRPDevice:
        cfg_kw: dict = {"device_args": self._device_args}
        cfg_kw.update(kwargs)
        cfg = USRPConfig(**cfg_kw)
        return USRPDevice(
            config=cfg, use_mock=self._use_mock, loopback=self._loopback,
        )

    # ── Step 1: 设备初始化 ──

    def verify_init(self):
        print("\n=== Step 1: 设备初始化 ===")
        try:
            dev = self._make_device()
            self._report(
                "设备创建",
                True,
                f"{'Mock' if dev.is_mock else 'HW'} 模式",
            )
            status = dev.status_string()
            self._report("状态查询", bool(status), status)
        except Exception as e:
            self._report("设备创建", False, str(e))

    # ── Step 2: 频率设置与信道切换 ──

    def verify_frequency(self):
        print("\n=== Step 2: 频率与信道切换 ===")
        dev = self._make_device()

        # 验证各边界信道
        test_channels = [0, 19, 39]
        for ch in test_channels:
            try:
                dev.tune_channel(ch, BAND_2400)
                expected_mhz = channel_to_freq(ch, BAND_2400)
                actual_hz = dev.config.center_freq_hz
                ok = abs(actual_hz - expected_mhz * 1e6) < 1.0
                self._report(
                    f"信道 {ch}",
                    ok,
                    f"期望 {expected_mhz:.1f} MHz, "
                    f"实际 {actual_hz / 1e6:.1f} MHz",
                )
            except Exception as e:
                self._report(f"信道 {ch}", False, str(e))

        # 验证快速信道切换
        t0 = time.perf_counter()
        n_hops = 100
        for i in range(n_hops):
            dev.tune_channel(i % 40, BAND_2400)
        dt = time.perf_counter() - t0
        avg_us = dt / n_hops * 1e6
        self._report(
            f"快速跳频 ({n_hops} 次)",
            True,
            f"平均切换 {avg_us:.1f} us/次",
        )

    # ── Step 3: 增益控制 ──

    def verify_gain(self):
        print("\n=== Step 3: 增益控制 ===")
        dev = self._make_device()

        # RX 增益
        for g in [0.0, 30.0, 50.0, E310_RX_GAIN_MAX]:
            try:
                dev.set_rx_gain(g)
                self._report(f"RX gain {g:.1f} dB", True)
            except Exception as e:
                self._report(f"RX gain {g:.1f} dB", False, str(e))

        # TX 增益
        for g in [0.0, 20.0, 50.0, E310_TX_GAIN_MAX]:
            try:
                dev.set_tx_gain(g)
                self._report(f"TX gain {g:.1f} dB", True)
            except Exception as e:
                self._report(f"TX gain {g:.1f} dB", False, str(e))

        # 越界检查
        try:
            dev.set_rx_gain(E310_RX_GAIN_MAX + 1)
            self._report("RX gain 越界拒绝", False, "未抛出异常")
        except ValueError:
            self._report("RX gain 越界拒绝", True)

    # ── Step 4: 单载波 IQ 回环 ──

    def verify_iq_loopback(self):
        print("\n=== Step 4: IQ 回环 ===")
        # 创建带 loopback 的设备
        ch_cfg = ChannelConfig(snr_db=60.0, channel_type="awgn", seed=0)
        ch_model = ChannelModel(config=ch_cfg)
        self._loopback = LoopbackBuffer(channel_model=ch_model, seed=0)

        dev = self._make_device()
        xcvr = SLETransceiver(dev)
        xcvr.open()

        # 生成单载波测试信号
        n_samps = 1024
        t = np.arange(n_samps) / dev.config.sample_rate_hz
        fc = 100e3  # 100 kHz 单载波
        tx_iq = np.exp(1j * 2 * np.pi * fc * t).astype(np.complex64)

        self._loopback.clear()
        n_sent = xcvr.transmit_iq(tx_iq)
        rx_iq = xcvr.receive_iq(n_sent)

        # 计算相关性
        corr = np.abs(np.corrcoef(tx_iq.real, rx_iq.real)[0, 1])
        ok = corr > 0.95
        self._report(
            f"单载波回环 ({n_samps} 样本)",
            ok,
            f"TX/RX 相关系数 {corr:.4f}",
        )

        # 功率检查
        tx_pwr = np.mean(np.abs(tx_iq) ** 2)
        rx_pwr = np.mean(np.abs(rx_iq) ** 2)
        pwr_ratio_db = 10 * np.log10(rx_pwr / tx_pwr) if tx_pwr > 0 else -999
        self._report(
            "功率比",
            abs(pwr_ratio_db) < 10,
            f"RX/TX = {pwr_ratio_db:.1f} dB",
        )

        xcvr.close()
        self._loopback = None

    # ── Step 5: PHY 帧级回环 ──

    def verify_phy_loopback(self):
        print("\n=== Step 5: PHY 帧级回环 ===")
        ch_cfg = ChannelConfig(snr_db=50.0, channel_type="awgn", seed=1)
        ch_model = ChannelModel(config=ch_cfg)
        self._loopback = LoopbackBuffer(channel_model=ch_model, seed=1)

        dev = self._make_device()
        xcvr = SLETransceiver(dev)
        xcvr.open()

        payload = b"SLE E310 HW Verify"
        cfg = TxConfig(frame_type=2, mcs_index=7)

        iq = mac_to_iq(payload, cfg)
        self._loopback.clear()
        n_sent = xcvr.transmit_iq(iq)
        rx_iq = xcvr.receive_iq(n_sent)
        result = iq_to_mac(rx_iq, cfg, len(payload))

        self._report("PHY 头部 CRC", result.head_crc_ok)
        self._report("PHY 数据 CRC", result.crc_ok)
        if result.crc_ok:
            match = result.mac_payload == payload
            self._report("载荷比对", match)
        else:
            self._report("载荷比对", False, "CRC 失败, 跳过比对")

        xcvr.close()
        self._loopback = None

    # ── Step 6: 跳频回环 ──

    def verify_hopping_loopback(self):
        print("\n=== Step 6: 跳频回环 ===")
        ch_cfg = ChannelConfig(snr_db=60.0, channel_type="awgn", seed=2)
        ch_model = ChannelModel(config=ch_cfg)
        self._loopback = LoopbackBuffer(channel_model=ch_model, seed=2)

        dev = self._make_device()
        xcvr = SLETransceiver(dev)
        xcvr.open()

        n_samps = 256
        tx_iq = np.ones(n_samps, dtype=np.complex64) * (1 + 0j)
        hop_channels = [0, 10, 20, 30, 39]

        for ch in hop_channels:
            self._loopback.clear()
            xcvr.hop_and_transmit(ch, tx_iq)
            rx = xcvr.hop_and_receive(ch, n_samps)
            pwr = np.mean(np.abs(rx) ** 2)
            ch_ok = pwr > 0.5
            detail = f"信道 {ch}, 接收功率 {pwr:.3f}"
            self._report(f"跳频信道 {ch}", ch_ok, detail)
            if not ch_ok:
                pass  # 跳频失败不阻断后续测试

        xcvr.close()
        self._loopback = None

    # ── 执行全部验证 ──

    def run_all(self):
        mode = "MockUSRP" if self._use_mock else "USRP E310"
        uhd_status = "可用" if uhd_available() else "不可用"
        print(f"NearLink SDR 硬件验证 -- 模式: {mode}, UHD: {uhd_status}")
        print("=" * 60)

        self.verify_init()
        self.verify_frequency()
        self.verify_gain()
        self.verify_iq_loopback()
        self.verify_phy_loopback()
        self.verify_hopping_loopback()

        print("\n" + "=" * 60)
        total = self._pass_count + self._fail_count
        print(
            f"验证结果: {self._pass_count}/{total} 通过, "
            f"{self._fail_count} 失败"
        )
        return self._fail_count == 0


def main():
    parser = argparse.ArgumentParser(description="USRP E310 硬件验证")
    parser.add_argument(
        "--mock", action="store_true",
        help="使用 MockUSRP (无硬件环境)",
    )
    parser.add_argument(
        "--addr", type=str, default="",
        help="UHD 设备地址参数 (例如 'addr=192.168.10.2')",
    )
    args = parser.parse_args()

    use_mock = args.mock or not uhd_available()
    verifier = HWVerifier(use_mock=use_mock, device_args=args.addr)
    ok = verifier.run_all()
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
