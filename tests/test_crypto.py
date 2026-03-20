"""安全子系统加密模块测试 -- TXS-10002-2025 标准 9.3"""

from __future__ import annotations

import contextlib
import os

import pytest
from cryptography.exceptions import InvalidTag

from nearlink_sdr.mac.crypto import (
    AuthMethod,
    KdfType,
    aes_ccm_decrypt,
    aes_ccm_encrypt,
    aes_cmac,
    build_ccm_nonce_async,
    build_ccm_nonce_other,
    compute_iv,
    derive_dh_verify_key,
    derive_group_session_key,
    derive_kg,
    derive_link_key,
    derive_session_key,
    generate_confirm_code,
    generate_dh_verify_code,
    generate_group_key,
    generate_numeric_code,
    generate_resolvable_address,
    kdf,
    obfuscate,
    resolve_address,
)

# ---------------------------------------------------------------------------
# KDF 基础函数
# ---------------------------------------------------------------------------


class TestAesCmac:
    """AES-CMAC 测试"""

    def test_output_length(self):
        key = b"\x00" * 16
        mac = aes_cmac(key, b"hello world")
        assert len(mac) == 16

    def test_deterministic(self):
        key = os.urandom(16)
        msg = b"test message"
        assert aes_cmac(key, msg) == aes_cmac(key, msg)

    def test_different_keys(self):
        msg = b"same message"
        mac1 = aes_cmac(b"\x00" * 16, msg)
        mac2 = aes_cmac(b"\x01" * 16, msg)
        assert mac1 != mac2

    def test_different_messages(self):
        key = b"\xAA" * 16
        mac1 = aes_cmac(key, b"message one")
        mac2 = aes_cmac(key, b"message two")
        assert mac1 != mac2

    def test_empty_message(self):
        key = b"\x00" * 16
        mac = aes_cmac(key, b"")
        assert len(mac) == 16


class TestKdf:
    """KDF 分发测试"""

    def test_aes_cmac_type(self):
        key = b"\x00" * 16
        result = kdf(KdfType.AES_CMAC, key, b"test")
        assert result == aes_cmac(key, b"test")

    def test_hmac_sm3_not_available(self):
        # gmssl 不一定安装, 取决于环境
        key = b"\x00" * 16
        with contextlib.suppress(NotImplementedError):
            kdf(KdfType.HMAC_SM3, key, b"test")


# ---------------------------------------------------------------------------
# CCM Nonce 构建
# ---------------------------------------------------------------------------


class TestBuildCcmNonce:
    """CCM Nonce 构建测试"""

    def test_async_nonce_length(self):
        nonce = build_ccm_nonce_async(
            payload_count=0x123456789,
            direction=1,
            iv_base=b"\xAA" * 8,
            data_length=256,
        )
        assert len(nonce) == 16

    def test_async_nonce_flag(self):
        nonce = build_ccm_nonce_async(
            payload_count=0, direction=0,
            iv_base=b"\x00" * 8, data_length=0,
            flag=0x49,
        )
        assert nonce[0] == 0x49

    def test_async_nonce_encrypt_flag(self):
        nonce = build_ccm_nonce_async(
            payload_count=0, direction=0,
            iv_base=b"\x00" * 8, data_length=0,
            flag=0x01,
        )
        assert nonce[0] == 0x01

    def test_async_nonce_data_length(self):
        nonce = build_ccm_nonce_async(
            payload_count=0, direction=0,
            iv_base=b"\x00" * 8, data_length=0x7FF,
        )
        assert nonce[14] == 0x07
        assert nonce[15] == 0xFF

    def test_other_nonce_length(self):
        nonce = build_ccm_nonce_other(
            system_slot_seq=0x3FFFFFFF,
            day_count=0x3FF,
            iv_base=b"\xBB" * 8,
            data_length=100,
        )
        assert len(nonce) == 16

    def test_other_nonce_flag(self):
        nonce = build_ccm_nonce_other(
            system_slot_seq=0, day_count=0,
            iv_base=b"\x00" * 8, data_length=0,
        )
        assert nonce[0] == 0x49

    def test_async_direction_bit(self):
        nonce0 = build_ccm_nonce_async(
            payload_count=0, direction=0,
            iv_base=b"\x00" * 8, data_length=0,
        )
        nonce1 = build_ccm_nonce_async(
            payload_count=0, direction=1,
            iv_base=b"\x00" * 8, data_length=0,
        )
        # direction 嵌入在 nonce 中, 不同 direction 结果不同
        assert nonce0 != nonce1

    def test_async_payload_count_encoded(self):
        nonce = build_ccm_nonce_async(
            payload_count=1, direction=0,
            iv_base=b"\x00" * 8, data_length=0,
        )
        nonce_zero = build_ccm_nonce_async(
            payload_count=0, direction=0,
            iv_base=b"\x00" * 8, data_length=0,
        )
        assert nonce != nonce_zero


