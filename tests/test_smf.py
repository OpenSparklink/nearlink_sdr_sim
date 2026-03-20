"""系统管理帧与广播测量配置测试

覆盖:
- mac/smf.py: SMFHeader, ScheduleSignaling, LinkSignaling, OffsetSignaling,
              SMFSignalingTLV, SystemManagementFrame, reassemble_smf
- mac/broadcast.py: NarrowbandMeasurementConfig, UWBPulseMeasurementConfig
"""

import pytest

from nearlink_sdr.mac.broadcast import (
    NarrowbandMeasurementConfig,
    UWBPulseMeasurementConfig,
)
from nearlink_sdr.mac.smf import (
    FrameTypeConfig,
    LinkSignaling,
    OffsetSignaling,
    OffsetUnit,
    ScheduleSignaling,
    ScheduleSlotLength,
    SegmentIndication,
    SMFHeader,
    SMFSignalingTLV,
    SMFSignalingType,
    SystemManagementFrame,
    TimeResourceEntry,
    reassemble_smf,
)

# =========================================================================
# SMFHeader
# =========================================================================


class TestSMFHeader:
    def test_pack_unpack_roundtrip(self):
        hdr = SMFHeader(segment_indication=2, signaling_number=42)
        data = hdr.pack()
        assert len(data) == 1
        restored = SMFHeader.unpack(data)
        assert restored.segment_indication == 2
        assert restored.signaling_number == 42

    def test_all_segment_values(self):
        for si in range(4):
            hdr = SMFHeader(segment_indication=si, signaling_number=63)
            restored = SMFHeader.unpack(hdr.pack())
            assert restored.segment_indication == si
            assert restored.signaling_number == 63

    def test_unpack_short_data(self):
        with pytest.raises(ValueError, match="数据不足"):
            SMFHeader.unpack(b"")

    def test_boundary_values(self):
        hdr = SMFHeader(segment_indication=3, signaling_number=0)
        data = hdr.pack()
        assert data == bytes([0xC0])  # 11_000000

        hdr2 = SMFHeader(segment_indication=0, signaling_number=63)
        data2 = hdr2.pack()
        assert data2 == bytes([0x3F])  # 00_111111


# =========================================================================
# ScheduleSignaling
# =========================================================================


class TestScheduleSignaling:
    def test_pack_unpack_roundtrip(self):
        sig = ScheduleSignaling(
            effective_slot=0x12345678,
            interval=0x0100,
            frame_type=FrameTypeConfig.FT3_M2,
            bandwidth=2,
            pilot_density=1,
            channel_count=3,
            channel_table=bytes([10, 20, 30]),
        )
        data = sig.pack()
        restored = ScheduleSignaling.unpack(data)
        assert restored.effective_slot == 0x12345678
        assert restored.interval == 0x0100
        assert restored.frame_type == FrameTypeConfig.FT3_M2
        assert restored.bandwidth == 2
        assert restored.pilot_density == 1
        assert restored.channel_count == 3
        assert restored.channel_table == bytes([10, 20, 30])

    def test_empty_channel_table(self):
        sig = ScheduleSignaling(channel_count=0, channel_table=b"")
        data = sig.pack()
        assert len(data) == 8  # 4+2+1+1
        restored = ScheduleSignaling.unpack(data)
        assert restored.channel_count == 0
        assert restored.channel_table == b""

    def test_unpack_short_data(self):
        with pytest.raises(ValueError, match="调度信令数据不足"):
            ScheduleSignaling.unpack(b"\x00" * 7)

    def test_frame_type_config_values(self):
        for ft in range(14):
            sig = ScheduleSignaling(frame_type=ft)
            restored = ScheduleSignaling.unpack(sig.pack())
            assert restored.frame_type == ft


# =========================================================================
# TimeResourceEntry
# =========================================================================


class TestTimeResourceEntry:
    def test_pack_unpack_roundtrip(self):
        entry = TimeResourceEntry(
            offset=100, duration=200, period=300, repeat_count=5,
        )
        data = entry.pack()
        assert len(data) == 7
        restored = TimeResourceEntry.unpack(data)
        assert restored.offset == 100
        assert restored.duration == 200
        assert restored.period == 300
        assert restored.repeat_count == 5

    def test_max_values(self):
        entry = TimeResourceEntry(
            offset=0xFFFF, duration=0xFFFF, period=0xFFFF, repeat_count=255,
        )
        restored = TimeResourceEntry.unpack(entry.pack())
        assert restored.offset == 0xFFFF
        assert restored.duration == 0xFFFF
        assert restored.repeat_count == 255

    def test_unpack_short_data(self):
        with pytest.raises(ValueError, match="时间资源条目"):
            TimeResourceEntry.unpack(b"\x00" * 6)


