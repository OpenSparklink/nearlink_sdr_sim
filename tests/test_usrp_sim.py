"""USRP 环回仿真测试。

验证 MockUSRP loopback 模式下的端到端功能, 覆盖:
- IQ 级环回
- PHY 全链路环回 (各帧类型)
- MAC 数据帧环回
- 跳频序列环回
- 批量帧仿真
- SleNode 双节点端到端
"""

import numpy as np

from nearlink_sdr.phy.channel import ChannelModel
from nearlink_sdr.phy.gfsk import GFSKModulator
from nearlink_sdr.phy.psk import PSKModulator
from nearlink_sdr.phy.tx_pipeline import TxConfig
from nearlink_sdr.phy.usrp import (
    LoopbackBuffer,
    MockRXMetadata,
    MockStreamCmd,
    MockStreamer,
    MockStreamMode,
    MockTXMetadata,
    MockUSRP,
    SLETransceiver,
    USRPDevice,
)
from nearlink_sdr.sim.usrp_sim import (
    USRPLoopbackSim,
    USRPSimResult,
)

# =========================================================================
# LoopbackBuffer 单元测试
# =========================================================================

class TestLoopbackBuffer:
    """LoopbackBuffer 基本读写验证。"""

    def test_push_pull_exact(self):
        buf = LoopbackBuffer()
        data = np.array([1 + 2j, 3 + 4j], dtype=np.complex64)
        buf.push(data)
        out = buf.pull(2)
        np.testing.assert_array_almost_equal(out, data)

    def test_push_pull_partial(self):
        buf = LoopbackBuffer()
        data = np.arange(10, dtype=np.complex64)
        buf.push(data)
        out1 = buf.pull(3)
        assert len(out1) == 3
        out2 = buf.pull(7)
        assert len(out2) == 7
        np.testing.assert_array_almost_equal(
            np.concatenate([out1, out2]), data,
        )

    def test_empty_pull(self):
        buf = LoopbackBuffer()
        out = buf.pull(100)
        assert len(out) == 0

    def test_available(self):
        buf = LoopbackBuffer()
        assert buf.available == 0
        buf.push(np.zeros(50, dtype=np.complex64))
        assert buf.available == 50
        buf.pull(20)
        assert buf.available == 30

    def test_clear(self):
        buf = LoopbackBuffer()
        buf.push(np.zeros(100, dtype=np.complex64))
        buf.clear()
        assert buf.available == 0

    def test_with_channel_model(self):
        ch = ChannelModel(snr_db=50.0)
        buf = LoopbackBuffer(channel_model=ch)
        data = np.ones(100, dtype=np.complex64)
        buf.push(data)
        out = buf.pull(100)
        assert len(out) == 100
        # 高 SNR 下信号应接近原值
        assert np.mean(np.abs(out - data)) < 0.5

    def test_multiple_pushes(self):
        buf = LoopbackBuffer()
        buf.push(np.array([1, 2, 3], dtype=np.complex64))
        buf.push(np.array([4, 5], dtype=np.complex64))
        assert buf.available == 5
        out = buf.pull(5)
        np.testing.assert_array_almost_equal(
            out[:3], [1, 2, 3],
        )


# =========================================================================
# MockStreamer loopback 模式测试
# =========================================================================

