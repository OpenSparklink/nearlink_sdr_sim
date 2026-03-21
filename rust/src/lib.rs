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
        for i in 0..self.big_n {
            self.l_buf[[0, i]] = llr[i];
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
                self.b_buf[[self.n, start]] =
                    if self.l_buf[[depth, start]] >= 0.0 { 0 } else { 1 };
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

/// 模块入口
#[pymodule]
fn nearlink_sdr_accel(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<RustPolarDecoder>()?;
    Ok(())
}
