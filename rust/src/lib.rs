use numpy::ndarray::Array2;
use numpy::{PyArray1, PyReadonlyArray1};
use pyo3::prelude::*;

/// SSC 优化的 Polar SC 解码器 (Rust 加速版)
///
/// node_type 编码: 2D 数组 [depth][start], 0=rate-0, 1=rate-1, 2=partial
/// 默认值 2 (partial) 用于未显式标注的节点
struct ScDecoder {
    n: usize,
    big_n: usize,
    is_frozen: Vec<bool>,
    node_type: Array2<i8>,
    l_buf: Array2<f64>,
    b_buf: Array2<i8>,
    info_positions: Vec<usize>,
}

impl ScDecoder {
    fn new(n: usize, is_frozen: &[bool], info_positions: &[usize]) -> Self {
        let big_n = 1 << n;
        // 构建 node_type 表
        let mut node_type = Array2::<i8>::from_elem((n + 1, big_n), 2);
        // 前缀和
        let mut prefix = vec![0i32; big_n + 1];
        for i in 0..big_n {
            prefix[i + 1] = prefix[i] + if is_frozen[i] { 1 } else { 0 };
        }
        // 迭代构建
        let mut stack: Vec<(usize, usize, usize)> = vec![(0, big_n, 0)];
        while let Some((start, length, depth)) = stack.pop() {
            let cnt = prefix[start + length] - prefix[start];
            if cnt == length as i32 {
                node_type[[depth, start]] = 0; // rate-0
            } else if cnt == 0 {
                node_type[[depth, start]] = 1; // rate-1
            } else {
                node_type[[depth, start]] = 2; // partial
                if length > 1 {
                    let half = length >> 1;
                    let d1 = depth + 1;
                    stack.push((start, half, d1));
                    stack.push((start + half, half, d1));
                }
            }
        }

        ScDecoder {
            n,
            big_n,
            is_frozen: is_frozen.to_vec(),
            node_type,
            l_buf: Array2::<f64>::zeros((n + 1, big_n)),
            b_buf: Array2::<i8>::zeros((n + 1, big_n)),
            info_positions: info_positions.to_vec(),
        }
    }

    fn decode(&mut self, llr: &[f64]) -> Vec<i8> {
        // 初始化 LLR
        for (i, &val) in llr.iter().enumerate().take(self.big_n) {
            self.l_buf[[0, i]] = val;
        }
        // 清零 B
        self.b_buf.fill(0);

        self.sc(0, self.big_n, 0);

        // 提取信息位
        self.info_positions
            .iter()
            .map(|&pos| self.b_buf[[self.n, pos]])
            .collect()
    }

    fn sc(&mut self, start: usize, length: usize, depth: usize) {
        let nt = self.node_type[[depth, start]];

        if nt == 0 {
            // rate-0: 全零
            let end = start + length;
            for i in start..end {
                self.b_buf[[self.n, i]] = 0;
                self.b_buf[[depth, i]] = 0;
            }
            return;
        }

        if nt == 1 {
            // rate-1: 硬判决
            let end = start + length;
            // 硬判决得到编码位 x
            let mut x = vec![0i8; length];
            for (idx, i) in (start..end).enumerate() {
                x[idx] = if self.l_buf[[depth, i]] < 0.0 { 1 } else { 0 };
                self.b_buf[[depth, i]] = x[idx];
            }
            if length == 1 {
                self.b_buf[[self.n, start]] = x[0];
            } else {
                // 极性变换 x -> u
                let mut u = x;
                let mut step = length;
                while step >= 2 {
                    let half_s = step >> 1;
                    let n_groups = length / step;
                    for g in 0..n_groups {
                        let base = g * step;
                        for j in 0..half_s {
                            u[base + j] ^= u[base + half_s + j];
                        }
                    }
                    step >>= 1;
                }
                for (idx, i) in (start..end).enumerate() {
                    self.b_buf[[self.n, i]] = u[idx];
                }
            }
            return;
        }

        // partial 节点
        if length == 1 {
            if self.is_frozen[start] {
                self.b_buf[[self.n, start]] = 0;
            } else {
                self.b_buf[[self.n, start]] = if self.l_buf[[depth, start]] >= 0.0 {
                    0
                } else {
                    1
                };
            }
            return;
        }

        let half = length >> 1;
        let mid = start + half;
        let d1 = depth + 1;

        // f 操作: f(a,b) = sign(a)*sign(b)*min(|a|,|b|)
        for j in 0..half {
            let a = self.l_buf[[depth, start + j]];
            let b = self.l_buf[[depth, mid + j]];
            let abs_a = a.abs();
            let abs_b = b.abs();
            let min_abs = if abs_a < abs_b { abs_a } else { abs_b };
            self.l_buf[[d1, start + j]] = min_abs.copysign(a * b);
        }

        self.sc(start, half, d1);

        // g 操作: g(a,b,u) = (1-2u)*a + b
        for j in 0..half {
            let a = self.l_buf[[depth, start + j]];
            let b = self.l_buf[[depth, mid + j]];
            let u = self.b_buf[[d1, start + j]] as f64;
            self.l_buf[[d1, mid + j]] = (1.0 - 2.0 * u) * a + b;
        }

        self.sc(mid, half, d1);

        // 合并 partial sums
        for j in 0..half {
            let left = self.b_buf[[d1, start + j]];
            let right = self.b_buf[[d1, mid + j]];
            self.b_buf[[depth, start + j]] = left ^ right;
            self.b_buf[[depth, mid + j]] = right;
        }
    }
}

