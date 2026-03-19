"""TXS-10002-2025 信道模型: AWGN / Rayleigh / Rician / 多径频率选择性衰落。

SparkLink SLE 工作于 2.4 GHz ISM 频段,典型场景为室内短距通信。
参考 IEEE 802.15.4 / ITU-R P.1238 室内信道参数:
  - RMS 时延扩展: 10 ~ 50 ns
  - Rician K 因子: 3 ~ 10 dB (视距)
  - 最大多普勒频移: < 50 Hz (行人速度)
"""

from dataclasses import dataclass, field

import numpy as np

# ── 典型室内功率时延谱 (PDP) ──

# 简化两径模型: 直射径 + 一条反射径
PDP_2TAP = [
    (0, 0.0),       # 直射径, 0 dB
    (1, -10.0),      # 反射径, -10 dB, 延迟 1 符号
]

# ITU Indoor Office B (简化 6 径模型, 相对时延单位: 符号周期)
PDP_INDOOR_OFFICE = [
    (0, 0.0),
    (1, -3.6),
    (2, -6.5),
    (3, -9.4),
    (4, -12.4),
    (5, -15.4),
]


@dataclass
class ChannelConfig:
    """信道配置参数。

    Attributes:
        snr_db: 信噪比 (dB)。
        channel_type: "awgn" | "rayleigh" | "rician" | "multipath"。
        rician_k_db: Rician K 因子 (dB), 仅 "rician" 模式使用。
        pdp: 功率时延谱 [(delay_samples, power_dB), ...], 仅 "multipath" 使用。
        max_doppler_hz: 最大多普勒频移 (Hz)。0 表示准静态。
        seed: 随机种子。
    """
    snr_db: float = 10.0
    channel_type: str = "awgn"
    rician_k_db: float = 6.0
    pdp: list[tuple[int, float]] = field(default_factory=lambda: list(PDP_2TAP))
    max_doppler_hz: float = 0.0
    seed: int | None = None