# =========================================================================
# LinkSignaling
# =========================================================================


class TestLinkSignaling:
    def test_pack_unpack_roundtrip(self):
        entries = [
            TimeResourceEntry(offset=10, duration=20, period=50, repeat_count=3),
            TimeResourceEntry(offset=100, duration=40, period=80, repeat_count=1),
        ]
        sig = LinkSignaling(
            llid=0xABCDEF,
            effective_slot=0x11223344,
            link_period_factor=8,
            schedule_slot_length=ScheduleSlotLength.US_125,
            resources=entries,
        )
        data = sig.pack()
        restored = LinkSignaling.unpack(data)
        assert restored.llid == 0xABCDEF
        assert restored.effective_slot == 0x11223344
        assert restored.link_period_factor == 8
        assert restored.schedule_slot_length == ScheduleSlotLength.US_125
        assert len(restored.resources) == 2
        assert restored.resources[0].offset == 10
        assert restored.resources[1].duration == 40

    def test_empty_resources(self):
        sig = LinkSignaling(llid=0x000001, resources=[])
        data = sig.pack()
        assert len(data) == 9  # 3+4+1+1
        restored = LinkSignaling.unpack(data)
        assert len(restored.resources) == 0

    def test_unpack_short_data(self):
        with pytest.raises(ValueError, match="链路信令数据不足"):
            LinkSignaling.unpack(b"\x00" * 8)

    def test_truncated_resource_entries(self):
        sig = LinkSignaling(
            resources=[TimeResourceEntry(offset=1, duration=2, period=3, repeat_count=4)],
        )
        data = sig.pack()
        # 截断最后一个条目的数据
        with pytest.raises(ValueError, match="时间资源条目数据截断"):
            LinkSignaling.unpack(data[:-2])


# =========================================================================
# OffsetSignaling
# =========================================================================


class TestOffsetSignaling:
    def test_pack_unpack_roundtrip(self):
        sig = OffsetSignaling(
            llid=0x123456,
            offset=0x7FFF,      # 最大值
            offset_unit=OffsetUnit.US_300,
        )
        data = sig.pack()
        assert len(data) == 5
        restored = OffsetSignaling.unpack(data)
        assert restored.llid == 0x123456
        assert restored.offset == 0x7FFF
        assert restored.offset_unit == OffsetUnit.US_300

    def test_unit_25us(self):
        sig = OffsetSignaling(llid=1, offset=100, offset_unit=OffsetUnit.US_25)
        restored = OffsetSignaling.unpack(sig.pack())
        assert restored.offset_unit == 0
        assert restored.offset == 100

    def test_unpack_short_data(self):
        with pytest.raises(ValueError, match="偏移信令数据不足"):
            OffsetSignaling.unpack(b"\x00" * 4)


# =========================================================================
# SMFSignalingTLV
# =========================================================================


class TestSMFSignalingTLV:
    def test_pack_unpack_roundtrip(self):
        tlv = SMFSignalingTLV(sig_type=1, content=b"\xAA\xBB\xCC")
        data = tlv.pack()
        assert data[0] == 1
        assert data[1] == 3
        restored, consumed = SMFSignalingTLV.unpack(data)
        assert consumed == 5
        assert restored.sig_type == 1
        assert restored.content == b"\xAA\xBB\xCC"

    def test_empty_content(self):
        tlv = SMFSignalingTLV(sig_type=0, content=b"")
        data = tlv.pack()
        assert len(data) == 2
        restored, consumed = SMFSignalingTLV.unpack(data)
        assert consumed == 2
        assert restored.content == b""

    def test_max_content(self):
        content = bytes(range(255))
        tlv = SMFSignalingTLV(sig_type=2, content=content)
        data = tlv.pack()
        restored, _ = SMFSignalingTLV.unpack(data)
        assert restored.content == content

    def test_content_too_long(self):
        with pytest.raises(ValueError, match="超出最大长度"):
            SMFSignalingTLV(sig_type=0, content=b"\x00" * 256).pack()

    def test_unpack_short_data(self):
        with pytest.raises(ValueError, match="TLV 数据不足"):
            SMFSignalingTLV.unpack(b"\x00")

    def test_unpack_content_truncated(self):
        with pytest.raises(ValueError, match="TLV 内容不足"):
            SMFSignalingTLV.unpack(b"\x00\x05\xAA")


