"""安全流程集成管理测试 -- PairingManager 和 FrameCryptoContext。"""

from __future__ import annotations

import os

import pytest
from cryptography.exceptions import InvalidTag

from nearlink_sdr.mac.security import (
    GNodeConfirmCode,
    PairingConfirm,
    PairingFailure,
    PairingInitialInfo,
    PairingInitiate,
    PairingRequest,
    PairingResponse,
    RaMessage,
    RbMessage,
    TNodeConfirmCode,
)
from nearlink_sdr.mac.security_manager import (
    ECDHKeyPair,
    FrameCryptoContext,
    PairingManager,
    PairingState,
    run_pairing_procedure,
)

# ── ECDH 密钥交换 ──


class TestECDHKeyPair:
    """P-256 椭圆曲线密钥对测试。"""

    def test_generate_key_pair(self):
        kp = ECDHKeyPair.generate()
        assert len(kp.private_key_bytes) > 0
        assert len(kp.public_key_x) == 32
        assert len(kp.public_key_y) == 32

    def test_shared_secret(self):
        kp_a = ECDHKeyPair.generate()
        kp_b = ECDHKeyPair.generate()
        secret_a = kp_a.compute_shared_secret(kp_b.public_key_x, kp_b.public_key_y)
        secret_b = kp_b.compute_shared_secret(kp_a.public_key_x, kp_a.public_key_y)
        assert secret_a == secret_b
        assert len(secret_a) == 32

    def test_different_keypairs_different_secrets(self):
        kp_a = ECDHKeyPair.generate()
        kp_b = ECDHKeyPair.generate()
        kp_c = ECDHKeyPair.generate()
        secret_ab = kp_a.compute_shared_secret(kp_b.public_key_x, kp_b.public_key_y)
        secret_ac = kp_a.compute_shared_secret(kp_c.public_key_x, kp_c.public_key_y)
        assert secret_ab != secret_ac


# ── PairingManager 基础 ──


class TestPairingManagerBasic:
    """配对管理器基本功能测试。"""

    def test_initial_state(self):
        mgr = PairingManager()
        assert mgr.state == PairingState.IDLE
        assert not mgr.is_paired

    def test_g_node_start_pairing(self):
        mgr = PairingManager(is_g_node=True)
        msgs = mgr.start_pairing()
        assert mgr.state == PairingState.REQUEST_SENT
        assert len(msgs) == 2
        assert isinstance(msgs[0], PairingInitiate)
        assert isinstance(msgs[1], PairingRequest)
        assert len(mgr.local_keypair.public_key_x) == 32

    def test_t_node_start_pairing(self):
        mgr = PairingManager(is_g_node=False)
        msgs = mgr.start_pairing()
        assert mgr.state == PairingState.INITIATED
        assert len(msgs) == 0
        assert len(mgr.local_keypair.public_key_x) == 32

    def test_t_node_handle_initiate(self):
        mgr = PairingManager(is_g_node=False)
        mgr.start_pairing()
        responses = mgr.process_message(PairingInitiate(auth_request=0x01))
        assert mgr.state == PairingState.INITIATED
        assert len(responses) == 0

    def test_t_node_handle_request(self):
        mgr = PairingManager(is_g_node=False)
        mgr.start_pairing()
        responses = mgr.process_message(
            PairingRequest(
                io_capability=0x03,
                oob_data_flag=0,
                auth_request=0x01,
                max_key_length=16,
                security_dist_info=0x01,
                crypto_capability=b"\x01\x00\x00\x00",
                psk_indication=0,
            )
        )
        assert mgr.state == PairingState.RESPONSE_SENT
        assert len(responses) == 1
        assert isinstance(responses[0], PairingResponse)

    def test_g_node_handle_response(self):
        g = PairingManager(is_g_node=True)
        g.start_pairing()
        responses = g.process_message(
            PairingResponse(
                io_capability=0x03,
                oob_data_flag=0,
                auth_request=0x01,
                max_key_length=16,
                security_dist_info=0x01,
                crypto_capability=b"\x01\x00\x00\x00",
                psk_indication=0,
            )
        )
        assert g.state == PairingState.CONFIRM_SENT
        assert len(responses) == 1
        assert isinstance(responses[0], PairingConfirm)
        confirm = responses[0]
        assert confirm.g_public_key_x == g.local_keypair.public_key_x
        assert confirm.g_public_key_y == g.local_keypair.public_key_y


# ── 配对交互流程 ──


