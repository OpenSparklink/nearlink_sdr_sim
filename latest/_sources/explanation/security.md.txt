# 安全子系统详解

本文详细解释 SparkLink SLE 安全子系统的设计与实现, 涵盖配对鉴权、密钥派生、帧加密、隐私保护和 UWB 测量安全, 对标 TXS-10002-2025 标准第 9 章。

## 安全架构

SLE 安全子系统分为三层:

- **配对鉴权层**: 建立信任关系, 交换密钥材料 (§9.2)
- **帧加密层**: 保护数据传输的机密性和完整性 (§9.3)
- **隐私保护层**: 防止设备追踪 (§9.4)

安全的基础是 ECDH P-256 密钥协商, 派生出所有后续密钥。

## 配对流程 (§9.2)

配对是两个设备首次建立安全关联的过程。标准定义了 6 种鉴权方法:

| 方法 | 适用场景 |
|------|----------|
| 数值比较 | 双方有显示和输入能力 |
| 密码输入 | 一方有输入能力 |
| 密码校验 | 预共享密码 |
| 带外传输 | NFC 等侧信道 |
| 预共享密钥 | 工厂预置密钥 |
| 无输入 | 无交互能力 (Just Works) |

鉴权方法的选择由双方 IO 能力 (无输入无输出、仅显示、仅键盘、显示+键盘、显示+是否) 协商决定。

### 配对状态机

配对流程由 9 个状态组成:

```text
IDLE → INITIATED → REQUEST_SENT → RESPONSE_SENT
     → CONFIRM_SENT → PUBLIC_KEY_EXCHANGED
     → CONFIRM_CODE_SENT → COMPLETED / FAILED
```

G 节点视角:

1. **IDLE → REQUEST_SENT**: 发送 `PairingRequest`, 携带 IO 能力、密钥长度、安全分发信息、加密能力
2. **REQUEST_SENT → CONFIRM_SENT**: 收到 `PairingResponse`, 发送 `PairingConfirm` (含 G 节点 P-256 公钥 X/Y 坐标, 各 32 字节)
3. **CONFIRM_SENT → PUBLIC_KEY_EXCHANGED**: 收到 `PairingInitialInfo` (T 节点公钥), 计算 ECDH 共享密钥, 发送 Ra 随机数
4. **PUBLIC_KEY_EXCHANGED → CONFIRM_CODE_SENT**: 收到 Rb, 发送 `GNodeConfirmCode`
5. **CONFIRM_CODE_SENT → COMPLETED**: 收到 `TNodeConfirmCode`, 验证确认码, 派生密钥

T 节点视角是上述流程的镜像:

1. **IDLE → INITIATED**: 收到 `PairingInitiate`
2. **INITIATED → RESPONSE_SENT**: 收到 `PairingRequest`, 发送 `PairingResponse`
3. **RESPONSE_SENT → PUBLIC_KEY_EXCHANGED**: 收到 `PairingConfirm`, 保存 G 公钥, 发送自身公钥
4. **PUBLIC_KEY_EXCHANGED → CONFIRM_CODE_SENT**: 收到 Ra, 计算 DH Key, 发送 Rb
5. **CONFIRM_CODE_SENT → COMPLETED**: 收到 `GNodeConfirmCode`, 验证后发送 `TNodeConfirmCode`, 派生密钥

### 失败处理

12 种失败原因:

| 代码 | 原因 |
|------|------|
| 0x01 | 密码输入失败 |
| 0x02 | 带外数据不可用 |
| 0x03 | 鉴权要求不满足 |
| 0x04 | 确认值校验失败 |
| 0x05 | 配对不支持 |
| 0x06 | 密钥长度不足 |
| 0x07 | 命令不支持 |
| 0x08 | 未指定原因 |
| 0x09 | 重复尝试 |
| 0x0A | 参数无效 |
| 0x0B | DH Key 校验失败 |
| 0x0C | 数值比较失败 |

**代码实现**: `mac.security_manager.PairingManager` 实现状态机, `mac.security` 模块定义 20 种配对信令消息类, `mac.security_manager.ECDHKeyPair` 封装 P-256 椭圆曲线运算。