# ---------------------------------------------------------------------------
# AES-CCM 加解密
# ---------------------------------------------------------------------------


class TestAesCcm:
    """AES-CCM 加解密测试"""

    def test_encrypt_decrypt_roundtrip(self):
        key = os.urandom(16)
        nonce = os.urandom(13)
        plaintext = b"Hello SLE encryption"
        ct, mic = aes_ccm_encrypt(key, nonce, plaintext)
        pt = aes_ccm_decrypt(key, nonce, ct, mic)
        assert pt == plaintext

    def test_mic_length(self):
        key = os.urandom(16)
        nonce = os.urandom(13)
        _, mic = aes_ccm_encrypt(key, nonce, b"test", mic_len=4)
        assert len(mic) == 4

    def test_mic_length_8(self):
        key = os.urandom(16)
        nonce = os.urandom(13)
        _, mic = aes_ccm_encrypt(key, nonce, b"test", mic_len=8)
        assert len(mic) == 8

    def test_with_aad(self):
        key = os.urandom(16)
        nonce = os.urandom(13)
        pt = b"payload data"
        aad = b"header"
        ct, mic = aes_ccm_encrypt(key, nonce, pt, associated_data=aad)
        result = aes_ccm_decrypt(
            key, nonce, ct, mic, associated_data=aad
        )
        assert result == pt

    def test_wrong_key_fails(self):
        key = os.urandom(16)
        nonce = os.urandom(13)
        ct, mic = aes_ccm_encrypt(key, nonce, b"test")
        wrong_key = os.urandom(16)
        with pytest.raises(InvalidTag):
            aes_ccm_decrypt(wrong_key, nonce, ct, mic)

    def test_tampered_mic_fails(self):
        key = os.urandom(16)
        nonce = os.urandom(13)
        ct, mic = aes_ccm_encrypt(key, nonce, b"test")
        bad_mic = bytes(b ^ 0xFF for b in mic)
        with pytest.raises(InvalidTag):
            aes_ccm_decrypt(key, nonce, ct, bad_mic)

    def test_empty_plaintext(self):
        key = os.urandom(16)
        nonce = os.urandom(13)
        ct, mic = aes_ccm_encrypt(key, nonce, b"")
        pt = aes_ccm_decrypt(key, nonce, ct, mic)
        assert pt == b""


# ---------------------------------------------------------------------------
# 初始化向量计算
# ---------------------------------------------------------------------------


class TestComputeIv:
    """IV 计算测试"""

    def test_ft1_xor_low32(self):
        iv_base = b"\x00\x00\x00\x00\x00\x00\x00\xFF"
        result = compute_iv(iv_base, 0xFF, frame_type=1)
        # 低32位 XOR: 0x000000FF ^ 0x000000FF = 0x00000000
        assert result == b"\x00" * 8

    def test_ft2_xor_low32(self):
        iv_base = b"\x00\x00\x00\x00\xAA\xBB\xCC\xDD"
        sync_seq = 0xAABBCCDD
        result = compute_iv(iv_base, sync_seq, frame_type=2)
        assert result == b"\x00" * 8

    def test_ft3_xor_low24(self):
        iv_base = b"\x00\x00\x00\x00\x00\x00\x00\xAB"
        link_id = 0xAB
        result = compute_iv(iv_base, link_id, frame_type=3)
        assert result == b"\x00" * 8

    def test_ft4_xor_low24(self):
        iv_base = b"\x00\x00\x00\x00\x00\x12\x34\x56"
        link_id = 0x123456
        result = compute_iv(iv_base, link_id, frame_type=4)
        assert result == b"\x00" * 8

    def test_output_length(self):
        result = compute_iv(b"\x00" * 8, 0, frame_type=1)
        assert len(result) == 8


