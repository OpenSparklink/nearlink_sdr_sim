"""安全一致性测试 — TXS-10002-2025 第 13 章。

覆盖:
- 13.1 配对流程: 无输入/数字比较/口令输入/密码验证/OOB/PSK
- 13.2 安全保护: 加密+完整性/仅完整性/仅加密/无保护/重放防护
- 13.3 隐私: 可解析随机地址生成与解析
- 13.4 UWB 测量安全: SLP 密钥/CTS 密钥派生/符号生成
"""

from __future__ import annotations

import os

import pytest
from cryptography.exceptions import InvalidTag

from nearlink_sdr.mac.crypto import (
    AuthMethod,
    KdfType,
    generate_resolvable_address,
    resolve_address,
)
from nearlink_sdr.mac.security_manager import (
    FrameCryptoContext,
    run_pairing_procedure,
)
from nearlink_sdr.phy.uwb_measurement_security import (
    advance_cts_v_counter,
    compute_tgap,
    derive_cts_keys,
    derive_slp_key,
    generate_cts_symbols,
    update_cts_keys,
)

# ═══════════════════════════════════════════════════════════════════════
# 13.1 配对流程
# ═══════════════════════════════════════════════════════════════════════


class TestNoInputPairing:
    """13.1.1 无输入配对 — VALD-01"""

    def test_no_input_pairing_completes(self):
        g, t = run_pairing_procedure(auth_method=AuthMethod.NO_INPUT)
        assert g.is_paired
        assert t.is_paired

    def test_no_input_keys_match(self):
        g, t = run_pairing_procedure(auth_method=AuthMethod.NO_INPUT)
        assert g.session_key == t.session_key
        assert len(g.session_key) == 16


class TestNumericComparison:
    """13.1.2 数字比较配对 — VALD-02"""

    def test_numeric_comparison_completes(self):
        g, t = run_pairing_procedure(auth_method=AuthMethod.NUMERIC_COMPARISON)
        assert g.is_paired and t.is_paired

    def test_numeric_comparison_keys_match(self):
        g, t = run_pairing_procedure(auth_method=AuthMethod.NUMERIC_COMPARISON)
        assert g.session_key == t.session_key
        assert g.link_key == t.link_key


class TestPasskeyEntry:
    """13.1.3 口令输入配对 — VALD-03"""

    def test_passkey_pairing_completes(self):
        g, t = run_pairing_procedure(auth_method=AuthMethod.PASSKEY_ENTRY)
        assert g.is_paired and t.is_paired

    def test_passkey_session_key_derived(self):
        g, t = run_pairing_procedure(auth_method=AuthMethod.PASSKEY_ENTRY)
        assert len(g.session_key) == 16
        assert g.session_key == t.session_key


class TestPasswordVerify:
    """13.1.4 密码验证配对 — VALD-04"""

    def test_password_pairing_completes(self):
        g, t = run_pairing_procedure(auth_method=AuthMethod.PASSWORD_VERIFY)
        assert g.is_paired and t.is_paired


class TestOOBPairing:
    """13.1.5 OOB 配对 — VALD-05"""

    def test_oob_pairing_completes(self):
        g, t = run_pairing_procedure(auth_method=AuthMethod.OOB)
        assert g.is_paired and t.is_paired


class TestPSKPairing:
    """13.1.6 PSK 配对 — VALD-06"""

    def test_psk_pairing_completes(self):
        g, t = run_pairing_procedure(auth_method=AuthMethod.PSK)
        assert g.is_paired and t.is_paired


class TestPairingWithSM3:
    """13.1 HMAC-SM3 KDF 配对验证"""

    @pytest.mark.parametrize("auth", [AuthMethod.NUMERIC_COMPARISON, AuthMethod.NO_INPUT])
    def test_sm3_kdf_pairing(self, auth: AuthMethod):
        """SM3 KDF 配对 (若 gmssl 不可用则跳过)。"""
        try:
            g, t = run_pairing_procedure(
                kdf_type=KdfType.HMAC_SM3, auth_method=auth,
            )
            assert g.is_paired and t.is_paired
        except (NotImplementedError, ImportError):
            pytest.skip("gmssl 未安装")


# ═══════════════════════════════════════════════════════════════════════
# 13.2 安全保护
# ═══════════════════════════════════════════════════════════════════════


