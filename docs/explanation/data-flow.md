# 端到端数据流

本文从应用数据出发, 追踪一个数据包从发送端到接收端经过的完整处理链路, 涵盖 MAC 层封装、信道编码、调制成型、空口传输、接收解调和数据恢复的全过程。

## 全局视图

```text
发送端                                 接收端
┌─────────┐      ┌────────┐      ┌─────────┐
│ 应用数据 │      │  空口  │      │ 应用数据 │
│         │      │        │      │         │
│ QoS管理 │      │ 无线   │      │ QoS管理 │
│ MAC封帧 │ ──→  │ 信道   │ ──→  │ MAC解帧 │
│ 信道编码│      │        │      │ 信道解码│
│ 调制成型│      │        │      │ 解调滤波│
└─────────┘      └────────┘      └─────────┘
```

## 发射流水线

### 第一步: QoS 决策

`SleNode.transmit()` 首先调用 `QosManager.prepare_tx()`, 从优先级队列中取出待发送数据:

- 五级优先级队列: CONTROL > REALTIME > HIGH > NORMAL > LOW
- 流控检查: 发送窗口是否有信用额度
- HARQ 检查: 是否有需要重传的码块

### 第二步: 帧加密 (可选)

如果链路已开启加密, 调用 `FrameCryptoContext.encrypt()`:

1. 计算 IV: `compute_iv(iv_base, sync_or_link_id, frame_type)`
2. 构建 CCM nonce: `build_ccm_nonce_async(flag, payload_count, direction, iv, data_len)`, 取 B0[1:14] 作为 13 字节 nonce
3. AES-CCM 加密: `aes_ccm_encrypt(session_key, nonce, plaintext, aad, mic_len)` → 密文 + MIC
4. payload_count 递增

### 第三步: MAC 封帧

数据被封装为 `AsyncDataFrame`:

```text
┌────────────┬─────────────┬──────────┬──────────┐
│ 分段标志   │ 数据长度    │  保留    │  载荷    │
│  2 bit     │  11 bit     │  3 bit   │  N 字节  │
└────────────┴─────────────┴──────────┴──────────┘
```

如果数据超过最大 PDU 长度, 按 FIRST / MIDDLE / LAST 分段。

### 第四步: 信道编码 (`tx_chain`)

`mac_to_iq()` 将 MAC 字节转换为比特流, 构建控制信息, 然后调用 `tx_chain()`:

#### 头部编码 (`encode_head`)

控制信息比特 (28 或 44 位) 经过:

1. **Polar 编码**: 按可靠性序列选择信息位位置, 冻结位填零, 蝶形运算生成码字
2. **加扰**: 7 位 Galois LFSR ($x^7 + x^4 + 1$), 异或每个比特

#### 载荷编码 (`encode_payload`)

用户数据比特经过:

1. **CRC 附加**: 计算 CRC-24 或 CRC-32, 附加到数据尾部
2. **码块分割**: 当编码后比特数超过 Polar 码最大母码长度时, 将数据拆分为多个码块
3. **Polar 编码**: 每个码块独立 Polar 编码, 按 MCS 指定的码率
4. **加扰**: 与头部使用相同的 LFSR, 异或每个码字比特

### 第五步: 帧组装

编码后的比特按帧结构组装:

```text
┌──────────┬──────────┬──────────┬──────────┬──────────┐
│ 前导码   │ 同步序列 │ 头部     │ 载荷     │ (导频)   │
│ m序列    │ SyncWord │ Polar码字│ Polar码字│ 定期插入 │
└──────────┴──────────┴──────────┴──────────┴──────────┘
```

- **前导码**: m 序列, 不同帧类型使用不同长度 (FT1: 32 bit, FT2: 64 sym, FT3: 62 sym, FT4: 126 sym)
- **同步序列**: 由 PID 生成, 用于帧同步检测
- **导频**: 按 `pilot_interval` 周期性插入已知符号, 用于信道估计

### 第六步: 调制成型

- **FT1 (GFSK)**: 高斯频移键控, BT = 0.5, 直接调制为瞬时频率变化
- **FT2-FT4 (PSK)**: 相移键控 (BPSK/QPSK/8PSK), 先映射星座点, 再经 RRC 脉冲成型滤波 (滚降系数 $\beta = 0.4$)

输出为复数基带 IQ 信号。

### 第七步: 射频发送

