"""安全子系统补充测试 -- TXS-10002-2025 标准 9.3.2 / 9.3.3 / 9.5

覆盖:
  9.3.3 安全信息分发信令 (GNodeIRK / TNodeIRK / GNodeAddress / TNodeAddress)
  9.3.2 组播安全信令 (MulticastAlgorithmConfig / MulticastKeyConfig)
  9.5   超宽带脉冲测量安全 (密钥派生 / TGap / CTS 符号)
"""

from __future__ import annotations

import os

import pytest

from nearlink_sdr.mac.security import (
    AddrType,
    GNodeAddress,
    GNodeIRK,
    MulticastAlgorithmConfig,
    MulticastKeyConfig,
    ResolutionAlgorithm,
    TNodeAddress,
    TNodeIRK,
)
from nearlink_sdr.phy.uwb_measurement_security import (
    LABEL_CTS_GAP_K,
    LABEL_CTS_INIT_C,
    LABEL_CTS_K,
    LABEL_CTS_V,
    LABEL_SLP,
    CTSKeys,
    CTSSymbolResult,
    EncryptionAlgo,
    UWBMeasInputContext,
    _build_kdf_message,
    advance_cts_v_counter,
    compute_tgap,
    derive_cts_keys,
    derive_slp_key,
    generate_cts_symbols,
    update_cts_keys,
)

# ═══════════════════════════════════════════════════════════════════════════
# 9.3.3 安全信息分发
# ═══════════════════════════════════════════════════════════════════════════


class TestResolutionAlgorithm:
    def test_values(self):
        assert ResolutionAlgorithm.HMAC_SM3 == 0x01
        assert ResolutionAlgorithm.AES_CMAC_128 == 0x02


class TestAddrType:
    def test_values(self):
        assert AddrType.UNION_ALLOCATED == 0x00
        assert AddrType.THIRD_PARTY_LOCAL == 0x02
        assert AddrType.UNION_RESERVED == 0x05
        assert AddrType.PRIVATE == 0x06


class TestGNodeIRK:
    def test_roundtrip(self):
        irk = os.urandom(16)
        msg = GNodeIRK(
            resolution_algorithm=ResolutionAlgorithm.AES_CMAC_128,
            irk=irk,
            irk_id=0x03,
        )
        data = msg.pack()
        assert len(data) == 18
        got = GNodeIRK.unpack(data)
        assert got.resolution_algorithm == ResolutionAlgorithm.AES_CMAC_128
        assert got.irk == irk
        assert got.irk_id == 0x03

    def test_data_type_index(self):
        assert GNodeIRK.DATA_TYPE_INDEX == 0x0143

    def test_pack_bad_irk_length(self):
        with pytest.raises(ValueError, match="IRK"):
            GNodeIRK(0x01, b"\x00" * 15, 0x00).pack()

    def test_unpack_short(self):
        with pytest.raises(ValueError, match="数据不足"):
            GNodeIRK.unpack(b"\x00" * 17)


class TestTNodeIRK:
    def test_roundtrip(self):
        irk = os.urandom(16)
        msg = TNodeIRK(
            resolution_algorithm=ResolutionAlgorithm.HMAC_SM3,
            irk=irk,
            irk_id=0x07,
        )
        data = msg.pack()
        assert len(data) == 18
        got = TNodeIRK.unpack(data)
        assert got.resolution_algorithm == ResolutionAlgorithm.HMAC_SM3
        assert got.irk == irk
        assert got.irk_id == 0x07

    def test_data_type_index(self):
        assert TNodeIRK.DATA_TYPE_INDEX == 0x0144

    def test_pack_bad_irk_length(self):
        with pytest.raises(ValueError, match="IRK"):
            TNodeIRK(0x02, b"\x00" * 17, 0x00).pack()

    def test_unpack_short(self):
        with pytest.raises(ValueError, match="数据不足"):
            TNodeIRK.unpack(b"\x00" * 17)


