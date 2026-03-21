# 快速入门

本教程引导你从安装到运行第一次链路仿真, 完成对 nearlink-sdr 的初步了解。

## 前置条件

- Python 3.14 或更高版本
- [uv](https://docs.astral.sh/uv/) 包管理器

## 安装

克隆仓库并安装依赖:

```bash
git clone https://github.com/sanchuanhehe/nearlink_sdr_sim.git nearlink-sdr
cd nearlink-sdr
uv sync
```

## 运行测试

确认所有模块工作正常:

```bash
uv run pytest tests/ -v --tb=short
```

## 第一次仿真: GFSK 链路

GFSK 是 SparkLink SLE 帧类型 1 使用的调制方式。下面的代码演示一次完整的 GFSK 调制-信道-解调流程:

:::{literalinclude} ../../examples/getting_started.py
:language: python
:start-after: "# [gfsk-link-start]"
:end-before: "# [gfsk-link-end]"
:dedent:
:::

完整代码见 `examples/getting_started.py` 中的 `gfsk_link()` 函数。

## 第一次仿真: PSK 编码链路

帧类型 2/3/4 使用 PSK 调制。结合 Polar 编码可以获得编码增益:

:::{literalinclude} ../../examples/getting_started.py
:language: python
:start-after: "# [polar-psk-start]"
:end-before: "# [polar-psk-end]"
:dedent:
:::

## BER 曲线仿真

项目内置了批量仿真函数, 可以直接绘制 BER 曲线:

```bash
uv run python -m nearlink_sdr.sim.link_sim phase1
# 输出 BER 数据并保存 ber_phase1.png
```

## 全链路 Pipeline 仿真

调用 `sim_pipeline_link` 进行端到端仿真, 覆盖 CRC、Polar 编码、加扰、调制、帧组装等全部物理层处理:

:::{literalinclude} ../../examples/getting_started.py
:language: python
:start-after: "# [pipeline-sim-start]"
:end-before: "# [pipeline-sim-end]"
:dedent:
:::

## SleNode 节点仿真

`SleNode` 是项目的顶层实体, 将物理层和 MAC 层全部组件整合为统一接口:

:::{literalinclude} ../../examples/getting_started.py
:language: python
:start-after: "# [node-basic-start]"
:end-before: "# [node-basic-end]"
:dedent:
:::

## Phase 15 集成仿真

项目提供基于 SleNode 的完整集成仿真, 覆盖跳频、功率自适应、接入流程和信道扫频:

```bash
uv run python -m nearlink_sdr.sim.link_sim phase15
# 输出四面板可视化图: 跳频/接入/功率/信道
```

## 运行示例

所有入门示例已整合为独立脚本, 可直接运行:

```bash
uv run python examples/getting_started.py
```

## 下一步

- 阅读 [操作指南](../how-to/index.md) 了解具体任务的操作方法
- 阅读 [协议总览](../explanation/overview.md) 理解 SparkLink SLE 协议全貌
- 阅读 [设计说明](../explanation/architecture.md) 理解系统架构
- 查阅 [技术参考](../reference/index.md) 获取完整的接口文档