## 密钥派生 (§9.3)

配对完成后, 通过 ECDH 共享密钥逐级派生出各功能密钥:

```text
ECDH P-256 共享密钥 (32 字节)
    │
    ├─► Link Key (16 字节)
    │       KDF(dh_key_low128, "lk" ‖ Ra ‖ Rb ‖ 地址)
    │
    ├─► DH Verify Key
    │       KDF(dh_key_low128, "dk" ‖ Ra ‖ Rb ‖ 地址)
    │       └─► DH 验证码 (16 字节)
    │
    └─► Session Key (16 字节)
            KDF(link_key, G_Diversifier ‖ T_Diversifier)
            └─► 认证加密: SK 同时用于加密和完整性
                分离算法: EnK (加密) + InK (完整性)
```

### KDF 算法

标准支持两种 KDF:

- **AES-CMAC**: 128 位密钥, 输出 128 位 MAC (§9.3.4)
- **HMAC-SM3**: 256 位摘要取低 128 位 (§9.3.4)

双方在配对阶段协商使用哪种 KDF。

### 确认码生成 (§9.3.4.3)

确认码保证远端设备确实持有 DH Key。生成方式取决于鉴权方法:

- **数值比较**: KDF(PKax, PKax ‖ PKbx ‖ Ra ‖ 0)
- **密码输入**: KDF(PKax, PKax ‖ PKbx ‖ Ra ‖ Ri)
- **密码校验**: KDF(PKax, PKax ‖ PKbx ‖ Ra ‖ Pwd)
- **带外/预共享/Just Works**: 类似数值比较

### 数值比较码 (§9.3.4.6)

从 KDF 输出取 4 字节, 对 $10^6$ 取模, 得到 6 位十进制数字, 双方显示给用户比对。

**代码实现**: `mac.crypto` 模块实现全部密钥派生函数:

- `aes_cmac()`, `hmac_sm3()`, `kdf()`
- `derive_link_key()`, `derive_session_key()`, `derive_dh_verify_key()`
- `generate_confirm_code()`, `generate_dh_verify_code()`, `generate_numeric_code()`
- `obfuscate()` 混淆算法 (§9.3.4.7)
- `secure_random_256()` 安全随机函数 (§6.10.7)

## 帧加密 (§9.3.1)

### AES-CCM

SLE 使用 AES-CCM (Counter with CBC-MAC) 进行帧加密, 同时保证机密性和完整性:

- **机密性**: AES-CTR 模式加密载荷
- **完整性**: CBC-MAC 生成 MIC (消息完整性校验码), 长度 4/8/12/16 字节

### Nonce 构建

Nonce 是 AES-CCM 的关键输入, 保证每个帧使用不同的计数器:

**异步/同步单播和组播链路**:

```text
┌───────┬──────────────────┬────────────┬─────────────┬──────────┐
│ Flag  │ payload_count    │ Direction  │     IV      │ data_len │
│ 1B    │ 5B (bit38:0)     │ 1b         │  8B         │ 2B       │
└───────┴──────────────────┴────────────┴─────────────┴──────────┘
```

- `payload_count`: 单调递增计数器 (39 位), 防止 nonce 重用
- `Direction`: 0 = G→T, 1 = T→G
- `IV`: 由 IV 基值和帧参数计算得出

**其他链路** (广播/SMF):

```text
┌───────┬──────────────────┬────────────┬─────────────┬──────────┐
│ Flag  │ slot_seq         │ day_count  │     IV      │ data_len │
│ 1B    │ 4B (bit29:0)     │ 2B(bit9:0) │  8B         │ 2B       │
└───────┴──────────────────┴────────────┴─────────────┴──────────┘
```

### IV 计算 (§9.3.1)

IV 基值 (8 字节) 与不同参数异或:

- **FT1/FT2**: IV = IV_base $\oplus$ 同步序列号
- **FT3/FT4**: IV = IV_base $\oplus$ 链路 ID

**代码实现**: `mac.security_manager.FrameCryptoContext` 管理加解密上下文, 维护 TX/RX payload_count, 调用 `mac.crypto.aes_ccm_encrypt()`/`aes_ccm_decrypt()`。

