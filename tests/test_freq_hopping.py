"""跳频序列与频率管理模块测试 — 对标 TXS-10002-2025 6.10.3 / 8.1.2。"""

import pytest
import numpy as np

from nearlink_sdr.phy.freq_hopping import (
    BAND_2400, BAND_5100, BAND_5800,
    _BAND_PARAMS, _2M_PHYS_2400, _4M_PHYS_2400,
    channel_to_freq, freq_to_channel,
    FreqTable,
    _bit_reverse_byte, _reverse_16,
    hopping_prng, derive_hop_param2,
    data_link_hop, _available_freq_map,
    mgmt_frame_hop,
    MEAS_HOP_ASCENDING, MEAS_HOP_DESCENDING, MEAS_HOP_RANDOM,
    MeasLinkHopper,
    generate_hopping_sequence,
)


# ====================================================================
# 8.1.2 信道频率映射
# ====================================================================

class TestChannelFreqMapping:
    """射频信道号与中心频率的映射 (8.1.2)。"""

    def test_2400_channel_0(self):
        """2.4 GHz 信道 0 → 2402 MHz。"""
        assert channel_to_freq(0, BAND_2400) == 2402

    def test_2400_channel_78(self):
        """2.4 GHz 信道 78 → 2480 MHz。"""
        assert channel_to_freq(78, BAND_2400) == 2480

    def test_2400_channel_39(self):
        """2.4 GHz 信道 39 → 2441 MHz。"""
        assert channel_to_freq(39, BAND_2400) == 2441

    def test_5100_channel_79(self):
        """5.1 GHz 信道 79 → 5152 MHz。"""
        assert channel_to_freq(79, BAND_5100) == 5152

    def test_5100_channel_275(self):
        """5.1 GHz 信道 275 → 5348 MHz。"""
        assert channel_to_freq(275, BAND_5100) == 5348

    def test_5800_channel_276(self):
        """5.8 GHz 信道 276 → 5727 MHz。"""
        assert channel_to_freq(276, BAND_5800) == 5727

    def test_5800_channel_397(self):
        """5.8 GHz 信道 397 → 5848 MHz。"""
        assert channel_to_freq(397, BAND_5800) == 5848

    def test_freq_to_channel_roundtrip_2400(self):
        """频率 ↔ 信道号往返一致性 (2.4 GHz)。"""
        for n in range(79):
            f = channel_to_freq(n, BAND_2400)
            assert freq_to_channel(f, BAND_2400) == n

    def test_freq_to_channel_roundtrip_5100(self):
        """频率 ↔ 信道号往返一致性 (5.1 GHz)。"""
        for n in [79, 100, 200, 275]:
            f = channel_to_freq(n, BAND_5100)
            assert freq_to_channel(f, BAND_5100) == n


# ====================================================================
# 频点表管理
# ====================================================================

class TestFreqTable:
    """频率表管理功能。"""

    def test_full_table_2400_1m(self):
        """2.4 GHz 1 MHz: 完整表有 76 个数据信道 (排除广播 76/77/78)。"""
        ft = FreqTable(band=BAND_2400, bandwidth_mhz=1)
        full = ft.full_table()
        assert len(full) == 76
        assert 76 not in full
        assert 77 not in full
        assert 78 not in full
        assert full == sorted(full)

    def test_full_table_2400_2m(self):
        """2.4 GHz 2 MHz: 完整表只包含 2 MHz 有效信道。"""
        ft = FreqTable(band=BAND_2400, bandwidth_mhz=2)
        full = ft.full_table()
        assert len(full) == len(_2M_PHYS_2400)
        for ch in full:
            assert ch in _2M_PHYS_2400

    def test_full_table_2400_4m(self):
        """2.4 GHz 4 MHz: 完整表只包含 4 MHz 有效信道。"""
        ft = FreqTable(band=BAND_2400, bandwidth_mhz=4)
        full = ft.full_table()
        assert len(full) == len(_4M_PHYS_2400)
        for ch in full:
            assert ch in _4M_PHYS_2400

    def test_available_table_excludes_blocked(self):
        """可用表排除被阻塞的信道。"""
        blocked = {0, 5, 10, 40, 75}
        ft = FreqTable(band=BAND_2400, bandwidth_mhz=1, blocked_channels=blocked)
        avail = ft.available_table()
        assert len(avail) == 76 - len(blocked)
        for ch in blocked:
            assert ch not in avail

    def test_available_table_sorted(self):
        """可用频点表按升序排列。"""
        ft = FreqTable(band=BAND_2400, blocked_channels={20, 30, 50})
        avail = ft.available_table()
        assert avail == sorted(avail)

    def test_full_table_5100(self):
        """5.1 GHz: 共 197 个信道, 减去 3 个广播 = 194 个数据信道。"""
        ft = FreqTable(band=BAND_5100, bandwidth_mhz=1)
        full = ft.full_table()
        assert len(full) == 194
        assert 273 not in full
        assert 274 not in full
        assert 275 not in full

    def test_full_table_5800(self):
        """5.8 GHz: 共 122 个信道, 无广播信道。"""
        ft = FreqTable(band=BAND_5800, bandwidth_mhz=1)
        full = ft.full_table()
        assert len(full) == 122