# ---------------------------------------------------------------------------
# 会话密钥派生
# ---------------------------------------------------------------------------


class TestDeriveSessionKey:
    """会话密钥派生测试"""

    def test_authenticated(self):
        link_key = os.urandom(16)
        g_div = os.urandom(8)
        t_div = os.urandom(8)
        sk, ink = derive_session_key(
            KdfType.AES_CMAC, link_key, g_div, t_div,
            use_authenticated=True,
        )
        assert len(sk) == 16
        assert ink is None

    def test_separate_keys(self):
        link_key = os.urandom(16)
        g_div = os.urandom(8)
        t_div = os.urandom(8)
        enk, ink = derive_session_key(
            KdfType.AES_CMAC, link_key, g_div, t_div,
            use_authenticated=False,
        )
        assert len(enk) == 16
        assert ink is not None
        assert len(ink) == 16
        assert enk != ink

    def test_deterministic(self):
        link_key = b"\x42" * 16
        g_div = b"\x01" * 8
        t_div = b"\x02" * 8
        sk1, _ = derive_session_key(
            KdfType.AES_CMAC, link_key, g_div, t_div
        )
        sk2, _ = derive_session_key(
            KdfType.AES_CMAC, link_key, g_div, t_div
        )
        assert sk1 == sk2


# ---------------------------------------------------------------------------
# 链路密钥与 DH Key 验证码密钥
# ---------------------------------------------------------------------------


class TestDeriveKeys:
    """链路密钥派生测试"""

    def test_link_key_output(self):
        dh_key = os.urandom(32)
        ra = os.urandom(16)
        rb = os.urandom(16)
        g_addr = os.urandom(6)
        t_addr = os.urandom(6)
        lk = derive_link_key(
            KdfType.AES_CMAC, dh_key, ra, rb, g_addr, t_addr
        )
        assert len(lk) == 16

    def test_dh_verify_key_output(self):
        dh_key = os.urandom(32)
        ra = os.urandom(16)
        rb = os.urandom(16)
        g_addr = os.urandom(6)
        t_addr = os.urandom(6)
        vk = derive_dh_verify_key(
            KdfType.AES_CMAC, dh_key, ra, rb, g_addr, t_addr
        )
        assert len(vk) == 16

    def test_link_key_differs_from_verify_key(self):
        dh_key = os.urandom(32)
        ra = os.urandom(16)
        rb = os.urandom(16)
        g_addr = os.urandom(6)
        t_addr = os.urandom(6)
        lk = derive_link_key(
            KdfType.AES_CMAC, dh_key, ra, rb, g_addr, t_addr
        )
        vk = derive_dh_verify_key(
            KdfType.AES_CMAC, dh_key, ra, rb, g_addr, t_addr
        )
        # 使用不同 keyID ("lk" vs "dk"), 结果不同
        assert lk != vk


# ---------------------------------------------------------------------------
# 确认码生成
# ---------------------------------------------------------------------------


class TestConfirmCode:
    """确认码生成测试"""

    def test_numeric_comparison(self):
        ra = os.urandom(16)
        g_pub = os.urandom(64)
        t_pub = os.urandom(64)
        code = generate_confirm_code(
            KdfType.AES_CMAC, AuthMethod.NUMERIC_COMPARISON,
            ra, g_pub, t_pub,
        )
        assert len(code) == 16

    def test_oob_g_node(self):
        code = generate_confirm_code(
            KdfType.AES_CMAC, AuthMethod.OOB,
            os.urandom(16), os.urandom(64), os.urandom(64),
            is_g_node=True,
        )
        assert len(code) == 16

    def test_oob_t_node_uses_t_pubkey(self):
        ra = os.urandom(16)
        g_pub = os.urandom(64)
        t_pub = os.urandom(64)
        code_g = generate_confirm_code(
            KdfType.AES_CMAC, AuthMethod.OOB,
            ra, g_pub, t_pub, is_g_node=True,
        )
        code_t = generate_confirm_code(
            KdfType.AES_CMAC, AuthMethod.OOB,
            ra, g_pub, t_pub, is_g_node=False,
        )
        # G 节点使用 g_pub, T 节点使用 t_pub, 结果不同
        assert code_g != code_t

    def test_passkey_with_obfuscated(self):
        code = generate_confirm_code(
            KdfType.AES_CMAC, AuthMethod.PASSKEY_ENTRY,
            os.urandom(16), os.urandom(64), os.urandom(64),
            obfuscated=os.urandom(16),
        )
        assert len(code) == 16

    def test_psk_auth(self):
        psk = os.urandom(16)
        code = generate_confirm_code(
            KdfType.AES_CMAC, AuthMethod.PSK,
            psk, os.urandom(64), os.urandom(64),
            obfuscated=os.urandom(16),
        )
        assert len(code) == 16

    def test_no_input_auth(self):
        code = generate_confirm_code(
            KdfType.AES_CMAC, AuthMethod.NO_INPUT,
            os.urandom(16), os.urandom(64), os.urandom(64),
        )
        assert len(code) == 16

    def test_password_verify(self):
        code = generate_confirm_code(
            KdfType.AES_CMAC, AuthMethod.PASSWORD_VERIFY,
            os.urandom(16), os.urandom(64), os.urandom(64),
            obfuscated=os.urandom(16),
        )
        assert len(code) == 16


