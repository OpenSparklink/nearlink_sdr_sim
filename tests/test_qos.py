"""QoS 服务质量管理模块测试。"""

import pytest

from nearlink_sdr.mac.qos import (
    ArqState,
    FeedbackMode,
    FlowController,
    HarqController,
    LinkQualityTracker,
    LinkType,
    Priority,
    QosManager,
    TxDecision,
    TxQueue,
    TxQueueItem,
)

# ===================================================================
# ArqState 测试
# ===================================================================


class TestArqStateFT1:
    """FT1 帧类型的 ARQ: 1-bit SN。"""

    def test_initial_state(self):
        arq = ArqState(frame_type=1)
        assert arq.tx_sn == 0
        assert arq.expected_rx_sn == 0
        assert arq.sn_modulus == 2
        assert not arq.pending_ack

    def test_tx_new_sets_pending(self):
        arq = ArqState(frame_type=1)
        sn = arq.on_tx_new(b"\x01\x02")
        assert sn == 0
        assert arq.pending_ack
        assert arq._last_tx_data == b"\x01\x02"

    def test_ack_flips_sn(self):
        arq = ArqState(frame_type=1)
        arq.on_tx_new(b"\xAA")
        arq.on_ack_received()
        assert arq.tx_sn == 1
        assert not arq.pending_ack

    def test_sn_wraps_around(self):
        arq = ArqState(frame_type=1)
        arq.on_tx_new(b"\x01")
        arq.on_ack_received()
        assert arq.tx_sn == 1
        arq.on_tx_new(b"\x02")
        arq.on_ack_received()
        assert arq.tx_sn == 0

    def test_nack_triggers_retransmit(self):
        arq = ArqState(frame_type=1)
        arq.on_tx_new(b"\x01")
        decision = arq.on_nack_received()
        assert decision == TxDecision.RETRANSMIT
        assert arq.retransmit_count == 1

    def test_rx_new_packet(self):
        arq = ArqState(frame_type=1)
        assert arq.on_rx_packet(0)
        assert arq.expected_rx_sn == 1

    def test_rx_duplicate_packet(self):
        arq = ArqState(frame_type=1)
        arq.on_rx_packet(0)
        assert not arq.on_rx_packet(0)
        assert arq.expected_rx_sn == 1


class TestArqStateFT2:
    """FT2 帧类型: 1-bit SN (ControlInfoA2)。"""

    def test_sn_modulus(self):
        arq = ArqState(frame_type=2)
        assert arq.sn_modulus == 2

    def test_async_retransmit_unlimited(self):
        arq = ArqState(frame_type=2, link_type=LinkType.ASYNC)
        arq.on_tx_new(b"\x01")
        for _ in range(100):
            decision = arq.on_nack_received()
            assert decision == TxDecision.RETRANSMIT
        assert arq.retransmit_count == 100


class TestArqStateFT34:
    """FT3/FT4 帧类型: 5-bit SN (ControlInfoA3)。"""

    def test_sn_modulus(self):
        arq = ArqState(frame_type=3)
        assert arq.sn_modulus == 32

    def test_ft4_sn_modulus(self):
        arq = ArqState(frame_type=4)
        assert arq.sn_modulus == 32

    def test_5bit_sn_wrap(self):
        arq = ArqState(frame_type=3)
        for i in range(32):
            assert arq.tx_sn == i
            arq.on_tx_new(bytes([i]))
            arq.on_ack_received()
        assert arq.tx_sn == 0

    def test_5bit_rx_sn_wrap(self):
        arq = ArqState(frame_type=4)
        for i in range(32):
            assert arq.on_rx_packet(i)
        assert arq.expected_rx_sn == 0


class TestArqStateSyncLink:
    """同步链路 ARQ: 有限重传。"""

    def test_discard_after_max_retransmit(self):
        arq = ArqState(frame_type=3, link_type=LinkType.SYNC, max_retransmit=3)
        arq.on_tx_new(b"\x01")
        for _ in range(3):
            assert arq.on_nack_received() == TxDecision.RETRANSMIT
        decision = arq.on_nack_received()
        assert decision == TxDecision.NEW_DATA
        assert not arq.pending_ack

    def test_no_feedback_same_as_nack(self):
        arq = ArqState(frame_type=2, link_type=LinkType.SYNC, max_retransmit=1)
        arq.on_tx_new(b"\x01")
        assert arq.on_no_feedback() == TxDecision.RETRANSMIT
        decision = arq.on_no_feedback()
        assert decision == TxDecision.NEW_DATA


# ===================================================================
# HarqController 测试
# ===================================================================