class TestGNodeAddress:
    def test_roundtrip(self):
        addr = os.urandom(6)
        msg = GNodeAddress(addr_type=AddrType.PRIVATE, addr=addr)
        data = msg.pack()
        assert len(data) == 7
        got = GNodeAddress.unpack(data)
        assert got.addr_type == AddrType.PRIVATE
        assert got.addr == addr

    def test_data_type_index(self):
        assert GNodeAddress.DATA_TYPE_INDEX == 0x0145

    def test_pack_bad_addr_length(self):
        with pytest.raises(ValueError, match="地址"):
            GNodeAddress(0x00, b"\x00" * 5).pack()

    def test_unpack_short(self):
        with pytest.raises(ValueError, match="数据不足"):
            GNodeAddress.unpack(b"\x00" * 6)


class TestTNodeAddress:
    def test_roundtrip(self):
        addr = os.urandom(6)
        msg = TNodeAddress(addr_type=AddrType.UNION_ALLOCATED, addr=addr)
        data = msg.pack()
        assert len(data) == 7
        got = TNodeAddress.unpack(data)
        assert got.addr_type == AddrType.UNION_ALLOCATED
        assert got.addr == addr

    def test_data_type_index(self):
        assert TNodeAddress.DATA_TYPE_INDEX == 0x0146

    def test_pack_bad_addr_length(self):
        with pytest.raises(ValueError, match="地址"):
            TNodeAddress(0x00, b"\x00" * 7).pack()

    def test_unpack_short(self):
        with pytest.raises(ValueError, match="数据不足"):
            TNodeAddress.unpack(b"\x00" * 6)


# ═══════════════════════════════════════════════════════════════════════════
# 9.3.2 组播安全
# ═══════════════════════════════════════════════════════════════════════════


class TestMulticastAlgorithmConfig:
    def test_roundtrip(self):
        rand = os.urandom(16)
        msg = MulticastAlgorithmConfig(
            rand=rand, kdf_type=0x00, encryption_algo=0x02, integrity_algo=0x01,
        )
        data = msg.pack()
        assert len(data) == 19
        got = MulticastAlgorithmConfig.unpack(data)
        assert got.rand == rand
        assert got.kdf_type == 0x00
        assert got.encryption_algo == 0x02
        assert got.integrity_algo == 0x01

    def test_data_type_index(self):
        assert MulticastAlgorithmConfig.DATA_TYPE_INDEX == 0x0148

    def test_pack_bad_rand_length(self):
        with pytest.raises(ValueError, match="RAND"):
            MulticastAlgorithmConfig(b"\x00" * 15, 0, 0, 0).pack()

    def test_unpack_short(self):
        with pytest.raises(ValueError, match="数据不足"):
            MulticastAlgorithmConfig.unpack(b"\x00" * 18)


class TestMulticastKeyConfig:
    def test_roundtrip(self):
        c = os.urandom(16)
        msg = MulticastKeyConfig(c=c)
        data = msg.pack()
        assert len(data) == 16
        got = MulticastKeyConfig.unpack(data)
        assert got.c == c

    def test_data_type_index(self):
        assert MulticastKeyConfig.DATA_TYPE_INDEX == 0x0149

    def test_pack_bad_c_length(self):
        with pytest.raises(ValueError, match="C"):
            MulticastKeyConfig(b"\x00" * 15).pack()

    def test_unpack_short(self):
        with pytest.raises(ValueError, match="数据不足"):
            MulticastKeyConfig.unpack(b"\x00" * 15)


# ═══════════════════════════════════════════════════════════════════════════
# 9.5 超宽带脉冲测量安全
# ═══════════════════════════════════════════════════════════════════════════


class TestLabels:
    """验证 Label 常量长度和编码 (标准表 70)。"""

    def test_label_lengths(self):
        for label in [LABEL_SLP, LABEL_CTS_INIT_C, LABEL_CTS_K,
                      LABEL_CTS_GAP_K, LABEL_CTS_V]:
            assert len(label) == 8

    def test_slp_contains_ascii(self):
        # "SLP" = 0x534C50
        assert b"SLP" in LABEL_SLP

    def test_cts_init_c_contains_ascii(self):
        assert LABEL_CTS_INIT_C == b"ctsInitC"

    def test_cts_k_contains_ascii(self):
        assert b"ctsK" in LABEL_CTS_K

    def test_cts_gap_k_contains_ascii(self):
        assert b"ctsGapK" in LABEL_CTS_GAP_K

    def test_cts_v_contains_ascii(self):
        assert b"ctsV" in LABEL_CTS_V


