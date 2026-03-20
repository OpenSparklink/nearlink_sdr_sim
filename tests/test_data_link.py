"""数据链路传输规程 + 同步等时链路管理 测试。"""

from __future__ import annotations

from nearlink_sdr.phy.data_link import (
    AdaptMode,
    AperiodicServiceAdaptor,
    AsyncDataLinkParams,
    AsyncFlowControl,
    EventGroupSet,
    PeriodicServiceAdaptor,
    SyncDataDiscard,
    SyncDataLinkParams,
    SyncFlowControl,
    TransmissionMode,
)

# ======================================================================
# 6.5.1.2 异步数据链路参数
# ======================================================================


class TestAsyncDataLinkParams:
    def test_default_params(self):
        p = AsyncDataLinkParams()
        assert p.tx_pdu_max == 251
        assert p.rx_pdu_max == 251
        assert p.mode == TransmissionMode.UNICAST
        assert p.first_tx is True

    def test_max_event_length(self):
        p = AsyncDataLinkParams(tx_max_time_offset=10, rx_max_time_offset=8)
        assert p.max_event_length == 18

    def test_custom_mode(self):
        p = AsyncDataLinkParams(mode=TransmissionMode.MULTICAST)
        assert p.mode == TransmissionMode.MULTICAST


# ======================================================================
# 6.5.1.3 异步数据链路流控
# ======================================================================


class TestAsyncFlowControl:
    def setup_method(self):
        self.fc = AsyncFlowControl()

    def test_unicast_stop_on_all_zero(self):
        assert self.fc.should_stop_unicast_tx(0, 0, True, 0) is True

    def test_unicast_no_stop_on_data(self):
        assert self.fc.should_stop_unicast_tx(0, 0, True, 10) is False

    def test_unicast_stop_on_no_feedback(self):
        assert self.fc.should_stop_unicast_tx(0, None, None, None) is True

    def test_unicast_no_stop_flow_nonzero(self):
        assert self.fc.should_stop_unicast_tx(1, 0, True, 0) is False

    def test_multicast_semi_reliable_stop(self):
        assert self.fc.should_stop_multicast_semi_reliable(0, False) is True

    def test_multicast_semi_reliable_no_stop(self):
        assert self.fc.should_stop_multicast_semi_reliable(0, True) is False

    def test_multicast_full_stop(self):
        members = [(0, True, 0), (0, True, 0)]
        assert self.fc.should_stop_multicast_full(0, members) is True

    def test_multicast_full_no_stop_nack(self):
        members = [(0, False, 0), (0, True, 0)]
        assert self.fc.should_stop_multicast_full(0, members) is False

    def test_feedback_leader_stop(self):
        members = [(0, True, 0)]
        assert self.fc.should_stop_feedback_multicast_leader(0, members) is True

    def test_feedback_member_stop(self):
        assert self.fc.should_stop_feedback_multicast_member(0, True) is True

    def test_feedback_member_no_stop(self):
        assert self.fc.should_stop_feedback_multicast_member(1, True) is False


# ======================================================================
# 6.5.2.2 同步数据链路参数
# ======================================================================


class TestSyncDataLinkParams:
    def test_default_params(self):
        p = SyncDataLinkParams()
        assert p.event_count == 1
        assert p.new_pkt_count == 1
        assert p.discard_period == 3
        assert p.adapt_mode == AdaptMode.PERIODIC

    def test_max_event_length(self):
        p = SyncDataLinkParams(tx_max_time_offset=5, rx_max_time_offset=3)
        assert p.max_event_length == 8


# ======================================================================
# 6.5.2.3 同步数据链路流控
# ======================================================================


class TestSyncFlowControl:
    def setup_method(self):
        self.fc = SyncFlowControl()

    def test_unicast_stop(self):
        assert self.fc.should_stop_unicast_tx(0, 0, True, 0) is True

    def test_unicast_no_stop_on_no_feedback(self):
        # 同步链路: 未收到反馈不停止 (与异步不同)
        assert self.fc.should_stop_unicast_tx(0, None, None, None) is False

    def test_multicast_semi_reliable(self):
        assert self.fc.should_stop_multicast_semi_reliable(0, False) is True

    def test_feedback_leader(self):
        assert self.fc.should_stop_feedback_leader(0, [(0, True, 0)]) is True

    def test_feedback_member(self):
        assert self.fc.should_stop_feedback_member(0, True) is True


# ======================================================================
# 6.5.2.4 同步数据丢弃机制
# ======================================================================