class TestHarqControllerTB:
    """TB 模式 HARQ。"""

    def test_encode_feedback_tb(self):
        harq = HarqController(feedback_mode=FeedbackMode.TB)
        fb = harq.encode_harq_feedback(ack=True, peer_sn=5)
        assert fb == 5

    def test_decode_feedback_tb(self):
        harq = HarqController(feedback_mode=FeedbackMode.TB, n_cbg=4)
        result = harq.decode_harq_feedback(0x03)
        assert result == [True, True, True, True]

    def test_no_cbg_retransmit_in_tb(self):
        harq = HarqController(feedback_mode=FeedbackMode.TB)
        assert not harq.needs_cbg_retransmit()

    def test_decide_tx_ack(self):
        harq = HarqController(feedback_mode=FeedbackMode.TB)
        arq = ArqState(frame_type=2)
        arq.on_tx_new(b"\x01")
        decision = harq.decide_tx(ack_received=True, arq=arq)
        assert decision == TxDecision.NEW_DATA
        assert not arq.pending_ack


class TestHarqControllerCBG:
    """CBG 模式 HARQ。"""

    def test_encode_cbg_bitmap(self):
        harq = HarqController(feedback_mode=FeedbackMode.CBG, n_cbg=4)
        harq.update_cbg_status([True, False, True, False])
        fb = harq.encode_harq_feedback(ack=False)
        assert fb == 0b0101

    def test_decode_cbg_bitmap(self):
        harq = HarqController(feedback_mode=FeedbackMode.CBG, n_cbg=4)
        result = harq.decode_harq_feedback(0b1010)
        assert result == [False, True, False, True]

    def test_needs_cbg_retransmit_partial(self):
        harq = HarqController(feedback_mode=FeedbackMode.CBG, n_cbg=4)
        harq.update_cbg_status([True, False, True, False])
        assert harq.needs_cbg_retransmit()

    def test_no_retransmit_all_acked(self):
        harq = HarqController(feedback_mode=FeedbackMode.CBG, n_cbg=4)
        harq.update_cbg_status([True, True, True, True])
        assert not harq.needs_cbg_retransmit()

    def test_no_retransmit_none_acked(self):
        harq = HarqController(feedback_mode=FeedbackMode.CBG, n_cbg=4)
        assert not harq.needs_cbg_retransmit()

    def test_retransmit_cbg_mask(self):
        harq = HarqController(feedback_mode=FeedbackMode.CBG, n_cbg=4)
        harq.update_cbg_status([True, False, True, False])
        mask = harq.get_retransmit_cbg_mask()
        assert mask == 0b1010

    def test_decide_tx_cbg_retransmit(self):
        harq = HarqController(feedback_mode=FeedbackMode.CBG, n_cbg=4)
        arq = ArqState(frame_type=3)
        arq.on_tx_new(b"\x01")
        harq.update_cbg_status([True, False, True, False])
        decision = harq.decide_tx(ack_received=False, arq=arq)
        assert decision == TxDecision.RETRANSMIT_CBG

    def test_reset_cbg(self):
        harq = HarqController(feedback_mode=FeedbackMode.CBG, n_cbg=4)
        harq.update_cbg_status([True, True, True, True])
        harq.reset_cbg()
        assert not harq.all_cbg_acked

    def test_all_cbg_acked(self):
        harq = HarqController(feedback_mode=FeedbackMode.CBG, n_cbg=2)
        harq.update_cbg_status([True, True])
        assert harq.all_cbg_acked

    def test_max_cbg_clamped(self):
        harq = HarqController(feedback_mode=FeedbackMode.CBG, n_cbg=16)
        assert len(harq._cbg_status) == 8


# ===================================================================
# FlowController 测试
# ===================================================================


class TestFlowController:

    def test_initial_state(self):
        fc = FlowController()
        assert fc.flow_ctrl_bit == 0
        assert not fc.is_paused
        assert fc.buffer_count == 0

    def test_enqueue_sets_flow_ctrl(self):
        fc = FlowController()
        fc.enqueue()
        assert fc.flow_ctrl_bit == 1

    def test_dequeue_clears_flow_ctrl(self):
        fc = FlowController()
        fc.enqueue()
        fc.dequeue()
        assert fc.flow_ctrl_bit == 0

    def test_high_watermark_pause(self):
        fc = FlowController(buffer_high_watermark=4, buffer_low_watermark=1)
        for _ in range(4):
            fc.enqueue()
        assert fc.is_paused

    def test_low_watermark_unpause(self):
        fc = FlowController(buffer_high_watermark=4, buffer_low_watermark=1)
        for _ in range(4):
            fc.enqueue()
        assert fc.is_paused
        for _ in range(3):
            fc.dequeue()
        assert not fc.is_paused

    def test_dequeue_below_zero(self):
        fc = FlowController()
        fc.dequeue(5)
        assert fc.buffer_count == 0

    def test_batch_enqueue_dequeue(self):
        fc = FlowController()
        fc.enqueue(10)
        assert fc.buffer_count == 10
        fc.dequeue(5)
        assert fc.buffer_count == 5