class TestPairingFlow:
    """配对完整信令交互测试。"""

    @pytest.fixture()
    def g_and_t(self):
        g_addr = b"\x01\x02\x03\x04\x05\x06"
        t_addr = b"\x0A\x0B\x0C\x0D\x0E\x0F"
        g = PairingManager(
            is_g_node=True,
            local_address=g_addr,
            peer_address=t_addr,
        )
        t = PairingManager(
            is_g_node=False,
            local_address=t_addr,
            peer_address=g_addr,
        )
        return g, t

    def test_key_exchange_phase(self, g_and_t):
        """公钥交换阶段: Initiate → Request → Response → Confirm → InitialInfo。"""
        g, t = g_and_t
        g_msgs = g.start_pairing()
        t.start_pairing()

        # T 收到 Initiate
        t.process_message(g_msgs[0])
        # T 收到 Request, 返回 Response
        t_responses = t.process_message(g_msgs[1])
        assert len(t_responses) == 1
        assert isinstance(t_responses[0], PairingResponse)

        # G 收到 Response, 发送 Confirm
        g_responses = g.process_message(t_responses[0])
        assert len(g_responses) == 1
        assert isinstance(g_responses[0], PairingConfirm)

        # T 收到 Confirm, 发送 InitialInfo
        t_responses = t.process_message(g_responses[0])
        assert len(t_responses) == 1
        assert isinstance(t_responses[0], PairingInitialInfo)
        assert t.state == PairingState.PUBLIC_KEY_EXCHANGED

        # G 收到 InitialInfo, 发送 Ra
        g_responses = g.process_message(t_responses[0])
        assert len(g_responses) == 1
        assert isinstance(g_responses[0], RaMessage)
        assert g.state == PairingState.PUBLIC_KEY_EXCHANGED

    def test_random_exchange_to_confirm(self, g_and_t):
        """随机数交换到确认码阶段。"""
        g, t = g_and_t

        # 快速推进到公钥交换完成
        g_msgs = g.start_pairing()
        t.start_pairing()
        t.process_message(g_msgs[0])
        t_resp = t.process_message(g_msgs[1])
        g_resp = g.process_message(t_resp[0])
        t_resp = t.process_message(g_resp[0])
        g_resp = g.process_message(t_resp[0])

        # g_resp 是 Ra
        assert isinstance(g_resp[0], RaMessage)
        # T 收到 Ra, 发送 Rb
        t_resp = t.process_message(g_resp[0])
        assert len(t_resp) == 1
        assert isinstance(t_resp[0], RbMessage)

        # G 收到 Rb, 发送 G 确认码
        g_resp = g.process_message(t_resp[0])
        assert len(g_resp) == 1
        assert isinstance(g_resp[0], GNodeConfirmCode)
        assert g.state == PairingState.CONFIRM_CODE_SENT

    def test_full_pairing_flow(self, g_and_t):
        """完整配对流程 (端到端)。"""
        g, t = g_and_t

        # 推进到 Rb 交换
        g_msgs = g.start_pairing()
        t.start_pairing()
        t.process_message(g_msgs[0])
        t_resp = t.process_message(g_msgs[1])
        g_resp = g.process_message(t_resp[0])
        t_resp = t.process_message(g_resp[0])
        g_resp = g.process_message(t_resp[0])
        t_resp = t.process_message(g_resp[0])
        g_resp = g.process_message(t_resp[0])

        # g_resp 是 GNodeConfirmCode
        assert isinstance(g_resp[0], GNodeConfirmCode)

        # T 收到 G 确认码, 验证并发送 T 确认码
        t_resp = t.process_message(g_resp[0])
        assert t.state == PairingState.COMPLETED
        assert len(t_resp) == 1
        assert isinstance(t_resp[0], TNodeConfirmCode)

        # G 收到 T 确认码, 验证完成配对
        g_resp = g.process_message(t_resp[0])
        assert g.state == PairingState.COMPLETED
        assert g.is_paired
        assert t.is_paired

        # 验证密钥一致性
        assert len(g.link_key) == 16
        assert len(t.link_key) == 16
        assert len(g.session_key) == 16
        assert len(t.session_key) == 16