/// Python 端缓存的解码器实例
#[pyclass]
struct RustPolarDecoder {
    inner: ScDecoder,
}

#[pymethods]
impl RustPolarDecoder {
    #[new]
    fn new(
        n: usize,
        is_frozen: PyReadonlyArray1<'_, bool>,
        info_positions: PyReadonlyArray1<'_, i64>,
    ) -> Self {
        let frozen_slice = is_frozen.as_slice().unwrap();
        let info_pos: Vec<usize> = info_positions
            .as_slice()
            .unwrap()
            .iter()
            .map(|&x| x as usize)
            .collect();
        RustPolarDecoder {
            inner: ScDecoder::new(n, frozen_slice, &info_pos),
        }
    }

    fn decode<'py>(
        &mut self,
        py: Python<'py>,
        llr: PyReadonlyArray1<'_, f64>,
    ) -> Bound<'py, PyArray1<i8>> {
        let llr_slice = llr.as_slice().unwrap();
        let result = self.inner.decode(llr_slice);
        PyArray1::from_vec(py, result)
    }
}

/// Polar 编码器: 蝶形 GF(2) 变换
#[pyclass]
struct RustPolarEncoder {
    big_n: usize,
    info_positions: Vec<usize>,
}

#[pymethods]
impl RustPolarEncoder {
    #[new]
    fn new(big_n: usize, info_positions: PyReadonlyArray1<'_, i64>) -> Self {
        let info_pos: Vec<usize> = info_positions
            .as_slice()
            .unwrap()
            .iter()
            .map(|&x| x as usize)
            .collect();
        RustPolarEncoder {
            big_n,
            info_positions: info_pos,
        }
    }

    fn encode<'py>(
        &self,
        py: Python<'py>,
        info_bits: PyReadonlyArray1<'_, i8>,
    ) -> Bound<'py, PyArray1<i8>> {
        let bits = info_bits.as_slice().unwrap();
        let d = polar_encode_core(bits, self.big_n, &self.info_positions);
        PyArray1::from_vec(py, d)
    }
}

// ===== 纯 Rust 核心逻辑 (可直接 cargo test) =====

/// CRC 移位寄存器计算
fn crc_calculate_core(data_bits: &[i64], poly: u64, crc_len: usize, seed: u64) -> Vec<i64> {
    let mask = (1u64 << crc_len) - 1;
    let mut reg = seed & mask;

    for &bit in data_bits {
        let msb = (reg >> (crc_len - 1)) & 1;
        let feedback = (bit as u64) ^ msb;
        reg = (reg << 1) & mask;
        if feedback != 0 {
            reg ^= poly;
        }
    }

    let mut parity = vec![0i64; crc_len];
    for (i, p) in parity.iter_mut().enumerate() {
        *p = ((reg >> (crc_len - 1 - i)) & 1) as i64;
    }
    parity
}

/// m 序列 LFSR 生成
fn m_sequence_core(order: usize, taps: u64, init_val: u64, length: usize) -> Vec<i64> {
    let mask = (1u64 << order) - 1;
    let mut reg = init_val;
    let mut seq = vec![0i64; length];

    for item in seq.iter_mut() {
        *item = (reg & 1) as i64;
        let feedback_bits = reg & (taps & mask);
        let feedback = feedback_bits.count_ones() as u64 & 1;
        reg = ((reg >> 1) | (feedback << (order - 1))) & mask;
    }

    seq
}

/// Polar 编码核心: 蝶形 GF(2) 变换
fn polar_encode_core(info_bits: &[i8], big_n: usize, info_positions: &[usize]) -> Vec<i8> {
    let mut d = vec![0i8; big_n];
    for (idx, &pos) in info_positions.iter().enumerate() {
        d[pos] = info_bits[idx];
    }
    let mut stage = 1usize;
    while stage < big_n {
        let stride = 2 * stage;
        let mut j = 0usize;
        while j < big_n {
            for k in 0..stage {
                d[j + k] ^= d[j + stage + k];
            }
            j += stride;
        }
        stage <<= 1;
    }
    d
}

