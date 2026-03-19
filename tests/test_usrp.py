"""USRP E310 硬件接口层测试。

使用 MockUSRP 验证所有接口逻辑, 不依赖实际硬件。
"""

import numpy as np
import pytest

from nearlink_sdr.phy.usrp import (
    USRPConfig,
    USRPDevice,
    TXStream,
    RXStream,
    SLETransceiver,
    MockUSRP,
    MockStreamer,
    MockStreamCmd,
    MockStreamMode,
    MockRXMetadata,
    MockTXMetadata,
    E310_FREQ_MIN_HZ,
    E310_FREQ_MAX_HZ,
    E310_RX_GAIN_MAX,
    E310_TX_GAIN_MAX,
    E310_BW_MAX_HZ,
    SLE_BANDWIDTHS_MHZ,
    uhd_available,
)
from nearlink_sdr.phy.freq_hopping import (
    channel_to_freq,
    BAND_2400,
    BAND_5100,
    BAND_5800,
)


# =========================================================================
# USRPConfig 测试
# =========================================================================

class TestUSRPConfig:
    """USRPConfig 配置参数验证。"""

    def test_default_config(self):
        cfg = USRPConfig()
        assert cfg.channel_num == 0
        assert cfg.band == BAND_2400
        assert cfg.sample_rate_hz == 1e6
        assert cfg.rx_gain_db == 30.0
        assert cfg.tx_gain_db == 20.0

    def test_center_freq_2400(self):
        cfg = USRPConfig(channel_num=0, band=BAND_2400)
        assert cfg.center_freq_hz == 2402e6

    def test_center_freq_2400_ch22(self):
        cfg = USRPConfig(channel_num=22, band=BAND_2400)
        assert cfg.center_freq_hz == 2424e6

    def test_center_freq_2400_ch78(self):
        cfg = USRPConfig(channel_num=78, band=BAND_2400)
        assert cfg.center_freq_hz == 2480e6

    def test_center_freq_5100(self):
        cfg = USRPConfig(channel_num=79, band=BAND_5100)
        assert cfg.center_freq_hz == 5152e6

    def test_center_freq_5800(self):
        cfg = USRPConfig(channel_num=276, band=BAND_5800)
        assert cfg.center_freq_hz == 5727e6

    def test_bandwidth_mhz(self):
        cfg = USRPConfig(sample_rate_hz=2e6)
        assert cfg.bandwidth_mhz == 2.0

    def test_invalid_rx_gain_high(self):
        with pytest.raises(ValueError, match="RX gain"):
            USRPConfig(rx_gain_db=80.0)

    def test_invalid_rx_gain_low(self):
        with pytest.raises(ValueError, match="RX gain"):
            USRPConfig(rx_gain_db=-1.0)

    def test_invalid_tx_gain(self):
        with pytest.raises(ValueError, match="TX gain"):
            USRPConfig(tx_gain_db=100.0)

    def test_invalid_sample_rate_zero(self):
        with pytest.raises(ValueError, match="采样率"):
            USRPConfig(sample_rate_hz=0)

    def test_invalid_sample_rate_too_high(self):
        with pytest.raises(ValueError, match="采样率"):
            USRPConfig(sample_rate_hz=100e6)

    def test_valid_edge_gains(self):
        cfg = USRPConfig(rx_gain_db=0.0, tx_gain_db=0.0)
        assert cfg.rx_gain_db == 0.0
        assert cfg.tx_gain_db == 0.0

    def test_valid_max_gains(self):
        cfg = USRPConfig(rx_gain_db=E310_RX_GAIN_MAX, tx_gain_db=E310_TX_GAIN_MAX)
        assert cfg.rx_gain_db == E310_RX_GAIN_MAX
        assert cfg.tx_gain_db == E310_TX_GAIN_MAX

    def test_sle_bandwidths(self):
        for bw in SLE_BANDWIDTHS_MHZ:
            cfg = USRPConfig(sample_rate_hz=bw * 1e6)
            assert cfg.bandwidth_mhz == bw


# =========================================================================
# MockUSRP 测试
# =========================================================================

