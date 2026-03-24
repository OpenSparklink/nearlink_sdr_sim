"""SDR 后端抽象层单元测试。

覆盖 sdr_backend、mock_backend 的核心功能,
pluto_backend / uhd_backend 仅测试无硬件环境下的条件导入与配置校验。
"""

from __future__ import annotations

import numpy as np
import pytest

from nearlink_sdr.phy.mock_backend import LoopbackBuffer, MockDevice
from nearlink_sdr.phy.sdr_backend import SDRConfig, create_device

# ── SDRConfig ──


class TestSDRConfig:
    def test_defaults(self):
        cfg = SDRConfig()
        assert cfg.backend == "mock"
        assert cfg.channel_num == 0
        assert cfg.band == "2400"
        assert cfg.sample_rate_hz == 1e6

    def test_center_freq_channel_0(self):
        cfg = SDRConfig(channel_num=0, band="2400")
        assert cfg.center_freq_hz == pytest.approx(2402e6)

    def test_center_freq_channel_39(self):
        cfg = SDRConfig(channel_num=39, band="2400")
        assert cfg.center_freq_hz == pytest.approx(2441e6)


# ── create_device 工厂 ──


class TestCreateDevice:
    def test_mock(self):
        dev = create_device(SDRConfig(backend="mock"))
        assert isinstance(dev, MockDevice)
        assert dev.is_mock

    def test_unknown_raises(self):
        with pytest.raises(ValueError, match="不支持的后端类型"):
            create_device(SDRConfig(backend="unknown"))

    def test_pluto_without_lib(self):
        """pluto 后端在无 pyadi-iio 时应报 RuntimeError。"""
        from nearlink_sdr.phy.pluto_backend import adi_available

        if adi_available():
            pytest.skip("pyadi-iio 已安装, 跳过此测试")
        with pytest.raises(RuntimeError, match="pyadi-iio"):
            create_device(SDRConfig(backend="pluto"))


# ── LoopbackBuffer ──


class TestLoopbackBuffer:
    def test_push_pull(self):
        buf = LoopbackBuffer()
        data = np.array([1 + 2j, 3 + 4j], dtype=np.complex64)
        buf.push(data)
        assert buf.available == 2
        out = buf.pull(2)
        assert len(out) == 2
        np.testing.assert_allclose(out, data, atol=1e-5)

    def test_partial_pull(self):
        buf = LoopbackBuffer()
        data = np.ones(10, dtype=np.complex64)
        buf.push(data)
        out1 = buf.pull(3)
        assert len(out1) == 3
        assert buf.available == 7
        out2 = buf.pull(20)
        assert len(out2) == 7

    def test_empty_pull(self):
        buf = LoopbackBuffer()
        out = buf.pull(5)
        assert len(out) == 0

    def test_clear(self):
        buf = LoopbackBuffer()
        buf.push(np.ones(5, dtype=np.complex64))
        buf.clear()
        assert buf.available == 0


# ── MockDevice ──


class TestMockDevice:
    def setup_method(self):
        self.cfg = SDRConfig(
            backend="mock",
            channel_num=5,
            band="2400",
            sample_rate_hz=2e6,
            rx_gain_db=20.0,
            tx_gain_db=10.0,
        )

    def test_create_and_configure(self):
        dev = MockDevice(self.cfg)
        assert dev.is_mock
        assert "Mock" in dev.status_string()

    def test_transmit_receive_noise(self):
        """无环回时, receive 返回噪声。"""
        dev = MockDevice(self.cfg)
        n = dev.transmit(np.ones(100, dtype=np.complex64))
        assert n == 100
        rx = dev.receive(64)
        assert rx.shape == (64,)
        assert rx.dtype == np.complex64

    def test_loopback(self):
        """环回模式下 TX 数据能被 RX 读回。"""
        buf = LoopbackBuffer()
        dev = MockDevice(self.cfg, loopback=buf)
        tx_data = np.array([1 + 0j, 0 + 1j, -1 + 0j], dtype=np.complex64)
        dev.transmit(tx_data)
        rx = dev.receive(3)
        np.testing.assert_allclose(rx, tx_data, atol=1e-6)

    def test_loopback_pad_short(self):
        """环回数据不足时补零。"""
        buf = LoopbackBuffer()
        dev = MockDevice(self.cfg, loopback=buf)
        dev.transmit(np.ones(3, dtype=np.complex64))
        rx = dev.receive(10)
        assert len(rx) == 10
        np.testing.assert_allclose(rx[:3], np.ones(3, dtype=np.complex64))
        np.testing.assert_allclose(rx[3:], np.zeros(7, dtype=np.complex64))

    def test_set_frequency(self):
        dev = MockDevice(self.cfg)
        dev.set_frequency(2450e6)
        assert dev._freq_hz == 2450e6

    def test_set_sample_rate(self):
        dev = MockDevice(self.cfg)
        dev.set_sample_rate(4e6)
        assert dev._sample_rate_hz == 4e6
        assert dev.config.sample_rate_hz == 4e6

    def test_set_gains(self):
        dev = MockDevice(self.cfg)
        dev.set_rx_gain(50.0)
        dev.set_tx_gain(30.0)
        assert dev._rx_gain_db == 50.0
        assert dev._tx_gain_db == 30.0

    def test_tune_channel(self):
        dev = MockDevice(self.cfg)
        dev.tune_channel(20)
        assert dev.config.channel_num == 20
        # 信道 20 → 2422 MHz (标准频率表)
        assert dev._freq_hz == pytest.approx(2422e6)

    def test_close(self):
        buf = LoopbackBuffer()
        buf.push(np.ones(5, dtype=np.complex64))
        dev = MockDevice(self.cfg, loopback=buf)
        dev.close()
        assert buf.available == 0


# ── PlutoDevice 常量 ──


class TestPlutoConstants:
    def test_freq_range(self):
        from nearlink_sdr.phy.pluto_backend import PLUTO_FREQ_MAX_HZ, PLUTO_FREQ_MIN_HZ

        assert PLUTO_FREQ_MIN_HZ < 2.4e9 < PLUTO_FREQ_MAX_HZ

    def test_gain_to_attn(self):
        from nearlink_sdr.phy.pluto_backend import PlutoDevice

        # 0 dB 增益 → 0 dB 衰减
        assert PlutoDevice._gain_to_attn(0.0) == 0.0
        # 50 dB 增益 → -50 dB 衰减
        assert PlutoDevice._gain_to_attn(50.0) == -50.0
        # 超过 89.75 → clamp 到 -89.75
        assert PlutoDevice._gain_to_attn(100.0) == -89.75
        # 负值 → clamp 到 0
        assert PlutoDevice._gain_to_attn(-5.0) == 0.0


# ── node.py SDR 集成 ──


class TestNodeSDRIntegration:
    def test_node_with_sdr_config_mock(self):
        """通过 sdr_config 使用 mock 后端创建节点。"""
        from nearlink_sdr.node import NodeConfig, SleNode, TransportMode

        cfg = NodeConfig(
            transport=TransportMode.USRP,
            sdr_config=SDRConfig(backend="mock"),
        )
        node = SleNode(cfg)
        assert node.sdr_device is not None
        assert node.sdr_device.is_mock
        node.close_transceiver()

    def test_node_without_sdr_config(self):
        """不提供 sdr_config 时走旧 USRP 路径或 None。"""
        from nearlink_sdr.node import NodeConfig, SleNode, TransportMode

        cfg = NodeConfig(transport=TransportMode.SIMULATION)
        node = SleNode(cfg)
        assert node.sdr_device is None
