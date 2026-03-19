"""功率控制信令编解码与状态管理测试 -- 7.2.13 / 7.3.2.27-29"""


import pytest

from nearlink_sdr.mac.power_control import (
    TX_POWER_STOP_MANAGEMENT,
    TX_POWER_UNAVAILABLE,
    Bandwidth,
    FreqDensity,
    PowerChangeIndication,
    PowerController,
    PowerControlRequest,
    PowerControlResponse,
)

# ============================================================================
# 7.3.2.27 功率控制请求
# ============================================================================

class TestPowerControlRequest:
    def test_pack_unpack_roundtrip(self):
        req = PowerControlRequest(
            frame_type=5,
            bandwidth=Bandwidth.BW_2MHZ,
            freq_density=FreqDensity.RATIO_8_1,
            tx_power_change=-3,
            sender_tx_power=10,
        )
        data = req.pack()
        assert len(data) == 3
        decoded = PowerControlRequest.unpack(data)
        assert decoded.frame_type == 5
        assert decoded.bandwidth == Bandwidth.BW_2MHZ
        assert decoded.freq_density == FreqDensity.RATIO_8_1
        assert decoded.tx_power_change == -3
        assert decoded.sender_tx_power == 10

    def test_boundary_values(self):
        req = PowerControlRequest(0, 0, 0, -128, -127)
        data = req.pack()
        dec = PowerControlRequest.unpack(data)
        assert dec.tx_power_change == -128
        assert dec.sender_tx_power == -127

    def test_max_values(self):
        req = PowerControlRequest(15, 3, 3, 127, 20)
        data = req.pack()
        dec = PowerControlRequest.unpack(data)
        assert dec.frame_type == 15
        assert dec.bandwidth == 3
        assert dec.freq_density == 3
        assert dec.tx_power_change == 127
        assert dec.sender_tx_power == 20

    def test_unavailable_power(self):
        req = PowerControlRequest(0, 0, 0, 0, TX_POWER_UNAVAILABLE)
        data = req.pack()
        dec = PowerControlRequest.unpack(data)
        assert dec.sender_tx_power == TX_POWER_UNAVAILABLE

    def test_data_length_check(self):
        with pytest.raises(ValueError, match="数据长度不足"):
            PowerControlRequest.unpack(b"\x00\x00")

    def test_known_encoding(self):
        # frame_type=2(0010), bw=1(01), fd=0(00) => byte0 = 0b0010_01_00 = 0x24
        # tx_power_change = +5 => 0x05
        # sender_tx_power = -10 => 0xF6
        req = PowerControlRequest(2, Bandwidth.BW_2MHZ, FreqDensity.RATIO_4_1, 5, -10)
        data = req.pack()
        assert data == bytes([0x24, 0x05, 0xF6])


# ============================================================================
# 7.3.2.28 功率控制响应
# ============================================================================

class TestPowerControlResponse:
    def test_pack_unpack_roundtrip(self):
        resp = PowerControlResponse(
            sender_min_power=False,
            sender_max_power=True,
            tx_power_change=3,
            sender_tx_power=15,
            acceptable_power_reduction=42,
        )
        data = resp.pack()
        assert len(data) == 4
        dec = PowerControlResponse.unpack(data)
        assert dec.sender_min_power is False
        assert dec.sender_max_power is True
        assert dec.tx_power_change == 3
        assert dec.sender_tx_power == 15
        assert dec.acceptable_power_reduction == 42

    def test_min_power_flag(self):
        resp = PowerControlResponse(True, False, -5, -100, 0)
        data = resp.pack()
        dec = PowerControlResponse.unpack(data)
        assert dec.sender_min_power is True
        assert dec.sender_max_power is False
        assert dec.tx_power_change == -5

    def test_stop_management(self):
        resp = PowerControlResponse(False, False, 0, TX_POWER_STOP_MANAGEMENT, 0)
        data = resp.pack()
        dec = PowerControlResponse.unpack(data)
        assert dec.sender_tx_power == TX_POWER_STOP_MANAGEMENT

    def test_data_length_check(self):
        with pytest.raises(ValueError, match="数据长度不足"):
            PowerControlResponse.unpack(b"\x00\x00\x00")

    def test_known_encoding(self):
        # sender_min=1, sender_max=0, reserved=0 => byte0 = 0b1_0_000000 = 0x80
        # tx_power_change = -1 => 0xFF
        # sender_tx_power = 0 => 0x00
        # acceptable_power_reduction = 200 => 0xC8
        resp = PowerControlResponse(True, False, -1, 0, 200)
        data = resp.pack()
        assert data == bytes([0x80, 0xFF, 0x00, 0xC8])


# ============================================================================
# 7.3.2.29 功率变化指示
# ============================================================================