class TestBuildKdfMessage:
    def test_length(self):
        msg = _build_kdf_message(b"\x00" * 8, b"\x00" * 16)
        assert len(msg) == 32  # 256 bit

    def test_structure(self):
        label = b"\x01\x02\x03\x04\x05\x06\x07\x08"
        context = os.urandom(16)
        msg = _build_kdf_message(label, context)
        assert msg[:8] == b"\x00" * 8       # 预留字段
        assert msg[8:16] == label
        assert msg[16:32] == context

    def test_bad_label_length(self):
        with pytest.raises(ValueError, match="Label"):
            _build_kdf_message(b"\x00" * 7, b"\x00" * 16)

    def test_bad_context_length(self):
        with pytest.raises(ValueError, match="Context"):
            _build_kdf_message(b"\x00" * 8, b"\x00" * 15)


class TestUWBMeasInputContext:
    def test_pack_length(self):
        ctx = UWBMeasInputContext()
        data = ctx.pack()
        assert len(data) == 16  # 128 bit

    def test_pack_fields(self):
        ctx = UWBMeasInputContext(
            phy_channel=37,
            ranging_method=2,
            ranging_mode=1,
            code_len_duty=0x0C,
            symbol_index=5,
            nmss=1024,
            g_node_l2id=b"\x01\x02\x03\x04\x05\x06",
            meas_signal_config_index=10,
            tx_antenna_first=2,
            rx_antenna_first=3,
            tx_antenna_second=1,
            rx_antenna_second=4,
        )
        data = ctx.pack()
        assert data[0] == 37  # phy_channel
        # 字节 1: ranging_method(2) | ranging_mode(2) | code_len_duty(4)
        expected_byte1 = 2 | (1 << 2) | (0x0C << 4)
        assert data[1] == expected_byte1
        assert data[2] == 5   # symbol_index
        assert data[14] == 2 | (3 << 4)  # tx/rx antenna first
        assert data[15] == 1 | (4 << 4)  # tx/rx antenna second

    def test_default_ranging_method(self):
        """默认 ranging_method=1, 其余为 0。"""
        ctx = UWBMeasInputContext()
        data = ctx.pack()
        assert data[0] == 0       # phy_channel
        assert data[1] == 0x01    # ranging_method=1, mode=0, code_len_duty=0
        assert data[2:] == b"\x00" * 14


class TestDeriveSLPKey:
    def test_returns_16_bytes(self):
        link_key = os.urandom(16)
        slp = derive_slp_key(link_key)
        assert len(slp) == 16

    def test_deterministic(self):
        link_key = os.urandom(16)
        assert derive_slp_key(link_key) == derive_slp_key(link_key)

    def test_different_keys_different_results(self):
        k1 = os.urandom(16)
        k2 = os.urandom(16)
        assert derive_slp_key(k1) != derive_slp_key(k2)


class TestDeriveCTSKeys:
    def test_full_pipeline(self):
        link_key = os.urandom(16)
        ctx = UWBMeasInputContext(phy_channel=10, nmss=256)
        slp = derive_slp_key(link_key)
        keys = derive_cts_keys(slp, ctx.pack())
        assert isinstance(keys, CTSKeys)
        assert len(keys.cts_key) == 16
        assert len(keys.cts_value) == 16
        assert len(keys.cts_gap) == 16
        assert len(keys.cts_content) == 16

    def test_deterministic(self):
        link_key = os.urandom(16)
        ctx_data = UWBMeasInputContext(phy_channel=5).pack()
        slp = derive_slp_key(link_key)
        k1 = derive_cts_keys(slp, ctx_data)
        k2 = derive_cts_keys(slp, ctx_data)
        assert k1.cts_key == k2.cts_key
        assert k1.cts_value == k2.cts_value
        assert k1.cts_gap == k2.cts_gap

    def test_different_context_different_keys(self):
        link_key = os.urandom(16)
        slp = derive_slp_key(link_key)
        k1 = derive_cts_keys(slp, UWBMeasInputContext(phy_channel=1).pack())
        k2 = derive_cts_keys(slp, UWBMeasInputContext(phy_channel=2).pack())
        assert k1.cts_key != k2.cts_key

    def test_bad_context_length(self):
        with pytest.raises(ValueError, match="inputContext"):
            derive_cts_keys(b"\x00" * 16, b"\x00" * 15)

    def test_cts_content_structure(self):
        """验证 ctsContent = MSB96 || ctsContent32Bit。"""
        link_key = os.urandom(16)
        slp = derive_slp_key(link_key)
        ctx_data = b"\x00" * 16
        keys = derive_cts_keys(slp, ctx_data)
        # ctsContent32Bit 应在 cts_content 的末尾 4 字节 (小端)
        tail_32 = int.from_bytes(keys.cts_content[12:16], "little")
        assert tail_32 == keys.cts_content_32bit