class TestMockUSRP:
    """MockUSRP 行为验证。"""

    def test_create_default(self):
        mock = MockUSRP()
        assert mock.get_mboard_name() == "E310 (Mock)"

    def test_rx_rate(self):
        mock = MockUSRP()
        mock.set_rx_rate(2e6)
        assert mock.get_rx_rate() == 2e6

    def test_tx_rate(self):
        mock = MockUSRP()
        mock.set_tx_rate(4e6)
        assert mock.get_tx_rate() == 4e6

    def test_rx_freq(self):
        mock = MockUSRP()
        mock.set_rx_freq(2424e6)
        assert mock.get_rx_freq() == 2424e6

    def test_tx_freq(self):
        mock = MockUSRP()
        mock.set_tx_freq(2424e6)
        assert mock.get_tx_freq() == 2424e6

    def test_rx_gain(self):
        mock = MockUSRP()
        mock.set_rx_gain(50.0)
        assert mock.get_rx_gain() == 50.0

    def test_tx_gain(self):
        mock = MockUSRP()
        mock.set_tx_gain(40.0)
        assert mock.get_tx_gain() == 40.0

    def test_rx_antenna(self):
        mock = MockUSRP()
        mock.set_rx_antenna("TX/RX")
        assert mock.get_rx_antenna() == "TX/RX"

    def test_tx_antenna(self):
        mock = MockUSRP()
        mock.set_tx_antenna("TX/RX")
        assert mock.get_tx_antenna() == "TX/RX"

    def test_bandwidth(self):
        mock = MockUSRP()
        mock.set_rx_bandwidth(2e6)
        assert mock.get_rx_bandwidth() == 2e6

    def test_call_log(self):
        mock = MockUSRP()
        mock.set_rx_rate(1e6)
        mock.set_rx_freq(2402e6)
        assert len(mock._call_log) == 2
        assert mock._call_log[0][0] == "set_rx_rate"
        assert mock._call_log[1][0] == "set_rx_freq"

    def test_pp_string(self):
        mock = MockUSRP()
        s = mock.get_pp_string()
        assert "MockUSRP" in s
        assert "E310" in s

    def test_get_rx_stream(self):
        mock = MockUSRP()
        streamer = mock.get_rx_stream("fc32")
        assert isinstance(streamer, MockStreamer)

    def test_get_tx_stream(self):
        mock = MockUSRP()
        streamer = mock.get_tx_stream("fc32")
        assert isinstance(streamer, MockStreamer)


# =========================================================================
# MockStreamer 测试
# =========================================================================

class TestMockStreamer:
    """MockStreamer 收发行为验证。"""

    def test_rx_not_started(self):
        s = MockStreamer("rx")
        buf = np.zeros((1, 100), dtype=np.complex64)
        meta = MockRXMetadata()
        n = s.recv(buf, meta)
        assert n == 0

    def test_rx_started(self):
        s = MockStreamer("rx")
        cmd = MockStreamCmd(MockStreamMode.start_cont)
        s.issue_stream_cmd(cmd)
        buf = np.zeros((1, 100), dtype=np.complex64)
        meta = MockRXMetadata()
        n = s.recv(buf, meta)
        assert n > 0
        assert np.any(buf[0, :n] != 0)

    def test_rx_stop(self):
        s = MockStreamer("rx")
        s.issue_stream_cmd(MockStreamCmd(MockStreamMode.start_cont))
        s.issue_stream_cmd(MockStreamCmd(MockStreamMode.stop_cont))
        buf = np.zeros((1, 100), dtype=np.complex64)
        meta = MockRXMetadata()
        n = s.recv(buf, meta)
        assert n == 0

    def test_tx_send(self):
        s = MockStreamer("tx")
        data = np.ones(500, dtype=np.complex64)
        meta = MockTXMetadata()
        n = s.send(data, meta)
        assert n == 500

    def test_tx_send_2d(self):
        s = MockStreamer("tx")
        data = np.ones((1, 300), dtype=np.complex64)
        meta = MockTXMetadata()
        n = s.send(data, meta)
        assert n == 300

    def test_max_num_samps(self):
        s = MockStreamer("rx", samps_per_buffer=2048)
        assert s.get_max_num_samps() == 2048


# =========================================================================
# USRPDevice 测试
# =========================================================================