# =========================================================================
# SystemManagementFrame
# =========================================================================


class TestSystemManagementFrame:
    def test_build_and_parse_complete_frame(self):
        smf = SystemManagementFrame(
            header=SMFHeader(
                segment_indication=SegmentIndication.COMPLETE,
                signaling_number=10,
            ),
        )
        sched = ScheduleSignaling(
            effective_slot=1000,
            interval=500,
            frame_type=FrameTypeConfig.FT2,
            bandwidth=1,
            pilot_density=0,
            channel_count=2,
            channel_table=bytes([5, 15]),
        )
        link = LinkSignaling(
            llid=0x000ABC,
            effective_slot=2000,
            link_period_factor=4,
            schedule_slot_length=ScheduleSlotLength.US_50,
            resources=[
                TimeResourceEntry(offset=0, duration=10, period=100, repeat_count=9),
            ],
        )
        offset = OffsetSignaling(llid=0x000ABC, offset=500, offset_unit=0)

        smf.add_schedule(sched)
        smf.add_link(link)
        smf.add_offset(offset)

        data = smf.pack()
        restored = SystemManagementFrame.unpack(data)

        assert restored.header.signaling_number == 10
        assert len(restored.signalings) == 3

        scheds = restored.get_schedules()
        assert len(scheds) == 1
        assert scheds[0].effective_slot == 1000
        assert scheds[0].channel_table == bytes([5, 15])

        links = restored.get_links()
        assert len(links) == 1
        assert links[0].llid == 0x000ABC
        assert len(links[0].resources) == 1

        offsets = restored.get_offsets()
        assert len(offsets) == 1
        assert offsets[0].offset == 500

    def test_empty_frame(self):
        smf = SystemManagementFrame()
        data = smf.pack()
        assert len(data) == 1  # 仅 header
        restored = SystemManagementFrame.unpack(data)
        assert len(restored.signalings) == 0

    def test_unpack_empty_data(self):
        with pytest.raises(ValueError, match="数据为空"):
            SystemManagementFrame.unpack(b"")

    def test_multiple_same_type_signalings(self):
        smf = SystemManagementFrame()
        smf.add_schedule(ScheduleSignaling(effective_slot=100))
        smf.add_schedule(ScheduleSignaling(effective_slot=200))
        data = smf.pack()
        restored = SystemManagementFrame.unpack(data)
        scheds = restored.get_schedules()
        assert len(scheds) == 2
        assert scheds[0].effective_slot == 100
        assert scheds[1].effective_slot == 200


# =========================================================================
# reassemble_smf
# =========================================================================


class TestReassembleSMF:
    def test_single_complete_fragment(self):
        smf = SystemManagementFrame(
            header=SMFHeader(
                segment_indication=SegmentIndication.COMPLETE,
                signaling_number=1,
            ),
        )
        smf.add_offset(OffsetSignaling(llid=0x001122, offset=42, offset_unit=0))
        data = smf.pack()
        result = reassemble_smf([data])
        offsets = result.get_offsets()
        assert len(offsets) == 1
        assert offsets[0].offset == 42

    def test_multi_fragment_reassembly(self):
        # 模拟分段: 首段含一个调度信令, 尾段含一个偏移信令
        sched_tlv = SMFSignalingTLV(
            sig_type=SMFSignalingType.SCHEDULE,
            content=ScheduleSignaling(effective_slot=999, channel_count=0).pack(),
        )
        offset_tlv = SMFSignalingTLV(
            sig_type=SMFSignalingType.OFFSET,
            content=OffsetSignaling(llid=1, offset=50, offset_unit=1).pack(),
        )
        # 首段
        first = SMFHeader(
            segment_indication=SegmentIndication.FIRST,
            signaling_number=5,
        ).pack() + sched_tlv.pack()
        # 尾段
        last = SMFHeader(
            segment_indication=SegmentIndication.LAST,
            signaling_number=5,
        ).pack() + offset_tlv.pack()

        result = reassemble_smf([first, last])
        assert result.header.signaling_number == 5
        assert len(result.get_schedules()) == 1
        assert len(result.get_offsets()) == 1
        assert result.get_schedules()[0].effective_slot == 999

    def test_empty_fragments_raises(self):
        with pytest.raises(ValueError, match="没有可重组"):
            reassemble_smf([])


