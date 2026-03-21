"""链路仿真示例。

对应文档: how-to/run-simulation.md
"""

import numpy as np


def ber_gfsk():
    """GFSK 无编码 BER 仿真。"""
    # [ber-gfsk-start]
    from nearlink_sdr.sim.link_sim import sim_gfsk_link

    result = sim_gfsk_link(
        num_data_bits=5000,
        snr_range_db=np.arange(0, 16, 2),
    )
    for snr, ber in zip(result["snr_db"], result["ber"], strict=False):
        print(f"SNR={snr:2d} dB  BER={ber:.5f}")
    # [ber-gfsk-end]
    return result


def ber_psk():
    """QPSK 无编码 BER 仿真。"""
    # [ber-psk-start]
    from nearlink_sdr.sim.link_sim import sim_psk_link

    result = sim_psk_link(
        num_data_bits=5000,
        mod_type="QPSK",
        snr_range_db=np.arange(0, 16, 2),
    )
    # [ber-psk-end]
    return result


def polar_coded_ber():
    """Polar 编码 BER 仿真。"""
    # [polar-coded-start]
    from nearlink_sdr.sim.link_sim import sim_polar_coded_psk_link

    result = sim_polar_coded_psk_link(
        num_info_bits=5000,
        mod_type="BPSK",
        rate_str="1/2",
        code_length=256,
        snr_range_db=np.arange(-2, 10, 1),
    )
    # [polar-coded-end]
    return result


def channel_model():
    """多径信道模型。"""
    # [channel-model-start]
    from nearlink_sdr.phy.channel import ChannelConfig, ChannelModel

    ch = ChannelModel(snr_db=15.0, config=ChannelConfig(channel_type="rayleigh"))
    signal = np.ones(100) + 0j
    rx = ch.apply_fading(signal)
    # [channel-model-end]
    return rx


def hopping_sequence():
    """跳频序列生成。"""
    # [hopping-seq-start]
    from nearlink_sdr.phy.freq_hopping import generate_hopping_sequence

    seq = generate_hopping_sequence(
        n_hops=100,
        hop_param2=0x123456,
    )
    # [hopping-seq-end]
    return seq


def pipeline_ft2():
    """全链路 Pipeline 仿真 (FT2)。"""
    # [pipeline-ft2-start]
    from nearlink_sdr.sim.link_sim import sim_pipeline_link

    # FT2 QPSK MCS7 (码率 7/8)
    result = sim_pipeline_link(
        frame_type=2,
        mcs_index=7,
        n_data_bytes=10,
        snr_range_db=np.arange(0, 16, 2),
        n_frames=50,
    )
    for snr, ber, fer in zip(result["snr_db"], result["ber"], result["fer"], strict=False):
        print(f"Eb/N0={snr:5.1f} dB  BER={ber:.5f}  FER={fer:.3f}")
    # [pipeline-ft2-end]
    return result


def pipeline_other_ft():
    """不同帧类型的 Pipeline 仿真。"""
    # [pipeline-other-start]
    from nearlink_sdr.sim.link_sim import sim_pipeline_link

    # FT1 GFSK (无编码)
    result_ft1 = sim_pipeline_link(frame_type=1, mcs_index=8)

    # FT4 BPSK MCS0 (码率 1/4, 高编码增益)
    result_ft4 = sim_pipeline_link(frame_type=4, mcs_index=0)
    # [pipeline-other-end]
    return result_ft1, result_ft4


def node_hopping_link():
    """SleNode 跳频数据链路仿真。"""
    # [node-hopping-start]
    from nearlink_sdr.sim.link_sim import sim_node_hopping_link

    result = sim_node_hopping_link(n_frames=50, snr_db=12.0)
    print(f"FER = {result['fer']:.4f}")
    # [node-hopping-end]
    return result


def node_access_flow():
    """节点接入流程仿真。"""
    # [node-access-start]
    from nearlink_sdr.sim.link_sim import sim_node_access_flow

    result = sim_node_access_flow()
    # [node-access-end]
    return result


def node_channel_sweep():
    """信道扫频仿真。"""
    # [node-sweep-start]
    from nearlink_sdr.sim.link_sim import sim_node_channel_sweep

    result = sim_node_channel_sweep(snr_range_db=np.array([0, 5, 10, 15], dtype=float))
    # [node-sweep-end]
    return result


def node_power_adapt():
    """功率自适应仿真。"""
    # [node-power-start]
    from nearlink_sdr.sim.link_sim import sim_node_power_adapt

    result = sim_node_power_adapt(n_frames=100)
    # [node-power-end]
    return result


def channel_impairment():
    """信道损伤仿真: 衰落、均衡、频偏。"""
    # [channel-impairment-start]
    from nearlink_sdr.sim.link_sim import sim_pipeline_channel_link

    # Rayleigh 平坦衰落, 无均衡
    result_no_eq = sim_pipeline_channel_link(
        frame_type=2,
        mcs_index=7,
        channel_type="rayleigh",
        eq_method="none",
        snr_range_db=np.arange(0, 20, 2),
        n_frames=50,
    )

    # Rayleigh + MMSE 均衡 (genie-aided)
    result_mmse = sim_pipeline_channel_link(
        frame_type=2,
        mcs_index=7,
        channel_type="rayleigh",
        eq_method="mmse",
        snr_range_db=np.arange(0, 20, 2),
        n_frames=50,
    )

    # AWGN + 500Hz 载波频偏
    result_cfo = sim_pipeline_channel_link(
        frame_type=2,
        mcs_index=7,
        channel_type="awgn",
        cfo_hz=500.0,
        snr_range_db=np.arange(0, 16, 2),
    )
    # [channel-impairment-end]
    return result_no_eq, result_mmse, result_cfo