class TestUSRPDevice:
    """USRPDevice 设备管理。"""

    def test_create_mock(self):
        dev = USRPDevice(use_mock=True)
        assert dev.is_mock
        assert "Mock" in dev.status_string()

    def test_default_config(self):
        dev = USRPDevice(use_mock=True)
        cfg = dev.config
        assert cfg.channel_num == 0
        assert cfg.band == BAND_2400

    def test_configure_applies_rx_params(self):
        cfg = USRPConfig(rx_gain_db=50.0, sample_rate_hz=2e6)
        dev = USRPDevice(config=cfg, use_mock=True)
        mock = dev.usrp
        assert mock.get_rx_gain() == 50.0
        assert mock.get_rx_rate() == 2e6

    def test_configure_applies_tx_params(self):
        cfg = USRPConfig(tx_gain_db=40.0, sample_rate_hz=4e6)
        dev = USRPDevice(config=cfg, use_mock=True)
        mock = dev.usrp
        assert mock.get_tx_gain() == 40.0
        assert mock.get_tx_rate() == 4e6

    def test_configure_freq(self):
        cfg = USRPConfig(channel_num=22, band=BAND_2400)
        dev = USRPDevice(config=cfg, use_mock=True)
        mock = dev.usrp
        assert mock.get_rx_freq() == 2424e6
        assert mock.get_tx_freq() == 2424e6

    def test_configure_antenna(self):
        cfg = USRPConfig(rx_antenna="TX/RX", tx_antenna="TX/RX")
        dev = USRPDevice(config=cfg, use_mock=True)
        mock = dev.usrp
        assert mock.get_rx_antenna() == "TX/RX"
        assert mock.get_tx_antenna() == "TX/RX"

    def test_tune_channel(self):
        dev = USRPDevice(use_mock=True)
        dev.tune_channel(40)
        assert dev.config.channel_num == 40
        expected_freq = channel_to_freq(40, BAND_2400) * 1e6
        assert dev.usrp.get_rx_freq() == expected_freq
        assert dev.usrp.get_tx_freq() == expected_freq

    def test_tune_channel_band_switch(self):
        dev = USRPDevice(use_mock=True)
        dev.tune_channel(79, band=BAND_5100)
        assert dev.config.band == BAND_5100
        assert dev.config.channel_num == 79
        expected_freq = channel_to_freq(79, BAND_5100) * 1e6
        assert dev.usrp.get_rx_freq() == expected_freq

    def test_set_rx_gain(self):
        dev = USRPDevice(use_mock=True)
        dev.set_rx_gain(60.0)
        assert dev.config.rx_gain_db == 60.0
        assert dev.usrp.get_rx_gain() == 60.0

    def test_set_rx_gain_invalid(self):
        dev = USRPDevice(use_mock=True)
        with pytest.raises(ValueError):
            dev.set_rx_gain(100.0)

    def test_set_tx_gain(self):
        dev = USRPDevice(use_mock=True)
        dev.set_tx_gain(50.0)
        assert dev.config.tx_gain_db == 50.0
        assert dev.usrp.get_tx_gain() == 50.0

    def test_set_tx_gain_invalid(self):
        dev = USRPDevice(use_mock=True)
        with pytest.raises(ValueError):
            dev.set_tx_gain(-5.0)

    def test_set_sample_rate(self):
        dev = USRPDevice(use_mock=True)
        dev.set_sample_rate(4e6)
        assert dev.config.sample_rate_hz == 4e6
        assert dev.usrp.get_rx_rate() == 4e6
        assert dev.usrp.get_tx_rate() == 4e6

    def test_set_sample_rate_invalid(self):
        dev = USRPDevice(use_mock=True)
        with pytest.raises(ValueError):
            dev.set_sample_rate(0)

    def test_status_string_format(self):
        dev = USRPDevice(use_mock=True)
        s = dev.status_string()
        assert "Mock" in s
        assert "CH0" in s
        assert "2402.0MHz" in s

    def test_bandwidth_applied(self):
        cfg = USRPConfig(bandwidth_hz=2e6)
        dev = USRPDevice(config=cfg, use_mock=True)
        assert dev.usrp.get_rx_bandwidth() == 2e6


# =========================================================================
# TXStream 测试
# =========================================================================