# ====================================================================
# 6.10.3.2 伪随机数生成器
# ====================================================================

class TestBitReverse:
    """位反转子函数测试。"""

    def test_reverse_byte_0x80(self):
        """0b10000000 → 0b00000001。"""
        assert _bit_reverse_byte(0x80) == 0x01

    def test_reverse_byte_0x01(self):
        """0b00000001 → 0b10000000。"""
        assert _bit_reverse_byte(0x01) == 0x80

    def test_reverse_byte_0xFF(self):
        """0xFF 反转仍为 0xFF。"""
        assert _bit_reverse_byte(0xFF) == 0xFF

    def test_reverse_byte_0x00(self):
        """0x00 反转仍为 0x00。"""
        assert _bit_reverse_byte(0x00) == 0x00

    def test_reverse_byte_0xA5(self):
        """0b10100101 → 0b10100101。"""
        assert _bit_reverse_byte(0xA5) == 0xA5

    def test_reverse_byte_0x0F(self):
        """0b00001111 → 0b11110000。"""
        assert _bit_reverse_byte(0x0F) == 0xF0

    def test_reverse_16_low_high_separate(self):
        """16 位反转: 高 8 位和低 8 位分别反转。"""
        # 0x0180 = high=0x01, low=0x80
        # reversed: high=0x80, low=0x01 → 0x8001
        assert _reverse_16(0x0180) == 0x8001

    def test_reverse_16_identity(self):
        """0xFFFF 反转仍为 0xFFFF。"""
        assert _reverse_16(0xFFFF) == 0xFFFF


class TestHoppingPRNG:
    """标准 6.10.3.2 PRNG 测试。"""

    def test_output_16bit(self):
        """输出总是 16 位。"""
        for p1, p2 in [(0, 0), (0xFFFF, 0xFFFF), (12345, 54321)]:
            r = hopping_prng(p1, p2)
            assert 0 <= r <= 0xFFFF

    def test_deterministic(self):
        """相同输入产生相同输出。"""
        r1 = hopping_prng(100, 200)
        r2 = hopping_prng(100, 200)
        assert r1 == r2

    def test_different_param1_different_output(self):
        """不同的 hop_param1 (时隙号) 产生不同输出。"""
        results = set()
        for slot in range(100):
            results.add(hopping_prng(slot, 12345))
        # 100 个不同时隙应产生高度分散的结果
        assert len(results) >= 90

    def test_different_param2_different_output(self):
        """不同的 hop_param2 产生不同输出 (同一时隙)。"""
        r1 = hopping_prng(42, 1000)
        r2 = hopping_prng(42, 2000)
        assert r1 != r2

    def test_zero_inputs(self):
        """零输入的确定性结果。"""
        r = hopping_prng(0, 0)
        assert isinstance(r, int)
        assert 0 <= r <= 0xFFFF

    def test_uniformity(self):
        """输出在 0~65535 之间分布相对均匀。"""
        hp2 = 0xABCD
        results = [hopping_prng(i, hp2) for i in range(1000)]
        mean_val = np.mean(results)
        # 均匀分布理论均值 ~32768, 容忍 ±20%
        assert 20000 < mean_val < 50000


class TestDeriveHopParam2:
    """hop_param2 派生函数测试。"""

    def test_32bit_sync(self):
        """32 位同步序列: low16 XOR high16。"""
        sync = 0xAABBCCDD
        expected = (0xCCDD) ^ (0xAABB)
        assert derive_hop_param2(sync, 32) == expected

    def test_64bit_sync_takes_low32(self):
        """64 位同步序列: 取低 32 位, 再 low16 XOR high16。"""
        sync = 0x1122334455667788
        low32 = sync & 0xFFFFFFFF  # 0x55667788
        expected = (0x7788) ^ (0x5566)
        assert derive_hop_param2(sync, 64) == expected

    def test_24bit_link_id(self):
        """24 位逻辑链路标识: 高位补零至 32 位。"""
        link_id = 0xABCDEF
        # 高位补零 → 0x00ABCDEF
        expected = (0xCDEF) ^ (0x00AB)
        assert derive_hop_param2(link_id, 24) == expected

    def test_output_16bit(self):
        """输出总是 16 位。"""
        for val in [0, 0xFFFFFFFF, 0x123456]:
            r = derive_hop_param2(val)
            assert 0 <= r <= 0xFFFF


