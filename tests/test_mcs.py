"""MCS 表与速率适配表 (6.10.5 / 6.10.6) 测试"""

from fractions import Fraction

import pytest

from nearlink_sdr.common.mcs import (
    CODE_LENGTHS,
    MCS_TABLE,
    RATE_ADAPT_TABLE_1,
    RATE_ADAPT_TABLE_2,
    Modulation,
    RateConfig,
    get_kcb,
    get_mcs,
)


class TestMCSTable:
    """MCS 表完整性"""

    def test_13_entries(self):
        assert len(MCS_TABLE) == 13

    def test_indices_0_to_12(self):
        assert [e.index for e in MCS_TABLE] == list(range(13))

    @pytest.mark.parametrize("idx, mod", [
        (0, Modulation.BPSK), (1, Modulation.BPSK),
        (2, Modulation.QPSK), (8, Modulation.QPSK),
        (9, Modulation.PSK8), (12, Modulation.PSK8),
    ])
    def test_modulation(self, idx, mod):
        assert get_mcs(idx).modulation == mod

    @pytest.mark.parametrize("idx, rate", [
        (0, Fraction(1, 4)),
        (4, Fraction(1, 2)),
        (6, Fraction(3, 4)),
        (8, Fraction(1, 1)),
        (12, Fraction(1, 1)),
    ])
    def test_code_rate(self, idx, rate):
        assert get_mcs(idx).code_rate == rate

    @pytest.mark.parametrize("idx, eff", [
        (0, 0.250), (4, 1.000), (8, 2.000), (12, 3.000),
    ])
    def test_spectral_efficiency(self, idx, eff):
        assert abs(get_mcs(idx).spectral_efficiency - eff) < 1e-6

    def test_bits_per_symbol(self):
        assert get_mcs(0).bits_per_symbol == 1   # BPSK
        assert get_mcs(4).bits_per_symbol == 2   # QPSK
        assert get_mcs(10).bits_per_symbol == 3  # 8PSK

    def test_invalid_index(self):
        with pytest.raises(ValueError):
            get_mcs(13)
        with pytest.raises(ValueError):
            get_mcs(-1)

    def test_efficiency_equals_rate_times_bits(self):
        """传输效率 = 编码速率 * 每符号比特数"""
        for e in MCS_TABLE:
            expected = float(e.code_rate) * e.bits_per_symbol
            assert abs(e.spectral_efficiency - expected) < 1e-6


class TestRateAdaptTable1:
    """速率适配第一表格 (表23)"""

    def test_all_rates_present(self):
        expected_rates = [
            Fraction(1, 4), Fraction(3, 8), Fraction(1, 2),
            Fraction(5, 8), Fraction(3, 4), Fraction(7, 8),
        ]
        assert set(RATE_ADAPT_TABLE_1.keys()) == set(expected_rates)

    def test_all_code_lengths_present(self):
        for rate_map in RATE_ADAPT_TABLE_1.values():
            assert set(rate_map.keys()) == set(CODE_LENGTHS)

    @pytest.mark.parametrize("rate, n, kcb", [
        (Fraction(1, 4), 1024, 256),
        (Fraction(1, 4), 64,   12),
        (Fraction(3, 8), 512,  160),
        (Fraction(1, 2), 256,  112),
        (Fraction(5, 8), 128,  72),
        (Fraction(3, 4), 1024, 768),
        (Fraction(7, 8), 64,   52),
    ])
    def test_specific_values(self, rate, n, kcb):
        assert get_kcb(rate, n, table=1) == kcb

    def test_kcb_leq_code_length(self):
        """信息比特数不能超过码长"""
        for rate_map in RATE_ADAPT_TABLE_1.values():
            for n, kcb in rate_map.items():
                assert kcb <= n


class TestRateAdaptTable2:
    """速率适配第二表格 (表24)"""

    def test_only_high_rates(self):
        expected_rates = [Fraction(5, 8), Fraction(3, 4), Fraction(7, 8)]
        assert set(RATE_ADAPT_TABLE_2.keys()) == set(expected_rates)

    @pytest.mark.parametrize("rate, n, kcb", [
        (Fraction(5, 8), 512,  316),
        (Fraction(3, 4), 256,  189),
        (Fraction(7, 8), 1024, 896),
        (Fraction(7, 8), 64,   53),
    ])
    def test_specific_values(self, rate, n, kcb):
        assert get_kcb(rate, n, table=2) == kcb

    def test_table2_kcb_may_differ_from_table1(self):
        """表2 的 Kcb 和表1 不同 (除码长 1024 和部分码长 64)"""
        for rate in RATE_ADAPT_TABLE_2:
            for n in (512, 256, 128):
                kcb1 = get_kcb(rate, n, table=1)
                kcb2 = get_kcb(rate, n, table=2)
                assert kcb2 >= kcb1  # 表2 的值通常更大或相等


class TestGetKcb:
    """get_kcb 边界检查"""

    def test_invalid_code_length(self):
        with pytest.raises(ValueError):
            get_kcb(Fraction(1, 4), 100)

    def test_invalid_rate_table1(self):
        with pytest.raises(ValueError):
            get_kcb(Fraction(1, 1), 1024, table=1)  # R=1 不在表中

    def test_invalid_rate_table2(self):
        with pytest.raises(ValueError):
            get_kcb(Fraction(1, 4), 1024, table=2)  # R=1/4 不在表2中


class TestRateConfig:
    """RateConfig 集成"""

    def test_from_mcs(self):
        rc = RateConfig.from_mcs(6)
        assert rc.mcs_index == 6
        assert rc.modulation == Modulation.QPSK
        assert rc.code_rate == Fraction(3, 4)
        assert rc.bits_per_symbol == 2

    def test_kcb_lookup(self):
        rc = RateConfig.from_mcs(4)  # R=1/2
        assert rc.kcb(1024) == 512
        assert rc.kcb(64) == 28

    def test_kcb_table2(self):
        rc = RateConfig.from_mcs(6)  # R=3/4
        assert rc.kcb(512, table=2) == 382

    def test_all_mcs_indices(self):
        for i in range(13):
            rc = RateConfig.from_mcs(i)
            assert rc.mcs_index == i