## 组播安全 (§9.3.2)

组播链路使用独立的密钥体系:

```text
RAND1, RAND2 (各 16 字节随机数)
    │
    └─► 组播密钥 GK = KDF(RAND1, RAND2)
            │
            └─► 组播会话密钥 GSK (16B)
                或 GEnK + GInK (各 16B)
```

分发流程:

1. G 节点生成 RAND 和 KDF/加密/完整性算法参数, 通过 `MulticastAlgorithmConfig` 发送
2. G 节点计算 $K_g$ = KDF(link_key, RAND), 发送 $C$ = $K_g \oplus GK$ 通过 `MulticastKeyConfig`
3. T 节点用自身 link_key 计算 $K_g$, 恢复 $GK$ = $C \oplus K_g$

**代码实现**: `mac.crypto.generate_group_key()`, `derive_group_session_key()`, `derive_kg()`; `mac.security` 模块定义 `MulticastAlgorithmConfig` 和 `MulticastKeyConfig` 信令。

## 隐私保护 (§9.4)

SLE 支持可解析随机地址, 防止第三方追踪设备:

1. 设备生成 IRK (身份解析密钥, 16 字节), 在配对阶段通过 `GNodeIRK`/`TNodeIRK` 交换
2. 设备使用 IRK 和随机数生成可解析地址 (48 位): 高 24 位为 hash(IRK, prand), 低 24 位为 prand
3. 已知 IRK 的设备可以验证和解析该地址, 未知 IRK 的设备无法关联不同地址

地址分发通过 `GNodeAddress`/`TNodeAddress` 信令完成, 携带地址类型 (联盟分配、第三方本地、联盟预留、私有) 和 6 字节地址。

**代码实现**: `mac.crypto.generate_resolvable_address(kdf_type, irk, rand_part)` 和 `resolve_address(kdf_type, irk, addr)`。

## UWB 测量安全 (§9.5)

UWB 脉冲测量信号需要专用的安全机制, 防止距离欺骗攻击。

### CTS 密钥体系

从 Link Key 出发, 派生 UWB 测量专用密钥:

```text
Link Key (16B)
    │
    └─► SLP Key = KDF(link_key, reserved ‖ "SLP" ‖ zeros)
            │
            ├─► ctsInitContent = KDF(SLP, "ctsInitC" ‖ inputContext)
            │       └─► ctsContent32Bit = ctsInitContent 低 32 位
            │
            ├─► ctsKey   = KDF(SLP, "ctsK"    ‖ ctsContent)
            ├─► ctsValue = KDF(SLP, "ctsV"    ‖ ctsContent)
            └─► ctsGap   = KDF(SLP, "ctsGapK" ‖ ctsContent)
```

### inputContext (§9.5, 表 71)

128 位上下文参数, 编码测量会话的物理层配置:

- 物理信道号
- 测距方法和模式
- NMSS 采样数
- G 节点 L2 ID
- 天线配置
- 其他保留位

### 密钥更新

每次测量会话结束后, `ctsContent32Bit` 递增, 重新派生三个密钥。这确保每次测量使用不同的加扰序列。

### TGap 计算 (§9.5.4)

TGap 控制 CTS 符号间的时间间隔, 从 `ctsGap` 的 128 位值中按偏移截取 10 位:

$$T_{gap} = T_{base} - T_{offset}$$

其中 $T_{offset}$ 由 ctsGap 对应位计算。

### CTS 符号生成 (§9.5.5)

CTS 符号序列用于 UWB 测量帧的时域加扰:

1. 对每个符号, 用 ctsKey 进行 ECB 加密生成加扰块
2. 提取符号索引和 SC 值 (+1 或 -1)
3. ctsVCounter 逐符号递增

**代码实现**: `phy.uwb_measurement_security` 模块:

- `UWBMeasInputContext`: 128 位上下文编码
- `CTSKeys`: 密钥组容器
- `derive_slp_key()`, `derive_cts_keys()`, `update_cts_keys()`
- `compute_tgap()`: TGap 时间间隔计算
- `generate_cts_symbols()`: CTS 符号序列生成