# ====================================================================
# 6.10.3.3 数据链路跳频
# ====================================================================

class TestDataLinkHop:
    """数据链路跳频测试。"""

    def test_output_in_available(self):
        """输出信道必须在可用频点表中。"""
        ft = FreqTable(band=BAND_2400, bandwidth_mhz=1)
        avail = set(ft.available_table())
        hp2 = derive_hop_param2(0x12345678)
        for slot in range(200):
            ch = data_link_hop(slot, hp2, ft)
            assert ch in avail

    def test_blocked_channels_avoided(self):
        """阻塞信道不会被选中。"""
        blocked = {i for i in range(0, 76, 2)}  # 阻塞所有偶数信道
        ft = FreqTable(band=BAND_2400, blocked_channels=blocked)
        hp2 = derive_hop_param2(0xDEADBEEF)
        for slot in range(200):
            ch = data_link_hop(slot, hp2, ft)
            assert ch not in blocked

    def test_deterministic(self):
        """相同参数产生相同跳频序列。"""
        ft = FreqTable()
        hp2 = 0x1234
        seq1 = [data_link_hop(i, hp2, ft) for i in range(50)]
        seq2 = [data_link_hop(i, hp2, ft) for i in range(50)]
        assert seq1 == seq2

    def test_different_param2_different_seq(self):
        """不同参数 2 产生不同跳频序列。"""
        ft = FreqTable()
        seq1 = [data_link_hop(i, 0x1111, ft) for i in range(20)]
        seq2 = [data_link_hop(i, 0x2222, ft) for i in range(20)]
        assert seq1 != seq2

    def test_2m_bandwidth_valid_channels(self):
        """2 MHz 带宽: 输出信道必须是 2M 有效信道。"""
        ft = FreqTable(band=BAND_2400, bandwidth_mhz=2)
        valid_2m = set(_2M_PHYS_2400)
        hp2 = 0xABCD
        for slot in range(200):
            ch = data_link_hop(slot, hp2, ft)
            assert ch in valid_2m

    def test_4m_bandwidth_valid_channels(self):
        """4 MHz 带宽: 输出信道必须是 4M 有效信道。"""
        ft = FreqTable(band=BAND_2400, bandwidth_mhz=4)
        valid_4m = set(_4M_PHYS_2400)
        hp2 = 0x5678
        for slot in range(200):
            ch = data_link_hop(slot, hp2, ft)
            assert ch in valid_4m

    def test_spread_over_channels(self):
        """跳频序列应分散覆盖多个信道。"""
        ft = FreqTable()
        hp2 = 0x9999
        channels_used = set()
        for slot in range(500):
            channels_used.add(data_link_hop(slot, hp2, ft))
        # 76 个可用信道, 500 次跳频应覆盖大部分
        assert len(channels_used) >= 50


class TestAvailableFreqMap:
    """可用频点映射过程测试。"""

    def test_single_channel(self):
        """只有一个可用信道时, 必然输出该信道。"""
        for rand16 in [0, 32768, 65535]:
            ch = _available_freq_map(rand16, [42])
            assert ch == 42

    def test_mapping_range(self):
        """输出总在可用表范围内。"""
        avail = list(range(10, 30))
        for rand16 in range(0, 65536, 100):
            ch = _available_freq_map(rand16, avail)
            assert ch in avail

    def test_empty_raises(self):
        """空表抛出 ValueError。"""
        with pytest.raises(ValueError):
            _available_freq_map(100, [])

    def test_uniform_distribution(self):
        """映射结果在可用表上近似均匀。"""
        avail = list(range(76))
        counts = {ch: 0 for ch in avail}
        for r in range(65536):
            counts[_available_freq_map(r, avail)] += 1
        vals = list(counts.values())
        expected = 65536 / 76
        # 每个信道计数应在 ±50% 范围内
        for v in vals:
            assert expected * 0.5 < v < expected * 1.5


# ====================================================================
# 6.10.3.4 系统管理帧链路跳频
# ====================================================================

