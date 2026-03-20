"""时序调度器测试 -- TXS-10002-2025 标准 6.3/6.6/7.2。

验证基础时隙、调度时隙、超帧管理、事件组调度和收发间隔管理。
"""

from __future__ import annotations

from nearlink_sdr.mac.scheduler import (
    SLOT_COUNTER_MAX,
    TSYS_US,
    EventGroupScheduler,
    EventTimingParams,
    LinkScheduleEntry,
    MultiLevelInterval,
    ScheduleManager,
    ScheduleSlotType,
    SleepClockAccuracy,
    SlotCounter,
    SmfScheduleConfig,
    Superframe,
    TimeSlice,
    TxRxIntervalType,
    schedule_slot_us,
    tx_rx_interval_us,
)

# -----------------------------------------------------------------------
# 系统常量与枚举
# -----------------------------------------------------------------------


class TestConstants:
    """系统常量验证。"""

    def test_tsys_125us(self):
        """系统基础时隙固定 125 μs。"""
        assert TSYS_US == 125

    def test_slot_counter_30bit(self):
        """时隙计数器 30 bit 最大值。"""
        assert SLOT_COUNTER_MAX == (1 << 30) - 1

    def test_schedule_slot_values(self):
        """调度时隙枚举 → 微秒转换。"""
        assert schedule_slot_us(ScheduleSlotType.T_25US) == 25
        assert schedule_slot_us(ScheduleSlotType.T_50US) == 50
        assert schedule_slot_us(ScheduleSlotType.T_75US) == 75
        assert schedule_slot_us(ScheduleSlotType.T_100US) == 100
        assert schedule_slot_us(ScheduleSlotType.T_125US) == 125

    def test_schedule_slot_invalid(self):
        """未知调度时隙类型返回默认 125 μs。"""
        assert schedule_slot_us(7) == 125

    def test_sleep_clock_accuracy_enum(self):
        """睡眠时钟精度枚举。"""
        assert SleepClockAccuracy.PPM_0_20 == 7
        assert SleepClockAccuracy.PPM_251_500 == 0


# -----------------------------------------------------------------------
# 时隙计数器
# -----------------------------------------------------------------------


class TestSlotCounter:
    """时隙计数器测试。"""

    def test_initial_zero(self):
        """初始计数为零。"""
        c = SlotCounter()
        assert c.value == 0
        assert c.time_us() == 0

    def test_advance(self):
        """前进指定时隙数。"""
        c = SlotCounter()
        c.advance(100)
        assert c.value == 100
        assert c.time_us() == 100 * 125

    def test_advance_wrap(self):
        """30 bit 回绕。"""
        c = SlotCounter(value=SLOT_COUNTER_MAX)
        c.advance(1)
        assert c.value == 0

    def test_advance_wrap_large(self):
        """大步长回绕。"""
        c = SlotCounter(value=SLOT_COUNTER_MAX - 5)
        c.advance(10)
        assert c.value == 4

    def test_set_from_us(self):
        """从微秒值设置计数器。"""
        c = SlotCounter()
        c.set_from_us(1000)
        assert c.value == 1000 // 125  # 8

    def test_set_from_us_floor(self):
        """微秒值向下取整。"""
        c = SlotCounter()
        c.set_from_us(130)
        assert c.value == 1  # 130 // 125

    def test_distance_to(self):
        """计算到目标的距离。"""
        c = SlotCounter(value=100)
        assert c.distance_to(200) == 100

    def test_distance_to_wrap(self):
        """回绕距离计算。"""
        c = SlotCounter(value=SLOT_COUNTER_MAX - 5)
        assert c.distance_to(5) == 11

    def test_int_conversion(self):
        """整数转换。"""
        c = SlotCounter(value=42)
        assert int(c) == 42


# -----------------------------------------------------------------------
# 事件计时参数
# -----------------------------------------------------------------------


class TestEventTimingParams:
    """事件计时参数测试。"""

    def test_default_schedule_slot(self):
        """默认使用 125 μs 调度时隙。"""
        p = EventTimingParams()
        assert p.schedule_slot_us == 125

    def test_event_group_period_us(self):
        """事件组周期微秒转换。"""
        p = EventTimingParams(
            event_group_period=100,
            schedule_slot_type=ScheduleSlotType.T_50US,
        )
        assert p.event_group_period_us == 100 * 50

    def test_event_period_us(self):
        """事件周期微秒转换。"""
        p = EventTimingParams(
            event_period=20,
            schedule_slot_type=ScheduleSlotType.T_125US,
        )
        assert p.event_period_us == 20 * 125

    def test_supervision_timeout_us(self):
        """超时时间换算。"""
        p = EventTimingParams(supervision_timeout=100)
        assert p.supervision_timeout_us == 100 * 10_000

    def test_max_event_duration(self):
        """最大事件持续时间。"""
        p = EventTimingParams(tx_max_offset=3, rx_max_offset=3)
        assert p.max_event_duration_us == (3 + 3 + 1) * 125


