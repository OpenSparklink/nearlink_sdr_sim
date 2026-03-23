"""基于 hypothesis 的模糊测试, 覆盖关键编解码和安全 API。"""

import numpy as np
import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from nearlink_sdr.common.bch import bch_31_26_encode, bch_63_24_encode
from nearlink_sdr.common.code_block_seg import (
    segment_with_crc,
    segment_without_crc,
)
from nearlink_sdr.common.crc import (
    CRC12_POLY,
    CRC24A_POLY,
    CRC24B_POLY,
    crc_attach,
    crc_check,
)
from nearlink_sdr.common.polar import PolarDecoder, PolarEncoder
from nearlink_sdr.common.scrambler import (
    descramble,
    scramble,
    scramble_sequence,
)
from nearlink_sdr.mac.crypto import (
    KdfType,
    aes_ccm_decrypt,
    aes_ccm_encrypt,
    aes_cmac,
    generate_resolvable_address,
    kdf,
    resolve_address,
    secure_random_256,
)
from nearlink_sdr.mac.frame import (
    AsyncDataFrame,
    ControlFrame,
    SyncDataFrame,
)

# ---------------------------------------------------------------------------
# 策略定义
# ---------------------------------------------------------------------------

bit_arrays = st.integers(min_value=1, max_value=256).flatmap(
    lambda n: st.builds(
        lambda data: np.array(data, dtype=np.uint8),
        st.lists(st.integers(0, 1), min_size=n, max_size=n),
    )
)

short_bit_arrays = st.integers(min_value=1, max_value=64).flatmap(
    lambda n: st.builds(
        lambda data: np.array(data, dtype=np.uint8),
        st.lists(st.integers(0, 1), min_size=n, max_size=n),
    )
)


# ---------------------------------------------------------------------------
# CRC roundtrip
# ---------------------------------------------------------------------------

class TestCRCFuzz:
    @given(
        data=bit_arrays,
        poly_choice=st.sampled_from([
            (CRC12_POLY, 12),
            (CRC24A_POLY, 24),
            (CRC24B_POLY, 24),
        ]),
    )
    @settings(max_examples=200, deadline=2000)
    def test_crc_roundtrip(self, data, poly_choice):
        poly, crc_len = poly_choice
        attached = crc_attach(data, poly, crc_len)
        assert len(attached) == len(data) + crc_len
        assert crc_check(attached, poly, crc_len)

    @given(data=bit_arrays)
    @settings(max_examples=100, deadline=2000)
    def test_crc_bitflip_detection(self, data):
        poly, crc_len = CRC24A_POLY, 24
        attached = crc_attach(data, poly, crc_len)
        idx = np.random.randint(0, len(attached))
        corrupted = attached.copy()
        corrupted[idx] ^= 1
        assert not crc_check(corrupted, poly, crc_len)


# ---------------------------------------------------------------------------
# Scrambler roundtrip
# ---------------------------------------------------------------------------

class TestScramblerFuzz:
    @given(
        data=bit_arrays,
        seed=st.integers(min_value=0, max_value=127),
    )
    @settings(max_examples=200, deadline=2000)
    def test_scramble_roundtrip(self, data, seed):
        scrambled = scramble(data, seed)
        recovered = descramble(scrambled, seed)
        np.testing.assert_array_equal(recovered, data)

    @given(
        data=bit_arrays,
        seed=st.integers(min_value=0, max_value=127),
    )
    @settings(max_examples=100, deadline=2000)
    def test_scramble_self_inverse(self, data, seed):
        double = scramble(scramble(data, seed), seed)
        np.testing.assert_array_equal(double, data)

    @given(seed=st.integers(min_value=128, max_value=1000))
    @settings(max_examples=20)
    def test_scramble_invalid_seed(self, seed):
        with pytest.raises(ValueError):
            scramble_sequence(10, seed)


# ---------------------------------------------------------------------------
# BCH 编码
# ---------------------------------------------------------------------------

