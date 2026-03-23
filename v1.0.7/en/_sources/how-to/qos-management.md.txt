# QoS 服务质量管理

## 概述

`mac.qos` 模块实现了标准 6.5 节定义的数据传输质量控制, 包含 ARQ 重传管理、
HARQ 混合自动重传、流控、链路质量跟踪和优先级发送队列。

## 基本用法

### 创建 QoS 管理器

:::{literalinclude} ../../examples/qos_management.py
:language: python
:start-after: "# [qos-create-start]"
:end-before: "# [qos-create-end]"
:dedent:
:::

### 提交数据并发送

:::{literalinclude} ../../examples/qos_management.py
:language: python
:start-after: "# [qos-submit-start]"
:end-before: "# [qos-submit-end]"
:dedent:
:::

### 处理 ACK/NACK 反馈

:::{literalinclude} ../../examples/qos_management.py
:language: python
:start-after: "# [qos-feedback-start]"
:end-before: "# [qos-feedback-end]"
:dedent:
:::

### 获取控制信息字段

:::{literalinclude} ../../examples/qos_management.py
:language: python
:start-after: "# [qos-ctrl-fields-start]"
:end-before: "# [qos-ctrl-fields-end]"
:dedent:
:::

## ARQ 序列号管理

`ArqState` 管理不同帧类型的发送/接收序列号:

| 帧类型 | SN 位宽 | 取值范围 |
|--------|---------|----------|
| FT1    | 1 bit   | 0-1      |
| FT2    | 1 bit   | 0-1      |
| FT3/FT4 | 5 bit  | 0-31     |

异步链路默认无限重传, 同步链路可设置 `max_retransmit` 限制。

:::{literalinclude} ../../examples/qos_management.py
:language: python
:start-after: "# [arq-start]"
:end-before: "# [arq-end]"
:dedent:
:::

## HARQ 反馈

`HarqController` 支持两种反馈模式:

- **TB 模式**: 整个传输块 ACK/NACK, `harq_feedback` 字段为期望 SN
- **CBG 模式**: 按编码块组反馈, `harq_feedback` 每 bit 对应一个 CBG

:::{literalinclude} ../../examples/qos_management.py
:language: python
:start-after: "# [harq-start]"
:end-before: "# [harq-end]"
:dedent:
:::

## 链路质量跟踪与 AMC

`LinkQualityTracker` 通过滑动窗口统计 FER, 建议 MCS 调整:

:::{literalinclude} ../../examples/qos_management.py
:language: python
:start-after: "# [quality-tracker-start]"
:end-before: "# [quality-tracker-end]"
:dedent:
:::

## 流控

`FlowController` 基于高/低水位机制实现背压:

:::{literalinclude} ../../examples/qos_management.py
:language: python
:start-after: "# [flow-control-start]"
:end-before: "# [flow-control-end]"
:dedent:
:::

## 优先级发送队列

`TxQueue` 提供 5 级优先级 (CONTROL > REALTIME > HIGH > NORMAL > LOW),
重传数据在同优先级内优先出队:

:::{literalinclude} ../../examples/qos_management.py
:language: python
:start-after: "# [tx-queue-start]"
:end-before: "# [tx-queue-end]"
:dedent:
:::

## 运行示例

```bash
make examples
```
