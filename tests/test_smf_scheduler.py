"""SMF 发送调度模块测试 — 标准 6.6.3。"""

from __future__ import annotations

import pytest

from nearlink_sdr.mac.smf import (
    LinkSignaling,
    OffsetSignaling,
    OffsetUnit,
    TimeResourceEntry,
)
from nearlink_sdr.mac.smf_scheduler import (
    SMFActivationSource,
    SMFScheduleParams,
    SMFTransmission,
    SMFTransmitScheduler,
    smf_params_from_access,
    smf_params_from_broadcast,
)

# ===== SMFScheduleParams 构造 =====


class TestSMFParamsFromAccess:
    def test_basic(self):
        p = smf_params_from_access(
            smf_baseline_slot=100,
            smf_offset=300,
            smf_link_id=0x000001,
            smf_period=800,
            smf_frame_type=2,
            smf_bandwidth=0,
            smf_pilot_density=0,
            smf_channel_count=3,
            smf_channel_table=b"\x00\x01\x02",
        )
        assert p.source == SMFActivationSource.ACCESS
        assert p.baseline_slot == 100
        assert p.interval == 800
        assert p.channel_count == 3

    def test_all_fields_set(self):
        p = smf_params_from_access(
            0, 0, 0x100, 1600, 5, 2, 1, 5, b"\x01\x02\x03\x04\x05")
        assert p.frame_type == 5
        assert p.bandwidth == 2
        assert p.pilot_density == 1
        assert len(p.channel_table) == 5


class TestSMFParamsFromBroadcast:
    def test_basic(self):
        p = smf_params_from_broadcast(
            baseline_slot=200,
            offset=600,
            access_addr=0xABCDEF,
            period=1600,
            frame_type=3,
            bandwidth=1,
            pilot_density=2,
            channel_count=2,
            channel_table=b"\x10\x20",
        )
        assert p.source == SMFActivationSource.BROADCAST
        assert p.access_addr == 0xABCDEF
        assert p.interval == 1600

    def test_broadcast_fields(self):
        p = smf_params_from_broadcast(
            500, 100, 0x123, 400, 0, 0, 0, 1, b"\x00")
        assert p.offset_us == 100
        assert p.channel_count == 1


# ===== SMFTransmitScheduler =====


