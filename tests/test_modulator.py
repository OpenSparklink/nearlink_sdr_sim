import numpy as np

from nearlink_sdr.phy.demodulator import SLEDemodulator
from nearlink_sdr.phy.modulator import SLEModulator


def test_bpsk_modulation():
    modulator = SLEModulator(sps=4)
    bits = np.array([0, 1, 0, 1])
    signal = modulator.modulate(bits)
    assert len(signal) == 16
    assert np.all(signal[:4] == -1)
    assert np.all(signal[4:8] == 1)


class TestSLEDemodulator:
    """SLEDemodulator BPSK 解调器测试。"""

    def test_demod_roundtrip(self):
        """调制→解调应恢复原始比特 (无噪声)。"""
        mod = SLEModulator(sps=4)
        demod = SLEDemodulator(sps=4)
        bits = np.array([0, 1, 1, 0, 1, 0])
        signal = mod.modulate(bits)
        recovered = demod.demodulate(signal)
        np.testing.assert_array_equal(recovered, bits)

    def test_output_length(self):
        demod = SLEDemodulator(sps=4)
        signal = np.ones(40, dtype=complex)
        out = demod.demodulate(signal)
        assert len(out) == 10  # 40 / 4 = 10 symbols

    def test_default_sps(self):
        demod = SLEDemodulator()
        assert demod.sps == 4