class TestUpdateCTSKeys:
    def test_counter_increment(self):
        link_key = os.urandom(16)
        slp = derive_slp_key(link_key)
        ctx_data = UWBMeasInputContext().pack()
        keys0 = derive_cts_keys(slp, ctx_data)
        keys1 = update_cts_keys(slp, keys0)
        assert keys1.cts_content_32bit == (keys0.cts_content_32bit + 1) & 0xFFFFFFFF

    def test_keys_change_after_update(self):
        link_key = os.urandom(16)
        slp = derive_slp_key(link_key)
        ctx_data = UWBMeasInputContext(phy_channel=20).pack()
        keys0 = derive_cts_keys(slp, ctx_data)
        keys1 = update_cts_keys(slp, keys0)
        assert keys1.cts_key != keys0.cts_key

    def test_msb96_preserved(self):
        """递增只影响低 32 位, 高 96 位不变。"""
        link_key = os.urandom(16)
        slp = derive_slp_key(link_key)
        keys0 = derive_cts_keys(slp, UWBMeasInputContext().pack())
        keys1 = update_cts_keys(slp, keys0)
        assert keys1.cts_content[:12] == keys0.cts_content[:12]

    def test_counter_wraps(self):
        link_key = os.urandom(16)
        slp = derive_slp_key(link_key)
        keys0 = derive_cts_keys(slp, UWBMeasInputContext().pack())
        # 人为设置 counter 到最大值
        keys0.cts_content_32bit = 0xFFFFFFFF
        keys0.cts_content = keys0.cts_content[:12] + (0xFFFFFFFF).to_bytes(4, "little")
        keys1 = update_cts_keys(slp, keys0)
        assert keys1.cts_content_32bit == 0


class TestComputeTGap:
    def test_basic(self):
        # 已知输入, 手动计算验证
        cts_gap = b"\xFF" * 16  # 全 1, 任何移位后截取 10 bit => 0x3FF
        t_base = 5000
        code_len = 4
        delta_l = 10
        # raw_10bit = 0x3FF, high_2=3, low_8=0xFF=255
        # t_offset = 3*4*10 + 255 = 120 + 255 = 375
        result = compute_tgap(cts_gap, 0, t_base, code_len, delta_l)
        assert result == 5000 - 375

    def test_zero_gap(self):
        cts_gap = b"\x00" * 16  # 全 0
        result = compute_tgap(cts_gap, 0, 1000, 4, 10)
        # raw_10bit = 0, t_offset = 0
        assert result == 1000

    def test_shift(self):
        # 0x03 在低字节, 即 int 值为 3
        cts_gap = bytes([0x03]) + b"\x00" * 15
        # shift=0: raw_10bit = 0x003 = 3, high_2=0, low_8=3, offset=3
        t0 = compute_tgap(cts_gap, 0, 1000, 4, 10)
        assert t0 == 1000 - 3
        # shift=1: int >> 1 => 1, raw_10bit = 1, offset=1
        t1 = compute_tgap(cts_gap, 1, 1000, 4, 10)
        assert t1 == 1000 - 1

    def test_tgap_sequence_varies(self):
        """连续帧的 TGap 随 shift 变化。"""
        cts_gap = os.urandom(16)
        results = [
            compute_tgap(cts_gap, shift, 10000, 4, 5)
            for shift in range(10)
        ]
        # 不同 shift 不太可能全部相同
        assert len(set(results)) > 1