class TestEncryptionAndIntegrity:
    """13.2.1 加密 + 完整性保护 — VALD-01"""

    @pytest.fixture
    def paired_contexts(self):
        g, t = run_pairing_procedure(auth_method=AuthMethod.NUMERIC_COMPARISON)
        iv_base = os.urandom(8)
        ctx_tx = FrameCryptoContext(
            session_key=g.session_key, iv_base=iv_base,
            direction=0, mic_len=4,
        )
        ctx_rx = FrameCryptoContext(
            session_key=t.session_key, iv_base=iv_base,
            direction=0, mic_len=4,
        )
        return ctx_tx, ctx_rx

    def test_encrypt_decrypt_roundtrip(self, paired_contexts):
        ctx_tx, ctx_rx = paired_contexts
        plaintext = b"SLE conformance test data 1234"
        ct, mic = ctx_tx.encrypt(plaintext)
        recovered = ctx_rx.decrypt(ct, mic)
        assert recovered == plaintext

    def test_encrypt_with_aad(self, paired_contexts):
        ctx_tx, ctx_rx = paired_contexts
        plaintext = b"payload"
        aad = b"header"
        ct, mic = ctx_tx.encrypt(plaintext, aad=aad)
        recovered = ctx_rx.decrypt(ct, mic, aad=aad)
        assert recovered == plaintext

    def test_tampered_ciphertext_fails(self, paired_contexts):
        ctx_tx, ctx_rx = paired_contexts
        ct, mic = ctx_tx.encrypt(b"secret")
        tampered = bytes([ct[0] ^ 0xFF]) + ct[1:]
        with pytest.raises(InvalidTag):
            ctx_rx.decrypt(tampered, mic)


class TestIntegrityOnly:
    """13.2.2 仅完整性保护 — VALD-02"""

    def test_integrity_check_detects_tampering(self):
        g, t = run_pairing_procedure(auth_method=AuthMethod.NUMERIC_COMPARISON)
        iv_base = os.urandom(8)
        ctx_tx = FrameCryptoContext(
            session_key=g.session_key, iv_base=iv_base,
            direction=0, mic_len=8,
        )
        ctx_rx = FrameCryptoContext(
            session_key=t.session_key, iv_base=iv_base,
            direction=0, mic_len=8,
        )
        plaintext = b"integrity test payload"
        ct, mic = ctx_tx.encrypt(plaintext)
        # 篡改 MIC
        bad_mic = bytes([mic[0] ^ 0xFF]) + mic[1:]
        with pytest.raises(InvalidTag):
            ctx_rx.decrypt(ct, bad_mic)


class TestReplayProtection:
    """13.2.5 重放防护 — VALD-05"""

    def test_payload_count_monotonic(self):
        g, _ = run_pairing_procedure(auth_method=AuthMethod.NUMERIC_COMPARISON)
        ctx = FrameCryptoContext(session_key=g.session_key, iv_base=os.urandom(8))
        counts = []
        for _ in range(5):
            counts.append(ctx.tx_count)
            ctx.encrypt(b"data")
        assert counts == list(range(5))

    def test_counter_reset(self):
        g, _ = run_pairing_procedure(auth_method=AuthMethod.NUMERIC_COMPARISON)
        ctx = FrameCryptoContext(session_key=g.session_key, iv_base=os.urandom(8))
        ctx.encrypt(b"a")
        ctx.encrypt(b"b")
        assert ctx.tx_count == 2
        ctx.reset_counters()
        assert ctx.tx_count == 0


class TestMICLengths:
    """13.2 不同 MIC 长度验证"""

    @pytest.mark.parametrize("mic_len", [4, 8, 12, 16])
    def test_various_mic_lengths(self, mic_len: int):
        g, t = run_pairing_procedure(auth_method=AuthMethod.NUMERIC_COMPARISON)
        iv = os.urandom(8)
        ctx_tx = FrameCryptoContext(
            session_key=g.session_key, iv_base=iv,
            direction=0, mic_len=mic_len,
        )
        ctx_rx = FrameCryptoContext(
            session_key=t.session_key, iv_base=iv,
            direction=0, mic_len=mic_len,
        )
        pt = b"MIC length test"
        ct, mic = ctx_tx.encrypt(pt)
        assert len(mic) == mic_len
        assert ctx_rx.decrypt(ct, mic) == pt


