# 物理层原理

本节阐述 SparkLink SLE 物理层中关键信号处理模块的数学原理。

## Polar 编码

### 信道极化

Polar 码基于信道极化现象: 对 $N$ 个独立信道实例做线性变换后, 各子信道的可靠性出现分化 --- 部分子信道的容量趋近 1, 其余趋近 0。Arikan 证明当 $N \to \infty$ 时, 这种分化是完全的。

核心变换矩阵为 Kronecker 幂:

$$
G_N = B_N \cdot F^{\otimes n}, \quad F = \begin{bmatrix} 1 & 0 \\ 1 & 1 \end{bmatrix}, \quad N = 2^n
$$

其中 $B_N$ 为比特翻转置换矩阵。编码过程:

$$
x = u \cdot G_N
$$

其中 $u$ 的冻结位 (低可靠性子信道) 设为 0, 信息位放在高可靠性子信道上。

### 可靠性序列

SparkLink SLE 标准 6.9.1.4 节定义了固定的可靠性排序表, 给出每个子信道的可靠性排名。编码器根据码率 $R = K/N$ 选取最可靠的 $K$ 个位置放置信息比特, 其余位置填充已知冻结位。

### SC 解码

逐次消除 (Successive Cancellation) 解码器按自然序逐位判决。对第 $i$ 位:

- 若 $i$ 是冻结位, 直接判为 0。
- 若 $i$ 是信息位, 按 LLR 符号做硬判决: $\hat{u}_i = \begin{cases} 0, & L_i \geq 0 \\ 1, & L_i < 0 \end{cases}$。

LLR 递归计算依赖两个基本运算:

$$
f(a, b) = 2 \tanh^{-1}\!\bigl(\tanh(a/2) \cdot \tanh(b/2)\bigr) \approx \operatorname{sign}(a) \cdot \operatorname{sign}(b) \cdot \min(|a|, |b|)
$$

$$
g(a, b, s) = (-1)^s \cdot a + b
$$

其中 $a, b$ 是来自子节点的 LLR, $s$ 是已判决的上层比特。

## PSK 调制

### 星座映射

SparkLink SLE 支持 BPSK, QPSK 和 8PSK 三种调制方式, 星座点定义为:

$$
s_k = e^{j 2\pi k / M}, \quad k = 0, 1, \ldots, M-1
$$

其中 $M \in \{2, 4, 8\}$。比特到符号的映射采用格雷编码, 相邻星座点仅差 1 bit, 降低高信噪比下的比特错误率。

### RRC 脉冲成型

根升余弦 (Root Raised Cosine) 滤波器的频域响应为:

$$
H(f) = \begin{cases}
1, & |f| \leq \frac{1-\alpha}{2T} \\
\cos\!\left(\frac{\pi T}{2\alpha}\left(|f| - \frac{1-\alpha}{2T}\right)\right), & \frac{1-\alpha}{2T} < |f| \leq \frac{1+\alpha}{2T} \\
0, & \text{otherwise}
\end{cases}
$$

其中 $\alpha$ 为滚降系数, $T$ 为符号周期。收发两端各用一个 RRC 滤波器, 级联后等效为升余弦滤波器, 满足 Nyquist 无码间干扰准则。标准规定 $\alpha = 0.5$, 每符号采样数 $L = 4$。

## GFSK 调制

高斯频移键控的瞬时频率偏移为:

$$
f(t) = h \cdot \sum_k a_k \cdot g(t - kT)
$$

其中 $h$ 为调制指数, $a_k \in \{-1, +1\}$ 为数据符号, $g(t)$ 为高斯脉冲 (带宽时间积 $BT$):

$$
g(t) = \frac{1}{2T}\left[\operatorname{erf}\!\left(\frac{\pi}{\sqrt{\ln 2}} \cdot BT \cdot \frac{t + T/2}{T}\right) - \operatorname{erf}\!\left(\frac{\pi}{\sqrt{\ln 2}} \cdot BT \cdot \frac{t - T/2}{T}\right)\right]
$$

SparkLink SLE 标准规定调制指数 $h = 0.5$ (最小频移), $BT = 0.5$。

