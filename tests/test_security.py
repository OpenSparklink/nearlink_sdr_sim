"""安全层配对信令 roundtrip 测试 -- TXS-10002-2025 标准 9.2"""

from __future__ import annotations

import os
from typing import ClassVar

import pytest

from nearlink_sdr.mac.security import (
    GNodeConfirmCode,
    GNodeConfirmCodeWithRandom,
    GNodeDHKeyVerify,
    PairingConfirm,
    PairingFailure,
    PairingInitialInfo,
    PairingInitiate,
    PairingRequest,
    PairingResponse,
    RaMessage,
    RbMessage,
    RgMessage,
    RtMessage,
    TNodeConfirmCode,
    TNodeConfirmCodeWithRandom,
    TNodeDHKeyVerify,
)
from nearlink_sdr.mac.signaling import (
    _SIGNALING_REGISTRY,
    decode_signaling,
    encode_signaling,
)


class TestPairingInitiate:
    """9.2.1.1 配对发起消息"""

    def test_roundtrip(self):
        msg = PairingInitiate(auth_request=0b01_1_0_0000)
        data = msg.pack()
        assert len(data) == 1
        got = PairingInitiate.unpack(data)
        assert got.auth_request == msg.auth_request

    def test_data_type_index(self):
        assert PairingInitiate.DATA_TYPE_INDEX == 0x0133

    def test_fields(self):
        # 安全属性=01(绑定), 防中间人=1, 按键提示=0
        msg = PairingInitiate(auth_request=0b01_1_0_0000)
        data = msg.pack()
        assert data[0] == 0b01_1_0_0000


class TestPairingRequest:
    """9.2.2.1 配对请求消息"""

    def test_roundtrip(self):
        crypto = bytes([0x01, 0x02, 0x01, 0x02])
        msg = PairingRequest(
            io_capability=0x04,
            oob_data_flag=0x01,
            auth_request=0b01_1_1_0000,
            max_key_length=16,
            security_dist_info=0x07,
            crypto_capability=crypto,
            psk_indication=0x01,
        )
        data = msg.pack()
        assert len(data) == 10
        got = PairingRequest.unpack(data)
        assert got.io_capability == 0x04
        assert got.oob_data_flag == 0x01
        assert got.auth_request == 0b01_1_1_0000
        assert got.max_key_length == 16
        assert got.security_dist_info == 0x07
        assert got.crypto_capability == crypto
        assert got.psk_indication == 0x01

    def test_data_type_index(self):
        assert PairingRequest.DATA_TYPE_INDEX == 0x0134


class TestPairingResponse:
    """9.2.2.2 配对回应消息"""

    def test_roundtrip(self):
        crypto = bytes([0x02, 0x01, 0x02, 0x01])
        msg = PairingResponse(
            io_capability=0x00,
            oob_data_flag=0x00,
            auth_request=0b00_0_0_0000,
            max_key_length=16,
            security_dist_info=0x03,
            crypto_capability=crypto,
            psk_indication=0x00,
        )
        data = msg.pack()
        assert len(data) == 10
        got = PairingResponse.unpack(data)
        assert got.io_capability == 0x00
        assert got.crypto_capability == crypto

    def test_data_type_index(self):
        assert PairingResponse.DATA_TYPE_INDEX == 0x0135


class TestPairingConfirm:
    """9.2.2.3 配对确认消息"""

    def test_roundtrip(self):
        pk_x = os.urandom(32)
        pk_y = os.urandom(32)
        crypto = bytes([0x01, 0x01, 0x01, 0x01])
        msg = PairingConfirm(
            key_length=16,
            auth_method=0x00,
            crypto_algorithm=crypto,
            g_public_key_x=pk_x,
            g_public_key_y=pk_y,
        )
        data = msg.pack()
        assert len(data) == 70
        got = PairingConfirm.unpack(data)
        assert got.key_length == 16
        assert got.auth_method == 0x00
        assert got.crypto_algorithm == crypto
        assert got.g_public_key_x == pk_x
        assert got.g_public_key_y == pk_y

    def test_data_type_index(self):
        assert PairingConfirm.DATA_TYPE_INDEX == 0x0136


class TestPairingInitialInfo:
    """9.2.2.4 配对初始信息"""

    def test_roundtrip(self):
        pk_x = os.urandom(32)
        pk_y = os.urandom(32)
        msg = PairingInitialInfo(t_public_key_x=pk_x, t_public_key_y=pk_y)
        data = msg.pack()
        assert len(data) == 64
        got = PairingInitialInfo.unpack(data)
        assert got.t_public_key_x == pk_x
        assert got.t_public_key_y == pk_y

    def test_data_type_index(self):
        assert PairingInitialInfo.DATA_TYPE_INDEX == 0x0137


