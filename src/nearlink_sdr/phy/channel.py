import numpy as np

class ChannelModel:
    def __init__(self, snr_db=10):
        self.snr_db = snr_db

    def apply_awgn(self, signal):
        snr_linear = 10 ** (self.snr_db / 10.0)
        signal_power = np.mean(np.abs(signal) ** 2)
        noise_power = signal_power / snr_linear
        noise = np.sqrt(noise_power / 2) * (np.random.randn(*signal.shape) + 1j * np.random.randn(*signal.shape))
        return signal + noise

    def apply_fading(self, signal):
        # 占位结构：支持多径衰落信道
        return signal
