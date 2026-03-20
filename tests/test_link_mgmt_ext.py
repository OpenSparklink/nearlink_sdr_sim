"""7.2.20-7.2.25 链路管理扩展方法测试。"""

from __future__ import annotations


def _make_connected_lm():
    """构造处于 CONNECTED 状态的 LinkManager 实例。"""
    from nearlink_sdr.mac.link_manager import (
        Event,
        EventType,
        LinkManager,
        LinkManagerCallback,
        Role,
    )

    class DummyCb(LinkManagerCallback):
        pass

    lm = LinkManager(callback=DummyCb())
    lm.process_event(Event(EventType.START_BROADCAST))
    lm.process_event(Event(
        EventType.ACCESS_REQUEST_RECEIVED,
        {"accepted": True, "role": Role.G_NODE},
    ))
    return lm


# ======================================================================
# 7.2.20 广播链路管理
# ======================================================================


class TestBroadcastLinkManagement:
    def test_broadcast_link_setup_default(self):
        lm = _make_connected_lm()
        frame = lm.indicate_broadcast_link_setup()
        assert frame is not None

    def test_broadcast_link_setup_custom(self):
        lm = _make_connected_lm()
        frame = lm.indicate_broadcast_link_setup(
            base_link_id=0x123456, event_count=4,
            frame_type=2, bandwidth=1,
        )
        assert frame is not None

    def test_broadcast_link_param_update_default(self):
        lm = _make_connected_lm()
        frame = lm.indicate_broadcast_link_param_update()
        assert frame is not None

    def test_broadcast_link_param_update_custom(self):
        lm = _make_connected_lm()
        frame = lm.indicate_broadcast_link_param_update(
            event_group_set_id=3, event_group_period=200,
            sdu_max=100,
        )
        assert frame is not None

    def test_broadcast_hop_map_update(self):
        lm = _make_connected_lm()
        frame = lm.update_broadcast_hop_map(
            hop_map=b"\xaa" * 10, effective_slot=5000,
        )
        assert frame is not None

    def test_broadcast_link_disconnect(self):
        lm = _make_connected_lm()
        frame = lm.indicate_broadcast_link_disconnect(
            link_id=0x001234, error_reason=1,
        )
        assert frame is not None


# ======================================================================
# 7.2.21 系统管理帧链路管理
# ======================================================================


class TestSMFLinkManagement:
    def test_smf_param_update_request(self):
        lm = _make_connected_lm()
        frame = lm.request_smf_param_update(
            smf_period=200, link_id=0x100,
        )
        assert frame is not None

    def test_smf_param_update_indication(self):
        lm = _make_connected_lm()
        frame = lm.indicate_smf_param_update(
            smf_period=200, crc_init=0xDEADBEEF,
        )
        assert frame is not None

    def test_smf_timeslot_update_request(self):
        lm = _make_connected_lm()
        frame = lm.request_smf_timeslot_update(
            link_id=0x100, current_offset=10,
            offsets=(1, 2, 3, 4),
        )
        assert frame is not None

    def test_smf_timeslot_update_response(self):
        lm = _make_connected_lm()
        frame = lm.respond_smf_timeslot_update(
            link_id=0x100, offset=5, effective_slot=10000,
        )
        assert frame is not None

    def test_smf_signaling_terminate(self):
        lm = _make_connected_lm()
        frame = lm.terminate_smf_signaling(terminate_type=1)
        assert frame is not None


# ======================================================================
# 7.2.22 异步组播链路管理
# ======================================================================


class TestAsyncMulticastLinkManagement:
    def test_multicast_link_setup_default(self):
        lm = _make_connected_lm()
        frame = lm.indicate_async_multicast_link_setup()
        assert frame is not None

    def test_multicast_link_setup_custom(self):
        lm = _make_connected_lm()
        frame = lm.indicate_async_multicast_link_setup(
            tx_link_id=0x100, rx_link_id=0x200,
            event_group_period=50, tx_sdu_max=128,
        )
        assert frame is not None

    def test_multicast_param_exchange_request(self):
        lm = _make_connected_lm()
        frame = lm.request_async_multicast_param_exchange(
            payload=b"\xab" * 41,
        )
        assert frame is not None

    def test_multicast_param_exchange_response(self):
        lm = _make_connected_lm()
        frame = lm.respond_async_multicast_param_exchange(
            payload=b"\xcd" * 41,
        )
        assert frame is not None

    def test_multicast_param_update_request(self):
        lm = _make_connected_lm()
        frame = lm.request_async_multicast_param_update(
            param_tag_id=1, event_group_set_id=2, event_group_id=3,
        )
        assert frame is not None

    def test_multicast_param_update_indication(self):
        lm = _make_connected_lm()
        frame = lm.indicate_async_multicast_param_update(
            param_tag_id=1, effective_ref_slot=5000,
            event_group_offset=100,
        )
        assert frame is not None

    def test_multicast_reconfig_default(self):
        lm = _make_connected_lm()
        frame = lm.indicate_async_multicast_reconfig()
        assert frame is not None

    def test_multicast_reconfig_custom(self):
        lm = _make_connected_lm()
        frame = lm.indicate_async_multicast_reconfig(
            event_group_period=200, timeout=600,
        )
        assert frame is not None

    def test_multicast_disconnect(self):
        lm = _make_connected_lm()
        frame = lm.disconnect_multicast(link_id=0x123)
        assert frame is not None