class TestSyncDataDiscard:
    def test_local_baseline_early(self):
        d = SyncDataDiscard(new_pkt_count=2, discard_period=3)
        d.event_group_index = 2
        assert d.local_baseline == 0

    def test_local_baseline_late(self):
        d = SyncDataDiscard(new_pkt_count=2, discard_period=3)
        d.event_group_index = 3
        assert d.local_baseline == 2

    def test_local_baseline_much_later(self):
        d = SyncDataDiscard(new_pkt_count=2, discard_period=3)
        d.event_group_index = 5
        assert d.local_baseline == 6

    def test_on_ack(self):
        d = SyncDataDiscard()
        d.on_ack()
        assert d.tx_sn == 1
        assert d.payload_count == 1

    def test_on_nack(self):
        d = SyncDataDiscard()
        d.on_nack_or_timeout()
        assert d.tx_sn == 0

    def test_event_group_boundary(self):
        d = SyncDataDiscard(new_pkt_count=2)
        d.tx_sn = 3
        d.on_event_group_boundary()
        assert d.tx_sn == 1
        assert d.event_group_index == 1

    def test_event_group_boundary_clamp(self):
        d = SyncDataDiscard(new_pkt_count=5)
        d.tx_sn = 2
        d.on_event_group_boundary()
        assert d.tx_sn == 0

    def test_is_discarded(self):
        d = SyncDataDiscard(new_pkt_count=2, discard_period=3)
        d.event_group_index = 4
        assert d.is_discarded(1) is True
        assert d.is_discarded(4) is False

    def test_active_discard(self):
        d = SyncDataDiscard()
        d.tx_sn = 5
        d.active_discard()
        assert d.tx_sn == 6
        assert d.payload_count == 1

    def test_standard_example(self):
        """验证标准表14的样例: discard_period=3, event_count=4, new_pkt_count=2"""
        d = SyncDataDiscard(new_pkt_count=2, discard_period=3)
        # 事件组#0 ~ #2: local_baseline = 0
        for _eg in range(3):
            assert d.local_baseline == 0
            d.on_event_group_boundary()
        # 事件组#3: local_baseline = 2
        assert d.local_baseline == 2
        d.on_event_group_boundary()
        # 事件组#4: local_baseline = 4
        assert d.local_baseline == 4
        d.on_event_group_boundary()
        # 事件组#5: local_baseline = 6
        assert d.local_baseline == 6


# ======================================================================
# 6.5.2.5 事件组集合
# ======================================================================


class TestEventGroupSet:
    def test_single_group(self):
        egs = EventGroupSet(event_group_count=1)
        assert egs.event_group_offsets() == [0]

    def test_multiple_groups(self):
        egs = EventGroupSet(
            event_group_count=3,
            event_group_spacing_slots=10,
            schedule_slot_us=125,
        )
        offsets = egs.event_group_offsets()
        assert offsets == [0, 1250, 2500]

    def test_duration(self):
        egs = EventGroupSet(
            event_group_count=2,
            event_group_spacing_slots=10,
            event_group_period_us=5000,
            schedule_slot_us=125,
        )
        assert egs.set_duration_us() == 1250 + 5000

    def test_validate_ok(self):
        egs = EventGroupSet(
            event_group_count=2,
            event_group_spacing_slots=100,
            event_group_period_us=5000,
            schedule_slot_us=125,
        )
        assert egs.validate() is True

    def test_validate_overlap(self):
        egs = EventGroupSet(
            event_group_count=2,
            event_group_spacing_slots=10,
            event_group_period_us=5000,
            schedule_slot_us=125,
        )
        # 1250 < 5000, 会交叠
        assert egs.validate() is False

    def test_empty_group(self):
        egs = EventGroupSet(event_group_count=0)
        assert egs.set_duration_us() == 0


# ======================================================================
# 6.5.3.2 周期适配
# ======================================================================


class TestPeriodicServiceAdaptor:
    def test_segments_per_sdu(self):
        a = PeriodicServiceAdaptor(sdu_max=512, pdu_max=251)
        assert a.segments_per_sdu == 3  # ceil(512/251)

    def test_sdus_per_event_group(self):
        a = PeriodicServiceAdaptor(
            event_group_period_us=10000, sdu_period_us=2500,
        )
        assert a.sdus_per_event_group == 4

    def test_frames_per_event_group(self):
        a = PeriodicServiceAdaptor(
            sdu_max=512, pdu_max=251,
            event_group_period_us=10000, sdu_period_us=5000,
        )
        assert a.frames_per_event_group == 6  # 3 * 2

    def test_segment_sdu(self):
        a = PeriodicServiceAdaptor(sdu_max=10, pdu_max=4)
        sdu = b"\x01\x02\x03\x04\x05\x06\x07\x08\x09\x0a"
        segs = a.segment_sdu(sdu)
        assert len(segs) == 3  # ceil(10/4) = 3
        assert segs[0] == b"\x01\x02\x03\x04"
        assert segs[1] == b"\x05\x06\x07\x08"
        assert segs[2] == b"\x09\x0a"

    def test_segment_sdu_empty(self):
        a = PeriodicServiceAdaptor(sdu_max=10, pdu_max=4)
        segs = a.segment_sdu(b"")
        assert segs == [b""]

    def test_segment_sdu_pad(self):
        a = PeriodicServiceAdaptor(sdu_max=20, pdu_max=10)
        sdu = b"\x01\x02\x03"
        segs = a.segment_sdu(sdu)
        assert len(segs) == 2  # ceil(20/10) = 2
        assert segs[0] == b"\x01\x02\x03"
        assert segs[1] == b""

    def test_reassemble_sdu(self):
        a = PeriodicServiceAdaptor()
        pdus = [b"\x01\x02", b"\x03\x04"]
        assert a.reassemble_sdu(pdus) == b"\x01\x02\x03\x04"

    def test_tx_accept_time(self):
        a = PeriodicServiceAdaptor(
            event_group_period_us=10000, sdu_period_us=5000,
            sync_ref_delay_us=100,
        )
        t0 = a.tx_accept_time(event_group_start_us=50000)
        # t0 = 50000 - (2-1)*5000 - 100 = 44900
        assert t0 == 44900

    def test_rx_deliver_time(self):
        a = PeriodicServiceAdaptor(
            event_group_period_us=10000,
            sync_anchor_delay_us=200,
            discard_period=3,
        )
        r1 = a.rx_deliver_time(event_group_start_us=0)
        # r1 = 0 + 200 + (3-1)*10000 = 20200
        assert r1 == 20200