class TestTXStream:
    """TXStream 发射流测试。"""

    def _make_tx(self):
        dev = USRPDevice(use_mock=True)
        tx = TXStream(dev)
        return tx

    def test_send_before_open(self):
        tx = self._make_tx()
        with pytest.raises(RuntimeError, match="TX streamer 未打开"):
            tx.send(np.zeros(100, dtype=np.complex64))

    def test_open_and_send(self):
        tx = self._make_tx()
        tx.open()
        data = np.ones(500, dtype=np.complex64) * 0.5
        n = tx.send(data)
        assert n == 500

    def test_send_float_coercion(self):
        tx = self._make_tx()
        tx.open()
        # float64 数据应自动转为 complex64
        data = np.ones(100) + 1j * np.ones(100)
        n = tx.send(data)
        assert n == 100

    def test_send_continuous(self):
        tx = self._make_tx()
        tx.open()
        data = np.ones(200, dtype=np.complex64) * 0.3
        total = tx.send_continuous(data, num_repeats=3)
        assert total == 600

    def test_close(self):
        tx = self._make_tx()
        tx.open()
        tx.close()
        with pytest.raises(RuntimeError):
            tx.send(np.zeros(10, dtype=np.complex64))


# =========================================================================
# RXStream 测试
# =========================================================================

class TestRXStream:
    """RXStream 接收流测试。"""

    def _make_rx(self):
        dev = USRPDevice(use_mock=True)
        rx = RXStream(dev)
        return rx

    def test_recv_before_open(self):
        rx = self._make_rx()
        with pytest.raises(RuntimeError, match="RX streamer 未打开"):
            rx.recv_num_samps(100)

    def test_open_and_recv(self):
        rx = self._make_rx()
        rx.open()
        samples = rx.recv_num_samps(500)
        assert len(samples) > 0
        assert samples.dtype == np.complex64

    def test_recv_exact_count(self):
        rx = self._make_rx()
        rx.open(samps_per_buffer=1000)
        samples = rx.recv_num_samps(1000)
        assert len(samples) == 1000

    def test_continuous_mode(self):
        rx = self._make_rx()
        rx.open()
        rx.start_continuous()
        buf = rx.recv_once()
        assert len(buf) > 0
        rx.stop_continuous()

    def test_recv_once_before_start(self):
        rx = self._make_rx()
        rx.open()
        with pytest.raises(RuntimeError, match="连续接收未启动"):
            rx.recv_once()

    def test_close(self):
        rx = self._make_rx()
        rx.open()
        rx.close()
        with pytest.raises(RuntimeError):
            rx.recv_num_samps(100)


# =========================================================================
# SLETransceiver 测试
# =========================================================================

class TestSLETransceiver:
    """SLETransceiver Pipeline 测试。"""

    def _make_xcvr(self, **kwargs):
        cfg = USRPConfig(**kwargs)
        dev = USRPDevice(config=cfg, use_mock=True)
        xcvr = SLETransceiver(dev)
        return xcvr

    def test_not_open(self):
        xcvr = self._make_xcvr()
        with pytest.raises(RuntimeError, match="Pipeline 未打开"):
            xcvr.transmit_iq(np.zeros(100, dtype=np.complex64))

    def test_open_close(self):
        xcvr = self._make_xcvr()
        xcvr.open()
        assert xcvr.is_open
        xcvr.close()
        assert not xcvr.is_open

    def test_transmit_iq(self):
        xcvr = self._make_xcvr()
        xcvr.open()
        n = xcvr.transmit_iq(np.ones(300, dtype=np.complex64) * 0.5)
        assert n == 300
        xcvr.close()

    def test_receive_iq(self):
        xcvr = self._make_xcvr()
        xcvr.open()
        samples = xcvr.receive_iq(500)
        assert len(samples) > 0
        assert samples.dtype == np.complex64
        xcvr.close()

    def test_transmit_frame_with_modulator(self):
        xcvr = self._make_xcvr()
        xcvr.open()
        # 简单调制函数
        def mock_mod(bits):
            return (2.0 * bits - 1.0).astype(np.complex64)
        bits = np.array([0, 1, 1, 0, 1], dtype=np.int8)
        n = xcvr.transmit_frame(bits, mock_mod)
        assert n == len(bits)
        xcvr.close()

    def test_receive_frame_with_demodulator(self):
        xcvr = self._make_xcvr()
        xcvr.open()
        def mock_demod(iq):
            return (np.real(iq) > 0).astype(np.int8)
        bits = xcvr.receive_frame(100, mock_demod)
        assert len(bits) > 0
        xcvr.close()

    def test_hop_and_transmit(self):
        xcvr = self._make_xcvr()
        xcvr.open()
        data = np.ones(200, dtype=np.complex64) * 0.3
        n = xcvr.hop_and_transmit(40, data)
        assert n == 200
        assert xcvr.device.config.channel_num == 40
        expected_freq = channel_to_freq(40, BAND_2400) * 1e6
        assert xcvr.device.usrp.get_rx_freq() == expected_freq
        xcvr.close()

    def test_hop_and_receive(self):
        xcvr = self._make_xcvr()
        xcvr.open()
        samples = xcvr.hop_and_receive(50, 300)
        assert len(samples) > 0
        assert xcvr.device.config.channel_num == 50
        xcvr.close()

    def test_hop_band_switch(self):
        xcvr = self._make_xcvr()
        xcvr.open()
        xcvr.hop_and_transmit(79, np.zeros(100, dtype=np.complex64), band=BAND_5100)
        assert xcvr.device.config.band == BAND_5100
        xcvr.close()

    def test_device_access(self):
        xcvr = self._make_xcvr()
        assert isinstance(xcvr.device, USRPDevice)
        assert xcvr.device.is_mock