# =========================================================================
# NarrowbandMeasurementConfig
# =========================================================================


class TestNarrowbandMeasurementConfig:
    def test_pack_unpack_no_hop_channels(self):
        cfg = NarrowbandMeasurementConfig(
            config_index=42,
            event_group_start_offset=1000,
            nb_event_period=100,
            nb_event_group_period=500,
            nb_events_in_group=10,
            nb_event_group_count=5,
            nb_event_stat_count=3,
            schedule_slot=4,
            meas_signal_bw=2,
            hopping_mode=1,
            init_channel=50,
            init_interaction_type=0,
            init_sync_signal=6,
            init_sync_config=0xABCDEF,
            init_meas_signal_type=1,
            init_meas_signal1_len=3,
            init_intra_event_interval=200,
            init_switch_interval=10,
            init_meas_signal2_len=32,
            init_inter_event_interval=300,
            mf1_inter_event_interval=400,
            mf2_inter_event_interval=500,
            nb_intra_event_interval=150,
            nb_inter_group_interval=2000,
            nb_event_total=20,
            mf1_event_period=4,
            mf1_switch_interval=8,
            tx_sync_signal=3,
            tx_antenna_count=2,
            tx_sync_config=0x112233,
            tx_meas_signal_type=0,
            tx_meas_signal1_len=5,
            tx_meas_signal1_security=2,
            tx_meas_signal2_multitone=1,
            tx_first_sub_signal_len=16,
            tx_antenna_switch_interval=4,
            tx_meas_signal2_len=48,
            hop_band_bitmap=0,      # 无跳频信道
            stability=1,
            reserved=0,
        )
        data = cfg.pack()
        restored = NarrowbandMeasurementConfig.unpack(data)
        assert restored.config_index == 42
        assert restored.event_group_start_offset == 1000
        assert restored.nb_event_period == 100
        assert restored.nb_events_in_group == 10
        assert restored.schedule_slot == 4
        assert restored.meas_signal_bw == 2
        assert restored.hopping_mode == 1
        assert restored.init_channel == 50
        assert restored.init_sync_signal == 6
        assert restored.init_sync_config == 0xABCDEF
        assert restored.tx_sync_signal == 3
        assert restored.tx_antenna_count == 2
        assert restored.tx_meas_signal2_len == 48
        assert restored.stability == 1

    def test_pack_unpack_with_2g4_channels(self):
        cfg = NarrowbandMeasurementConfig(
            config_index=1,
            hop_band_bitmap=0x01,    # 仅 2.4GHz
            hop_channel_2g4=(1 << 79) - 1,  # 79 个信道全开
        )
        data = cfg.pack()
        restored = NarrowbandMeasurementConfig.unpack(data)
        assert restored.hop_band_bitmap == 0x01
        assert restored.hop_channel_2g4 == (1 << 79) - 1

    def test_pack_unpack_all_bands(self):
        cfg = NarrowbandMeasurementConfig(
            config_index=99,
            hop_band_bitmap=0x07,    # 所有频带
            hop_channel_2g4=0xFFFF,
            hop_channel_5g1=0xAAAA,
            hop_channel_5g8=0x5555,
        )
        data = cfg.pack()
        restored = NarrowbandMeasurementConfig.unpack(data)
        assert restored.hop_band_bitmap == 0x07
        assert restored.hop_channel_2g4 == 0xFFFF
        assert restored.hop_channel_5g1 == 0xAAAA
        assert restored.hop_channel_5g8 == 0x5555

    def test_default_values(self):
        cfg = NarrowbandMeasurementConfig()
        data = cfg.pack()
        restored = NarrowbandMeasurementConfig.unpack(data)
        assert restored.config_index == 0
        assert restored.schedule_slot == 4
        assert restored.stability == 0


# =========================================================================
# UWBPulseMeasurementConfig
# =========================================================================


