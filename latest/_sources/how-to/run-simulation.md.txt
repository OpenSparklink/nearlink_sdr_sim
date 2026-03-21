# 运行链路仿真

## 无编码 BER 仿真

使用内置仿真函数, 在多个信噪比上批量计算 BER:

:::{literalinclude} ../../examples/run_simulation.py
:language: python
:start-after: "# [ber-gfsk-start]"
:end-before: "# [ber-gfsk-end]"
:dedent:
:::

QPSK 仿真:

:::{literalinclude} ../../examples/run_simulation.py
:language: python
:start-after: "# [ber-psk-start]"
:end-before: "# [ber-psk-end]"
:dedent:
:::

## Polar 编码 BER 仿真

:::{literalinclude} ../../examples/run_simulation.py
:language: python
:start-after: "# [polar-coded-start]"
:end-before: "# [polar-coded-end]"
:dedent:
:::

## 多径信道仿真

:::{literalinclude} ../../examples/run_simulation.py
:language: python
:start-after: "# [channel-model-start]"
:end-before: "# [channel-model-end]"
:dedent:
:::

## 跳频序列生成

:::{literalinclude} ../../examples/run_simulation.py
:language: python
:start-after: "# [hopping-seq-start]"
:end-before: "# [hopping-seq-end]"
:dedent:
:::

## 绘制 BER 曲线

```bash
uv run python -m nearlink_sdr.sim.link_sim phase1
# 结果保存到 ber_phase1.png
```

## 全链路 Pipeline 仿真

使用 `sim_pipeline_link` 运行端到端 Pipeline 仿真, 内部调用完整的 `tx_chain` -> AWGN 信道 -> `rx_chain` 链路:

:::{literalinclude} ../../examples/run_simulation.py
:language: python
:start-after: "# [pipeline-ft2-start]"
:end-before: "# [pipeline-ft2-end]"
:dedent:
:::

支持所有帧类型:

:::{literalinclude} ../../examples/run_simulation.py
:language: python
:start-after: "# [pipeline-other-start]"
:end-before: "# [pipeline-other-end]"
:dedent:
:::

## SleNode 集成仿真 (Phase 15)

Phase 15 基于 `SleNode` 实体进行端到端仿真:

:::{literalinclude} ../../examples/run_simulation.py
:language: python
:start-after: "# [node-hopping-start]"
:end-before: "# [node-hopping-end]"
:dedent:
:::

接入流程:

:::{literalinclude} ../../examples/run_simulation.py
:language: python
:start-after: "# [node-access-start]"
:end-before: "# [node-access-end]"
:dedent:
:::

信道扫频:

:::{literalinclude} ../../examples/run_simulation.py
:language: python
:start-after: "# [node-sweep-start]"
:end-before: "# [node-sweep-end]"
:dedent:
:::

功率自适应:

:::{literalinclude} ../../examples/run_simulation.py
:language: python
:start-after: "# [node-power-start]"
:end-before: "# [node-power-end]"
:dedent:
:::

批量执行并生成可视化图:

```bash
uv run python -m nearlink_sdr.sim.link_sim phase15
```

## Doppler 时变衰落与多用户干扰 (Phase 16)

### Doppler 扩展对 FER 的影响

使用 Jakes 求和正弦模型模拟不同移动速度下的信道衰落:

:::{literalinclude} ../../examples/run_simulation.py
:language: python
:start-after: "# [doppler-start]"
:end-before: "# [doppler-end]"
:dedent:
:::

### SIR 扫描

在固定 SNR 下, 改变信干比观察多用户干扰对 FER 的影响:

:::{literalinclude} ../../examples/run_simulation.py
:language: python
:start-after: "# [interference-start]"
:end-before: "# [interference-end]"
:dedent:
:::

### Doppler + 多径联合

ITU Indoor Office 功率延迟谱与 Doppler 衰落的联合仿真:

:::{literalinclude} ../../examples/run_simulation.py
:language: python
:start-after: "# [doppler-multipath-start]"
:end-before: "# [doppler-multipath-end]"
:dedent:
:::

批量执行 Phase 16 全部仿真并生成四面板可视化图:

```bash
uv run python -m nearlink_sdr.sim.link_sim phase16
```

## 信道损伤仿真

使用 `sim_pipeline_channel_link` 模拟衰落信道、载波频偏和均衡对链路的影响:

:::{literalinclude} ../../examples/run_simulation.py
:language: python
:start-after: "# [channel-impairment-start]"
:end-before: "# [channel-impairment-end]"
:dedent:
:::

批量信道损伤仿真 (含均衡对比):

```bash
uv run python -m nearlink_sdr.sim.link_sim phase7
# 结果保存到 ber_phase7.png
```

## MAC 帧级仿真

Phase 9 通过 MAC-PHY 适配层将 MAC 帧编码为 IQ 信号, 经信道传输后在接收端还原 MAC 载荷:

:::{literalinclude} ../../examples/run_simulation.py
:language: python
:start-after: "# [mac-sim-start]"
:end-before: "# [mac-sim-end]"
:dedent:
:::

```bash
uv run python -m nearlink_sdr.sim.link_sim phase9
```

## 多链路调度仿真

Phase 10 仿真调度器驱动的多链路并发传输:

:::{literalinclude} ../../examples/run_simulation.py
:language: python
:start-after: "# [multi-link-start]"
:end-before: "# [multi-link-end]"
:dedent:
:::

```bash
uv run python -m nearlink_sdr.sim.link_sim phase10
```

## 安全通信仿真

Phase 11 模拟完整的安全链路建立: 接入 -> 配对 -> 加密数据传输:

:::{literalinclude} ../../examples/run_simulation.py
:language: python
:start-after: "# [security-sim-start]"
:end-before: "# [security-sim-end]"
:dedent:
:::

```bash
uv run python -m nearlink_sdr.sim.link_sim phase11
```

## AMC 自适应调制编码仿真

Phase 12 扫描全部 MCS 等级 (0-12), 生成 AMC 包络吞吐量曲线:

:::{literalinclude} ../../examples/run_simulation.py
:language: python
:start-after: "# [amc-start]"
:end-before: "# [amc-end]"
:dedent:
:::

仅仿真特定 MCS 子集:

:::{literalinclude} ../../examples/run_simulation.py
:language: python
:start-after: "# [amc-subset-start]"
:end-before: "# [amc-subset-end]"
:dedent:
:::

## HARQ 重传仿真

对比有/无 HARQ 重传的 FER 和吞吐量:

:::{literalinclude} ../../examples/run_simulation.py
:language: python
:start-after: "# [harq-start]"
:end-before: "# [harq-end]"
:dedent:
:::

## 跳频多径仿真

对比固定信道与跳频在 Rayleigh 衰落下的 FER:

:::{literalinclude} ../../examples/run_simulation.py
:language: python
:start-after: "# [hopping-multipath-start]"
:end-before: "# [hopping-multipath-end]"
:dedent:
:::

生成 Phase 12 全部仿真图:

```bash
uv run python -m nearlink_sdr.sim.link_sim phase12
# 结果保存到 ber_phase12.png
```

## Phase 14: 双节点端到端仿真

使用 SleNode 实体进行完整的双节点数据交换仿真:

:::{literalinclude} ../../examples/run_simulation.py
:language: python
:start-after: "# [dual-node-start]"
:end-before: "# [dual-node-end]"
:dedent:
:::

生成 Phase 14 全部仿真图:

```bash
uv run python -m nearlink_sdr.sim.link_sim phase14
# 结果保存到 ber_phase14.png
```

## 运行示例

```bash
uv run python examples/run_simulation.py
```
