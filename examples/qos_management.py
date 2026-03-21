"""QoS 服务质量管理示例。

对应文档: how-to/qos-management.md
"""


def qos_basic_workflow():
    """QoS 基本工作流: 创建管理器、提交数据、处理反馈。"""
    # [qos-create-start]
    from nearlink_sdr.mac.qos import Priority, QosManager

    mgr = QosManager()
    # [qos-create-end]

    # [qos-submit-start]
    mgr.submit_data(b"\x01\x02\x03", priority=Priority.NORMAL)
    decision, _item = mgr.prepare_tx()
    # decision == TxDecision.NEW_DATA, _item 包含待发送数据
    # [qos-submit-end]

    # [qos-feedback-start]
    from nearlink_sdr.mac.qos import TxDecision

    decision = mgr.on_tx_feedback(crc_ok=True)
    if decision == TxDecision.NEW_DATA:
        # 对端确认, 可发送下一帧
        pass
    # [qos-feedback-end]

    # [qos-ctrl-fields-start]
    fields = mgr.get_ctrl_fields()
    # fields["tx_sn"], fields["rx_sn"], fields["flow_ctrl"], etc.
    # [qos-ctrl-fields-end]

    return decision, fields


def arq_usage():
    """ARQ 序列号管理。"""
    # [arq-start]
    from nearlink_sdr.mac.qos import ArqState, LinkType

    arq = ArqState(frame_type=3, link_type=LinkType.SYNC, max_retransmit=5)
    # [arq-end]
    return arq


def harq_usage():
    """HARQ 混合自动重传。"""
    # [harq-start]
    from nearlink_sdr.mac.qos import FeedbackMode, HarqController

    harq = HarqController(feedback_mode=FeedbackMode.CBG, n_cbg=4)
    harq.update_cbg_status([True, False, True, False])
    mask = harq.get_retransmit_cbg_mask()  # 返回位掩码, 每个 bit 对应一个 CBG
    # [harq-end]
    return mask


def quality_tracker():
    """链路质量跟踪与 AMC 自适应。"""
    # [quality-tracker-start]
    from nearlink_sdr.mac.qos import LinkQualityTracker

    tracker = LinkQualityTracker(window_size=32)
    frame_results = [True] * 28 + [False] * 4  # 模拟 32 帧结果
    for crc_ok in frame_results:
        tracker.record(crc_ok)

    adj = tracker.suggest_mcs_adjustment()
    # +1: 建议提升 MCS, -1: 建议降低, 0: 保持
    new_mcs = tracker.apply_suggestion()
    # [quality-tracker-end]
    return adj, new_mcs


def flow_control():
    """流控背压机制。"""
    # [flow-control-start]
    from nearlink_sdr.mac.qos import FlowController

    fc = FlowController(buffer_high_watermark=16, buffer_low_watermark=4)
    fc.enqueue(10)
    print(fc.flow_ctrl_bit)  # 1 (有后续数据)
    print(fc.is_paused)      # False
    # [flow-control-end]
    return fc.flow_ctrl_bit, fc.is_paused


def tx_queue():
    """优先级发送队列。"""
    # [tx-queue-start]
    from nearlink_sdr.mac.qos import Priority, TxQueue, TxQueueItem

    q = TxQueue(max_size=64)
    q.push(TxQueueItem(priority=Priority.NORMAL, data=b"hello"))
    q.push(TxQueueItem(priority=Priority.CONTROL, data=b"ctrl"))
    item = q.pop()  # 返回 CONTROL 优先级的 ctrl
    # [tx-queue-end]
    return item


if __name__ == "__main__":
    print("=== QoS 基本工作流 ===")
    decision, fields = qos_basic_workflow()
    print(f"decision={decision}, fields={fields}")
    print()

    print("=== ARQ ===")
    arq = arq_usage()
    print(f"frame_type={arq.frame_type}")
    print()

    print("=== HARQ ===")
    mask = harq_usage()
    print(f"retransmit mask={mask:#06b}")
    print()

    print("=== 链路质量跟踪 ===")
    adj, mcs = quality_tracker()
    print(f"adj={adj}, new_mcs={mcs}")
    print()

    print("=== 流控 ===")
    flow_control()
    print()

    print("=== 发送队列 ===")
    item = tx_queue()
    print(f"popped: priority={item.priority.name}, data={item.data}")