// ===== PyO3 包装层 =====

/// CRC 计算 (TXS-10002-2025 6.10.1)
#[pyfunction]
fn rust_crc_calculate<'py>(
    py: Python<'py>,
    data_bits: PyReadonlyArray1<'_, i64>,
    poly: u64,
    crc_len: usize,
    seed: u64,
) -> Bound<'py, PyArray1<i64>> {
    let result = crc_calculate_core(data_bits.as_slice().unwrap(), poly, crc_len, seed);
    PyArray1::from_vec(py, result)
}

/// m 序列生成 (TXS-10002-2025 6.10.2)
#[pyfunction]
fn rust_generate_m_sequence<'py>(
    py: Python<'py>,
    order: usize,
    taps: u64,
    init_val: u64,
    length: usize,
) -> Bound<'py, PyArray1<i64>> {
    let result = m_sequence_core(order, taps, init_val, length);
    PyArray1::from_vec(py, result)
}

/// 模块入口
#[pymodule]
fn nearlink_sdr_accel(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<RustPolarDecoder>()?;
    m.add_class::<RustPolarEncoder>()?;
    m.add_function(wrap_pyfunction!(rust_crc_calculate, m)?)?;
    m.add_function(wrap_pyfunction!(rust_generate_m_sequence, m)?)?;
    Ok(())
}

// ===== Rust 单元测试 =====

#[cfg(test)]
mod tests {
    use super::*;

    // --- CRC 测试 ---

    const CRC24A_POLY: u64 = 0x00065B;
    const CRC12_POLY: u64 = 0x80F;
    const CRC32_POLY: u64 = 0x04C11DB7;

    #[test]
    fn test_crc24a_zero_input() {
        let data = vec![0i64; 8];
        let parity = crc_calculate_core(&data, CRC24A_POLY, 24, 0);
        assert_eq!(parity.len(), 24);
        assert!(parity.iter().all(|&x| x == 0));
    }

    #[test]
    fn test_crc24a_attach_and_check() {
        let data: Vec<i64> = vec![1, 0, 1, 1, 0, 0, 1, 0, 1, 1, 0, 1, 0, 0, 1, 1];
        let parity = crc_calculate_core(&data, CRC24A_POLY, 24, 0);
        let mut combined = data;
        combined.extend_from_slice(&parity);
        let check = crc_calculate_core(&combined, CRC24A_POLY, 24, 0);
        assert!(check.iter().all(|&x| x == 0));
    }

    #[test]
    fn test_crc12_attach_and_check() {
        let data: Vec<i64> = vec![1, 1, 0, 1, 0, 1, 0, 0];
        let parity = crc_calculate_core(&data, CRC12_POLY, 12, 0);
        let mut combined = data;
        combined.extend_from_slice(&parity);
        let check = crc_calculate_core(&combined, CRC12_POLY, 12, 0);
        assert!(check.iter().all(|&x| x == 0));
    }

    #[test]
    fn test_crc32_attach_and_check() {
        let data: Vec<i64> = vec![1, 0, 1, 0, 1, 1, 0, 0, 1, 1, 0, 1, 0, 1, 0, 1];
        let parity = crc_calculate_core(&data, CRC32_POLY, 32, 0);
        let mut combined = data;
        combined.extend_from_slice(&parity);
        let check = crc_calculate_core(&combined, CRC32_POLY, 32, 0);
        assert!(check.iter().all(|&x| x == 0));
    }

    #[test]
    fn test_crc_detect_error() {
        let data: Vec<i64> = vec![1, 0, 1, 1, 0, 0, 1, 0];
        let parity = crc_calculate_core(&data, CRC24A_POLY, 24, 0);
        let mut combined = data;
        combined.extend_from_slice(&parity);
        combined[3] ^= 1;
        let check = crc_calculate_core(&combined, CRC24A_POLY, 24, 0);
        assert!(!check.iter().all(|&x| x == 0));
    }

    #[test]
    fn test_crc_deterministic() {
        let data: Vec<i64> = vec![0, 1, 0, 1, 1, 0, 1, 0, 0, 1];
        let p1 = crc_calculate_core(&data, CRC24A_POLY, 24, 0);
        let p2 = crc_calculate_core(&data, CRC24A_POLY, 24, 0);
        assert_eq!(p1, p2);
    }

