# nearlink-sdr

符合 TXS-10002-2025 SparkLink SLE 标准的软件无线电链路仿真系统。

本文档按 [Diataxis](https://diataxis.fr/) 框架组织为四个部分:

**[教程](tutorials/getting-started.md)**
: 从零开始运行第一次链路仿真, 逐步理解系统的基本用法。适合初次使用本项目的开发者。

**[操作指南](how-to/index.md)**
: 面向具体任务的操作说明。假定你已经了解项目的基本概念, 需要完成特定的工作。

**[技术参考](reference/index.md)**
: 模块和函数的完整接口文档, 从源代码注释自动生成。

**[设计说明](explanation/overview.md)**
: 协议总览、物理层、MAC 层、安全子系统、端到端数据流的逐层深入解析, 以及与标准条款的映射关系。

**[物理层原理](explanation/principles.md)**
: Polar 编码、PSK/GFSK 调制、信道模型、均衡器等核心算法的数学推导。

```{toctree}
:maxdepth: 2
:hidden:

tutorials/getting-started
how-to/index
reference/index
explanation/overview
explanation/physical-layer
explanation/mac-layer
explanation/security
explanation/data-flow
explanation/architecture
explanation/standard-mapping
explanation/principles
changelog
apidocs/index
```
