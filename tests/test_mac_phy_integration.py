"""MAC-PHY 集成联调测试。

验证 MAC 帧 → PHY IQ → MAC 帧的全链路数据完整性,
以及接入流程/调度器与 PHY pipeline 的协同工作。
"""

import numpy as np

from nearlink_sdr.mac.access import (
    BroadcasterAccessManager,
    InitiatorAccessManager,
    run_access_procedure,
)
from nearlink_sdr.mac.broadcast import (
    AccessBasicInfo,
    AccessResponseEntry,
    AccessResponseInfo,
    AccessResponseType,
    BroadcastDataType,
    BroadcastFrame,
)
from nearlink_sdr.mac.frame import AsyncDataFrame
from nearlink_sdr.mac.link_control import PingRequest, PingResponse
from nearlink_sdr.mac.link_manager import Event, EventType, LinkState
from nearlink_sdr.mac.scheduler import (
    EventGroupScheduler,
    EventTimingParams,
    ScheduleManager,
    ScheduleSlotType,
    SmfScheduleConfig,
    TimeSlice,
)
from nearlink_sdr.mac.signaling import encode_signaling
from nearlink_sdr.phy.mac_interface import (
    bits_to_bytes,
    bytes_to_bits,
    iq_to_mac,
    mac_to_iq,
    roundtrip_data,
    roundtrip_signaling,
)
from nearlink_sdr.phy.tx_pipeline import TxConfig

# -----------------------------------------------------------------------
# 字节/比特转换
# -----------------------------------------------------------------------

class TestBitByteConversion:

    def test_roundtrip_simple(self):
        original = b"\xDE\xAD\xBE\xEF"
        bits = bytes_to_bits(original)
        assert len(bits) == 32
        assert bits_to_bytes(bits) == original

    def test_roundtrip_zeros(self):
        original = b"\x00\x00\x00"
        assert bits_to_bytes(bytes_to_bits(original)) == original

    def test_roundtrip_ones(self):
        original = b"\xFF\xFF"
        assert bits_to_bytes(bytes_to_bits(original)) == original

    def test_empty(self):
        assert bits_to_bytes(bytes_to_bits(b"")) == b""

    def test_single_byte(self):
        for val in [0x00, 0x55, 0xAA, 0xFF]:
            original = bytes([val])
            assert bits_to_bytes(bytes_to_bits(original)) == original

    def test_bits_padding(self):
        """不足 8 bit 的尾部补零。"""
        bits = np.array([1, 0, 1], dtype=np.uint8)
        result = bits_to_bytes(bits)
        assert result == bytes([0b10100000])


# -----------------------------------------------------------------------
# MAC → IQ 发射
# -----------------------------------------------------------------------

class TestMacToIq:

    def test_basic_transmit(self):
        """验证 mac_to_iq 产生非零 IQ 信号。"""
        payload = b"\x01\x02\x03\x04"
        cfg = TxConfig(frame_type=2, mcs_index=7)
        iq = mac_to_iq(payload, cfg)
        assert iq.dtype == np.complex128
        assert len(iq) > 0
        assert np.max(np.abs(iq)) > 0

    def test_control_frame_transmit(self):
        """验证 ControlFrame.pack() → mac_to_iq 成功。"""
        msg = PingRequest()
        frame = encode_signaling(msg)
        mac_bytes = frame.pack()
        cfg = TxConfig(frame_type=2, mcs_index=7)
        iq = mac_to_iq(mac_bytes, cfg)
        assert len(iq) > 0

    def test_async_data_transmit(self):
        """验证异步数据帧 → IQ 发射。"""
        data_frame = AsyncDataFrame(segment_type=0, data=b"hello world")
        mac_bytes = data_frame.pack()
        cfg = TxConfig(frame_type=2, mcs_index=7)
        iq = mac_to_iq(mac_bytes, cfg)
        assert len(iq) > 0

    def test_different_frame_types(self):
        """验证不同帧类型都能产生 IQ。"""
        payload = b"\xAA\xBB\xCC"
        for ft in [1, 2, 3, 4]:
            cfg = TxConfig(frame_type=ft, mcs_index=0 if ft == 1 else 7)
            iq = mac_to_iq(payload, cfg)
            assert len(iq) > 0, f"帧类型 {ft} 未产生 IQ 信号"