# ======================================================================
# 7.2.23 窄带跳频测量
# ======================================================================


class TestNarrowbandMeasurement:
    def test_meas_cap_request(self):
        lm = _make_connected_lm()
        frame = lm.request_narrowband_meas_cap()
        assert frame is not None

    def test_meas_cap_response(self):
        lm = _make_connected_lm()
        frame = lm.respond_narrowband_meas_cap(payload=b"\x01" * 32)
        assert frame is not None

    def test_meas_config(self):
        lm = _make_connected_lm()
        frame = lm.config_narrowband_meas(payload=b"\x02\x03")
        assert frame is not None

    def test_meas_report(self):
        lm = _make_connected_lm()
        frame = lm.report_narrowband_meas(payload=b"\x04\x05")
        assert frame is not None

    def test_meas_action(self):
        lm = _make_connected_lm()
        frame = lm.action_narrowband_meas(
            config_index=1, start_slot=100, action_config=2,
        )
        assert frame is not None

    def test_coordinate_request(self):
        lm = _make_connected_lm()
        frame = lm.request_coordinate()
        assert frame is not None

    def test_coordinate_report(self):
        lm = _make_connected_lm()
        frame = lm.report_coordinate(
            rel_x=100, rel_y=200, rel_z=50,
            abs_lon=116000000, abs_lat=40000000, abs_alt=50,
        )
        assert frame is not None

    def test_coordinate_config(self):
        lm = _make_connected_lm()
        frame = lm.config_coordinate(
            rel_x=10, rel_y=20, rel_z=30,
        )
        assert frame is not None

    def test_narrowband_delay_request(self):
        lm = _make_connected_lm()
        frame = lm.request_narrowband_delay()
        assert frame is not None

    def test_narrowband_delay_response(self):
        lm = _make_connected_lm()
        frame = lm.respond_narrowband_delay(payload=b"\xaa\xbb")
        assert frame is not None


# ======================================================================
# 7.2.24 超宽带脉冲测量与感知
# ======================================================================


class TestUWBMeasAndSensing:
    def test_uwb_meas_cap_request(self):
        lm = _make_connected_lm()
        frame = lm.request_uwb_meas_cap()
        assert frame is not None

    def test_uwb_meas_cap_response(self):
        lm = _make_connected_lm()
        frame = lm.respond_uwb_meas_cap(payload=b"\x01" * 50)
        assert frame is not None

    def test_uwb_meas_config(self):
        lm = _make_connected_lm()
        frame = lm.config_uwb_meas(payload=b"\x10\x20")
        assert frame is not None

    def test_uwb_meas_config_feedback(self):
        lm = _make_connected_lm()
        frame = lm.feedback_uwb_meas_config(config_index=1, status=0)
        assert frame is not None

    def test_uwb_meas_report(self):
        lm = _make_connected_lm()
        frame = lm.report_uwb_meas(payload=b"\x30\x40")
        assert frame is not None

    def test_uwb_meas_action(self):
        lm = _make_connected_lm()
        frame = lm.action_uwb_meas(
            config_index=2, start_slot=500, action_config=1,
        )
        assert frame is not None

    def test_uwb_sensing_cap_request(self):
        lm = _make_connected_lm()
        frame = lm.request_uwb_sensing_cap()
        assert frame is not None

    def test_uwb_sensing_cap_response(self):
        lm = _make_connected_lm()
        frame = lm.respond_uwb_sensing_cap(payload=b"\x02" * 51)
        assert frame is not None

    def test_uwb_sensing_config(self):
        lm = _make_connected_lm()
        frame = lm.config_uwb_sensing(payload=b"\x50\x60")
        assert frame is not None

    def test_uwb_sensing_config_feedback(self):
        lm = _make_connected_lm()
        frame = lm.feedback_uwb_sensing_config(
            config_index=3, status=1,
        )
        assert frame is not None

    def test_uwb_sensing_report(self):
        lm = _make_connected_lm()
        frame = lm.report_uwb_sensing(payload=b"\x70\x80")
        assert frame is not None

    def test_uwb_sensing_action(self):
        lm = _make_connected_lm()
        frame = lm.action_uwb_sensing(
            config_index=4, start_slot=1000, action_config=2,
        )
        assert frame is not None

    def test_uwb_sensing_process_request(self):
        lm = _make_connected_lm()
        frame = lm.request_uwb_sensing_process(
            payload=b"\x01" * 16,
        )
        assert frame is not None

    def test_uwb_sensing_process_feedback(self):
        lm = _make_connected_lm()
        frame = lm.feedback_uwb_sensing_process(
            process_index=1, status=0,
        )
        assert frame is not None

    def test_uwb_proxy_sensing_request(self):
        lm = _make_connected_lm()
        frame = lm.request_uwb_proxy_sensing(
            proxy_index=1, sensing_index=2,
            meas_quantity=100, report_period=50, bandwidth=3,
        )
        assert frame is not None

    def test_uwb_proxy_sensing_feedback(self):
        lm = _make_connected_lm()
        frame = lm.feedback_uwb_proxy_sensing(
            proxy_index=1, sensing_index=2, status=0,
            meas_quantity1=100, meas_quantity2=200,
            bandwidth1=3, bandwidth2=4,
        )
        assert frame is not None