# ---------------------------------------------------------------------------
# DH Key 验证码
# ---------------------------------------------------------------------------


class TestDhVerifyCode:
    """DH Key 验证码测试"""

    def test_output(self):
        code = generate_dh_verify_code(
            KdfType.AES_CMAC,
            verify_key=os.urandom(16),
            random_value=os.urandom(16),
            salt=b"\x00" * 16,
            g_io_cap=0x01, t_io_cap=0x02,
            auth_method=0, crypto_alg=0,
            g_psk_ind=0, t_psk_ind=0,
            g_addr=os.urandom(6), t_addr=os.urandom(6),
        )
        assert len(code) == 16

    def test_different_salt(self):
        vk = os.urandom(16)
        rv = os.urandom(16)
        g_addr = os.urandom(6)
        t_addr = os.urandom(6)
        code1 = generate_dh_verify_code(
            KdfType.AES_CMAC, vk, rv, b"\x00" * 16,
            0, 0, 0, 0, 0, 0, g_addr, t_addr,
        )
        code2 = generate_dh_verify_code(
            KdfType.AES_CMAC, vk, rv, b"\xFF" * 16,
            0, 0, 0, 0, 0, 0, g_addr, t_addr,
        )
        assert code1 != code2


# ---------------------------------------------------------------------------
# 数字比较码和混淆算法
# ---------------------------------------------------------------------------


class TestNumericCodeAndObfuscate:
    """数字比较码和混淆算法测试"""

    def test_numeric_code_range(self):
        code = generate_numeric_code(
            KdfType.AES_CMAC,
            g_pubkey_x=os.urandom(32),
            t_pubkey=os.urandom(64),
            ra=os.urandom(16), rb=os.urandom(16),
        )
        assert 0 <= code <= 999_999

    def test_numeric_code_deterministic(self):
        gx = os.urandom(32)
        tp = os.urandom(64)
        ra = os.urandom(16)
        rb = os.urandom(16)
        c1 = generate_numeric_code(KdfType.AES_CMAC, gx, tp, ra, rb)
        c2 = generate_numeric_code(KdfType.AES_CMAC, gx, tp, ra, rb)
        assert c1 == c2

    def test_obfuscate_output(self):
        result = obfuscate(
            KdfType.AES_CMAC,
            g_pubkey_x=os.urandom(32),
            value=b"\x01\x02\x03",
        )
        assert len(result) == 16

    def test_obfuscate_deterministic(self):
        gx = os.urandom(32)
        val = b"123456"
        o1 = obfuscate(KdfType.AES_CMAC, gx, val)
        o2 = obfuscate(KdfType.AES_CMAC, gx, val)
        assert o1 == o2


# ---------------------------------------------------------------------------
# 组播密钥管理
# ---------------------------------------------------------------------------