class TestPairingFailure:
    """配对失败场景测试。"""

    def test_failure_message(self):
        mgr = PairingManager(is_g_node=True)
        mgr.start_pairing()
        mgr.process_message(PairingFailure(reason=0x04))
        assert mgr.state == PairingState.FAILED
        assert mgr.failure_reason is not None
        assert mgr.failure_reason.value == 0x04

    def test_wrong_confirm_code_g_rejects(self):
        """G 节点收到错误的 T 确认码应导致失败。"""
        g = PairingManager(is_g_node=True)
        g.start_pairing()
        # 人造密钥材料用于触发确认码验证
        g.dh_key = os.urandom(32)
        g.peer_random = os.urandom(16)
        g.peer_pub_x = os.urandom(32)
        g.peer_pub_y = os.urandom(32)
        g.state = PairingState.CONFIRM_CODE_SENT

        wrong_code = TNodeConfirmCode(confirm_code=os.urandom(16))
        responses = g.process_message(wrong_code)
        assert g.state == PairingState.FAILED
        assert len(responses) == 1
        assert isinstance(responses[0], PairingFailure)

    def test_wrong_confirm_code_t_rejects(self):
        """T 节点收到错误的 G 确认码应导致失败。"""
        t = PairingManager(is_g_node=False)
        t.start_pairing()
        t.dh_key = os.urandom(32)
        t.peer_random = os.urandom(16)
        t.peer_pub_x = os.urandom(32)
        t.peer_pub_y = os.urandom(32)
        t.state = PairingState.PUBLIC_KEY_EXCHANGED

        wrong_code = GNodeConfirmCode(confirm_code=os.urandom(16))
        responses = t.process_message(wrong_code)
        assert t.state == PairingState.FAILED
        assert len(responses) == 1
        assert isinstance(responses[0], PairingFailure)


# ── 端到端配对 ──


class TestRunPairingProcedure:
    """run_pairing_procedure 端到端测试。"""

    def test_default_pairing(self):
        g, t = run_pairing_procedure()
        assert g.is_paired
        assert t.is_paired
        assert len(g.session_key) == 16
        assert len(t.session_key) == 16

    def test_pairing_with_custom_addresses(self):
        g_addr = b"\xAA\xBB\xCC\xDD\xEE\xFF"
        t_addr = b"\x11\x22\x33\x44\x55\x66"
        g, t = run_pairing_procedure(g_address=g_addr, t_address=t_addr)
        assert g.is_paired
        assert t.is_paired
        assert g.local_address == g_addr
        assert t.local_address == t_addr


# ── FrameCryptoContext ──


class TestFrameCryptoContext:
    """帧加密上下文测试。"""

    @pytest.fixture()
    def crypto_pair(self):
        """创建配对的加解密上下文 (模拟 G→T 方向)。"""
        key = os.urandom(16)
        iv_base = os.urandom(8)
        tx_ctx = FrameCryptoContext(
            session_key=key,
            iv_base=iv_base,
            direction=0,
            mic_len=4,
            frame_type=2,
            link_id=0,
        )
        rx_ctx = FrameCryptoContext(
            session_key=key,
            iv_base=iv_base,
            direction=0,
            mic_len=4,
            frame_type=2,
            link_id=0,
        )
        return tx_ctx, rx_ctx

    def test_encrypt_decrypt_roundtrip(self, crypto_pair):
        tx_ctx, rx_ctx = crypto_pair
        plaintext = b"Hello SLE security"
        ct, mic = tx_ctx.encrypt(plaintext)
        pt = rx_ctx.decrypt(ct, mic)
        assert pt == plaintext

    def test_payload_count_increments(self, crypto_pair):
        tx_ctx, _rx_ctx = crypto_pair
        assert tx_ctx.tx_count == 0
        tx_ctx.encrypt(b"frame 1")
        assert tx_ctx.tx_count == 1
        tx_ctx.encrypt(b"frame 2")
        assert tx_ctx.tx_count == 2

    def test_rx_count_increments(self, crypto_pair):
        tx_ctx, rx_ctx = crypto_pair
        ct1, mic1 = tx_ctx.encrypt(b"frame 1")
        ct2, mic2 = tx_ctx.encrypt(b"frame 2")
        assert rx_ctx.rx_count == 0
        rx_ctx.decrypt(ct1, mic1)
        assert rx_ctx.rx_count == 1
        rx_ctx.decrypt(ct2, mic2)
        assert rx_ctx.rx_count == 2

    def test_multiple_frames(self, crypto_pair):
        tx_ctx, rx_ctx = crypto_pair
        for i in range(10):
            pt = f"frame data {i}".encode()
            ct, mic = tx_ctx.encrypt(pt)
            result = rx_ctx.decrypt(ct, mic)
            assert result == pt

    def test_different_keys_fail(self):
        tx_ctx = FrameCryptoContext(
            session_key=os.urandom(16),
            iv_base=os.urandom(8),
        )
        rx_ctx = FrameCryptoContext(
            session_key=os.urandom(16),
            iv_base=tx_ctx.iv_base,
        )
        ct, mic = tx_ctx.encrypt(b"secret")
        with pytest.raises(InvalidTag):
            rx_ctx.decrypt(ct, mic)

    def test_tampered_ciphertext_fails(self, crypto_pair):
        tx_ctx, rx_ctx = crypto_pair
        ct, mic = tx_ctx.encrypt(b"important data")
        tampered = bytes([ct[0] ^ 0xFF]) + ct[1:]
        with pytest.raises(InvalidTag):
            rx_ctx.decrypt(tampered, mic)

    def test_tampered_mic_fails(self, crypto_pair):
        tx_ctx, rx_ctx = crypto_pair
        ct, mic = tx_ctx.encrypt(b"important data")
        tampered_mic = bytes([mic[0] ^ 0xFF]) + mic[1:]
        with pytest.raises(InvalidTag):
            rx_ctx.decrypt(ct, tampered_mic)

    def test_with_aad(self, crypto_pair):
        tx_ctx, rx_ctx = crypto_pair
        pt = b"payload"
        aad = b"header info"
        ct, mic = tx_ctx.encrypt(pt, aad=aad)
        result = rx_ctx.decrypt(ct, mic, aad=aad)
        assert result == pt

    def test_wrong_aad_fails(self, crypto_pair):
        tx_ctx, rx_ctx = crypto_pair
        ct, mic = tx_ctx.encrypt(b"payload", aad=b"correct header")
        with pytest.raises(InvalidTag):
            rx_ctx.decrypt(ct, mic, aad=b"wrong header")

    def test_reset_counters(self, crypto_pair):
        tx_ctx, _ = crypto_pair
        tx_ctx.encrypt(b"data")
        tx_ctx.encrypt(b"data")
        assert tx_ctx.tx_count == 2
        tx_ctx.reset_counters()
        assert tx_ctx.tx_count == 0
        assert tx_ctx.rx_count == 0

    def test_mic_length_options(self):
        key = os.urandom(16)
        iv_base = os.urandom(8)
        for mic_len in (4, 8):
            tx = FrameCryptoContext(
                session_key=key, iv_base=iv_base, mic_len=mic_len,
            )
            rx = FrameCryptoContext(
                session_key=key, iv_base=iv_base, mic_len=mic_len,
            )
            ct, mic = tx.encrypt(b"test data")
            assert len(mic) == mic_len
            result = rx.decrypt(ct, mic)
            assert result == b"test data"