# -----------------------------------------------------------------------
# 时间片
# -----------------------------------------------------------------------


class TestTimeSlice:
    """时间片测试。"""

    def test_single_interval(self):
        """单次时间片。"""
        ts = TimeSlice(offset=10, duration=5, period=0, repeat_count=1)
        intervals = ts.absolute_intervals(125)
        assert len(intervals) == 1
        assert intervals[0] == (10 * 125, 15 * 125)

    def test_repeated_intervals(self):
        """重复时间片。"""
        ts = TimeSlice(offset=0, duration=10, period=50, repeat_count=3)
        intervals = ts.absolute_intervals(125)
        assert len(intervals) == 3
        assert intervals[0] == (0, 1250)
        assert intervals[1] == (50 * 125, 60 * 125)
        assert intervals[2] == (100 * 125, 110 * 125)

    def test_different_slot_unit(self):
        """不同调度时隙长度。"""
        ts = TimeSlice(offset=4, duration=2, period=0, repeat_count=1)
        intervals = ts.absolute_intervals(50)
        assert intervals[0] == (200, 300)


# -----------------------------------------------------------------------
# SMF 调度配置
# -----------------------------------------------------------------------


class TestSmfScheduleConfig:
    """SMF 调度配置测试。"""

    def test_default_interval(self):
        """默认 SMF 间隔 100 ms。"""
        c = SmfScheduleConfig()
        assert c.smf_interval_us == 800 * 125

    def test_custom_interval(self):
        """自定义 SMF 间隔。"""
        c = SmfScheduleConfig(smf_interval=400)
        assert c.smf_interval_us == 400 * 125


# -----------------------------------------------------------------------
# 超帧管理
# -----------------------------------------------------------------------


class TestSuperframe:
    """超帧管理测试。"""

    def test_duration(self):
        """超帧持续时间。"""
        sf = Superframe(
            smf_config=SmfScheduleConfig(smf_interval=800)
        )
        assert sf.duration_us == 100_000
        assert sf.duration_slots == 800

    def test_add_link(self):
        """注册链路。"""
        sf = Superframe()
        entry = LinkScheduleEntry(link_id=1)
        sf.add_link(entry)
        assert len(sf.link_entries) == 1
        assert sf.get_link(1) is not None

    def test_add_link_replace(self):
        """同 link_id 替换。"""
        sf = Superframe()
        sf.add_link(LinkScheduleEntry(link_id=1, period_factor=1))
        sf.add_link(LinkScheduleEntry(link_id=1, period_factor=2))
        assert len(sf.link_entries) == 1
        assert sf.get_link(1).period_factor == 2

    def test_remove_link(self):
        """移除链路。"""
        sf = Superframe()
        sf.add_link(LinkScheduleEntry(link_id=1))
        assert sf.remove_link(1) is True
        assert sf.get_link(1) is None

    def test_remove_link_missing(self):
        """移除不存在的链路。"""
        sf = Superframe()
        assert sf.remove_link(99) is False

    def test_get_link_missing(self):
        """查找不存在的链路。"""
        sf = Superframe()
        assert sf.get_link(99) is None

    def test_active_region_empty(self):
        """无链路时活动区间为零。"""
        sf = Superframe()
        assert sf.active_region_us() == (0, 0)

    def test_active_region(self):
        """活动区间计算。"""
        sf = Superframe()
        entry = LinkScheduleEntry(
            link_id=1,
            time_slices=[
                TimeSlice(offset=0, duration=10, period=0, repeat_count=1),
                TimeSlice(offset=20, duration=5, period=0, repeat_count=1),
            ],
        )
        sf.add_link(entry)
        start, end = sf.active_region_us()
        assert start == 0
        assert end == 25 * 125

    def test_no_conflict(self):
        """无冲突的时间片。"""
        sf = Superframe()
        sf.add_link(LinkScheduleEntry(
            link_id=1,
            time_slices=[TimeSlice(offset=0, duration=10)],
        ))
        sf.add_link(LinkScheduleEntry(
            link_id=2,
            time_slices=[TimeSlice(offset=10, duration=10)],
        ))
        assert len(sf.check_conflicts()) == 0

    def test_conflict_detected(self):
        """检测时间片冲突。"""
        sf = Superframe()
        sf.add_link(LinkScheduleEntry(
            link_id=1,
            time_slices=[TimeSlice(offset=0, duration=15)],
        ))
        sf.add_link(LinkScheduleEntry(
            link_id=2,
            time_slices=[TimeSlice(offset=10, duration=15)],
        ))
        conflicts = sf.check_conflicts()
        assert len(conflicts) == 1
        lid_a, lid_b, o_start, o_end = conflicts[0]
        assert {lid_a, lid_b} == {1, 2}
        assert o_start == 10 * 125
        assert o_end == 15 * 125


