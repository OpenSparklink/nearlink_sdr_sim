# 使用 SLE 节点实体

本指南说明如何使用 `SleNode` 进行数据收发和链路管理。

## 创建节点

```python
from nearlink_sdr.node import SleNode, NodeConfig, NodeRole

# 使用默认配置
node = SleNode()

# 自定义配置
config = NodeConfig(
    address=b"\x01\x02\x03\x04\x05\x06",
    role=NodeRole.G_NODE,
    frame_type=2,
    mcs_index=7,
    bandwidth_mhz=1,
    pilot_interval=8,
    enable_encryption=False,
)
node = SleNode(config=config)
```

## 建立连接

广播方与扫描方各创建一个节点:

```python
# 广播方
broadcaster = SleNode(config=NodeConfig(address=b"\xAA" * 6))
broadcaster.start_advertising()
# 收到接入请求后接受连接
broadcaster.accept_connection(peer_address=b"\xBB" * 6)

# 扫描方
scanner = SleNode(config=NodeConfig(address=b"\xBB" * 6))
scanner.start_scanning()
scanner.connect(peer_address=b"\xAA" * 6)
```

## 发送与接收数据

```python
from nearlink_sdr.mac.qos import Priority

# 发送方: 提交数据到队列, 然后调用 transmit 生成 IQ 信号
node.send(b"hello world", Priority.NORMAL)
tx_result = node.transmit()

if tx_result.iq is not None:
    # tx_result.iq 是 complex128 numpy 数组, 可写入 USRP 或通过信道模型传输
    iq_signal = tx_result.iq

# 接收方: 从 IQ 信号解码
from nearlink_sdr.mac.frame import AsyncDataFrame

frame = AsyncDataFrame(segment_type=0, data=b"hello world")
n_mac_bytes = len(frame.pack())
rx_result = node.receive(iq_signal, n_mac_bytes)

if rx_result.success:
    print(rx_result.data)  # b"hello world"
```

## 配对与加密

启用加密后的数据通信:

```python
config = NodeConfig(
    address=b"\x01" * 6,
    enable_encryption=True,
)
node = SleNode(config=config)
node.start_advertising()
node.accept_connection(b"\x02" * 6)

# 发起配对
outgoing_msgs = node.start_pairing(b"\x02" * 6)
# 将 outgoing_msgs 发送到对端, 对端 process_pairing_message() 处理后回复
# 完成配对后, 后续 transmit()/receive() 自动加解密
```

## 事件回调

```python
from nearlink_sdr.node import NodeCallback, NodeState

class MyCallback(NodeCallback):
    def on_state_changed(self, old, new):
        print(f"状态: {old.name} → {new.name}")

    def on_connected(self, peer_address, role):
        print(f"已连接 {peer_address.hex()} 角色 {role.name}")

    def on_disconnected(self, reason):
        print(f"断开: {reason.name}")

node = SleNode(callback=MyCallback())
```

## MCS 自适应

```python
# 查询建议 MCS
suggested = node.recommended_mcs

# 手动更新 MCS
node.update_mcs(suggested)

# 查看统计
print(node.stats)
```

## 查看节点状态

`stats` 属性返回包含所有关键指标的字典:

```python
s = node.stats
# s["state"]        当前状态 (IDLE / CONNECTED / ...)
# s["tx_count"]     发送计数
# s["rx_count"]     接收计数
# s["fer"]          帧错误率
# s["mcs"]          当前 MCS 索引
# s["queue_size"]   发送队列长度
# s["flow_paused"]  流控是否暂停
# s["paired"]       是否已配对
# s["encrypted"]    是否已加密
```

## 断连与重置

```python
# 断开连接
node.disconnect()

# 重置到初始状态 (可重新建连)
node.reset()
```