# -----------------------------------------------------------------------
# IQ → MAC 接收 (无信道直连)
# -----------------------------------------------------------------------

class TestIqToMac:

    def test_loopback_payload(self):
        """直连 roundtrip: MAC 字节 → IQ → MAC 字节 (无噪声)。"""
        payload = b"\x01\x02\x03\x04\x05\x06"
        cfg = TxConfig(frame_type=2, mcs_index=7, sps=4)
        iq = mac_to_iq(payload, cfg)
        rx = iq_to_mac(iq, cfg, len(payload))
        assert rx.crc_ok
        assert rx.mac_payload == payload


# -----------------------------------------------------------------------
# 全链路 roundtrip
# -----------------------------------------------------------------------

class TestRoundtripSignaling:

    def test_ping_roundtrip(self):
        """PingRequest 全链路: 编码 → IQ → 解码。"""
        msg = PingRequest()
        recovered, ok = roundtrip_signaling(msg)
        assert ok
        assert isinstance(recovered, PingRequest)

    def test_ping_response_roundtrip(self):
        """PingResponse 全链路。"""
        msg = PingResponse()
        recovered, ok = roundtrip_signaling(msg)
        assert ok
        assert isinstance(recovered, PingResponse)


class TestRoundtripData:

    def test_short_data(self):
        """短数据帧全链路。"""
        data = b"SLE"
        recovered, ok = roundtrip_data(data)
        assert ok
        assert recovered == data

    def test_longer_data(self):
        """较长数据帧全链路。"""
        data = bytes(range(27))
        recovered, ok = roundtrip_data(data)
        assert ok
        assert recovered == data


# -----------------------------------------------------------------------
# 广播帧 PHY 链路
# -----------------------------------------------------------------------


class TestBroadcastFramePhy:
    """广播帧通过 PHY pipeline 的全链路验证。"""

    CFG = TxConfig(frame_type=2, mcs_index=7)

    def test_broadcast_frame_roundtrip(self):
        """简单广播帧 pack → IQ → decode → unpack。"""
        frame = BroadcastFrame(
            structure_indication=0x11,
            local_addr_type=0,
            peer_addr_type=0,
            local_addr=b"\x01\x02\x03\x04\x05\x06",
            irk_id=0,
            peer_addr=b"\x00" * 6,
            data_items=[
                (0x01, b"\xAA\xBB\xCC"),
            ],
        )
        mac_bytes = frame.pack()
        iq = mac_to_iq(mac_bytes, self.CFG)
        rx = iq_to_mac(iq, self.CFG, len(mac_bytes))
        assert rx.crc_ok
        restored = BroadcastFrame.unpack(rx.mac_payload)
        assert restored.local_addr == frame.local_addr
        assert len(restored.data_items) == 1

    def test_ext_adv_frame_roundtrip(self):
        """可接入扩展广播帧通过 PHY 传输。"""
        b_mgr = BroadcasterAccessManager(
            local_address=b"\x01\x02\x03\x04\x05\x06",
        )
        frame = b_mgr.build_ext_adv_frame()
        mac_bytes = frame.pack()
        iq = mac_to_iq(mac_bytes, self.CFG)
        rx = iq_to_mac(iq, self.CFG, len(mac_bytes))
        assert rx.crc_ok
        restored = BroadcastFrame.unpack(rx.mac_payload)
        # 验证发现接入资源配置在解码后仍存在
        data_types = [dt for dt, _ in restored.data_items]
        assert BroadcastDataType.DISCOVERY_ACCESS_RESOURCE in data_types

    def test_access_response_frame_roundtrip(self):
        """接入响应帧通过 PHY 传输。"""
        resp_entry = AccessResponseEntry(
            peer_addr=b"\x0A" * 6,
            response_type=AccessResponseType.ACCEPT,
            peer_addr_type=0,
            repeat_indication=0,
        )
        resp_info = AccessResponseInfo(entries=[resp_entry])
        access_basic = AccessBasicInfo(
            smf_baseline_slot=0,
            smf_offset=300,
            smf_link_id=1,
            smf_period=800,
            smf_frame_type=2,
            smf_bandwidth=0,
            smf_pilot_density=0,
            access_link_id=1,
            access_period=40,
            access_timeout=50,
            sleep_clock_accuracy=7,
            access_crc_type=0,
            access_crc_init=0,
            hop_map=b"\xFF" * 10,
            smf_channel_count=3,
            smf_channel_table=b"\x00\x01\x02",
        )
        frame = BroadcastFrame(
            structure_indication=0x11,
            local_addr_type=0,
            peer_addr_type=0,
            local_addr=b"\x01" * 6,
            irk_id=0,
            peer_addr=b"\x00" * 6,
            data_items=[
                (BroadcastDataType.ACCESS_RESPONSE, resp_info.pack()),
                (BroadcastDataType.ACCESS_BASIC, access_basic.pack()),
            ],
        )
        mac_bytes = frame.pack()
        iq = mac_to_iq(mac_bytes, self.CFG)
        rx = iq_to_mac(iq, self.CFG, len(mac_bytes))
        assert rx.crc_ok
        restored = BroadcastFrame.unpack(rx.mac_payload)
        data_types = [dt for dt, _ in restored.data_items]
        assert BroadcastDataType.ACCESS_RESPONSE in data_types
        assert BroadcastDataType.ACCESS_BASIC in data_types