class TestMgmtFrameHop:
    """系统管理帧链路跳频测试。"""

    def test_output_in_available(self):
        """输出信道必须在可用频点表中。"""
        ft = FreqTable()
        avail = set(ft.available_table())
        hp2 = 0x4321
        for slot in range(100):
            ch = mgmt_frame_hop(slot, hp2, ft)
            assert ch in avail

    def test_deterministic(self):
        """相同参数产生同一结果。"""
        ft = FreqTable()
        assert mgmt_frame_hop(10, 0x1234, ft) == mgmt_frame_hop(10, 0x1234, ft)


# ====================================================================
# 6.10.3.5 测量链路跳频
# ====================================================================

class TestMeasLinkHopper:
    """测量链路跳频器测试。"""

    def test_ascending_order(self):
        """方案 1: 按射频信道号从低到高。"""
        ft = FreqTable(band=BAND_2400)
        hopper = MeasLinkHopper(mode=MEAS_HOP_ASCENDING, freq_table=ft)
        avail = ft.available_table()
        for i in range(len(avail)):
            ch = hopper.next_channel()
            assert ch == avail[i]

    def test_ascending_wraps(self):
        """方案 1: 遍历完后循环。"""
        ft = FreqTable(band=BAND_2400, blocked_channels=set(range(10, 76)))
        hopper = MeasLinkHopper(mode=MEAS_HOP_ASCENDING, freq_table=ft)
        avail = ft.available_table()
        n = len(avail)
        # 遍历 2 遍
        for i in range(2 * n):
            ch = hopper.next_channel()
            assert ch == avail[i % n]

    def test_descending_order(self):
        """方案 2: 按射频信道号从高到低。"""
        ft = FreqTable(band=BAND_2400)
        hopper = MeasLinkHopper(mode=MEAS_HOP_DESCENDING, freq_table=ft)
        avail = list(reversed(ft.available_table()))
        for i in range(len(avail)):
            ch = hopper.next_channel()
            assert ch == avail[i]

    def test_random_no_repeat_within_cycle(self):
        """方案 3: 一个周期内不重复 (每次使用后删除)。"""
        ft = FreqTable(band=BAND_2400, blocked_channels=set(range(20, 76)))
        hopper = MeasLinkHopper(
            mode=MEAS_HOP_RANDOM, freq_table=ft, hop_param2=0xBEEF,
        )
        avail = ft.available_table()
        n = len(avail)
        seen = set()
        for i in range(n):
            ch = hopper.next_channel(slot_counter=i)
            assert ch not in seen, f"信道 {ch} 在第 {i} 次跳频时重复"
            seen.add(ch)
        # 全部可用信道应被使用
        assert seen == set(avail)

    def test_random_reset_after_exhaust(self):
        """方案 3: 可用频点表耗尽后重置, 可继续跳频。"""
        blocked = set(range(10, 76))  # 只留 0..9
        ft = FreqTable(band=BAND_2400, blocked_channels=blocked)
        hopper = MeasLinkHopper(
            mode=MEAS_HOP_RANDOM, freq_table=ft, hop_param2=0x1234,
        )
        avail = ft.available_table()
        n = len(avail)
        # 耗尽第一轮
        for i in range(n):
            hopper.next_channel(slot_counter=i)
        # 继续第二轮, 应不报错
        ch = hopper.next_channel(slot_counter=n)
        assert ch in avail

    def test_init_phase_uses_init_channel(self):
        """初始化阶段使用配置的初始化频点。"""
        ft = FreqTable()
        hopper = MeasLinkHopper(
            mode=MEAS_HOP_RANDOM, freq_table=ft,
            hop_param2=0xAAAA, init_channel=42,
        )
        ch = hopper.next_channel(slot_counter=0, is_init_phase=True)
        assert ch == 42

    def test_init_phase_no_removal(self):
        """方案 3 初始化阶段不删除频点。"""
        blocked = set(range(5, 76))
        ft = FreqTable(band=BAND_2400, blocked_channels=blocked)
        hopper = MeasLinkHopper(
            mode=MEAS_HOP_RANDOM, freq_table=ft,
            hop_param2=0xBBBB, init_channel=0,
        )
        # 初始化阶段
        hopper.next_channel(slot_counter=0, is_init_phase=True)
        # 可用表长度仍然不变
        assert len(hopper._current_available) == len(ft.available_table())

    def test_reset(self):
        """reset 恢复初始状态。"""
        ft = FreqTable(band=BAND_2400, blocked_channels=set(range(10, 76)))
        hopper = MeasLinkHopper(
            mode=MEAS_HOP_ASCENDING, freq_table=ft,
        )
        hopper.next_channel()
        hopper.next_channel()
        hopper.reset()
        ch = hopper.next_channel()
        assert ch == ft.available_table()[0]


