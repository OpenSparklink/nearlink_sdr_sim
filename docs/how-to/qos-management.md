# QoS 服务质量管理

## 概述

`mac.qos` 模块实现了标准 6.5 节定义的数据传输质量控制, 包含 ARQ 重传管理、
HARQ 混合自动重传、流控、链路质量跟踪和优先级发送队列。

## 基本用法

### 创建 QoS 管理器

```python
from nearlink_sdr.mac.qos import QosManager, Priority

mgr = QosManager()
```

### 提交数据并发送

```python
mgr.submit_data(b"\x01\x02\x03", priority=Priority.NORMAL)
decision, item = mgr.prepare_tx()
# decision == TxDecision.NEW_DATA, item 包含待发送数据
```

### 处理 ACK/NACK 反馈

```python
from nearlink_sdr.mac.qos import TxDecision

decision = mgr.on_tx_feedback(crc_ok=True)
if decision == TxDecision.NEW_DATA:
    # 对端确认, 可发送下一帧
    pass
```

### 获取控制信息字段

```python
fields = mgr.get_ctrl_fields()
# fields["tx_sn"], fields["rx_sn"], fields["flow_ctrl"], etc.
```

## ARQ 序列号管理

`ArqState` 管理不同帧类型的发送/接收序列号:

| 帧类型 | SN 位宽 | 取值范围 |
|--------|---------|----------|
| FT1    | 1 bit   | 0-1      |
| FT2    | 1 bit   | 0-1      |
| FT3/FT4 | 5 bit  | 0-31     |

异步链路默认无限重传, 同步链路可设置 `max_retransmit` 限制。

```python
from nearlink_sdr.mac.qos import ArqState, LinkType

arq = ArqState(frame_type=3, link_type=LinkType.SYNC, max_retransmit=5)
```

## HARQ 反馈

`HarqController` 支持两种反馈模式:

- **TB 模式**: 整个传输块 ACK/NACK, `harq_feedback` 字段为期望 SN
- **CBG 模式**: 按编码块组反馈, `harq_feedback` 每 bit 对应一个 CBG

```python
from nearlink_sdr.mac.qos import HarqController, FeedbackMode

harq = HarqController(feedback_mode=FeedbackMode.CBG, n_cbg=4)
harq.update_cbg_status([True, False, True, False])
mask = harq.get_retransmit_cbg_mask()  # 需要重传的 CBG 掩码
```

## 链路质量跟踪与 AMC

`LinkQualityTracker` 通过滑动窗口统计 FER, 建议 MCS 调整:

```python
from nearlink_sdr.mac.qos import LinkQualityTracker

tracker = LinkQualityTracker(window_size=32)
for crc_ok in frame_results:
    tracker.record(crc_ok)

adj = tracker.suggest_mcs_adjustment()
# +1: 建议提升 MCS, -1: 建议降低, 0: 保持
new_mcs = tracker.apply_suggestion()
```

## 流控

`FlowController` 基于高/低水位机制实现背压:

```python
from nearlink_sdr.mac.qos import FlowController

fc = FlowController(buffer_high_watermark=16, buffer_low_watermark=4)
fc.enqueue(10)
print(fc.flow_ctrl_bit)  # 1 (有后续数据)
print(fc.is_paused)      # False
```

## 优先级发送队列

`TxQueue` 提供 5 级优先级 (CONTROL > REALTIME > HIGH > NORMAL > LOW),
重传数据在同优先级内优先出队:

```python
from nearlink_sdr.mac.qos import TxQueue, TxQueueItem, Priority

q = TxQueue(max_size=64)
q.push(TxQueueItem(priority=Priority.NORMAL, data=b"hello"))
q.push(TxQueueItem(priority=Priority.CONTROL, data=b"ctrl"))
item = q.pop()  # 返回 CONTROL 优先级的 ctrl
```