# =========================================================================
# 集成测试 — PHY 模块与 USRP 接口联合
# =========================================================================

class TestUSRPPhyIntegration:
    """PHY 调制器与 USRP 发射/接收 Pipeline 集成测试。"""

    def test_gfsk_modulate_transmit(self):
        from nearlink_sdr.phy.gfsk import GFSKModulator
        cfg = USRPConfig(sample_rate_hz=1e6)
        dev = USRPDevice(config=cfg, use_mock=True)
        xcvr = SLETransceiver(dev)
        xcvr.open()

        mod = GFSKModulator(sps=8)
        bits = np.array([1, 0, 1, 1, 0, 0, 1, 0], dtype=np.int8)
        iq = mod.modulate(bits)
        n = xcvr.transmit_iq(iq)
        assert n == len(iq)
        xcvr.close()

    def test_psk_modulate_transmit(self):
        from nearlink_sdr.phy.psk import PSKModulator
        cfg = USRPConfig(sample_rate_hz=1e6)
        dev = USRPDevice(config=cfg, use_mock=True)
        xcvr = SLETransceiver(dev)
        xcvr.open()

        mod = PSKModulator("BPSK", sps=4)
        bits = np.array([1, 0, 1, 1, 0, 0, 1, 0], dtype=np.int8)
        iq = mod.modulate(bits)
        n = xcvr.transmit_iq(iq)
        assert n == len(iq)
        xcvr.close()

    def test_transmit_frame_gfsk_pipeline(self):
        from nearlink_sdr.phy.gfsk import GFSKModulator
        cfg = USRPConfig(sample_rate_hz=1e6)
        dev = USRPDevice(config=cfg, use_mock=True)
        xcvr = SLETransceiver(dev)
        xcvr.open()

        mod = GFSKModulator(sps=8)
        bits = np.random.default_rng(42).integers(0, 2, 100).astype(np.int8)
        n = xcvr.transmit_frame(bits, mod.modulate)
        assert n == len(bits) * 8  # sps=8
        xcvr.close()

    def test_hopping_sequence_transmit(self):
        from nearlink_sdr.phy.gfsk import GFSKModulator
        from nearlink_sdr.phy.freq_hopping import (
            FreqTable,
            generate_hopping_sequence,
        )

        cfg = USRPConfig(sample_rate_hz=1e6)
        dev = USRPDevice(config=cfg, use_mock=True)
        xcvr = SLETransceiver(dev)
        xcvr.open()

        mod = GFSKModulator(sps=8)
        bits = np.array([1, 0, 1, 1, 0, 0], dtype=np.int8)
        iq = mod.modulate(bits)

        freq_table = FreqTable(BAND_2400)
        hop_seq = generate_hopping_sequence(
            n_hops=5, hop_param2=0x1234,
            freq_table=freq_table, link_type="data",
        )

        for ch in hop_seq:
            n = xcvr.hop_and_transmit(ch, iq)
            assert n == len(iq)

        xcvr.close()

    def test_multi_bandwidth_config(self):
        for bw_mhz in SLE_BANDWIDTHS_MHZ:
            cfg = USRPConfig(sample_rate_hz=bw_mhz * 1e6)
            dev = USRPDevice(config=cfg, use_mock=True)
            assert dev.usrp.get_rx_rate() == bw_mhz * 1e6
            assert dev.usrp.get_tx_rate() == bw_mhz * 1e6


# =========================================================================
# uhd_available() 测试
# =========================================================================

class TestUhdAvailable:
    """uhd_available() 函数测试。"""

    def test_returns_bool(self):
        result = uhd_available()
        assert isinstance(result, bool)