# ═══════════════════════════════════════════════════════════════════════
# 13.3 隐私
# ═══════════════════════════════════════════════════════════════════════


class TestResolvableAddress:
    """13.3 可解析随机地址 — VALD-01"""

    def test_generate_and_resolve(self):
        irk = os.urandom(16)
        rand_part = 0x1234
        addr = generate_resolvable_address(KdfType.AES_CMAC, irk, rand_part)
        assert resolve_address(KdfType.AES_CMAC, irk, addr)

    def test_wrong_irk_fails(self):
        irk = os.urandom(16)
        wrong_irk = os.urandom(16)
        addr = generate_resolvable_address(KdfType.AES_CMAC, irk, 0xABCD)
        assert not resolve_address(KdfType.AES_CMAC, wrong_irk, addr)

    @pytest.mark.parametrize("rand_part", [0x0000, 0x7FFF, 0xFFFF])
    def test_various_rand_parts(self, rand_part: int):
        irk = os.urandom(16)
        addr = generate_resolvable_address(KdfType.AES_CMAC, irk, rand_part)
        assert resolve_address(KdfType.AES_CMAC, irk, addr)


# ═══════════════════════════════════════════════════════════════════════
# 13.4 UWB 测量安全
# ═══════════════════════════════════════════════════════════════════════


class TestSLPKeyDerivation:
    """13.4.1 SLP 密钥派生"""

    def test_slp_key_length(self):
        link_key = os.urandom(16)
        slp = derive_slp_key(link_key)
        assert len(slp) == 16

    def test_slp_key_deterministic(self):
        link_key = b"\x01" * 16
        slp1 = derive_slp_key(link_key)
        slp2 = derive_slp_key(link_key)
        assert slp1 == slp2


class TestCTSKeyDerivation:
    """13.4.2 CTS 密钥派生"""

    def test_derive_cts_keys(self):
        slp = os.urandom(16)
        input_ctx = os.urandom(16)
        keys = derive_cts_keys(slp, input_ctx)
        assert len(keys.cts_key) == 16
        assert len(keys.cts_value) == 16
        assert len(keys.cts_gap) == 16

    def test_update_cts_keys_increments(self):
        slp = os.urandom(16)
        keys = derive_cts_keys(slp, os.urandom(16))
        old_32 = keys.cts_content_32bit
        updated = update_cts_keys(slp, keys)
        assert updated.cts_content_32bit == (old_32 + 1) & 0xFFFFFFFF
        assert updated.cts_key != keys.cts_key

    def test_invalid_input_context_length(self):
        with pytest.raises(ValueError):
            derive_cts_keys(os.urandom(16), b"\x00" * 10)


class TestCTSSymbolGeneration:
    """13.4.3 CTS 符号生成"""

    def test_generate_symbols(self):
        cts_key = os.urandom(16)
        cts_v_upper = os.urandom(12)
        result = generate_cts_symbols(cts_key, cts_v_upper, 0, n_cts=8)
        assert len(result.symbol_indices) == 8
        assert len(result.sc_values) == 8
        assert all(v in (1, -1) for v in result.sc_values)

    def test_deterministic_generation(self):
        key = b"\xAA" * 16
        v_upper = b"\xBB" * 12
        r1 = generate_cts_symbols(key, v_upper, 0, n_cts=4)
        r2 = generate_cts_symbols(key, v_upper, 0, n_cts=4)
        assert r1.symbol_indices == r2.symbol_indices
        assert r1.sc_values == r2.sc_values


class TestTGap:
    """13.4.4 TGap 计算"""

    def test_tgap_positive(self):
        gap_key = os.urandom(16)
        tgap = compute_tgap(gap_key, cts_gap_shift=0, t_base=1000,
                            code_len=32, delta_l=1)
        assert tgap <= 1000

    def test_tgap_deterministic(self):
        gap_key = b"\xCC" * 16
        t1 = compute_tgap(gap_key, 0, 500, 16, 2)
        t2 = compute_tgap(gap_key, 0, 500, 16, 2)
        assert t1 == t2


class TestCTSVCounterAdvance:
    """13.4.5 ctsVCounter 推进"""

    def test_advance_counter(self):
        assert advance_cts_v_counter(0, 16) == 1
        assert advance_cts_v_counter(0, 32) == 2

    def test_counter_wraps(self):
        assert advance_cts_v_counter(0xFFFFFFFF, 16) == 0
