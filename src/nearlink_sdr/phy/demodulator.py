
class SLEDemodulator:
    def __init__(self, sps=4):
        self.sps = sps

    def demodulate(self, rx_signal):
        # 匹配滤波，降采样
        rx_symbols = rx_signal[self.sps//2::self.sps]
        # BPSK解调判决
        rx_bits = (rx_symbols.real > 0).astype(int)
        return rx_bits