class TestCTSSymbolGeneration:
    def test_returns_correct_count(self):
        key = os.urandom(16)
        upper = os.urandom(12)
        result = generate_cts_symbols(key, upper, 0, n_cts=8)
        assert len(result.symbol_indices) == 8
        assert len(result.sc_values) == 8

    def test_sc_values_valid(self):
        """SC 只能是 +1 或 -1。"""
        key = os.urandom(16)
        upper = os.urandom(12)
        result = generate_cts_symbols(key, upper, 0, n_cts=32)
        for sc in result.sc_values:
            assert sc in (1, -1)

    def test_symbol_indices_in_range_32(self):
        """32 符号模式下索引范围 [0, 31]。"""
        key = os.urandom(16)
        upper = os.urandom(12)
        result = generate_cts_symbols(key, upper, 0, n_cts=64, symbol_count=32)
        for idx in result.symbol_indices:
            assert 0 <= idx <= 31

    def test_symbol_indices_in_range_16(self):
        """16 符号模式下索引范围 [0, 15]。"""
        key = os.urandom(16)
        upper = os.urandom(12)
        result = generate_cts_symbols(key, upper, 0, n_cts=32, symbol_count=16)
        for idx in result.symbol_indices:
            assert 0 <= idx <= 15

    def test_deterministic(self):
        key = os.urandom(16)
        upper = os.urandom(12)
        r1 = generate_cts_symbols(key, upper, 100, n_cts=16)
        r2 = generate_cts_symbols(key, upper, 100, n_cts=16)
        assert r1.symbol_indices == r2.symbol_indices
        assert r1.sc_values == r2.sc_values

    def test_different_counter_different_result(self):
        key = os.urandom(16)
        upper = os.urandom(12)
        r1 = generate_cts_symbols(key, upper, 0, n_cts=16)
        r2 = generate_cts_symbols(key, upper, 1, n_cts=16)
        # 极大概率不同
        assert r1.symbol_indices != r2.symbol_indices or r1.sc_values != r2.sc_values

    def test_default_aes128(self):
        """默认使用 AES-128 加密。"""
        key = os.urandom(16)
        upper = os.urandom(12)
        result = generate_cts_symbols(
            key, upper, 0, n_cts=4, encryption_algo=EncryptionAlgo.AES_128,
        )
        assert isinstance(result, CTSSymbolResult)


class TestAdvanceCTSVCounter:
    def test_advance(self):
        assert advance_cts_v_counter(0, 16) == 1
        assert advance_cts_v_counter(0, 32) == 2
        assert advance_cts_v_counter(0, 64) == 4

    def test_wrap(self):
        assert advance_cts_v_counter(0xFFFFFFFF, 16) == 0

    def test_minimum_one(self):
        # n_cts < 16 时 n = max(0, 1) = 1
        assert advance_cts_v_counter(10, 8) == 11


class TestEndToEndPipeline:
    """端到端测试: 从 Link Key 到 CTS 符号生成。"""

    def test_full_flow(self):
        link_key = os.urandom(16)
        ctx = UWBMeasInputContext(
            phy_channel=10,
            ranging_method=1,
            nmss=64,
            g_node_l2id=b"\xAA\xBB\xCC\xDD\xEE\xFF",
        )

        # 1. 派生 SLPKey
        slp = derive_slp_key(link_key)

        # 2. 派生 CTS 密钥组
        keys = derive_cts_keys(slp, ctx.pack())
        assert keys.cts_key != keys.cts_value  # 不同 Label 应产生不同密钥

        # 3. 生成 TGap
        tgap = compute_tgap(keys.cts_gap, 0, 8000, 4, 5)
        assert 0 < tgap <= 8000

        # 4. 生成 CTS 符号
        symbols = generate_cts_symbols(
            keys.cts_key,
            keys.cts_value[:12],
            keys.cts_content_32bit,
            n_cts=16,
        )
        assert len(symbols.symbol_indices) == 16

        # 5. 更新密钥 (下一帧)
        keys_next = update_cts_keys(slp, keys)
        assert keys_next.cts_key != keys.cts_key

        # 6. 推进 counter
        new_counter = advance_cts_v_counter(keys.cts_content_32bit, 16)
        assert new_counter == (keys.cts_content_32bit + 1) & 0xFFFFFFFF
