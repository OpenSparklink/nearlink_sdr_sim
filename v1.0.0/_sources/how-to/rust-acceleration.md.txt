# Rust 加速模块

nearlink-sdr 提供可选的 Rust 加速扩展，用于加速 Polar 编解码等计算密集型操作。安装后无需修改任何代码，Python 模块会自动检测并使用 Rust 实现。

## 前提条件

- Rust 工具链 (cargo, rustc)：通过 [rustup](https://rustup.rs/) 安装
- Python 开发头文件（多数系统已默认包含）

## 安装方式

### 自动安装

项目提供了一键安装脚本：

```bash
python scripts/install_accel.py
```

脚本会依次检查 Rust 工具链、安装 maturin 构建工具、编译并安装加速模块。安装失败不会影响项目正常使用，所有功能会回退到纯 Python 实现。

### 手动安装

:::{literalinclude} ../../Makefile
:language: makefile
:start-after: "# [accel-start]"
:end-before: "# [accel-end]"
:::

## 验证安装

```python
from nearlink_sdr_accel import RustPolarDecoder, RustPolarEncoder
print("Rust 加速模块已加载")
```

或者检查模块级标志：

```python
from nearlink_sdr.common.polar import _HAS_RUST_ACCEL
print(f"Rust 加速: {'已启用' if _HAS_RUST_ACCEL else '未启用'}")
```

## 性能对比

以 TX→RX 全链路 Pipeline 为基准（单次调用，含 Polar 编解码、调制解调、信道、均衡）：

| 配置 | 耗时 | 加速比 |
|------|------|--------|
| 纯 Python | 389 ms | 1.0x |
| + Rust SC 解码器 | 174 ms | 2.2x |
| + Rust 编码器 | 101 ms | 3.9x |

测试套件总耗时从 12.4 秒降至 4.1 秒。

## 加速范围

当前 Rust 加速覆盖以下模块：

| 模块 | 加速内容 | 实现方式 |
|------|----------|----------|
| `common/polar.py` | SC 解码（SSC 优化）| 递归节点类型表 + 标量运算 |
| `common/polar.py` | Polar 编码（蝶形 GF(2) 变换）| 原地位运算矩阵乘法 |

Rust 源码位于 `rust/src/lib.rs`，通过 PyO3 暴露为 Python 类，由 maturin 构建为本地扩展模块 `nearlink_sdr_accel`。

## 故障排除

**cargo 未找到**：运行 `curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh` 安装 Rust 工具链。

**编译失败**：确保 Rust 版本 >= 1.70，运行 `rustup update` 更新。

**maturin 找不到虚拟环境**：确认当前处于项目根目录的虚拟环境中（`source .venv/bin/activate` 或 `uv sync` 后执行）。