class TestUWBPulseMeasurementConfig:
    def test_pack_unpack_no_channels(self):
        cfg = UWBPulseMeasurementConfig(
            config_index=10,
            event_group_start_offset=5000,
            init_event_group_period=200,
            schedule_slot=3,
            init_channel_count=0,
            init_interaction_type=1,
            init_sync_signal=4,
            init_sync_config=0xDEAD00,
            init_intra_event_interval=100,
            init_switch_interval=20,
            init_meas_signal_type=1,
            init_meas_signal1_len=7,
            init_meas_signal2_len=64,
            tx_antenna_count=3,
            tx_multi_antenna_config=16,
            uwb_first_frame_start=0x3FFFFF,
            uwb_event_period=1000,
            uwb_event_group_period=5000,
            uwb_events_in_group=8,
            uwb_event_group_count=100,
            uwb_event_stat_count=4,
            uwb_channel=5,
            uwb_signal_bw=1,
            channel_overlap_mode=2,
            channel_order_mode=1,
            channel_stitch_count=4,
            channel_stitch_step=3,
            sync_symbol_kl=2,
            sync_symbol_n=128,
            sync_symbol_index=10,
            meas_symbol_shift=5,
            meas_seg_symbol_count=32,
            meas_seg_count=8,
            meas_seg_gap=500,
            meas_symbol_cp_len=6,
            meas_symbol_zero_len=8,
            stability=0,
            device_status=0b0010011,
        )
        data = cfg.pack()
        restored = UWBPulseMeasurementConfig.unpack(data)
        assert restored.config_index == 10
        assert restored.event_group_start_offset == 5000
        assert restored.init_event_group_period == 200
        assert restored.schedule_slot == 3
        assert restored.init_channel_count == 0
        assert restored.init_channel_list == []
        assert restored.init_interaction_type == 1
        assert restored.init_sync_signal == 4
        assert restored.uwb_first_frame_start == 0x3FFFFF
        assert restored.uwb_event_period == 1000
        assert restored.uwb_channel == 5
        assert restored.uwb_signal_bw == 1
        assert restored.channel_overlap_mode == 2
        assert restored.sync_symbol_kl == 2
        assert restored.sync_symbol_n == 128
        assert restored.meas_seg_symbol_count == 32
        assert restored.meas_symbol_cp_len == 6
        assert restored.meas_symbol_zero_len == 8
        assert restored.device_status == 0b0010011

    def test_pack_unpack_with_channels(self):
        cfg = UWBPulseMeasurementConfig(
            config_index=20,
            init_channel_count=3,
            init_channel_list=[100, 200, 300],
        )
        data = cfg.pack()
        restored = UWBPulseMeasurementConfig.unpack(data)
        assert restored.init_channel_count == 3
        assert restored.init_channel_list == [100, 200, 300]

    def test_default_values(self):
        cfg = UWBPulseMeasurementConfig()
        data = cfg.pack()
        restored = UWBPulseMeasurementConfig.unpack(data)
        assert restored.config_index == 0
        assert restored.schedule_slot == 4
        assert restored.stability == 0
        assert restored.device_status == 0

    def test_max_channels(self):
        channels = list(range(31))
        cfg = UWBPulseMeasurementConfig(
            init_channel_count=31,
            init_channel_list=channels,
        )
        data = cfg.pack()
        restored = UWBPulseMeasurementConfig.unpack(data)
        assert restored.init_channel_count == 31
        assert restored.init_channel_list == channels


# =========================================================================
# 枚举值覆盖
# =========================================================================


class TestEnums:
    def test_segment_indication(self):
        assert SegmentIndication.COMPLETE == 0
        assert SegmentIndication.FIRST == 1
        assert SegmentIndication.MIDDLE == 2
        assert SegmentIndication.LAST == 3

    def test_smf_signaling_type(self):
        assert SMFSignalingType.SCHEDULE == 0
        assert SMFSignalingType.LINK == 1
        assert SMFSignalingType.OFFSET == 2

    def test_frame_type_config(self):
        assert FrameTypeConfig.FT1 == 0
        assert FrameTypeConfig.FT4_M5 == 13

    def test_schedule_slot_length(self):
        assert ScheduleSlotLength.US_25 == 0
        assert ScheduleSlotLength.US_125 == 4

    def test_offset_unit(self):
        assert OffsetUnit.US_25 == 0
        assert OffsetUnit.US_300 == 1