def mac_signaling():
    """MAC 帧级仿真: 信令、数据、复用。"""
    # [mac-sim-start]
    from nearlink_sdr.sim.link_sim import (
        sim_mac_data_link,
        sim_mac_mux_link,
        sim_mac_signaling_link,
    )

    # 信令帧传输
    result_sig = sim_mac_signaling_link(
        snr_range_db=np.arange(0, 20, 2),
        n_frames=50,
    )

    # 数据帧传输
    result_data = sim_mac_data_link(
        snr_range_db=np.arange(0, 16, 2),
        n_frames=50,
        mcs_index=7,
    )

    # 复用帧传输
    result_mux = sim_mac_mux_link(
        snr_range_db=np.arange(0, 16, 2),
        n_frames=50,
    )
    # [mac-sim-end]
    return result_sig, result_data, result_mux


def multi_link():
    """多链路调度仿真。"""
    # [multi-link-start]
    from nearlink_sdr.sim.link_sim import (
        sim_access_scheduled_link,
        sim_multi_link,
    )

    # 多链路并发仿真
    result_multi = sim_multi_link(
        snr_range_db=np.arange(0, 16, 2),
        n_links=3,
    )

    # 接入建链 + 调度仿真
    result_access = sim_access_scheduled_link(
        snr_range_db=np.arange(0, 16, 2),
    )
    # [multi-link-end]
    return result_multi, result_access


def security_sim():
    """安全通信仿真。"""
    # [security-sim-start]
    from nearlink_sdr.sim.link_sim import (
        sim_encrypted_vs_plain,
        sim_secure_link,
    )

    # 安全链路端到端仿真
    result_secure = sim_secure_link(
        snr_range_db=np.arange(0, 16, 2),
        n_frames=50,
        mcs_index=7,
    )
    print(f"接入成功: {result_secure['access_ok']}, 配对成功: {result_secure['pairing_ok']}")

    # 加密与明文 FER 对比
    result_cmp = sim_encrypted_vs_plain(
        snr_range_db=np.arange(0, 16, 2),
        n_frames=50,
    )
    # [security-sim-end]
    return result_secure, result_cmp


def amc_throughput():
    """AMC 自适应调制编码吞吐量仿真。"""
    # [amc-start]
    from nearlink_sdr.sim.link_sim import sim_amc_throughput

    result = sim_amc_throughput(
        snr_range_db=np.arange(-2, 22, 1),
        n_frames=50,
    )

    # AMC 包络吞吐量 (每个 SNR 点选择最优 MCS)
    for snr, tp, mcs in zip(
        result["snr_db"], result["amc_throughput"], result["amc_mcs"],
        strict=False,
    ):
        print(f"SNR={snr:5.1f} dB  MCS={mcs:2d}  Throughput={tp:.3f} bit/symbol")
    # [amc-end]
    return result


def amc_subset():
    """仅仿真特定 MCS 子集。"""
    # [amc-subset-start]
    from nearlink_sdr.sim.link_sim import sim_amc_throughput

    result = sim_amc_throughput(mcs_indices=[0, 4, 8, 12])
    # [amc-subset-end]
    return result


def harq_retransmit():
    """HARQ 重传仿真。"""
    # [harq-start]
    from nearlink_sdr.sim.link_sim import sim_harq_link

    result = sim_harq_link(
        snr_range_db=np.arange(0, 16, 1),
        n_frames=100,
        mcs_index=7,
        max_retries=3,
    )

    for snr, fer_no, fer_harq, avg_tx in zip(
        result["snr_db"],
        result["fer_no_harq"],
        result["fer_harq"],
        result["avg_transmissions"],
        strict=False,
    ):
        print(
            f"SNR={snr:5.1f} dB  "
            f"FER(no HARQ)={fer_no:.3f}  "
            f"FER(HARQ)={fer_harq:.3f}  "
            f"Avg TX={avg_tx:.2f}"
        )
    # [harq-end]
    return result


def hopping_multipath():
    """跳频多径仿真。"""
    # [hopping-multipath-start]
    from nearlink_sdr.sim.link_sim import sim_hopping_multipath_link

    result = sim_hopping_multipath_link(
        snr_range_db=np.arange(0, 20, 2),
        n_frames=100,
        n_hop_channels=8,
    )
    # [hopping-multipath-end]
    return result


def dual_node_link():
    """双节点端到端仿真。"""
    # [dual-node-start]
    from nearlink_sdr.sim.link_sim import (
        sim_dual_node_link,
        sim_dual_node_mcs_adapt,
        sim_dual_node_secure_link,
    )

    # 基础 FER/BER 仿真
    result = sim_dual_node_link(
        snr_range_db=np.arange(0, 16, 2),
        n_frames=50,
        mcs_index=7,
        payload_size=10,
    )
    for snr, fer in zip(result["snr_db"], result["fer"], strict=False):
        print(f"SNR={snr:2.0f} dB  FER={fer:.3f}")

    # 安全通信仿真 (配对 + 加密)
    result_sec = sim_dual_node_secure_link(
        snr_range_db=np.arange(0, 16, 2),
        n_frames=50,
    )
    print(f"配对状态: {'成功' if result_sec['pairing_ok'] else '失败'}")

    # MCS 自适应跟踪
    result_mcs = sim_dual_node_mcs_adapt(
        snr_db=8.0,
        n_frames=100,
        initial_mcs=7,
    )
    print(f"最终 MCS: {result_mcs['mcs_history'][-1]}")
    # [dual-node-end]
    return result, result_sec, result_mcs


if __name__ == "__main__":
    print("=== GFSK BER ===")
    ber_gfsk()
    print()

    print("=== Pipeline FT2 ===")
    pipeline_ft2()