class TestConfirmCodes:
    """9.2.3 鉴权流程确认码消息"""

    def test_t_confirm_code(self):
        code = os.urandom(16)
        msg = TNodeConfirmCode(confirm_code=code)
        assert msg.pack() == code
        assert TNodeConfirmCode.unpack(code).confirm_code == code
        assert TNodeConfirmCode.DATA_TYPE_INDEX == 0x0138

    def test_ra_message(self):
        ra = os.urandom(16)
        msg = RaMessage(ra=ra)
        assert msg.pack() == ra
        assert RaMessage.unpack(ra).ra == ra
        assert RaMessage.DATA_TYPE_INDEX == 0x0139

    def test_rb_message(self):
        rb = os.urandom(16)
        msg = RbMessage(rb=rb)
        assert msg.pack() == rb
        assert RbMessage.unpack(rb).rb == rb
        assert RbMessage.DATA_TYPE_INDEX == 0x013A

    def test_g_confirm_with_random(self):
        code = os.urandom(16)
        ra = os.urandom(16)
        msg = GNodeConfirmCodeWithRandom(confirm_code=code, ra=ra)
        data = msg.pack()
        assert len(data) == 32
        got = GNodeConfirmCodeWithRandom.unpack(data)
        assert got.confirm_code == code
        assert got.ra == ra
        assert GNodeConfirmCodeWithRandom.DATA_TYPE_INDEX == 0x013B

    def test_t_confirm_with_random(self):
        code = os.urandom(16)
        rb = os.urandom(16)
        msg = TNodeConfirmCodeWithRandom(confirm_code=code, rb=rb)
        data = msg.pack()
        assert len(data) == 32
        got = TNodeConfirmCodeWithRandom.unpack(data)
        assert got.confirm_code == code
        assert got.rb == rb
        assert TNodeConfirmCodeWithRandom.DATA_TYPE_INDEX == 0x013C

    def test_g_confirm_code(self):
        code = os.urandom(16)
        msg = GNodeConfirmCode(confirm_code=code)
        assert msg.pack() == code
        assert GNodeConfirmCode.unpack(code).confirm_code == code
        assert GNodeConfirmCode.DATA_TYPE_INDEX == 0x013F


class TestDHKeyVerify:
    """9.2.3.7 DH Key 验证"""

    def test_g_dh_verify(self):
        code = os.urandom(16)
        msg = GNodeDHKeyVerify(verify_code=code)
        assert msg.pack() == code
        assert GNodeDHKeyVerify.unpack(code).verify_code == code
        assert GNodeDHKeyVerify.DATA_TYPE_INDEX == 0x0141

    def test_t_dh_verify(self):
        code = os.urandom(16)
        msg = TNodeDHKeyVerify(verify_code=code)
        assert msg.pack() == code
        assert TNodeDHKeyVerify.unpack(code).verify_code == code
        assert TNodeDHKeyVerify.DATA_TYPE_INDEX == 0x0142


class TestPairingFailure:
    """9.2.3.8 配对失败消息"""

    @pytest.mark.parametrize("reason", range(0x01, 0x0D))
    def test_roundtrip(self, reason):
        msg = PairingFailure(reason=reason)
        data = msg.pack()
        assert len(data) == 1
        got = PairingFailure.unpack(data)
        assert got.reason == reason

    def test_data_type_index(self):
        assert PairingFailure.DATA_TYPE_INDEX == 0x0147


class TestSM2KeyExchange:
    """9.2.2.5/9.2.2.6 SM2 密钥交换消息"""

    def test_rg_message(self):
        x = os.urandom(32)
        y = os.urandom(32)
        msg = RgMessage(rg_x=x, rg_y=y)
        data = msg.pack()
        assert len(data) == 64
        got = RgMessage.unpack(data)
        assert got.rg_x == x
        assert got.rg_y == y
        assert RgMessage.DATA_TYPE_INDEX == 0x0148

    def test_rt_message(self):
        x = os.urandom(32)
        y = os.urandom(32)
        msg = RtMessage(rt_x=x, rt_y=y)
        data = msg.pack()
        assert len(data) == 64
        got = RtMessage.unpack(data)
        assert got.rt_x == x
        assert got.rt_y == y
        assert RtMessage.DATA_TYPE_INDEX == 0x0149


