# 使用 SLE 节点实体

本指南说明如何使用 `SleNode` 进行数据收发和链路管理。

## 创建节点

:::{literalinclude} ../../examples/node_usage.py
:language: python
:start-after: "# [create-node-start]"
:end-before: "# [create-node-end]"
:dedent:
:::

## 建立连接

广播方与扫描方各创建一个节点:

:::{literalinclude} ../../examples/node_usage.py
:language: python
:start-after: "# [connection-start]"
:end-before: "# [connection-end]"
:dedent:
:::

## 发送与接收数据

:::{literalinclude} ../../examples/node_usage.py
:language: python
:start-after: "# [data-transfer-start]"
:end-before: "# [data-transfer-end]"
:dedent:
:::

## 配对与加密

启用加密后的数据通信:

:::{literalinclude} ../../examples/node_usage.py
:language: python
:start-after: "# [pairing-start]"
:end-before: "# [pairing-end]"
:dedent:
:::

## 事件回调

:::{literalinclude} ../../examples/node_usage.py
:language: python
:start-after: "# [callback-start]"
:end-before: "# [callback-end]"
:dedent:
:::

## 跳频

跳频通过 `advance_slot` 推进时隙, `current_channel` 获取当前信道:

:::{literalinclude} ../../examples/node_usage.py
:language: python
:start-after: "# [hopping-start]"
:end-before: "# [hopping-end]"
:dedent:
:::

## 功率控制

:::{literalinclude} ../../examples/node_usage.py
:language: python
:start-after: "# [power-control-start]"
:end-before: "# [power-control-end]"
:dedent:
:::

## 接入流程

:::{literalinclude} ../../examples/node_usage.py
:language: python
:start-after: "# [advertising-start]"
:end-before: "# [advertising-end]"
:dedent:
:::

## 测量信号

:::{literalinclude} ../../examples/node_usage.py
:language: python
:start-after: "# [measurement-start]"
:end-before: "# [measurement-end]"
:dedent:
:::

## MCS 自适应

:::{literalinclude} ../../examples/node_usage.py
:language: python
:start-after: "# [mcs-adaptive-start]"
:end-before: "# [mcs-adaptive-end]"
:dedent:
:::

## 查看节点状态

`stats` 属性返回包含所有关键指标的字典:

:::{literalinclude} ../../examples/node_usage.py
:language: python
:start-after: "# [node-stats-start]"
:end-before: "# [node-stats-end]"
:dedent:
:::

## 断连与重置

:::{literalinclude} ../../examples/node_usage.py
:language: python
:start-after: "# [disconnect-start]"
:end-before: "# [disconnect-end]"
:dedent:
:::

## 运行示例

```bash
uv run python examples/node_usage.py
```