# -----------------------------------------------------------------------
# 事件组调度器
# -----------------------------------------------------------------------


class TestEventGroupScheduler:
    """事件组调度器测试。"""

    def _make_scheduler(self, **kwargs) -> EventGroupScheduler:
        timing = EventTimingParams(
            event_group_period=100,
            event_period=10,
            intra_event_interval=200,
            event_count=3,
            tx_max_offset=3,
            rx_max_offset=3,
            **kwargs,
        )
        return EventGroupScheduler(
            timing=timing,
            anchor_slot=0,
            anchor_offset_us=0,
        )

    def test_anchor_time(self):
        """锚点时间计算。"""
        s = EventGroupScheduler(
            anchor_slot=100,
            anchor_offset_us=200,
        )
        assert s.anchor_time_us() == 100 * 125 + 200

    def test_event_start_times(self):
        """事件起始时间列表。"""
        s = self._make_scheduler()
        times = s.event_start_times(group_index=0)
        assert len(times) == 3
        assert times[0] == 0
        assert times[1] == 10 * 125  # event_period=10, slot=125
        assert times[2] == 20 * 125

    def test_event_start_times_second_group(self):
        """第二个事件组的起始时间。"""
        s = self._make_scheduler()
        times = s.event_start_times(group_index=1)
        assert times[0] == 100 * 125  # event_group_period=100

    def test_event_start_times_interval_based(self):
        """event_period=0 时使用事件间间隔。"""
        timing = EventTimingParams(
            event_group_period=100,
            event_period=0,
            intra_event_interval=200,
            inter_event_interval=500,
            event_count=3,
            tx_max_offset=3,
            rx_max_offset=3,
        )
        s = EventGroupScheduler(timing=timing)
        times = s.event_start_times()
        assert times[1] == 500
        assert times[2] == 1000

    def test_tx_window(self):
        """先发窗口计算。"""
        s = self._make_scheduler()
        start, end = s.tx_window(0)
        assert start == 0
        assert end == (3 + 1) * 125  # tx_max_offset=3

    def test_rx_window(self):
        """后发窗口计算。"""
        s = self._make_scheduler()
        start, end = s.rx_window(0)
        tx_dur = (3 + 1) * 125
        expected_start = tx_dur + 200  # intra_event_interval=200
        expected_end = expected_start + (3 + 1) * 125
        assert start == expected_start
        assert end == expected_end

    def test_event_schedule(self):
        """完整事件调度表。"""
        s = self._make_scheduler()
        schedule = s.event_schedule()
        assert len(schedule) == 3
        assert "event_start" in schedule[0]
        assert "tx_window" in schedule[0]
        assert "rx_window" in schedule[0]

    def test_next_event_group_start_before_anchor(self):
        """当前时间在锚点之前。"""
        s = self._make_scheduler()
        s.anchor_slot = 100
        assert s.next_event_group_start(0) == 100 * 125

    def test_next_event_group_start_after_anchor(self):
        """当前时间在锚点之后。"""
        s = self._make_scheduler()
        s.anchor_slot = 0
        period_us = 100 * 125
        # 当前在 period_us + 1 处, 下一个应是 2 * period_us
        assert s.next_event_group_start(period_us + 1) == 2 * period_us

    def test_next_event_group_zero_period(self):
        """周期为零时返回锚点。"""
        timing = EventTimingParams(
            event_group_period=0,
            event_period=10,
            intra_event_interval=200,
            event_count=3,
            tx_max_offset=3,
            rx_max_offset=3,
        )
        s = EventGroupScheduler(timing=timing)
        assert s.next_event_group_start(99999) == 0


# -----------------------------------------------------------------------
# 收发间隔
# -----------------------------------------------------------------------


class TestTxRxInterval:
    """收发间隔测试。"""

    def test_interval_values(self):
        """枚举微秒值。"""
        assert tx_rx_interval_us(TxRxIntervalType.INTERVAL_125US) == 125
        assert tx_rx_interval_us(TxRxIntervalType.INTERVAL_100US) == 100
        assert tx_rx_interval_us(TxRxIntervalType.INTERVAL_75US) == 75
        assert tx_rx_interval_us(TxRxIntervalType.INTERVAL_50US) == 50
        assert tx_rx_interval_us(TxRxIntervalType.INTERVAL_25US) == 25

    def test_interval_invalid(self):
        """未知类型返回默认。"""
        assert tx_rx_interval_us(0xF) == 125


# -----------------------------------------------------------------------
# 多级收发间隔
# -----------------------------------------------------------------------