    #[test]
    fn test_crc_with_seed() {
        let data: Vec<i64> = vec![1, 0, 1, 0];
        let p0 = crc_calculate_core(&data, CRC24A_POLY, 24, 0);
        let p1 = crc_calculate_core(&data, CRC24A_POLY, 24, 0xABCDEF);
        assert_ne!(p0, p1);
    }

    // --- m 序列测试 ---

    #[test]
    fn test_m31_length() {
        let seq = m_sequence_core(5, 0b100101, 0b00001, 31);
        assert_eq!(seq.len(), 31);
    }

    #[test]
    fn test_m63_length() {
        let seq = m_sequence_core(6, 0b1000011, 0b000001, 63);
        assert_eq!(seq.len(), 63);
    }

    #[test]
    fn test_m_sequence_binary_values() {
        let seq = m_sequence_core(5, 0b100101, 0b00001, 31);
        assert!(seq.iter().all(|&x| x == 0 || x == 1));
    }

    #[test]
    fn test_m31_balance_property() {
        let seq = m_sequence_core(5, 0b100101, 0b00001, 31);
        let ones: i64 = seq.iter().sum();
        let zeros = 31 - ones;
        assert_eq!(ones - zeros, 1);
    }

    #[test]
    fn test_m63_balance_property() {
        let seq = m_sequence_core(6, 0b1000011, 0b000001, 63);
        let ones: i64 = seq.iter().sum();
        let zeros = 63 - ones;
        assert_eq!(ones - zeros, 1);
    }

    #[test]
    fn test_m_sequence_periodicity() {
        let period = 31;
        let seq = m_sequence_core(5, 0b100101, 0b00001, period * 2);
        assert_eq!(seq[..period], seq[period..]);
    }

    #[test]
    fn test_m31_autocorrelation() {
        let seq = m_sequence_core(5, 0b100101, 0b00001, 31);
        let bipolar: Vec<f64> = seq.iter().map(|&x| 1.0 - 2.0 * x as f64).collect();
        let r0: f64 = bipolar.iter().map(|x| x * x).sum();
        assert!((r0 - 31.0).abs() < 1e-10);
        for tau in 1..31 {
            let r: f64 = (0..31).map(|i| bipolar[i] * bipolar[(i + tau) % 31]).sum();
            assert!((r + 1.0).abs() < 1e-10, "tau={tau}, r={r}");
        }
    }

    // --- Polar 编码测试 ---

    #[test]
    fn test_polar_encode_trivial() {
        let info = vec![1i8];
        let encoded = polar_encode_core(&info, 2, &[1]);
        assert_eq!(encoded, vec![1, 1]);
    }

    #[test]
    fn test_polar_encode_n4() {
        let info = vec![1i8, 0];
        let encoded = polar_encode_core(&info, 4, &[2, 3]);
        assert_eq!(encoded, vec![1, 0, 1, 0]);
    }

    #[test]
    fn test_polar_encode_all_zero() {
        let info = vec![0i8; 4];
        let encoded = polar_encode_core(&info, 8, &[4, 5, 6, 7]);
        assert!(encoded.iter().all(|&x| x == 0));
    }

    // --- SC 解码器测试 ---

    #[test]
    fn test_sc_decoder_basic() {
        let is_frozen = vec![true, true, false, false];
        let info_positions = vec![2usize, 3];
        let mut decoder = ScDecoder::new(2, &is_frozen, &info_positions);
        let encoded = polar_encode_core(&[1i8, 0], 4, &[2, 3]);
        let llr: Vec<f64> = encoded
            .iter()
            .map(|&x| if x == 0 { 5.0 } else { -5.0 })
            .collect();
        let decoded = decoder.decode(&llr);
        assert_eq!(decoded, vec![1, 0]);
    }

    #[test]
    fn test_sc_decoder_all_frozen() {
        let is_frozen = vec![true; 4];
        let info_positions: Vec<usize> = vec![];
        let mut decoder = ScDecoder::new(2, &is_frozen, &info_positions);
        let llr = vec![1.0, -1.0, 2.0, -2.0];
        let decoded = decoder.decode(&llr);
        assert!(decoded.is_empty());
    }

    #[test]
    fn test_sc_decoder_roundtrip() {
        let info_positions = vec![4usize, 5, 6, 7];
        let mut is_frozen = vec![true; 8];
        for &p in &info_positions {
            is_frozen[p] = false;
        }
        let info = vec![1i8, 0, 1, 1];
        let encoded = polar_encode_core(&info, 8, &info_positions);
        let llr: Vec<f64> = encoded
            .iter()
            .map(|&x| if x == 0 { 10.0 } else { -10.0 })
            .collect();
        let mut decoder = ScDecoder::new(3, &is_frozen, &info_positions);
        let decoded = decoder.decode(&llr);
        assert_eq!(decoded, info);
    }
}