# ======================================================================
# 7.2.25 窄带跳频感知
# ======================================================================


class TestNarrowbandSensing:
    def test_sensing_request(self):
        lm = _make_connected_lm()
        frame = lm.request_narrowband_sensing(payload=b"\xaa" * 16)
        assert frame is not None

    def test_sensing_feedback(self):
        lm = _make_connected_lm()
        frame = lm.feedback_narrowband_sensing(
            process_index=1, status=0,
        )
        assert frame is not None

    def test_sensing_cap_request(self):
        lm = _make_connected_lm()
        frame = lm.request_narrowband_sensing_cap()
        assert frame is not None

    def test_sensing_cap_response(self):
        lm = _make_connected_lm()
        frame = lm.respond_narrowband_sensing_cap(
            payload=b"\xbb" * 50,
        )
        assert frame is not None

    def test_sensing_config(self):
        lm = _make_connected_lm()
        frame = lm.config_narrowband_sensing(payload=b"\xcc\xdd")
        assert frame is not None

    def test_sensing_config_feedback(self):
        lm = _make_connected_lm()
        frame = lm.feedback_narrowband_sensing_config(
            config_index=5, status=0,
        )
        assert frame is not None

    def test_sensing_report(self):
        lm = _make_connected_lm()
        frame = lm.report_narrowband_sensing(payload=b"\xee\xff")
        assert frame is not None

    def test_sensing_action(self):
        lm = _make_connected_lm()
        frame = lm.action_narrowband_sensing(
            config_index=6, start_slot=2000, action_config=3,
        )
        assert frame is not None

    def test_proxy_sensing_request(self):
        lm = _make_connected_lm()
        frame = lm.request_narrowband_proxy_sensing(
            proxy_index=1, sensing_index=2,
            meas_quantity=50, report_period=25, bandwidth=2,
        )
        assert frame is not None

    def test_proxy_sensing_feedback(self):
        lm = _make_connected_lm()
        frame = lm.feedback_narrowband_proxy_sensing(
            proxy_index=1, sensing_index=2, status=0,
            meas_quantity1=50, meas_quantity2=100,
            bandwidth1=2, bandwidth2=3,
        )
        assert frame is not None

    def test_meas_config_update_request(self):
        lm = _make_connected_lm()
        frame = lm.request_narrowband_meas_config_update(
            payload=b"\x01" * 32,
        )
        assert frame is not None

    def test_meas_config_update_indication(self):
        lm = _make_connected_lm()
        frame = lm.indicate_narrowband_meas_config_update(
            payload=b"\x02" * 32,
        )
        assert frame is not None


# ======================================================================
# 资源预留
# ======================================================================


class TestResourceReservation:
    def test_reserve_resource(self):
        lm = _make_connected_lm()
        frame = lm.reserve_resource(
            config_index=1, effective_slot=1000,
            event_group_period=100, event_period=10,
            event_length=5, event_count=3, scheduling_slot=2,
        )
        assert frame is not None

    def test_terminate_resource_reservation(self):
        lm = _make_connected_lm()
        frame = lm.terminate_resource_reservation(
            config_index=1, reason=0,
        )
        assert frame is not None