- **仿真模式**: IQ 直接进入信道模型
- **USRP 模式**: IQ 通过 `SLETransceiver` 发送到 USRP E310 硬件, 上变频到 2.4 GHz 频段

## 空口传输

### 信道效应

数据经过无线信道时受到:

- **多径衰落**: Rayleigh/Rician 衰落, 多径时延扩展
- **频率偏移**: 本振不匹配导致的载波频偏
- **多普勒扩展**: 相对运动引起的时变信道
- **噪声**: 高斯白噪声 (AWGN)
- **多用户干扰**: 其他设备同频信号干扰

### 跳频

发射和接收两端按相同的跳频序列在 2402-2480 MHz 频段内切换信道, 每个时隙跳到不同频点, 改善频率分集增益并降低窄带干扰影响。

## 接收流水线

### 第一步: 射频接收

- **USRP 模式**: 硬件下变频, ADC 采样得到基带 IQ
- **仿真模式**: 从信道模型输出获取 IQ 信号

### 第二步: 匹配滤波

- **FT1 (GFSK)**: GFSK 解调器直接提取瞬时频率
- **FT2-FT4 (PSK)**: RRC 匹配滤波, 最大化信噪比, 然后降至 1 样本/符号

### 第三步: 帧同步 (`frame_sync`)

滑动互相关检测同步序列:

1. 根据帧类型生成同步参考序列
2. 计算接收信号与参考序列的互相关
3. 峰值超过均值 2 倍时判定同步成功, 返回帧起始位置

### 第四步: 帧结构解析

`symbols_to_data_bits()` 根据帧配置参数拆分各段:

1. 跳过前导码和同步序列
2. 提取头部符号 (固定长度)
3. 提取载荷符号 (长度由头部指示或预知)
4. 移除导频符号

### 第五步: 头部解码 (`decode_head`)

1. **解扰**: 相同的 LFSR 异或恢复原始码字
2. **Polar 解码**: SC (逐次消除) 解码, 恢复控制信息比特
3. **CRC-12 校验**: 验证头部完整性

### 第六步: 载荷解码 (`decode_payload`)

1. **解扰**: LFSR 异或
2. **Polar 解码**: 每个码块独立解码
3. **码块重组**: 多个码块合并为完整数据
4. **CRC 校验**: CRC-24 或 CRC-32 验证数据完整性

### 第七步: MAC 解帧

1. 比特流转换为字节: `bits_to_bytes()`
2. 解析 `AsyncDataFrame`: 提取分段标志和载荷
3. 分段重组: 如有分段, 按序号拼接

### 第八步: 帧解密 (可选)

调用 `FrameCryptoContext.decrypt()`:

1. 用与发送端相同的参数构建 nonce
2. AES-CCM 解密并验证 MIC
3. payload_count 递增
4. MIC 验证失败则丢弃

### 第九步: QoS 反馈

- ARQ: 发送 ACK/NACK
- HARQ: 反馈 TB 或 CBG 粒度的确认
- 流控: 更新信用额度
- 质量跟踪: 更新帧错误率统计, 推荐 MCS

## MAC-PHY 适配层

`phy.mac_interface` 模块是 MAC 和 PHY 之间的桥接:

| 函数 | 方向 | 说明 |
|------|------|------|
| `mac_to_iq()` | TX | MAC 字节 → IQ 信号 |
| `iq_to_mac()` | RX | IQ 信号 → MAC 字节 |
| `signaling_to_iq()` | TX | 信令对象 → IQ |
| `iq_to_signaling()` | RX | IQ → 信令对象 |
| `bytes_to_bits()` | 工具 | 字节 → 比特 (MSB) |
| `bits_to_bytes()` | 工具 | 比特 → 字节 |

## SleNode 集成

`SleNode` 是将所有功能集成到一个实体的节点类:

```text
SleNode
├── TxConfig          发射配置
├── QosManager        QoS 管理 (ARQ/HARQ/流控)
├── LinkManager       链路状态机 (8 状态)
├── FreqTable         跳频表
├── PowerController   功率控制
├── ScheduleManager   时序调度
├── FrameCryptoContext 帧加密上下文
├── ChannelModel      仿真信道 (可选)
└── SLETransceiver    USRP 收发器 (可选)
```

数据流路径:

- **发送**: `send(data)` → 入队 → `transmit()` → QoS → 加密 → MAC → PHY → IQ → 空口
- **接收**: 空口 → IQ → `receive()` → PHY → MAC → 解密 → QoS 反馈 → `on_data_received()`
