# 使用 SLE 节点实体

`SleNode` 是项目的顶层实体, 封装了物理层 (`TxConfig`, TX/RX Pipeline)、MAC 层 (`LinkManager`, `QosManager`, `Scheduler`) 和安全 (`FrameCryptoContext`) 的全部功能, 对外提供统一的数据收发接口。

```{contents}
:local:
:depth: 2
```

## 基础操作

### 创建节点

:::{literalinclude} ../../examples/node_usage.py
:language: python
:start-after: "# [create-node-start]"
:end-before: "# [create-node-end]"
:dedent:
:::

### 建立连接

广播方与扫描方各创建一个节点:

:::{literalinclude} ../../examples/node_usage.py
:language: python
:start-after: "# [connection-start]"
:end-before: "# [connection-end]"
:dedent:
:::

### 发送与接收数据

:::{literalinclude} ../../examples/node_usage.py
:language: python
:start-after: "# [data-transfer-start]"
:end-before: "# [data-transfer-end]"
:dedent:
:::

### 断连与重置

:::{literalinclude} ../../examples/node_usage.py
:language: python
:start-after: "# [disconnect-start]"
:end-before: "# [disconnect-end]"
:dedent:
:::

## 进阶功能

### 配对与加密

启用加密后的数据通信:

:::{literalinclude} ../../examples/node_usage.py
:language: python
:start-after: "# [pairing-start]"
:end-before: "# [pairing-end]"
:dedent:
:::

### 事件回调

:::{literalinclude} ../../examples/node_usage.py
:language: python
:start-after: "# [callback-start]"
:end-before: "# [callback-end]"
:dedent:
:::

### 跳频

跳频通过 `advance_slot` 推进时隙, `current_channel` 获取当前信道:

:::{literalinclude} ../../examples/node_usage.py
:language: python
:start-after: "# [hopping-start]"
:end-before: "# [hopping-end]"
:dedent:
:::

### 功率控制

:::{literalinclude} ../../examples/node_usage.py
:language: python
:start-after: "# [power-control-start]"
:end-before: "# [power-control-end]"
:dedent:
:::

### 接入流程

:::{literalinclude} ../../examples/node_usage.py
:language: python
:start-after: "# [advertising-start]"
:end-before: "# [advertising-end]"
:dedent:
:::

### 测量信号

:::{literalinclude} ../../examples/node_usage.py
:language: python
:start-after: "# [measurement-start]"
:end-before: "# [measurement-end]"
:dedent:
:::

### MCS 自适应

:::{literalinclude} ../../examples/node_usage.py
:language: python
:start-after: "# [mcs-adaptive-start]"
:end-before: "# [mcs-adaptive-end]"
:dedent:
:::

### 查看节点状态

`stats` 属性返回包含所有关键指标的字典:

:::{literalinclude} ../../examples/node_usage.py
:language: python
:start-after: "# [node-stats-start]"
:end-before: "# [node-stats-end]"
:dedent:
:::

## 运行示例

```bash
make examples
```
