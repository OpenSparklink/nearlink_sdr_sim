import numpy as np

from nearlink_sdr.common.m_sequence import generate_m_sequence, m31_sequence, m63_sequence


class TestMSequence:
    def test_m31_length(self):
        for idx in range(6):
            seq = m31_sequence(idx)
            assert len(seq) == 31

    def test_m63_length(self):
        for idx in range(6):
            seq = m63_sequence(idx)
            assert len(seq) == 63

    def test_m31_binary_values(self):
        seq = m31_sequence(0)
        assert set(np.unique(seq)).issubset({0, 1})

    def test_m31_balance_property(self):
        """m序列的平衡特性：一个周期内1的个数比0的个数多1"""
        seq = m31_sequence(0)
        ones = np.sum(seq)
        zeros = 31 - ones
        assert ones == zeros + 1

    def test_m63_balance_property(self):
        seq = m63_sequence(0)
        ones = np.sum(seq)
        zeros = 63 - ones
        assert ones == zeros + 1

    def test_m31_autocorrelation(self):
        """m序列的自相关特性：延迟非零时自相关值为 -1/N"""
        seq = m31_sequence(0)
        bipolar = 2 * seq - 1  # 转为 +-1
        N = len(bipolar)
        for d in range(1, N):
            shifted = np.roll(bipolar, d)
            corr = np.sum(bipolar * shifted)
            assert corr == -1

    def test_m63_autocorrelation(self):
        seq = m63_sequence(0)
        bipolar = 2 * seq - 1
        N = len(bipolar)
        for d in range(1, N):
            shifted = np.roll(bipolar, d)
            corr = np.sum(bipolar * shifted)
            assert corr == -1

    def test_m31_seq0_first_bits(self):
        """标准中 m31 序列0初始值 00001, 前5个输出应为 10000"""
        seq = m31_sequence(0, length=5)
        np.testing.assert_array_equal(seq, [1, 0, 0, 0, 0])

    def test_m31_different_sequences(self):
        """不同索引的m序列应不同"""
        s0 = m31_sequence(0)
        s1 = m31_sequence(1)
        assert not np.array_equal(s0, s1)

    def test_m31_periodicity(self):
        """m序列具有周期性，2个周期应相同"""
        seq = generate_m_sequence(5, 0b100101, 0b00001, 62)
        np.testing.assert_array_equal(seq[:31], seq[31:])