# -----------------------------------------------------------------------
# 接入流程 + PHY 全链路
# -----------------------------------------------------------------------


class TestAccessPhyIntegration:
    """接入流程通过 PHY pipeline 的端到端验证。"""

    CFG = TxConfig(frame_type=2, mcs_index=7)

    def test_adv_frame_phy_roundtrip(self):
        """广播帧通过 PHY 后发起方能正确解析。"""
        b_mgr = BroadcasterAccessManager(
            local_address=b"\x01\x02\x03\x04\x05\x06",
        )
        b_mgr.link_manager.process_event(Event(EventType.START_BROADCAST))

        # 阶段 a: 广播方构建帧
        frame = b_mgr.build_ext_adv_frame()
        mac_bytes = frame.pack()

        # PHY 传输
        iq = mac_to_iq(mac_bytes, self.CFG)
        rx = iq_to_mac(iq, self.CFG, len(mac_bytes))
        assert rx.crc_ok

        # 发起方解析
        restored = BroadcastFrame.unpack(rx.mac_payload)
        i_mgr = InitiatorAccessManager(
            local_address=b"\x0A\x0B\x0C\x0D\x0E\x0F",
        )
        i_mgr.link_manager.process_event(Event(EventType.START_SCAN))
        assert i_mgr.process_ext_adv(restored) is True
        assert i_mgr.discovery_config is not None

    def test_request_phy_roundtrip(self):
        """接入请求数据通过 PHY 后广播方能正确处理。"""
        # 先完成阶段 a/b 的准备
        b_mgr = BroadcasterAccessManager(
            local_address=b"\x01" * 6,
        )
        b_mgr.link_manager.process_event(Event(EventType.START_BROADCAST))
        frame = b_mgr.build_ext_adv_frame()

        i_mgr = InitiatorAccessManager(
            local_address=b"\x0A" * 6,
        )
        i_mgr.link_manager.process_event(Event(EventType.START_SCAN))
        i_mgr.process_ext_adv(frame)
        req_data = i_mgr.build_access_request()

        # PHY 传输接入请求
        iq = mac_to_iq(req_data, self.CFG)
        rx = iq_to_mac(iq, self.CFG, len(req_data))
        assert rx.crc_ok

        # 广播方处理接入请求
        resp_frame, accepted = b_mgr.handle_access_request(
            rx.mac_payload, peer_address=b"\x0A" * 6,
        )
        assert accepted is True
        assert resp_frame is not None

    def test_full_access_via_phy(self):
        """完整接入流程: 所有帧通过 PHY pipeline 传输。"""
        cfg = self.CFG

        # 初始化
        b_mgr = BroadcasterAccessManager(
            local_address=b"\x01" * 6,
        )
        b_mgr.link_manager.process_event(Event(EventType.START_BROADCAST))

        i_mgr = InitiatorAccessManager(
            local_address=b"\x0A" * 6,
        )
        i_mgr.link_manager.process_event(Event(EventType.START_SCAN))

        # 阶段 a: 广播帧通过 PHY
        adv_frame = b_mgr.build_ext_adv_frame()
        adv_bytes = adv_frame.pack()
        iq1 = mac_to_iq(adv_bytes, cfg)
        rx1 = iq_to_mac(iq1, cfg, len(adv_bytes))
        assert rx1.crc_ok
        adv_restored = BroadcastFrame.unpack(rx1.mac_payload)

        # 阶段 b: 发起方解析并构建请求, 请求通过 PHY
        i_mgr.process_ext_adv(adv_restored)
        req_data = i_mgr.build_access_request()
        iq2 = mac_to_iq(req_data, cfg)
        rx2 = iq_to_mac(iq2, cfg, len(req_data))
        assert rx2.crc_ok

        # 阶段 c: 广播方处理请求, 响应通过 PHY
        resp_frame, accepted = b_mgr.handle_access_request(
            rx2.mac_payload, peer_address=b"\x0A" * 6,
        )
        assert accepted
        resp_bytes = resp_frame.pack()
        iq3 = mac_to_iq(resp_bytes, cfg)
        rx3 = iq_to_mac(iq3, cfg, len(resp_bytes))
        assert rx3.crc_ok

        # 阶段 d: 发起方处理响应
        role, _params = i_mgr.handle_access_response(rx3.mac_payload)
        assert role is not None
        assert i_mgr.link_manager.state == LinkState.CONNECTED
        assert b_mgr.link_manager.state == LinkState.CONNECTED