class TestBCHFuzz:
    @given(
        data=st.builds(
            lambda bits: np.array(bits, dtype=np.uint8),
            st.lists(st.integers(0, 1), min_size=26, max_size=26),
        )
    )
    @settings(max_examples=200, deadline=2000)
    def test_bch_31_26_systematic(self, data):
        encoded = bch_31_26_encode(data)
        assert len(encoded) == 31
        np.testing.assert_array_equal(encoded[:26], data)

    @given(
        data=st.builds(
            lambda bits: np.array(bits, dtype=np.uint8),
            st.lists(st.integers(0, 1), min_size=24, max_size=24),
        )
    )
    @settings(max_examples=200, deadline=2000)
    def test_bch_63_24_systematic(self, data):
        encoded = bch_63_24_encode(data)
        assert len(encoded) == 63
        np.testing.assert_array_equal(encoded[:24], data)


# ---------------------------------------------------------------------------
# Polar 编解码 roundtrip
# ---------------------------------------------------------------------------

class TestPolarFuzz:
    @given(
        nk=st.sampled_from([(64, 16), (128, 48), (256, 128), (512, 384)]),
        data=st.data(),
    )
    @settings(
        max_examples=50,
        deadline=5000,
        suppress_health_check=[HealthCheck.too_slow],
    )
    def test_polar_roundtrip(self, nk, data):
        n, k = nk
        info = data.draw(st.builds(
            lambda bits: np.array(bits, dtype=np.uint8),
            st.lists(st.integers(0, 1), min_size=k, max_size=k),
        ))
        enc = PolarEncoder(n, k)
        dec = PolarDecoder(n, k)
        coded = enc.encode(info)
        assert len(coded) == n
        llr = np.where(coded == 0, 10.0, -10.0)
        recovered = dec.decode(llr)
        np.testing.assert_array_equal(recovered, info)


# ---------------------------------------------------------------------------
# 码块分割
# ---------------------------------------------------------------------------

class TestCodeBlockSegFuzz:
    @given(
        data=bit_arrays,
        rate=st.sampled_from(["1/4", "3/8", "1/2", "5/8", "3/4", "7/8"]),
    )
    @settings(max_examples=100, deadline=5000)
    def test_segment_concatenation(self, data, rate):
        segments = segment_without_crc(data, rate)
        assert len(segments) >= 1
        for n, _seg in segments:
            assert n in {64, 128, 256, 512, 1024}

    @given(
        data=st.builds(
            lambda bits: np.array(bits, dtype=np.uint8),
            st.lists(st.integers(0, 1), min_size=25, max_size=300),
        ),
        rate=st.sampled_from(["1/4", "3/8", "1/2", "5/8", "3/4", "7/8"]),
    )
    @settings(max_examples=50, deadline=5000)
    def test_segment_with_crc_valid(self, data, rate):
        segments = segment_with_crc(data, rate)
        assert len(segments) >= 1


# ---------------------------------------------------------------------------
# MAC 帧 pack/unpack roundtrip
# ---------------------------------------------------------------------------

class TestMACFrameFuzz:
    @given(
        data_type_index=st.integers(min_value=0, max_value=0xFFFF),
        payload=st.binary(min_size=0, max_size=200),
    )
    @settings(max_examples=200, deadline=2000)
    def test_control_frame_roundtrip(self, data_type_index, payload):
        frame = ControlFrame(data_type_index=data_type_index, payload=payload)
        packed = frame.pack()
        unpacked, consumed = ControlFrame.unpack(packed)
        assert consumed == len(packed)
        assert unpacked.data_type_index == data_type_index
        assert unpacked.payload == payload

    @given(
        segment_type=st.integers(min_value=0, max_value=3),
        data=st.binary(min_size=0, max_size=200),
    )
    @settings(max_examples=200, deadline=2000)
    def test_async_data_frame_roundtrip(self, segment_type, data):
        frame = AsyncDataFrame(segment_type=segment_type, data=data)
        packed = frame.pack()
        unpacked = AsyncDataFrame.unpack(packed)
        assert unpacked.segment_type == segment_type
        assert unpacked.data == data

    @given(
        pdu_seq=st.integers(min_value=0, max_value=31),
        event_group=st.integers(min_value=0, max_value=255),
        frame_format=st.integers(min_value=0, max_value=1),
        segment_type=st.integers(min_value=0, max_value=3),
        data=st.binary(min_size=0, max_size=100),
        time_offset=st.integers(min_value=0, max_value=0xFFFFFF),
        sdu_seq=st.integers(min_value=0, max_value=31),
    )
    @settings(max_examples=200, deadline=2000)
    def test_sync_data_frame_roundtrip(
        self, pdu_seq, event_group, frame_format,
        segment_type, data, time_offset, sdu_seq,
    ):
        frame = SyncDataFrame(
            pdu_seq=pdu_seq,
            event_group=event_group,
            frame_format=frame_format,
            segment_type=segment_type,
            data=data,
            time_offset=time_offset,
            sdu_seq=sdu_seq,
        )
        packed = frame.pack()
        unpacked = SyncDataFrame.unpack(packed)
        assert unpacked.pdu_seq == pdu_seq
        assert unpacked.event_group == event_group
        assert unpacked.frame_format == frame_format
        assert unpacked.segment_type == segment_type
        assert unpacked.data == data

    @given(raw=st.binary(min_size=0, max_size=2))
    @settings(max_examples=50, deadline=2000)
    def test_control_frame_unpack_short(self, raw):
        if len(raw) < 3:
            with pytest.raises((ValueError, IndexError, Exception)):
                ControlFrame.unpack(raw)