## 信道模型

### AWGN

加性高斯白噪声信道:

$$
y = x + n, \quad n \sim \mathcal{CN}(0, \sigma^2)
$$

噪声方差与信噪比的关系: $\sigma^2 = P_s / \text{SNR}_{\text{linear}}$, 其中 $P_s$ 为信号平均功率。

### Rayleigh 衰落

平坦 Rayleigh 衰落模型 (无直射路径):

$$
y = h \cdot x + n, \quad h \sim \mathcal{CN}(0, 1)
$$

$|h|$ 服从 Rayleigh 分布。在准静态模型中, 整个帧使用同一个衰落系数。

### Rician 衰落

含直射路径的衰落模型, K 因子定义为直射功率与散射功率之比:

$$
h = \sqrt{\frac{K}{K+1}} + \sqrt{\frac{1}{K+1}} \cdot h_{\text{scatter}}, \quad h_{\text{scatter}} \sim \mathcal{CN}(0, 1)
$$

$K$ 越大表示直射路径越强, $K \to \infty$ 退化为 AWGN, $K = 0$ 退化为 Rayleigh。

### 多径频率选择性

多径信道用有限长 FIR 模型描述:

$$
y(t) = \sum_{l=0}^{L-1} h_l(t) \cdot x(t - \tau_l) + n(t)
$$

其中 $\{h_l, \tau_l\}$ 由功率延迟谱 (PDP) 决定。频率选择性衰落会导致码间干扰, 需要均衡器恢复。

## 均衡器

### ZF 均衡

迫零均衡在频域直接求逆:

$$
\hat{X}(k) = \frac{Y(k)}{H(k)}
$$

优点是完全消除 ISI, 缺点是在信道零点处放大噪声。

### MMSE 均衡

最小均方误差准则在消除 ISI 和抑制噪声之间取平衡:

$$
\hat{X}(k) = \frac{H^*(k)}{|H(k)|^2 + \sigma_n^2 / \sigma_x^2} \cdot Y(k)
$$

当 SNR 较高时趋近 ZF; SNR 较低时自动减小增益, 避免噪声放大。

### 1-tap 均衡

对平坦衰落信道, 信道系数为标量 $h$, MMSE 均衡退化为单抽头:

$$
\hat{x} = \frac{h^*}{|h|^2 + \sigma^2} \cdot y
$$

## CRC 校验

循环冗余校验通过多项式除法检测传输错误。SparkLink SLE 定义了四种 CRC:

| 类型 | 长度 | 生成多项式 | 用途 |
|------|------|-----------|------|
| CRC12 | 12 bit | $x^{12} + x^{11} + x^3 + x^2 + x + 1$ | FT1/FT2 头部 |
| CRC24A | 24 bit | $x^{24} + x^{23} + x^6 + x^5 + x + 1$ | 数据载荷 |
| CRC24B | 24 bit | $x^{24} + x^{23} + x^{14} + x^{12} + x^{8} + 1$ | FT3/FT4 头部 |
| CRC32 | 32 bit | ITU-T CRC-32 | MAC 层 |

CRC24B 在 FT3/FT4 中使用种子 $\text{seed} = \texttt{0x555555} \oplus \text{LLID}$, 提供与链路标识绑定的完整性保护。

## 码块分割

当数据长度超过单个 Polar 码块容量时, 需要分割为多个码块:

- **segment_without_crc** (FT2): 按 Polar 码块大小 $N$ 和信息位数 $K$ 将数据切分, 各段独立编码。
- **segment_with_crc** (FT3/FT4): 每个分割段额外附加一个小 CRC, 为每段提供独立的错误检测能力。

分割后每段独立进行 Polar 编码、速率匹配和调制, 接收端逆序处理。

## 加扰

信道比特加扰使用 Galois 线性反馈移位寄存器 (LFSR), 生成伪随机序列与编码比特异或:

$$
c_{\text{scrambled}}(i) = c(i) \oplus s(i)
$$

加扰的目的是打散长连续 0/1 序列, 改善信号的频谱特性和定时恢复性能。解扰时使用相同的初始种子重新生成序列即可恢复原始比特。
