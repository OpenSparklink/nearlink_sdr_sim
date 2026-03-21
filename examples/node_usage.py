"""SLE 节点使用示例。

对应文档: how-to/node-usage.md
"""


def create_node():
    """创建节点: 默认配置与自定义配置。"""
    # [create-node-start]
    from nearlink_sdr.node import NodeConfig, NodeRole, SleNode

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
    # [create-node-end]
    return node


def connection_lifecycle():
    """建立连接: 广播方与扫描方。"""
    # [connection-start]
    from nearlink_sdr.node import NodeConfig, SleNode

    # 广播方
    broadcaster = SleNode(config=NodeConfig(address=b"\xAA" * 6))
    broadcaster.start_advertising()
    # 收到接入请求后接受连接
    broadcaster.accept_connection(peer_address=b"\xBB" * 6)

    # 扫描方
    scanner = SleNode(config=NodeConfig(address=b"\xBB" * 6))
    scanner.start_scanning()
    scanner.connect(peer_address=b"\xAA" * 6)
    # [connection-end]
    return broadcaster, scanner


def data_transfer():
    """发送与接收数据。"""
    # [data-transfer-start]
    from nearlink_sdr.mac.qos import Priority
    from nearlink_sdr.node import SleNode

    # 发送方: 提交数据到队列, 然后调用 transmit 生成 IQ 信号
    node = SleNode()
    node.send(b"hello world", Priority.NORMAL)
    tx_result = node.transmit()

    if tx_result.iq is not None:
        # tx_result.iq 是 complex128 numpy 数组, 可写入 USRP 或通过信道模型传输
        _iq_signal = tx_result.iq
    # [data-transfer-end]
    return tx_result


def pairing_encryption():
    """配对与加密通信。"""
    # [pairing-start]
    from nearlink_sdr.node import NodeConfig, SleNode

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
    # [pairing-end]
    return outgoing_msgs


def event_callback():
    """事件回调定义。"""
    # [callback-start]
    from nearlink_sdr.node import NodeCallback

    class MyCallback(NodeCallback):
        def on_state_changed(self, old, new):
            print(f"状态: {old.name} → {new.name}")

        def on_connected(self, peer_address, role):
            print(f"已连接 {peer_address.hex()} 角色 {role.name}")

        def on_disconnected(self, reason):
            print(f"断开: {reason.name}")
    # [callback-end]
    return MyCallback


def hopping():
    """跳频配置与操作。"""
    # [hopping-start]
    from nearlink_sdr.node import NodeConfig, SleNode

    config = NodeConfig(
        address=b"\x01" * 6,
        band="2400",
        hop_param2=0xABCD,
    )
    node = SleNode(config=config)
    node.advance_slot(1)
    channel = node.current_channel
    print(f"跳频信道: {channel}")
    # [hopping-end]
    return channel


def power_control():
    """功率控制。"""
    # [power-control-start]
    from nearlink_sdr.node import NodeConfig, SleNode

    config = NodeConfig(
        address=b"\x01" * 6,
        tx_power_dbm=0.0,
    )
    node = SleNode(config=config)
    new_power = node.adjust_power(3.0)  # 增加 3 dB
    print(f"当前功率: {new_power} dBm")
    # [power-control-end]
    return new_power


def advertising():
    """启动广播。"""
    # [advertising-start]
    from nearlink_sdr.node import NodeConfig, NodeRole, SleNode

    config = NodeConfig(
        address=b"\xAA" * 6,
        role=NodeRole.G_NODE,
    )
    node = SleNode(config=config)

    # 启动广播
    bcast = node.start_advertising()
    # [advertising-end]
    return bcast


def measurement_signal():
    """生成测量信号。"""
    # [measurement-start]
    from nearlink_sdr.node import SleNode

    node = SleNode()
    signal = node.generate_measurement_signal(n_measur=64, security_type=1)
    # [measurement-end]
    return signal


def mcs_adaptive():
    """MCS 自适应调整。"""
    # [mcs-adaptive-start]
    from nearlink_sdr.node import SleNode

    node = SleNode()

    # 查询建议 MCS
    suggested = node.recommended_mcs

    # 手动更新 MCS
    node.update_mcs(suggested)

    # 查看统计
    print(node.stats)
    # [mcs-adaptive-end]
    return suggested


def node_stats():
    """查看节点状态。"""
    # [node-stats-start]
    from nearlink_sdr.node import SleNode

    node = SleNode()
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
    # [node-stats-end]
    return s


def disconnect_reset():
    """断连与重置。"""
    # [disconnect-start]
    from nearlink_sdr.node import SleNode

    node = SleNode()
    # 断开连接
    node.disconnect()

    # 重置到初始状态 (可重新建连)
    node.reset()
    # [disconnect-end]
    return node


if __name__ == "__main__":
    print("=== 创建节点 ===")
    create_node()
    print()

    print("=== 建立连接 ===")
    connection_lifecycle()
    print()

    print("=== 数据收发 ===")
    data_transfer()
    print()

    print("=== 跳频 ===")
    hopping()
    print()

    print("=== 功率控制 ===")
    power_control()
    print()

    print("=== 节点状态 ===")
    node_stats()