class TestMockStreamerLoopback:
    """MockStreamer 环回模式验证。"""

    def test_loopback_tx_to_rx(self):
        lb = LoopbackBuffer()
        tx = MockStreamer("tx", loopback=lb)
        rx = MockStreamer("rx", loopback=lb)

        data = np.arange(200, dtype=np.complex64)
        meta_tx = MockTXMetadata()
        n_sent = tx.send(data, meta_tx)
        assert n_sent == 200

        cmd = MockStreamCmd(MockStreamMode.start_cont)
        rx.issue_stream_cmd(cmd)

        buf = np.zeros((1, 200), dtype=np.complex64)
        meta_rx = MockRXMetadata()
        n_recv = rx.recv(buf, meta_rx)
        assert n_recv == 200
        np.testing.assert_array_almost_equal(buf[0, :200], data)

    def test_loopback_with_noise(self):
        ch = ChannelModel(snr_db=40.0)
        lb = LoopbackBuffer(channel_model=ch)
        tx = MockStreamer("tx", loopback=lb)
        rx = MockStreamer("rx", loopback=lb)

        data = np.ones(100, dtype=np.complex64)
        tx.send(data, MockTXMetadata())

        rx.issue_stream_cmd(MockStreamCmd(MockStreamMode.start_cont))
        buf = np.zeros((1, 100), dtype=np.complex64)
        n = rx.recv(buf, MockRXMetadata())
        assert n == 100
        # 在 40dB SNR 下应该非常接近
        assert np.mean(np.abs(buf[0, :n] - data)) < 0.2

    def test_no_loopback_returns_noise(self):
        rx = MockStreamer("rx")
        rx.issue_stream_cmd(MockStreamCmd(MockStreamMode.start_cont))
        buf = np.zeros((1, 100), dtype=np.complex64)
        n = rx.recv(buf, MockRXMetadata())
        assert n > 0
        # 幅度很小 (0.01 倍噪声)
        assert np.max(np.abs(buf[0, :n])) < 1.0


# =========================================================================
# MockUSRP loopback 模式测试
# =========================================================================

class TestMockUSRPLoopback:
    """MockUSRP 环回模式验证。"""

    def test_create_with_loopback(self):
        lb = LoopbackBuffer()
        mock = MockUSRP(loopback=lb)
        tx_stream = mock.get_tx_stream("fc32")
        rx_stream = mock.get_rx_stream("fc32")
        assert tx_stream._loopback is lb
        assert rx_stream._loopback is lb

    def test_device_with_loopback(self):
        lb = LoopbackBuffer()
        dev = USRPDevice(use_mock=True, loopback=lb)
        assert dev.is_mock


# =========================================================================
# SLETransceiver loopback 测试
# =========================================================================

class TestSLETransceiverLoopback:
    """通过 SLETransceiver 进行 IQ 环回。"""

    def test_iq_roundtrip(self):
        lb = LoopbackBuffer()
        dev = USRPDevice(use_mock=True, loopback=lb)
        xcvr = SLETransceiver(dev)
        xcvr.open()

        data = np.exp(1j * np.linspace(0, 2 * np.pi, 500)).astype(np.complex64)
        n_sent = xcvr.transmit_iq(data)
        assert n_sent == 500

        rx_data = xcvr.receive_iq(500)
        assert len(rx_data) == 500
        np.testing.assert_array_almost_equal(rx_data, data)
        xcvr.close()

    def test_iq_roundtrip_with_channel(self):
        ch = ChannelModel(snr_db=30.0)
        lb = LoopbackBuffer(channel_model=ch)
        dev = USRPDevice(use_mock=True, loopback=lb)
        xcvr = SLETransceiver(dev)
        xcvr.open()

        t = np.linspace(0, 4 * np.pi, 300)
        data = (np.sin(t) + 1j * np.cos(t)).astype(np.complex64)
        xcvr.transmit_iq(data)
        rx = xcvr.receive_iq(300)
        assert len(rx) == 300
        assert np.corrcoef(np.real(data), np.real(rx))[0, 1] > 0.9
        xcvr.close()

    def test_gfsk_modulate_loopback(self):
        lb = LoopbackBuffer()
        dev = USRPDevice(use_mock=True, loopback=lb)
        xcvr = SLETransceiver(dev)
        xcvr.open()

        mod = GFSKModulator(sps=8)
        bits = np.array([1, 0, 1, 1, 0, 0, 1, 0], dtype=np.int8)
        iq = mod.modulate(bits)
        n = xcvr.transmit_iq(iq)
        rx_iq = xcvr.receive_iq(n)
        np.testing.assert_array_almost_equal(rx_iq, iq.astype(np.complex64))
        xcvr.close()

    def test_psk_modulate_loopback(self):
        lb = LoopbackBuffer()
        dev = USRPDevice(use_mock=True, loopback=lb)
        xcvr = SLETransceiver(dev)
        xcvr.open()

        mod = PSKModulator("QPSK", sps=4)
        bits = np.array([1, 0, 1, 1, 0, 0, 1, 0], dtype=np.int8)
        iq = mod.modulate(bits)
        n = xcvr.transmit_iq(iq)
        rx_iq = xcvr.receive_iq(n)
        np.testing.assert_array_almost_equal(rx_iq, iq.astype(np.complex64))
        xcvr.close()