# ===================================================================
# LinkQualityTracker 测试
# ===================================================================


class TestLinkQualityTracker:

    def test_initial_fer_zero(self):
        lqt = LinkQualityTracker()
        assert lqt.fer == 0.0
        assert lqt.success_rate == 1.0

    def test_all_success(self):
        lqt = LinkQualityTracker(window_size=10)
        for _ in range(10):
            lqt.record(True)
        assert lqt.fer == 0.0

    def test_all_failure(self):
        lqt = LinkQualityTracker(window_size=10)
        for _ in range(10):
            lqt.record(False)
        assert lqt.fer == 1.0

    def test_mixed_fer(self):
        lqt = LinkQualityTracker(window_size=10)
        for _ in range(8):
            lqt.record(True)
        for _ in range(2):
            lqt.record(False)
        assert lqt.fer == pytest.approx(0.2, abs=0.01)

    def test_sliding_window(self):
        lqt = LinkQualityTracker(window_size=4)
        for _ in range(4):
            lqt.record(False)
        assert lqt.fer == 1.0
        for _ in range(4):
            lqt.record(True)
        assert lqt.fer == 0.0

    def test_suggest_increase_mcs(self):
        lqt = LinkQualityTracker(window_size=8, fer_target_low=0.01)
        lqt._current_mcs = 5
        for _ in range(8):
            lqt.record(True)
        assert lqt.suggest_mcs_adjustment() == 1

    def test_suggest_decrease_mcs(self):
        lqt = LinkQualityTracker(window_size=8, fer_target_high=0.10)
        lqt._current_mcs = 5
        for _ in range(6):
            lqt.record(True)
        for _ in range(2):
            lqt.record(False)
        assert lqt.suggest_mcs_adjustment() == -1

    def test_suggest_hold_mcs(self):
        lqt = LinkQualityTracker(window_size=20, fer_target_low=0.01, fer_target_high=0.10)
        lqt._current_mcs = 5
        for _ in range(19):
            lqt.record(True)
        lqt.record(False)
        # FER = 1/20 = 0.05, 介于 0.01 和 0.10 之间
        assert lqt.suggest_mcs_adjustment() == 0

    def test_apply_suggestion(self):
        lqt = LinkQualityTracker(window_size=4)
        lqt._current_mcs = 11
        for _ in range(4):
            lqt.record(True)
        new_mcs = lqt.apply_suggestion()
        assert new_mcs == 12

    def test_mcs_clamp_max(self):
        lqt = LinkQualityTracker()
        lqt.current_mcs = 20
        assert lqt.current_mcs == 12

    def test_mcs_clamp_min(self):
        lqt = LinkQualityTracker()
        lqt.current_mcs = -5
        assert lqt.current_mcs == 0

    def test_encode_decode_lqi(self):
        lqt = LinkQualityTracker()
        lqt._current_mcs = 9
        lqi = lqt.encode_lqi()
        decoded = LinkQualityTracker.decode_lqi(lqi)
        assert decoded == 9

    def test_not_enough_history(self):
        lqt = LinkQualityTracker(window_size=32)
        for _ in range(10):
            lqt.record(True)
        assert lqt.suggest_mcs_adjustment() == 0

    def test_no_increase_at_max_mcs(self):
        lqt = LinkQualityTracker(window_size=4)
        lqt._current_mcs = 12
        for _ in range(4):
            lqt.record(True)
        assert lqt.suggest_mcs_adjustment() == 0

    def test_no_decrease_at_min_mcs(self):
        lqt = LinkQualityTracker(window_size=4, fer_target_high=0.1)
        lqt._current_mcs = 0
        for _ in range(4):
            lqt.record(False)
        assert lqt.suggest_mcs_adjustment() == 0


# ===================================================================
# TxQueue 测试
# ===================================================================