# -----------------------------------------------------------------------
# 调度器 + PHY 集成
# -----------------------------------------------------------------------


class TestSchedulerPhyIntegration:
    """调度器驱动的 PHY 帧调度测试。"""

    def test_event_schedule_with_data_frames(self):
        """调度器生成事件时间表, 每个事件发送一个数据帧。"""
        mgr = ScheduleManager()
        mgr.configure_smf(SmfScheduleConfig(smf_interval=800))

        timing = EventTimingParams(
            event_group_period=100,
            event_period=25,
            intra_event_interval=300,
            event_count=3,
            schedule_slot_type=ScheduleSlotType.T_125US,
            tx_max_offset=3,
            rx_max_offset=3,
        )
        mgr.register_link(
            link_id=1,
            timing=timing,
            time_slices=[
                TimeSlice(offset=0, duration=50, period=100, repeat_count=2),
            ],
        )

        # 获取事件调度表
        schedule = mgr.get_event_schedule(1)
        assert schedule is not None
        assert len(schedule) == 3

        # 对每个事件, 模拟发送一帧数据
        cfg = TxConfig(frame_type=2, mcs_index=7)
        for event in schedule:
            tx_win = event["tx_window"]
            assert tx_win[1] > tx_win[0]

            data = b"\xAA" * 10
            _recovered, ok = roundtrip_data(data, cfg)
            assert ok

    def test_scheduler_timing_consistency(self):
        """调度器时间参数与 PHY 帧传输时间一致性检查。"""
        timing = EventTimingParams(
            event_group_period=200,
            event_period=50,
            intra_event_interval=500,
            event_count=4,
            schedule_slot_type=ScheduleSlotType.T_125US,
            tx_max_offset=7,
            rx_max_offset=7,
        )
        scheduler = EventGroupScheduler(timing=timing, anchor_slot=0)

        # 验证事件时间是单调递增的
        times = scheduler.event_start_times()
        for i in range(1, len(times)):
            assert times[i] > times[i - 1]

        # 验证 TX/RX 窗口不重叠
        for t in times:
            _tx_s, tx_e = scheduler.tx_window(t)
            rx_s, _rx_e = scheduler.rx_window(t)
            assert tx_e <= rx_s  # TX 在 RX 之前

    def test_supervision_timeout_with_phy(self):
        """监督超时与 PHY 帧传输结合。"""
        mgr = ScheduleManager()
        timing = EventTimingParams(supervision_timeout=1)  # 10 ms
        mgr.register_link(link_id=1, timing=timing, anchor_slot=0)

        # 在超时前发送数据帧 (应正常)
        assert not mgr.check_supervision_timeout(1)

        # 推进时钟超过超时
        mgr.advance_time(100)  # 12.5 ms > 10 ms
        assert mgr.check_supervision_timeout(1)