class ChannelModel:
    """多模信道模型,支持 AWGN / 平坦衰落 / 频率选择性衰落。"""

    def __init__(self, snr_db: float = 10.0, config: ChannelConfig | None = None):
        if config is not None:
            self.cfg = config
        else:
            self.cfg = ChannelConfig(snr_db=snr_db)
        self._rng = np.random.default_rng(self.cfg.seed)
        self._last_taps: np.ndarray | None = None

    # ── 公共接口 ──

    def apply_awgn(self, signal: np.ndarray) -> np.ndarray:
        """仅加 AWGN 噪声 (保持向后兼容)。"""
        return self._add_noise(signal, self.cfg.snr_db)

    def apply_fading(self, signal: np.ndarray) -> np.ndarray:
        """按 config 类型应用衰落 + AWGN, 同时缓存信道系数到 last_taps。"""
        ct = self.cfg.channel_type
        n = len(signal)
        if ct == "awgn":
            self._last_taps = np.ones((1, n), dtype=complex)
            return self._add_noise(signal, self.cfg.snr_db)
        elif ct == "rayleigh":
            h = self._gen_rayleigh_coeffs(n)
            self._last_taps = h.reshape(1, -1)
            return self._add_noise(signal * h, self.cfg.snr_db)
        elif ct == "rician":
            h = self._gen_rician_coeffs(n)
            self._last_taps = h.reshape(1, -1)
            return self._add_noise(signal * h, self.cfg.snr_db)
        elif ct == "multipath":
            taps = self._gen_multipath_taps(n)
            self._last_taps = taps
            faded = self._apply_multipath_taps(signal, taps)
            return self._add_noise(faded, self.cfg.snr_db)
        else:
            raise ValueError(f"Unknown channel type: {ct}")

    @property
    def last_taps(self) -> np.ndarray | None:
        """上一次 apply_fading 使用的信道系数, 供均衡器使用。"""
        return self._last_taps

    def get_channel_taps(self, n_symbols: int) -> np.ndarray:
        """返回信道抽头系数矩阵 (n_taps × n_symbols), 用于均衡器。

        对于平坦衰落: 返回 (1, n_symbols)。
        对于多径: 返回 (max_delay+1, n_symbols)。
        """
        ct = self.cfg.channel_type
        if ct == "awgn":
            return np.ones((1, n_symbols), dtype=complex)
        elif ct == "rayleigh":
            return self._gen_rayleigh_coeffs(n_symbols).reshape(1, -1)
        elif ct == "rician":
            return self._gen_rician_coeffs(n_symbols).reshape(1, -1)
        elif ct == "multipath":
            return self._gen_multipath_taps(n_symbols)
        else:
            raise ValueError(f"Unknown channel type: {ct}")

    @property
    def noise_variance(self) -> float:
        """AWGN 噪声方差 (单边, 假设单位信号功率)。"""
        snr_lin = 10.0 ** (self.cfg.snr_db / 10.0)
        return 1.0 / (2.0 * snr_lin) if snr_lin > 0 else 1e10

    # ── 平坦衰落 ──

    def _rayleigh_flat(self, signal: np.ndarray) -> np.ndarray:
        h = self._gen_rayleigh_coeffs(len(signal))
        self._last_taps = h.reshape(1, -1)
        return signal * h

    def _rician_flat(self, signal: np.ndarray) -> np.ndarray:
        h = self._gen_rician_coeffs(len(signal))
        self._last_taps = h.reshape(1, -1)
        return signal * h

    def _gen_rayleigh_coeffs(self, n: int) -> np.ndarray:
        """生成 Rayleigh 衰落系数 (每符号独立, 或带多普勒相关)。"""
        if self.cfg.max_doppler_hz <= 0:
            # 准静态: 整段用同一个衰落系数
            h = (self._rng.standard_normal() + 1j * self._rng.standard_normal()) / np.sqrt(2)
            return np.full(n, h)
        # 独立 Rayleigh per symbol (简化, 不做 Jakes 滤波)
        return (self._rng.standard_normal(n) + 1j * self._rng.standard_normal(n)) / np.sqrt(2)

    def _gen_rician_coeffs(self, n: int) -> np.ndarray:
        """生成 Rician 衰落系数。K = LOS功率 / 散射功率。"""
        k_lin = 10.0 ** (self.cfg.rician_k_db / 10.0)
        los_amp = np.sqrt(k_lin / (k_lin + 1.0))
        scatter_amp = np.sqrt(1.0 / (k_lin + 1.0))

        if self.cfg.max_doppler_hz <= 0:
            scatter = (self._rng.standard_normal() + 1j * self._rng.standard_normal()) / np.sqrt(2)
            h = los_amp + scatter_amp * scatter
            return np.full(n, h)
        scatter = (self._rng.standard_normal(n) + 1j * self._rng.standard_normal(n)) / np.sqrt(2)
        return los_amp + scatter_amp * scatter

    # ── 多径频率选择性衰落 ──

    def _multipath(self, signal: np.ndarray) -> np.ndarray:
        """应用多径信道 (FIR 卷积模型)。"""
        taps = self._gen_multipath_taps(len(signal))
        self._last_taps = taps
        return self._apply_multipath_taps(signal, taps)

    @staticmethod
    def _apply_multipath_taps(signal: np.ndarray, taps: np.ndarray) -> np.ndarray:
        """用给定的抽头系数对信号做 FIR 多径卷积。"""
        n_taps = taps.shape[0]
        n = len(signal)
        out = np.zeros(n, dtype=complex)
        for k in range(n_taps):
            delay = k
            if delay < n:
                shifted = np.zeros(n, dtype=complex)
                shifted[delay:] = signal[:n - delay]
                out += taps[k, :n] * shifted
        return out

    def _gen_multipath_taps(self, n: int) -> np.ndarray:
        """生成多径信道抽头系数。

        返回 (n_taps, n) 的复数矩阵,每行对应一个多径分量。
        """
        pdp = self.cfg.pdp
        n_taps = len(pdp)
        taps = np.zeros((n_taps, n), dtype=complex)

        for i, (_, power_db) in enumerate(pdp):
            amp = 10.0 ** (power_db / 20.0)
            if self.cfg.max_doppler_hz <= 0:
                # 准静态: 每个抽头一个随机复数系数
                h = (self._rng.standard_normal() + 1j * self._rng.standard_normal()) / np.sqrt(2)
                taps[i, :] = amp * h
            else:
                h = (self._rng.standard_normal(n) + 1j * self._rng.standard_normal(n)) / np.sqrt(2)
                taps[i, :] = amp * h

        # 归一化: 使平均总功率为 1
        total_power = np.sum([10.0 ** (p / 10.0) for _, p in pdp])
        taps /= np.sqrt(total_power)

        return taps

    # ── AWGN ──

    def _add_noise(self, signal: np.ndarray, snr_db: float) -> np.ndarray:
        snr_linear = 10.0 ** (snr_db / 10.0)
        signal_power = np.mean(np.abs(signal) ** 2)
        if signal_power < 1e-20:
            return signal.copy()
        noise_power = signal_power / snr_linear
        noise = np.sqrt(noise_power / 2) * (
            self._rng.standard_normal(signal.shape)
            + 1j * self._rng.standard_normal(signal.shape)
        )
        return signal + noise