class TestTxQueue:

    def test_empty_queue(self):
        q = TxQueue()
        assert q.is_empty
        assert q.pop() is None
        assert q.peek() is None
        assert q.size == 0

    def test_push_pop(self):
        q = TxQueue()
        item = TxQueueItem(priority=Priority.NORMAL, data=b"\x01")
        assert q.push(item)
        assert q.size == 1
        result = q.pop()
        assert result is item
        assert q.is_empty

    def test_priority_ordering(self):
        q = TxQueue()
        low = TxQueueItem(priority=Priority.LOW, data=b"low")
        high = TxQueueItem(priority=Priority.HIGH, data=b"high")
        ctrl = TxQueueItem(priority=Priority.CONTROL, data=b"ctrl")
        q.push(low)
        q.push(high)
        q.push(ctrl)
        assert q.pop().data == b"ctrl"
        assert q.pop().data == b"high"
        assert q.pop().data == b"low"

    def test_fifo_within_priority(self):
        q = TxQueue()
        for i in range(3):
            q.push(TxQueueItem(priority=Priority.NORMAL, data=bytes([i])))
        assert q.pop().data == bytes([0])
        assert q.pop().data == bytes([1])
        assert q.pop().data == bytes([2])

    def test_retransmit_priority_within_level(self):
        q = TxQueue()
        normal = TxQueueItem(priority=Priority.NORMAL, data=b"new")
        retx = TxQueueItem(priority=Priority.NORMAL, data=b"retx", retransmit=True)
        q.push(normal)
        q.push(retx)
        assert q.pop().data == b"retx"

    def test_max_size_limit(self):
        q = TxQueue(max_size=2)
        q.push(TxQueueItem(priority=Priority.NORMAL, data=b"1"))
        q.push(TxQueueItem(priority=Priority.NORMAL, data=b"2"))
        assert q.is_full
        assert not q.push(TxQueueItem(priority=Priority.NORMAL, data=b"3"))
        assert q.size == 2

    def test_peek_does_not_remove(self):
        q = TxQueue()
        q.push(TxQueueItem(priority=Priority.NORMAL, data=b"x"))
        peek_result = q.peek()
        assert peek_result is not None
        assert q.size == 1

    def test_count_by_priority(self):
        q = TxQueue()
        q.push(TxQueueItem(priority=Priority.NORMAL, data=b"1"))
        q.push(TxQueueItem(priority=Priority.NORMAL, data=b"2"))
        q.push(TxQueueItem(priority=Priority.HIGH, data=b"3"))
        assert q.count_by_priority(Priority.NORMAL) == 2
        assert q.count_by_priority(Priority.HIGH) == 1
        assert q.count_by_priority(Priority.LOW) == 0

    def test_clear(self):
        q = TxQueue()
        for _ in range(5):
            q.push(TxQueueItem(priority=Priority.NORMAL, data=b"x"))
        q.clear()
        assert q.is_empty
        assert q.size == 0


# ===================================================================
# QosManager 集成测试
# ===================================================================


class TestQosManager:

    def test_submit_and_prepare_tx(self):
        mgr = QosManager()
        mgr.submit_data(b"hello", Priority.NORMAL)
        decision, item = mgr.prepare_tx()
        assert decision == TxDecision.NEW_DATA
        assert item is not None
        assert item.data == b"hello"
        assert mgr.arq.pending_ack

    def test_empty_prepare_tx(self):
        mgr = QosManager()
        decision, item = mgr.prepare_tx()
        assert decision == TxDecision.EMPTY
        assert item is None

    def test_retransmit_pending(self):
        mgr = QosManager()
        mgr.submit_data(b"hello")
        mgr.prepare_tx()
        decision, item = mgr.prepare_tx()
        assert decision == TxDecision.RETRANSMIT
        assert item is None

    def test_feedback_ack_advances(self):
        mgr = QosManager()
        mgr.submit_data(b"hello")
        mgr.prepare_tx()
        decision = mgr.on_tx_feedback(crc_ok=True)
        assert decision == TxDecision.NEW_DATA
        assert not mgr.arq.pending_ack

    def test_feedback_nack_retransmit(self):
        mgr = QosManager()
        mgr.submit_data(b"hello")
        mgr.prepare_tx()
        decision = mgr.on_tx_feedback(crc_ok=False)
        assert decision == TxDecision.RETRANSMIT

    def test_get_ctrl_fields(self):
        mgr = QosManager()
        mgr.submit_data(b"hello")
        mgr.prepare_tx()
        fields = mgr.get_ctrl_fields()
        assert "tx_sn" in fields
        assert "rx_sn" in fields
        assert "flow_ctrl" in fields
        assert "empty_packet" in fields
        assert "harq_feedback" in fields

    def test_quality_tracks_fer(self):
        mgr = QosManager()
        for _ in range(10):
            mgr.submit_data(b"x")
            mgr.prepare_tx()
            mgr.on_tx_feedback(crc_ok=True)
        assert mgr.quality.fer == 0.0

    def test_queue_full_rejects(self):
        mgr = QosManager(tx_queue=TxQueue(max_size=2))
        assert mgr.submit_data(b"1")
        assert mgr.submit_data(b"2")
        assert not mgr.submit_data(b"3")

    def test_flow_ctrl_reflects_queue(self):
        mgr = QosManager()
        assert mgr.flow.flow_ctrl_bit == 0
        mgr.submit_data(b"hello")
        assert mgr.flow.flow_ctrl_bit == 1
        mgr.prepare_tx()
        assert mgr.flow.flow_ctrl_bit == 0