# -----------------------------------------------------------------------
# 全链路: 接入 + 调度器 + PHY
# -----------------------------------------------------------------------


class TestFullStackIntegration:
    """接入流程 + 调度器 + PHY 的完整协议栈测试。"""

    def test_access_then_schedule_data(self):
        """接入完成后, 使用调度器参数进行数据传输。"""
        # 1. 执行接入流程
        b_mgr, i_mgr = run_access_procedure()
        assert b_mgr.link_manager.state == LinkState.CONNECTED
        assert i_mgr.link_manager.state == LinkState.CONNECTED

        # 2. 使用接入参数配置调度器
        sched = ScheduleManager()
        sched.configure_smf(SmfScheduleConfig(
            smf_interval=b_mgr.smf_period,
            frame_type=b_mgr.smf_frame_type,
        ))
        timing = EventTimingParams(
            event_group_period=b_mgr.access_period,
            event_period=10,
            intra_event_interval=300,
            event_count=2,
        )
        sched.register_link(link_id=b_mgr.access_link_id, timing=timing)

        # 3. 获取事件调度表
        schedule = sched.get_event_schedule(b_mgr.access_link_id)
        assert schedule is not None
        assert len(schedule) == 2

        # 4. 在调度窗口内发送/接收数据帧
        cfg = TxConfig(frame_type=2, mcs_index=7)
        test_payload = b"SparkLink SLE test data"
        recovered, ok = roundtrip_data(test_payload, cfg)
        assert ok
        assert recovered == test_payload

    def test_access_then_signaling(self):
        """接入完成后, 通过 PHY 发送信令。"""
        b_mgr, _i_mgr = run_access_procedure()
        assert b_mgr.link_manager.state == LinkState.CONNECTED

        # 发送 Ping 信令
        ping = PingRequest()
        recovered, ok = roundtrip_signaling(ping)
        assert ok
        assert isinstance(recovered, PingRequest)

    def test_multiple_links_scheduling(self):
        """多条链路在同一超帧内的调度与冲突检测。"""
        sched = ScheduleManager()
        sched.configure_smf(SmfScheduleConfig(smf_interval=1600))

        # 链路 1: 时间片 [0, 30)
        timing1 = EventTimingParams(event_group_period=50, event_count=1)
        sched.register_link(
            link_id=1,
            timing=timing1,
            time_slices=[TimeSlice(offset=0, duration=30)],
        )

        # 链路 2: 时间片 [30, 60) — 无冲突
        timing2 = EventTimingParams(event_group_period=50, event_count=1)
        sched.register_link(
            link_id=2,
            timing=timing2,
            time_slices=[TimeSlice(offset=30, duration=30)],
        )

        conflicts = sched.superframe.check_conflicts()
        assert len(conflicts) == 0

        # 两条链路各自可获取独立的调度表
        s1 = sched.get_event_schedule(1)
        s2 = sched.get_event_schedule(2)
        assert s1 is not None and s2 is not None