class TestGroupKey:
    """组播密钥管理测试"""

    def test_generate_gk(self):
        gk = generate_group_key(
            KdfType.AES_CMAC, os.urandom(16), os.urandom(16)
        )
        assert len(gk) == 16

    def test_group_session_authenticated(self):
        gk = os.urandom(16)
        gsk, gink = derive_group_session_key(
            KdfType.AES_CMAC, gk, use_authenticated=True
        )
        assert len(gsk) == 16
        assert gink is None

    def test_group_session_separate(self):
        gk = os.urandom(16)
        genk, gink = derive_group_session_key(
            KdfType.AES_CMAC, gk, use_authenticated=False
        )
        assert len(genk) == 16
        assert gink is not None
        assert len(gink) == 16
        assert genk != gink

    def test_derive_kg(self):
        link_key = os.urandom(16)
        rand = os.urandom(16)
        kg = derive_kg(KdfType.AES_CMAC, link_key, rand)
        assert len(kg) == 16

    def test_gk_xor_transport(self):
        """测试 GK 通过 Kg XOR 传输的完整流程"""
        link_key = os.urandom(16)
        rand = os.urandom(16)

        # G 节点生成 GK 和 Kg
        gk = generate_group_key(
            KdfType.AES_CMAC, os.urandom(16), os.urandom(16)
        )
        kg = derive_kg(KdfType.AES_CMAC, link_key, rand)

        # C = Kg XOR GK
        c = bytes(a ^ b for a, b in zip(kg, gk, strict=True))

        # T 节点恢复 GK = Kg XOR C
        kg_t = derive_kg(KdfType.AES_CMAC, link_key, rand)
        gk_restored = bytes(
            a ^ b for a, b in zip(kg_t, c, strict=True)
        )
        assert gk_restored == gk


# ---------------------------------------------------------------------------
# 隐私管理
# ---------------------------------------------------------------------------


class TestPrivacy:
    """隐私管理测试"""

    def test_generate_and_resolve(self):
        irk = os.urandom(16)
        rand_part = 0x1234
        addr = generate_resolvable_address(
            KdfType.AES_CMAC, irk, rand_part
        )
        assert resolve_address(KdfType.AES_CMAC, irk, addr)

    def test_wrong_irk_fails(self):
        irk = os.urandom(16)
        rand_part = 0xABCD
        addr = generate_resolvable_address(
            KdfType.AES_CMAC, irk, rand_part
        )
        wrong_irk = os.urandom(16)
        assert not resolve_address(KdfType.AES_CMAC, wrong_irk, addr)

    def test_address_is_48bit(self):
        irk = os.urandom(16)
        addr = generate_resolvable_address(
            KdfType.AES_CMAC, irk, 0xFFFF
        )
        assert addr < (1 << 48)


# ---------------------------------------------------------------------------
# 完整流程集成测试
# ---------------------------------------------------------------------------


class TestSecurityFlowIntegration:
    """安全流程集成测试"""

    def test_session_key_encrypt_decrypt(self):
        """完整的密钥派生 + 加密解密流程"""
        link_key = os.urandom(16)
        g_div = os.urandom(8)
        t_div = os.urandom(8)

        sk, _ = derive_session_key(
            KdfType.AES_CMAC, link_key, g_div, t_div
        )

        # 构建 nonce
        iv_base = os.urandom(8)
        nonce_block = build_ccm_nonce_async(
            payload_count=42, direction=1,
            iv_base=iv_base, data_length=0,
            flag=0x01,
        )
        # 取 13 字节 nonce (去掉 flag 和 length)
        ccm_nonce = nonce_block[1:14]

        plaintext = b"SLE data payload for encryption test"
        ct, mic = aes_ccm_encrypt(sk, ccm_nonce, plaintext)
        pt = aes_ccm_decrypt(sk, ccm_nonce, ct, mic)
        assert pt == plaintext

    def test_link_key_to_session_key(self):
        """DH Key -> Link Key -> Session Key 全链路"""
        dh_key = os.urandom(32)
        ra = os.urandom(16)
        rb = os.urandom(16)
        g_addr = b"\x01\x02\x03\x04\x05\x06"
        t_addr = b"\x0A\x0B\x0C\x0D\x0E\x0F"

        link_key = derive_link_key(
            KdfType.AES_CMAC, dh_key, ra, rb, g_addr, t_addr
        )
        assert len(link_key) == 16

        g_div = os.urandom(8)
        t_div = os.urandom(8)
        sk, _ = derive_session_key(
            KdfType.AES_CMAC, link_key, g_div, t_div
        )
        assert len(sk) == 16