class TestSMFTransmitScheduler:
    @pytest.fixture
    def scheduler(self):
        s = SMFTransmitScheduler()
        s.configure(SMFScheduleParams(
            baseline_slot=100,
            interval=800,
            frame_type=2,
            bandwidth=0,
            pilot_density=0,
            channel_count=3,
            channel_table=b"\x00\x01\x02",
        ))
        return s

    def test_next_smf_slot_before_base(self, scheduler: SMFTransmitScheduler):
        assert scheduler.next_smf_slot(50) == 100

    def test_next_smf_slot_at_base(self, scheduler: SMFTransmitScheduler):
        assert scheduler.next_smf_slot(100) == 900

    def test_next_smf_slot_after_base(self, scheduler: SMFTransmitScheduler):
        assert scheduler.next_smf_slot(101) == 900

    def test_next_smf_slot_at_period(self, scheduler: SMFTransmitScheduler):
        assert scheduler.next_smf_slot(900) == 1700

    def test_smf_slot_sequence(self, scheduler: SMFTransmitScheduler):
        slots = scheduler.smf_slot_sequence(50, 3)
        assert slots == [100, 900, 1700]

    def test_channel_rotation(self, scheduler: SMFTransmitScheduler):
        channels = []
        for _ in range(6):
            channels.append(scheduler._next_channel())
        assert channels == [0, 1, 2, 0, 1, 2]

    def test_channel_rotation_single(self):
        s = SMFTransmitScheduler()
        s.configure(SMFScheduleParams(channel_count=1, channel_table=b"\x05"))
        for _ in range(3):
            assert s._next_channel() == 0

    def test_channel_rotation_zero(self):
        s = SMFTransmitScheduler()
        s.configure(SMFScheduleParams(channel_count=0, channel_table=b""))
        assert s._next_channel() == 0

    def test_build_frame_includes_schedule(
        self, scheduler: SMFTransmitScheduler,
    ):
        frame = scheduler.build_smf_frame(include_schedule=True)
        schedules = frame.get_schedules()
        assert len(schedules) == 1
        assert schedules[0].interval == 800
        assert schedules[0].frame_type == 2

    def test_build_frame_dirty_clears(
        self, scheduler: SMFTransmitScheduler,
    ):
        assert scheduler._schedule_dirty
        scheduler.build_smf_frame(include_schedule=False)
        # dirty flag 导致仍然包含 schedule
        assert not scheduler._schedule_dirty

    def test_build_frame_no_schedule(
        self, scheduler: SMFTransmitScheduler,
    ):
        scheduler._schedule_dirty = False
        frame = scheduler.build_smf_frame(include_schedule=False)
        schedules = frame.get_schedules()
        assert len(schedules) == 0

    def test_register_link(self, scheduler: SMFTransmitScheduler):
        sig = LinkSignaling(
            llid=0x000123,
            effective_slot=1000,
            link_period_factor=4,
            schedule_slot_length=4,
            resources=[TimeResourceEntry(10, 20, 100, 5)],
        )
        scheduler.register_link(sig)
        frame = scheduler.build_smf_frame()
        links = frame.get_links()
        assert len(links) == 1
        assert links[0].llid == 0x000123

    def test_unregister_link(self, scheduler: SMFTransmitScheduler):
        sig = LinkSignaling(llid=0x000456)
        scheduler.register_link(sig)
        scheduler.register_offset(OffsetSignaling(llid=0x000456))
        scheduler.unregister_link(0x000456)
        frame = scheduler.build_smf_frame()
        assert len(frame.get_links()) == 0
        assert len(frame.get_offsets()) == 0

    def test_register_offset(self, scheduler: SMFTransmitScheduler):
        sig = OffsetSignaling(llid=0x000789, offset=100, offset_unit=0)
        scheduler.register_offset(sig)
        frame = scheduler.build_smf_frame()
        offsets = frame.get_offsets()
        assert len(offsets) == 1
        assert offsets[0].offset == 100

    def test_schedule_transmission(self, scheduler: SMFTransmitScheduler):
        tx = scheduler.schedule_transmission(50)
        assert isinstance(tx, SMFTransmission)
        assert tx.slot == 100
        assert 0 <= tx.channel_index < 3
        assert tx.frame is not None

    def test_schedule_transmission_sequence(
        self, scheduler: SMFTransmitScheduler,
    ):
        tx1 = scheduler.schedule_transmission(50)
        tx2 = scheduler.schedule_transmission(tx1.slot + 1)
        assert tx2.slot == 900
        assert tx2.channel_index != tx1.channel_index or \
            scheduler.params.channel_count == 1

    def test_schedule_transmission_frame_pack(
        self, scheduler: SMFTransmitScheduler,
    ):
        tx = scheduler.schedule_transmission(50)
        data = tx.frame.pack()
        assert len(data) > 0

    def test_update_schedule(self, scheduler: SMFTransmitScheduler):
        new_sched = scheduler.update_schedule(
            new_interval=1600, effective_slot=2000)
        assert new_sched.interval == 1600
        assert scheduler.params.interval == 1600
        assert scheduler.params.baseline_slot == 2000
        assert scheduler._schedule_dirty

    def test_update_schedule_partial(
        self, scheduler: SMFTransmitScheduler,
    ):
        scheduler.update_schedule(new_bandwidth=2)
        assert scheduler.params.bandwidth == 2
        assert scheduler.params.interval == 800  # 未变

    def test_update_channel_table(
        self, scheduler: SMFTransmitScheduler,
    ):
        scheduler.update_schedule(new_channel_table=b"\x0A\x0B")
        assert scheduler.params.channel_count == 2
        assert scheduler.params.channel_table == b"\x0A\x0B"

    def test_compute_offset(self, scheduler: SMFTransmitScheduler):
        sig = scheduler.compute_offset_us(
            smf_start_slot=100,
            link_first_slot=108,
            base_slot_us=125,
            unit=OffsetUnit.US_25,
        )
        expected_us = (108 - 100) * 125
        expected_offset = expected_us // 25
        assert sig.offset == expected_offset
        assert sig.offset_unit == OffsetUnit.US_25

    def test_compute_offset_300us_unit(
        self, scheduler: SMFTransmitScheduler,
    ):
        sig = scheduler.compute_offset_us(
            smf_start_slot=0, link_first_slot=24,
            base_slot_us=125, unit=OffsetUnit.US_300)
        expected_us = 24 * 125
        expected_offset = expected_us // 300
        assert sig.offset == expected_offset

    def test_compute_offset_negative_clamped(
        self, scheduler: SMFTransmitScheduler,
    ):
        sig = scheduler.compute_offset_us(
            smf_start_slot=200, link_first_slot=100)
        assert sig.offset == 0

    def test_alloc_seq_wraps(self, scheduler: SMFTransmitScheduler):
        for _i in range(65):
            seq = scheduler._alloc_seq()
        assert seq == 0  # 64 % 64 = 0

    def test_configure_resets(self, scheduler: SMFTransmitScheduler):
        scheduler._hop_index = 42
        scheduler._next_seq = 99
        scheduler.configure(SMFScheduleParams(interval=400))
        assert scheduler._hop_index == 0
        assert scheduler._next_seq == 0
        assert scheduler._last_tx_slot == -1

    def test_zero_interval(self):
        s = SMFTransmitScheduler()
        s.configure(SMFScheduleParams(interval=0))
        assert s.next_smf_slot(500) == 500

    def test_multiple_links_in_frame(
        self, scheduler: SMFTransmitScheduler,
    ):
        for i in range(5):
            scheduler.register_link(LinkSignaling(llid=i))
        frame = scheduler.build_smf_frame()
        assert len(frame.get_links()) == 5

    def test_frame_roundtrip(self, scheduler: SMFTransmitScheduler):
        scheduler.register_link(LinkSignaling(
            llid=0x100, effective_slot=500, link_period_factor=2,
            resources=[TimeResourceEntry(5, 10, 50, 3)],
        ))
        scheduler.register_offset(OffsetSignaling(llid=0x100, offset=40))
        frame = scheduler.build_smf_frame(include_schedule=True)
        data = frame.pack()
        from nearlink_sdr.mac.smf import SystemManagementFrame
        parsed = SystemManagementFrame.unpack(data)
        assert len(parsed.get_schedules()) == 1
        assert len(parsed.get_links()) == 1
        assert len(parsed.get_offsets()) == 1