# ====================================================================
# 跳频序列生成 (便捷函数)
# ====================================================================

class TestGenerateHoppingSequence:
    """跳频序列生成便捷函数测试。"""

    def test_data_link_length(self):
        """数据链路: 生成指定长度的序列。"""
        seq = generate_hopping_sequence(100, hop_param2=0x1234, link_type="data")
        assert len(seq) == 100

    def test_mgmt_link_length(self):
        """管理帧链路: 生成指定长度的序列。"""
        seq = generate_hopping_sequence(50, hop_param2=0x5678, link_type="mgmt")
        assert len(seq) == 50

    def test_meas_ascending(self):
        """测量链路升序: 序列按信道号升序。"""
        ft = FreqTable(band=BAND_2400, blocked_channels=set(range(10, 76)))
        seq = generate_hopping_sequence(
            10, hop_param2=0, freq_table=ft, link_type="meas_asc",
        )
        avail = ft.available_table()
        assert seq == avail[:10]

    def test_meas_descending(self):
        """测量链路降序: 序列按信道号降序。"""
        ft = FreqTable(band=BAND_2400, blocked_channels=set(range(10, 76)))
        seq = generate_hopping_sequence(
            10, hop_param2=0, freq_table=ft, link_type="meas_desc",
        )
        avail = list(reversed(ft.available_table()))
        assert seq == avail[:10]

    def test_meas_random_no_repeat(self):
        """测量链路随机: 一个周期内不重复。"""
        blocked = set(range(20, 76))
        ft = FreqTable(band=BAND_2400, blocked_channels=blocked)
        n = len(ft.available_table())
        seq = generate_hopping_sequence(
            n, hop_param2=0xABCD, freq_table=ft, link_type="meas_rand",
        )
        assert len(set(seq)) == n

    def test_start_slot_offset(self):
        """起始时隙偏移影响序列。"""
        ft = FreqTable()
        seq1 = generate_hopping_sequence(20, 0x1234, ft, "data", start_slot=0)
        seq2 = generate_hopping_sequence(20, 0x1234, ft, "data", start_slot=100)
        assert seq1 != seq2

    def test_default_freq_table(self):
        """默认频率表 (2.4 GHz 1 MHz 全可用)。"""
        seq = generate_hopping_sequence(10, hop_param2=0x9876)
        assert len(seq) == 10
        ft = FreqTable()
        avail = set(ft.available_table())
        for ch in seq:
            assert ch in avail


# ====================================================================
# 综合性测试
# ====================================================================

class TestIntegration:
    """跳频模块综合测试。"""

    def test_e2e_data_link_with_blocking(self):
        """端到端: 数据链路跳频, 部分信道被阻塞。"""
        blocked = {0, 10, 20, 30, 40, 50, 60, 70}
        ft = FreqTable(band=BAND_2400, blocked_channels=blocked)
        sync_seq = 0xDEADBEEF
        hp2 = derive_hop_param2(sync_seq, 32)
        seq = generate_hopping_sequence(100, hp2, ft, "data")
        for ch in seq:
            assert ch not in blocked
            assert 0 <= ch <= 75  # 数据信道范围

    def test_e2e_measurement_full_sweep(self):
        """端到端: 测量链路方案 3 完整扫频, 覆盖所有可用信道。"""
        ft = FreqTable(band=BAND_2400)
        avail = ft.available_table()
        n = len(avail)
        hp2 = derive_hop_param2(0x12345678)
        seq = generate_hopping_sequence(n, hp2, ft, "meas_rand")
        assert set(seq) == set(avail)

    def test_frequency_diversity(self):
        """跳频序列的频率分集: 相邻跳频信道应有足够间隔。"""
        ft = FreqTable()
        hp2 = derive_hop_param2(0xCAFEBABE)
        seq = generate_hopping_sequence(100, hp2, ft, "data")
        # 计算相邻跳频频率间隔
        freq_diff = [abs(seq[i + 1] - seq[i]) for i in range(len(seq) - 1)]
        avg_diff = np.mean(freq_diff)
        # 随机跳频的平均间隔应显著大于 1 (即不是简单连续)
        assert avg_diff > 10

    def test_5ghz_data_link(self):
        """5.1 GHz 频段数据链路跳频。"""
        ft = FreqTable(band=BAND_5100, bandwidth_mhz=1)
        avail = set(ft.available_table())
        hp2 = 0x5555
        for slot in range(100):
            ch = data_link_hop(slot, hp2, ft)
            assert ch in avail