class TestMultiLevelInterval:
    """多级收发间隔测试。"""

    def test_default_all_125(self):
        """默认全部 125 μs。"""
        m = MultiLevelInterval()
        for lvl in range(1, 32):
            assert m.get(lvl) == 125

    def test_set_get(self):
        """设置和获取。"""
        m = MultiLevelInterval()
        m.set(1, 50)
        m.set(31, 200)
        assert m.get(1) == 50
        assert m.get(31) == 200

    def test_out_of_range(self):
        """超范围级别返回默认值。"""
        m = MultiLevelInterval()
        assert m.get(0) == 125
        assert m.get(32) == 125

    def test_pack_unpack(self):
        """序列化/反序列化。"""
        m = MultiLevelInterval()
        m.set(5, 77)
        data = m.pack()
        assert len(data) == 31
        restored = MultiLevelInterval.unpack(data)
        assert restored.get(5) == 77


# -----------------------------------------------------------------------
# 综合调度管理器
# -----------------------------------------------------------------------


class TestScheduleManager:
    """综合调度管理器测试。"""

    def test_configure_smf(self):
        """配置 SMF。"""
        mgr = ScheduleManager()
        mgr.configure_smf(SmfScheduleConfig(smf_interval=1600))
        assert mgr.superframe.duration_us == 1600 * 125

    def test_register_link(self):
        """注册链路。"""
        mgr = ScheduleManager()
        timing = EventTimingParams(event_group_period=100, event_count=2)
        mgr.register_link(link_id=1, timing=timing)
        assert 1 in mgr.event_schedulers
        schedule = mgr.get_event_schedule(1)
        assert schedule is not None
        assert len(schedule) == 2

    def test_register_link_with_slices(self):
        """注册链路并分配时间片。"""
        mgr = ScheduleManager()
        timing = EventTimingParams(event_group_period=50)
        slices = [TimeSlice(offset=0, duration=20, period=50, repeat_count=2)]
        mgr.register_link(link_id=0x100, timing=timing, time_slices=slices)
        assert mgr.superframe.get_link(0x100) is not None

    def test_unregister_link(self):
        """注销链路。"""
        mgr = ScheduleManager()
        timing = EventTimingParams()
        slices = [TimeSlice(offset=0, duration=10)]
        mgr.register_link(link_id=5, timing=timing, time_slices=slices)
        mgr.unregister_link(5)
        assert 5 not in mgr.event_schedulers
        assert mgr.superframe.get_link(5) is None

    def test_get_event_schedule_missing(self):
        """查询不存在的链路。"""
        mgr = ScheduleManager()
        assert mgr.get_event_schedule(99) is None

    def test_next_smf_slot(self):
        """下一个 SMF 时隙。"""
        mgr = ScheduleManager()
        mgr.configure_smf(SmfScheduleConfig(
            effective_slot=100, smf_interval=800,
        ))
        mgr.slot_counter.value = 500
        assert mgr.next_smf_slot() == 900

    def test_next_smf_slot_before_effective(self):
        """当前在生效时隙之前。"""
        mgr = ScheduleManager()
        mgr.configure_smf(SmfScheduleConfig(
            effective_slot=100, smf_interval=800,
        ))
        mgr.slot_counter.value = 50
        assert mgr.next_smf_slot() == 100

    def test_advance_time(self):
        """推进全局时钟。"""
        mgr = ScheduleManager()
        mgr.advance_time(100)
        assert mgr.slot_counter.value == 100

    def test_update_tx_rx_interval(self):
        """更新收发间隔。"""
        mgr = ScheduleManager()
        result = mgr.update_tx_rx_interval(TxRxIntervalType.INTERVAL_50US)
        assert result == 50
        assert mgr.tx_rx_interval == TxRxIntervalType.INTERVAL_50US

    def test_supervision_timeout_not_expired(self):
        """未超时。"""
        mgr = ScheduleManager()
        timing = EventTimingParams(supervision_timeout=100)
        mgr.register_link(link_id=1, timing=timing, anchor_slot=0)
        mgr.slot_counter.value = 10
        assert mgr.check_supervision_timeout(1) is False

    def test_supervision_timeout_expired(self):
        """超时检测。"""
        mgr = ScheduleManager()
        timing = EventTimingParams(supervision_timeout=1)  # 10 ms
        mgr.register_link(link_id=1, timing=timing, anchor_slot=0)
        # 推进到超过 10 ms = 10000 μs = 80 个基础时隙
        mgr.slot_counter.value = 100
        assert mgr.check_supervision_timeout(1) is True

    def test_supervision_timeout_missing_link(self):
        """不存在的链路不超时。"""
        mgr = ScheduleManager()
        assert mgr.check_supervision_timeout(99) is False
