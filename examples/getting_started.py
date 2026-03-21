"""快速入门示例。

对应文档: tutorials/getting-started.md
"""

import numpy as np


def gfsk_link():
    """GFSK 调制-信道-解调完整流程。"""
    # [gfsk-link-start]
    from nearlink_sdr.phy.channel import ChannelModel
    from nearlink_sdr.phy.gfsk import GFSKDemodulator, GFSKModulator

    # 生成随机数据比特
    rng = np.random.default_rng(42)
    data_bits = rng.integers(0, 2, 200)

    # 调制
    mod = GFSKModulator(sps=8, mod_index=0.5)
    tx_signal = mod.modulate(data_bits)

    # 通过 AWGN 信道
    ch = ChannelModel(snr_db=12.0)
    rx_signal = ch.apply_awgn(tx_signal)

    # 解调
    demod = GFSKDemodulator(sps=8)
    rx_bits = demod.demodulate(rx_signal)

    # 计算误码率
    ber = np.mean(data_bits != rx_bits[:len(data_bits)])
    print(f"BER = {ber:.4f}")
    # [gfsk-link-end]
    return ber


def polar_psk_link():
    """Polar 编码 + BPSK 调制链路。"""
    # [polar-psk-start]
    from nearlink_sdr.common.polar import PolarDecoder, PolarEncoder, get_info_bit_count

    # Polar 编码参数: 码长 256, 码率 1/2
    code_length = 256
    K = get_info_bit_count("1/2", code_length)
    enc = PolarEncoder(code_length, K)
    dec = PolarDecoder(code_length, K)

    # 信息比特
    rng = np.random.default_rng(42)
    info_bits = rng.integers(0, 2, K, dtype=np.int8)

    # 编码
    coded_bits = enc.encode(info_bits)

    # BPSK 调制 (0 -> +1, 1 -> -1)
    bpsk_signal = 1.0 - 2.0 * coded_bits.astype(np.float64)

    # AWGN 信道
    snr_db = 2.0
    snr_lin = 10.0 ** (snr_db / 10.0)
    R = K / code_length
    noise_var = 1.0 / (2.0 * R * snr_lin)
    noise = rng.normal(0, np.sqrt(noise_var), code_length)
    received = bpsk_signal + noise

    # SC 解码
    llr = 2.0 * received / noise_var
    decoded = dec.decode(llr)

    errors = int(np.sum(info_bits != decoded))
    print(f"比特错误数: {errors}/{K}")
    # [polar-psk-end]
    return errors, K


def pipeline_sim():
    """全链路 Pipeline 仿真。"""
    # [pipeline-sim-start]
    from nearlink_sdr.sim.link_sim import sim_pipeline_link

    result = sim_pipeline_link(
        frame_type=2,
        mcs_index=7,
        n_data_bytes=10,
        snr_range_db=np.arange(0, 12, 2),
        n_frames=20,
    )
    for snr, ber in zip(result["snr_db"], result["ber"], strict=False):
        print(f"SNR={snr:2.0f} dB  BER={ber:.5f}")
    # [pipeline-sim-end]
    return result


def node_basic():
    """SleNode 节点基本操作。"""
    # [node-basic-start]
    from nearlink_sdr.node import NodeConfig, NodeRole, SleNode

    # 创建节点
    config = NodeConfig(
        address=b"\x01\x02\x03\x04\x05\x06",
        role=NodeRole.G_NODE,
        frame_type=2,
        mcs_index=7,
        band="2400",
        hop_param2=0x1234,
    )
    node = SleNode(config=config)

    # 推进时隙并获取当前跳频信道
    node.advance_slot(1)
    channel = node.current_channel
    print(f"当前信道: {channel}")

    # 功率调整
    node.adjust_power(3.0)  # 增加 3 dB

    # 查看节点状态
    stats = node.stats
    print(stats)
    # [node-basic-end]
    return channel, stats


if __name__ == "__main__":
    print("=== GFSK 链路 ===")
    gfsk_link()
    print()

    print("=== Polar + BPSK 链路 ===")
    polar_psk_link()
    print()

    print("=== Pipeline 仿真 ===")
    pipeline_sim()
    print()

    print("=== SleNode 基础 ===")
    node_basic()