# ── 配对 + 加密联合测试 ──


class TestPairingThenEncryption:
    """配对后使用会话密钥加密数据的集成测试。"""

    def test_paired_keys_encrypt_data(self):
        """配对完成后, 使用会话密钥进行帧加密和解密。"""
        g, t = run_pairing_procedure()
        assert g.is_paired and t.is_paired

        iv_base = os.urandom(8)

        g_tx = FrameCryptoContext(
            session_key=g.session_key,
            iv_base=iv_base,
            direction=0,
        )
        t_rx = FrameCryptoContext(
            session_key=t.session_key,
            iv_base=iv_base,
            direction=0,
        )

        # G→T 发送 5 帧
        for i in range(5):
            pt = f"data from G node {i}".encode()
            ct, mic = g_tx.encrypt(pt)
            result = t_rx.decrypt(ct, mic)
            assert result == pt

    def test_bidirectional_encryption(self):
        """双向加密: G→T 和 T→G 使用不同方向。"""
        g, t = run_pairing_procedure()
        iv_base = os.urandom(8)

        # G→T 方向
        g_tx = FrameCryptoContext(
            session_key=g.session_key, iv_base=iv_base, direction=0,
        )
        t_rx = FrameCryptoContext(
            session_key=t.session_key, iv_base=iv_base, direction=0,
        )

        # T→G 方向
        t_tx = FrameCryptoContext(
            session_key=t.session_key, iv_base=iv_base, direction=1,
        )
        g_rx = FrameCryptoContext(
            session_key=g.session_key, iv_base=iv_base, direction=1,
        )

        # G→T
        ct, mic = g_tx.encrypt(b"hello from G")
        assert t_rx.decrypt(ct, mic) == b"hello from G"

        # T→G
        ct, mic = t_tx.encrypt(b"hello from T")
        assert g_rx.decrypt(ct, mic) == b"hello from T"

    def test_signaling_pack_unpack(self):
        """配对信令序列化/反序列化完整性。"""
        g, _ = run_pairing_procedure()
        assert g.is_paired

        # 验证配对过程中生成的信令都可以序列化
        for msg in g._outgoing:
            packed = msg.pack()
            assert len(packed) == msg.BYTE_LENGTH
            unpacked = type(msg).unpack(packed)
            assert unpacked.pack() == packed