# =========================================================================
# USRPLoopbackSim 仿真引擎测试
# =========================================================================

class TestUSRPLoopbackSim:
    """USRPLoopbackSim 端到端仿真验证。"""

    def test_create_sim(self):
        sim = USRPLoopbackSim(snr_db=30.0)
        assert sim.device.is_mock
        assert sim.transceiver.is_open
        sim.close()

    def test_iq_loopback(self):
        sim = USRPLoopbackSim(snr_db=50.0)
        data = np.ones(200, dtype=np.complex64) * 0.5
        rx = sim.loopback_iq(data)
        assert len(rx) == 200
        assert np.mean(np.abs(rx - data)) < 0.1
        sim.close()

    def test_phy_loopback_ft2_high_snr(self):
        """FT2 帧类型高 SNR 环回, CRC 应通过。"""
        sim = USRPLoopbackSim(snr_db=50.0)
        rng = np.random.default_rng(42)
        data = rng.integers(0, 2, 80).astype(np.int8)
        cfg = TxConfig(frame_type=2, mcs_index=7, sps=4)
        result = sim.loopback_phy(data, cfg)
        assert result.crc_ok
        assert result.head_crc_ok
        assert result.ber == 0.0
        assert result.tx_samples > 0
        assert result.rx_samples > 0
        sim.close()

    def test_phy_loopback_ft1(self):
        """FT1 GFSK 帧类型无噪声环回。

        GFSK 频率鉴别器对微小噪声敏感, 此测试仅验证
        USRP 环回路径的数据完整性, 不加信道损伤。
        使用与 test_ft_pipeline 相同的 TV101 参数。
        """
        from nearlink_sdr.common.crc import CRC12_POLY, crc_attach
        from nearlink_sdr.common.prbs import prbs11
        from nearlink_sdr.phy.rx_pipeline import rx_chain
        from nearlink_sdr.phy.tx_pipeline import tx_chain

        lb = LoopbackBuffer()
        dev = USRPDevice(use_mock=True, loopback=lb)
        xcvr = SLETransceiver(dev)
        xcvr.open()

        cfg = TxConfig(
            frame_type=1, mcs_index=8, pid=0x873456,
            whitening_seed=0x4E, crc_seed=0x555555, crc_len=24,
            ctrl_bits_len=20, sps=8,
        )
        # 构造 TV101 标准头部和载荷
        seq = prbs11(20 + 256, seed=101)
        ctrl_raw = np.array(seq[:20], dtype=int)
        sync_seed = 0x27C8F4C6 & 0xFFF
        ctrl = crc_attach(ctrl_raw, CRC12_POLY, 12, seed=sync_seed)
        data = np.array(seq[20:], dtype=int)

        iq = tx_chain(ctrl, data, cfg)

        lb.clear()
        n = xcvr.transmit_iq(iq)
        rx_iq = xcvr.receive_iq(n)

        result = rx_chain(rx_iq, cfg, 32)
        assert result.crc_ok
        assert result.head_crc_ok
        xcvr.close()

    def test_phy_loopback_ft3(self):
        """FT3 帧类型环回。"""
        sim = USRPLoopbackSim(snr_db=50.0)
        rng = np.random.default_rng(1)
        data = rng.integers(0, 2, 80).astype(np.int8)
        cfg = TxConfig(frame_type=3, mcs_index=7, sps=4)
        result = sim.loopback_phy(data, cfg)
        assert result.crc_ok
        assert result.head_crc_ok
        sim.close()

    def test_phy_loopback_ft4(self):
        """FT4 帧类型环回。"""
        sim = USRPLoopbackSim(snr_db=50.0)
        rng = np.random.default_rng(2)
        data = rng.integers(0, 2, 80).astype(np.int8)
        cfg = TxConfig(frame_type=4, mcs_index=7, sps=4)
        result = sim.loopback_phy(data, cfg)
        assert result.crc_ok
        assert result.head_crc_ok
        sim.close()

    def test_mac_data_loopback(self):
        """MAC 异步数据帧环回。"""
        sim = USRPLoopbackSim(snr_db=50.0)
        payload = b"Hello SLE"
        cfg = TxConfig(frame_type=2, mcs_index=7)
        mac_rx, lr = sim.loopback_mac_data(payload, cfg)
        assert lr.crc_ok
        assert mac_rx.mac_payload == payload
        sim.close()

    def test_mac_data_loopback_default_cfg(self):
        """MAC 数据帧环回, 使用默认配置。"""
        sim = USRPLoopbackSim(snr_db=50.0)
        payload = b"\x01\x02\x03\x04\x05"
        mac_rx, lr = sim.loopback_mac_data(payload)
        assert lr.crc_ok
        assert mac_rx.mac_payload == payload
        sim.close()

    def test_hopping_loopback(self):
        """跳频序列环回。"""
        sim = USRPLoopbackSim(snr_db=50.0)
        iq = np.ones(100, dtype=np.complex64)
        hop_seq = [0, 10, 20, 30]
        results = sim.loopback_hopping(iq, hop_seq)
        assert len(results) == 4
        for ch, rx in results:
            assert ch in hop_seq
            assert len(rx) == 100
        sim.close()

    def test_batch_simulation(self):
        """批量帧仿真。"""
        sim = USRPLoopbackSim(snr_db=50.0)
        payloads = [bytes([i] * 5) for i in range(4)]
        cfg = TxConfig(frame_type=2, mcs_index=7)
        result = sim.run_batch(payloads, cfg)
        assert result.total_frames == 4
        assert result.success_frames == 4
        assert result.failed_frames == 0
        assert result.fer == 0.0
        assert result.avg_ber == 0.0
        sim.close()

    def test_low_snr_increases_ber(self):
        """低 SNR 环境下 BER 应增加。"""
        sim_high = USRPLoopbackSim(snr_db=50.0)
        sim_low = USRPLoopbackSim(snr_db=5.0)
        rng = np.random.default_rng(99)
        data = rng.integers(0, 2, 80).astype(np.int8)
        cfg = TxConfig(frame_type=2, mcs_index=7)

        r_high = sim_high.loopback_phy(data, cfg)
        r_low = sim_low.loopback_phy(data, cfg)
        # 高 SNR 应该 BER 更低
        assert r_high.ber <= r_low.ber
        sim_high.close()
        sim_low.close()