# ---------------------------------------------------------------------------
# AES-CCM 加解密 roundtrip
# ---------------------------------------------------------------------------

class TestCryptoFuzz:
    @given(
        plaintext=st.binary(min_size=1, max_size=256),
        ad=st.binary(min_size=0, max_size=64),
        mic_len=st.sampled_from([4, 6, 8, 10, 12, 14, 16]),
    )
    @settings(max_examples=100, deadline=5000)
    def test_aes_ccm_roundtrip(self, plaintext, ad, mic_len):
        key = b"\x01" * 16
        nonce = b"\x02" * 13
        ct, mic = aes_ccm_encrypt(key, nonce, plaintext, ad, mic_len)
        recovered = aes_ccm_decrypt(key, nonce, ct, mic, ad, mic_len)
        assert recovered == plaintext

    @given(
        key=st.binary(min_size=16, max_size=16),
        msg=st.binary(min_size=0, max_size=128),
    )
    @settings(max_examples=100, deadline=2000)
    def test_aes_cmac_deterministic(self, key, msg):
        result1 = aes_cmac(key, msg)
        result2 = aes_cmac(key, msg)
        assert result1 == result2
        assert len(result1) == 16

    @given(
        key=st.binary(min_size=16, max_size=16),
        msg=st.binary(min_size=0, max_size=64),
        kdf_type=st.sampled_from([KdfType.AES_CMAC]),
    )
    @settings(max_examples=50, deadline=2000)
    def test_kdf_deterministic(self, key, msg, kdf_type):
        r1 = kdf(kdf_type, key, msg)
        r2 = kdf(kdf_type, key, msg)
        assert r1 == r2

    @given(
        seed=st.binary(min_size=16, max_size=16),
        time_param=st.integers(min_value=0, max_value=0xFFFFFFFF),
    )
    @settings(max_examples=50, deadline=2000)
    def test_secure_random_256_output_size(self, seed, time_param):
        result = secure_random_256(seed, time_param)
        assert len(result) == 32

    @given(
        irk=st.binary(min_size=16, max_size=16),
        rand_part=st.integers(min_value=0, max_value=0xFFFF),
    )
    @settings(max_examples=50, deadline=2000)
    def test_resolvable_address_roundtrip(self, irk, rand_part):
        addr = generate_resolvable_address(KdfType.AES_CMAC, irk, rand_part)
        assert resolve_address(KdfType.AES_CMAC, irk, addr)

    @given(
        plaintext=st.binary(min_size=1, max_size=64),
        mic_len=st.sampled_from([4, 8, 16]),
    )
    @settings(max_examples=50, deadline=5000)
    def test_aes_ccm_tamper_detection(self, plaintext, mic_len):
        key = b"\xAA" * 16
        nonce = b"\xBB" * 13
        ct, mic = aes_ccm_encrypt(key, nonce, plaintext, b"", mic_len)
        tampered_ct = bytearray(ct)
        if len(tampered_ct) > 0:
            tampered_ct[0] ^= 0xFF
            with pytest.raises((ValueError, Exception)):
                aes_ccm_decrypt(
                    key, nonce, bytes(tampered_ct), mic, b"", mic_len
                )