class TestPowerChangeIndication:
    def test_pack_unpack_roundtrip(self):
        ind = PowerChangeIndication(
            frame_type=3,
            bandwidth=Bandwidth.BW_4MHZ,
            freq_density=FreqDensity.RATIO_16_1,
            sender_min_power=True,
            sender_max_power=False,
            tx_power_change=-10,
            sender_tx_power=5,
        )
        data = ind.pack()
        assert len(data) == 4
        dec = PowerChangeIndication.unpack(data)
        assert dec.frame_type == 3
        assert dec.bandwidth == Bandwidth.BW_4MHZ
        assert dec.freq_density == FreqDensity.RATIO_16_1
        assert dec.sender_min_power is True
        assert dec.sender_max_power is False
        assert dec.tx_power_change == -10
        assert dec.sender_tx_power == 5

    def test_data_length_check(self):
        with pytest.raises(ValueError, match="数据长度不足"):
            PowerChangeIndication.unpack(b"\x00\x00\x00")

    def test_known_encoding(self):
        # frame_type=7(0111), bw=0(00), fd=3(11) => byte0 = 0b0111_00_11 = 0x73
        # sender_min=0, sender_max=1, reserved=0 => byte1 = 0b0_1_000000 = 0x40
        # tx_power_change = 10 => 0x0A
        # sender_tx_power = -20 => 0xEC
        ind = PowerChangeIndication(7, 0, 3, False, True, 10, -20)
        data = ind.pack()
        assert data == bytes([0x73, 0x40, 0x0A, 0xEC])


# ============================================================================
# PowerController 状态管理
# ============================================================================

class TestPowerController:
    def test_init_defaults(self):
        pc = PowerController(tx_power_dbm=0.0)
        assert pc.tx_power_dbm == 0.0
        assert not pc.is_at_min_power
        assert not pc.is_at_max_power

    def test_at_min_power(self):
        pc = PowerController(tx_power_dbm=-127.0, min_power_dbm=-127.0)
        assert pc.is_at_min_power

    def test_at_max_power(self):
        pc = PowerController(tx_power_dbm=20.0, max_power_dbm=20.0)
        assert pc.is_at_max_power

    def test_acceptable_reduction(self):
        pc = PowerController(tx_power_dbm=10.0, min_power_dbm=-20.0)
        assert pc.acceptable_power_reduction == 30

    def test_acceptable_reduction_clamped(self):
        pc = PowerController(tx_power_dbm=10.0, min_power_dbm=-300.0)
        assert pc.acceptable_power_reduction == 255

    # -- 场景 a: 处理请求 --

    def test_handle_request_normal(self):
        pc = PowerController(tx_power_dbm=10.0, min_power_dbm=-20.0, max_power_dbm=20.0)
        req = PowerControlRequest(0, 0, 0, tx_power_change=-5, sender_tx_power=0)
        resp = pc.handle_request(req)
        assert pc.tx_power_dbm == 5.0
        assert resp.tx_power_change == -5
        assert resp.sender_tx_power == 5

    def test_handle_request_clamped_at_min(self):
        pc = PowerController(tx_power_dbm=-18.0, min_power_dbm=-20.0, max_power_dbm=20.0)
        req = PowerControlRequest(0, 0, 0, tx_power_change=-10, sender_tx_power=0)
        resp = pc.handle_request(req)
        assert pc.tx_power_dbm == -20.0
        assert resp.tx_power_change == -2
        assert resp.sender_min_power is True

    def test_handle_request_clamped_at_max(self):
        pc = PowerController(tx_power_dbm=18.0, min_power_dbm=-20.0, max_power_dbm=20.0)
        req = PowerControlRequest(0, 0, 0, tx_power_change=10, sender_tx_power=0)
        resp = pc.handle_request(req)
        assert pc.tx_power_dbm == 20.0
        assert resp.tx_power_change == 2
        assert resp.sender_max_power is True

    # -- 场景 b: 创建请求 --

    def test_create_request(self):
        pc = PowerController(tx_power_dbm=5.0)
        req = pc.create_request(-3, frame_type=2, bandwidth=Bandwidth.BW_2MHZ)
        assert req.tx_power_change == -3
        assert req.sender_tx_power == 5
        assert req.frame_type == 2
        assert req.bandwidth == Bandwidth.BW_2MHZ

    # -- 场景 c: 功率等级管理 --

    def test_power_management_lifecycle(self):
        pc = PowerController(tx_power_dbm=10.0)
        assert not pc.power_management_active
        pc.start_power_management()
        assert pc.power_management_active
        pc.stop_power_management()
        assert not pc.power_management_active

    def test_create_change_indication(self):
        pc = PowerController(tx_power_dbm=8.0, min_power_dbm=-20.0, max_power_dbm=20.0)
        ind = pc.create_change_indication(-2, frame_type=3, bandwidth=Bandwidth.BW_4MHZ)
        assert ind.tx_power_change == -2
        assert ind.sender_tx_power == 8
        assert ind.sender_min_power is False
        assert ind.sender_max_power is False

    # -- 场景 d: 查询功率等级 --

    def test_create_query_request(self):
        pc = PowerController(tx_power_dbm=12.0)
        req = pc.create_query_request(frame_type=1)
        assert req.tx_power_change == 0
        assert req.sender_tx_power == 12
        assert req.frame_type == 1