# =========================================================================
# SleNode 端到端仿真
# =========================================================================

class TestNodeUSRPSim:
    """SleNode 通过 USRP 环回完成端到端通信。"""

    def _make_node_pair(self):
        """创建建链后的节点对。"""
        from nearlink_sdr.node import NodeCallback, NodeConfig, SleNode

        node_a = SleNode(
            config=NodeConfig(address=b"\x11\x22\x33\x44\x55\x66"),
            callback=NodeCallback(),
        )
        node_b = SleNode(
            config=NodeConfig(address=b"\xAA\xBB\xCC\xDD\xEE\xFF"),
            callback=NodeCallback(),
        )
        # 建链
        node_a.start_advertising()
        node_b.start_scanning()
        node_a.connect(b"\xAA\xBB\xCC\xDD\xEE\xFF")
        node_b.accept_connection(b"\x11\x22\x33\x44\x55\x66")
        return node_a, node_b

    def test_node_transmit_loopback_receive(self):
        """Node A 发射 → USRP 环回 → Node B 接收。"""
        sim = USRPLoopbackSim(snr_db=50.0)
        node_a, node_b = self._make_node_pair()

        test_data = b"SLE USRP Test"
        node_a.send(test_data, priority=0)
        tx_result = node_a.transmit()
        assert tx_result.iq is not None
        assert tx_result.mac_bytes is not None

        # 通过 USRP 环回
        sim._loopback.clear()
        n_sent = sim.transceiver.transmit_iq(tx_result.iq)
        rx_iq = sim.transceiver.receive_iq(n_sent)

        # Node B 接收
        rx_result = node_b.receive(rx_iq, len(tx_result.mac_bytes))
        assert rx_result.success
        assert rx_result.data == test_data
        sim.close()

    def test_node_multi_frame_loopback(self):
        """多帧连续传输环回。"""
        sim = USRPLoopbackSim(snr_db=50.0)
        node_a, node_b = self._make_node_pair()

        messages = [f"msg-{i}".encode() for i in range(3)]
        for msg in messages:
            node_a.send(msg, priority=0)
            tx = node_a.transmit()
            assert tx.iq is not None

            sim._loopback.clear()
            n = sim.transceiver.transmit_iq(tx.iq)
            rx_iq = sim.transceiver.receive_iq(n)

            rx = node_b.receive(rx_iq, len(tx.mac_bytes))
            assert rx.success
            assert rx.data == msg
            # 反馈 ACK, 使 QoS 状态机推进到下一帧
            node_a.process_feedback(crc_ok=True)
        sim.close()

    def test_signaling_via_mac_interface(self):
        """信令通过 mac_interface + USRP 环回。"""
        from nearlink_sdr.mac.power_control import PowerControlRequest
        from nearlink_sdr.phy.mac_interface import iq_to_signaling, signaling_to_iq

        sim = USRPLoopbackSim(snr_db=50.0)
        cfg = TxConfig(frame_type=2, mcs_index=7)

        msg = PowerControlRequest(
            frame_type=2, bandwidth=0, freq_density=0,
            tx_power_change=-10, sender_tx_power=5,
        )
        iq = signaling_to_iq(msg, cfg)

        # 通过 USRP 环回发射和接收
        sim._loopback.clear()
        n_sent = sim.transceiver.transmit_iq(iq)
        rx_iq = sim.transceiver.receive_iq(n_sent)

        # 计算 mac_bytes 长度 (与 signaling_to_iq 内部一致)
        from nearlink_sdr.mac.signaling import encode_signaling
        frame = encode_signaling(msg)
        n_mac_bytes = len(frame.pack())

        recovered, ok = iq_to_signaling(rx_iq, cfg, n_mac_bytes)
        assert ok
        assert isinstance(recovered, PowerControlRequest)
        assert recovered.tx_power_change == -10
        sim.close()


# =========================================================================
# USRPSimResult 属性测试
# =========================================================================

class TestUSRPSimResult:
    """USRPSimResult 统计属性验证。"""

    def test_fer_zero(self):
        r = USRPSimResult(total_frames=10, success_frames=10, failed_frames=0)
        assert r.fer == 0.0

    def test_fer_half(self):
        r = USRPSimResult(total_frames=10, success_frames=5, failed_frames=5)
        assert r.fer == 0.5

    def test_fer_empty(self):
        r = USRPSimResult()
        assert r.fer == 0.0
