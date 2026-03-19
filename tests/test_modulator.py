import numpy as np

from nearlink_sdr.phy.modulator import SLEModulator


def test_bpsk_modulation():
    modulator = SLEModulator(sps=4)
    bits = np.array([0, 1, 0, 1])
    signal = modulator.modulate(bits)
    assert len(signal) == 16
    assert np.all(signal[:4] == -1)
    assert np.all(signal[4:8] == 1)