class TestSignalingRegistry:
    """验证配对信令已注册到信令注册表"""

    PAIRING_INDICES: ClassVar[list[int]] = [
        0x0133, 0x0134, 0x0135, 0x0136, 0x0137,
        0x0138, 0x0139, 0x013A, 0x013B, 0x013C,
        0x013F, 0x0141, 0x0142, 0x0147, 0x0148, 0x0149,
    ]

    @pytest.mark.parametrize("idx", PAIRING_INDICES)
    def test_registered(self, idx):
        assert idx in _SIGNALING_REGISTRY

    def test_encode_decode_pairing_request(self):
        crypto = bytes([0x01, 0x02, 0x01, 0x02])
        msg = PairingRequest(
            io_capability=0x04,
            oob_data_flag=0x00,
            auth_request=0b01_1_0_0000,
            max_key_length=16,
            security_dist_info=0x03,
            crypto_capability=crypto,
            psk_indication=0x01,
        )
        frame = encode_signaling(msg)
        got = decode_signaling(frame)
        assert isinstance(got, PairingRequest)
        assert got.io_capability == 0x04
        assert got.crypto_capability == crypto

    def test_encode_decode_pairing_confirm(self):
        pk_x = os.urandom(32)
        pk_y = os.urandom(32)
        msg = PairingConfirm(
            key_length=16,
            auth_method=0x05,
            crypto_algorithm=bytes([0x01, 0x01, 0x02, 0x02]),
            g_public_key_x=pk_x,
            g_public_key_y=pk_y,
        )
        frame = encode_signaling(msg)
        got = decode_signaling(frame)
        assert isinstance(got, PairingConfirm)
        assert got.g_public_key_x == pk_x
        assert got.g_public_key_y == pk_y


# ── 输入校验 ValueError 覆盖 ──


class TestValidationErrors:
    """安全信令 pack/unpack 输入校验。"""

    def test_bytes_message_pack_wrong_length(self):
        with pytest.raises(ValueError, match="字段长度"):
            TNodeConfirmCode(b"\x00" * 15).pack()

    def test_bytes_message_unpack_short(self):
        with pytest.raises(ValueError, match="数据不足"):
            TNodeConfirmCode.unpack(b"\x00" * 15)

    def test_two_bytes_message_pack_wrong_length(self):
        with pytest.raises(ValueError, match="字段长度错误"):
            PairingInitialInfo(b"\x00" * 31, b"\x00" * 32).pack()

    def test_two_bytes_message_unpack_short(self):
        with pytest.raises(ValueError, match="数据不足"):
            PairingInitialInfo.unpack(b"\x00" * 63)

    def test_pairing_initiate_unpack_empty(self):
        with pytest.raises(ValueError, match="数据不足"):
            PairingInitiate.unpack(b"")

    def test_pairing_request_pack_bad_crypto(self):
        req = PairingRequest(0, 0, 0, 16, 0, b"\x00" * 3, 0)
        with pytest.raises(ValueError, match="crypto_capability"):
            req.pack()

    def test_pairing_request_unpack_short(self):
        with pytest.raises(ValueError, match="数据不足"):
            PairingRequest.unpack(b"\x00" * 9)

    def test_pairing_response_pack_bad_crypto(self):
        resp = PairingResponse(0, 0, 0, 16, 0, b"\x00" * 3, 0)
        with pytest.raises(ValueError, match="crypto_capability"):
            resp.pack()

    def test_pairing_response_unpack_short(self):
        with pytest.raises(ValueError, match="数据不足"):
            PairingResponse.unpack(b"\x00" * 9)

    def test_pairing_confirm_pack_bad_crypto_algorithm(self):
        msg = PairingConfirm(16, 0, b"\x00" * 3, b"\x00" * 32, b"\x00" * 32)
        with pytest.raises(ValueError, match="crypto_algorithm"):
            msg.pack()

    def test_pairing_confirm_pack_bad_pubkey_x(self):
        msg = PairingConfirm(16, 0, b"\x00" * 4, b"\x00" * 31, b"\x00" * 32)
        with pytest.raises(ValueError, match="g_public_key_x"):
            msg.pack()

    def test_pairing_confirm_pack_bad_pubkey_y(self):
        msg = PairingConfirm(16, 0, b"\x00" * 4, b"\x00" * 32, b"\x00" * 31)
        with pytest.raises(ValueError, match="g_public_key_y"):
            msg.pack()

    def test_pairing_confirm_unpack_short(self):
        with pytest.raises(ValueError, match="数据不足"):
            PairingConfirm.unpack(b"\x00" * 69)

    def test_pairing_failure_unpack_empty(self):
        with pytest.raises(ValueError, match="数据不足"):
            PairingFailure.unpack(b"")