# ======================================================================
# 6.5.3.3 非周期适配
# ======================================================================


class TestAperiodicServiceAdaptor:
    def test_fragment_small_sdu(self):
        a = AperiodicServiceAdaptor(pdu_max=100, header_size=4)
        sdu = b"\x00" * 50
        frags = a.fragment_sdu(sdu, time_offset_us=1234)
        assert len(frags) == 1
        assert frags[0].is_first is True
        assert frags[0].is_last is True
        assert frags[0].time_offset_us == 1234
        assert frags[0].data == sdu

    def test_fragment_large_sdu(self):
        a = AperiodicServiceAdaptor(pdu_max=20, header_size=4)
        sdu = b"\xAB" * 40
        frags = a.fragment_sdu(sdu, time_offset_us=500)
        # payload_cap = 16, 需要 ceil(40/16) = 3 个分片
        assert len(frags) == 3
        assert frags[0].is_first is True
        assert frags[0].is_last is False
        assert frags[0].time_offset_us == 500
        assert frags[1].is_first is False
        assert frags[1].time_offset_us == 0
        assert frags[2].is_last is True

    def test_fragment_empty_sdu(self):
        a = AperiodicServiceAdaptor()
        frags = a.fragment_sdu(b"", time_offset_us=0)
        assert len(frags) == 1
        assert frags[0].is_first is True
        assert frags[0].is_last is True

    def test_reassemble(self):
        a = AperiodicServiceAdaptor(pdu_max=20, header_size=4)
        sdu = b"\xCD" * 40
        frags = a.fragment_sdu(sdu, time_offset_us=999)
        result, offset = a.reassemble_sdu(frags)
        assert result == sdu
        assert offset == 999

    def test_rx_deliver_time(self):
        a = AperiodicServiceAdaptor()
        r1 = a.rx_deliver_time(
            event_group_start_us=10000,
            sync_anchor_delay_us=200,
            discard_period=3,
            event_group_period_us=5000,
            sdu_period_us=2000,
            sdu_time_offset_us=500,
        )
        # r1 = 10000 + 200 + 3*5000 + 2000 - 500 = 26700
        assert r1 == 26700


# ======================================================================
# 7.2.19 同步等时链路管理 (LinkManager 方法)
# ======================================================================


class TestIsochronousLinkManagement:
    def _make_lm(self):
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
        # 通过标准事件序列推入 CONNECTED 状态
        lm.process_event(Event(EventType.START_BROADCAST))
        lm.process_event(Event(
            EventType.ACCESS_REQUEST_RECEIVED,
            {"accepted": True, "role": Role.G_NODE},
        ))
        return lm

    def test_isochronous_link_setup(self):
        lm = self._make_lm()
        frame = lm.request_isochronous_link_setup(
            event_group_set_id=1, event_group_id=2,
            event_group_period=100, event_period=50,
            event_count=4,
        )
        assert frame is not None

    def test_isochronous_param_exchange(self):
        lm = self._make_lm()
        frame = lm.request_isochronous_param_exchange(
            event_group_set_id=1, event_group_id=2,
            param_tag_id=3,
        )
        assert frame is not None

    def test_isochronous_param_exchange_response(self):
        lm = self._make_lm()
        frame = lm.respond_isochronous_param_exchange(
            event_group_set_id=1, event_group_id=2,
            param_tag_id=3,
        )
        assert frame is not None

    def test_isochronous_param_update_request(self):
        lm = self._make_lm()
        frame = lm.request_isochronous_param_update(
            param_tag_id=1, event_group_set_id=2, event_group_id=3,
        )
        assert frame is not None

    def test_isochronous_param_update_indication(self):
        lm = self._make_lm()
        frame = lm.indicate_isochronous_param_update(
            param_tag_id=1, event_group_set_id=2, event_group_id=3,
            effective_ref_slot=1000, event_group_offset=50,
        )
        assert frame is not None


# ======================================================================
# TransmissionMode / AdaptMode 枚举
# ======================================================================


class TestEnums:
    def test_transmission_modes(self):
        assert TransmissionMode.UNICAST == 0
        assert TransmissionMode.BROADCAST_SYNC == 5

    def test_adapt_modes(self):
        assert AdaptMode.PERIODIC == 0
        assert AdaptMode.APERIODIC == 1
