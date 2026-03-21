#!/usr/bin/env python3
"""尝试编译并安装 Rust 加速模块 nearlink_sdr_accel。

非必需依赖: Rust 扩展不可用时, 项目回退到纯 Python 实现。
需要: cargo (Rust 工具链) 和 maturin。
"""

import shutil
import subprocess
import sys
from pathlib import Path

RUST_DIR = Path(__file__).resolve().parent.parent / "rust"


def main() -> int:
    if not RUST_DIR.is_dir():
        print("rust/ 目录不存在, 跳过加速模块安装")
        return 0

    if shutil.which("cargo") is None:
        print("未检测到 cargo (Rust 工具链), 跳过加速模块安装")
        print("安装 Rust: https://rustup.rs/")
        return 0

    maturin_cmd = ["maturin"]
    if shutil.which("maturin") is None:
        print("安装 maturin ...")
        if shutil.which("uv") is not None:
            subprocess.check_call(["uv", "pip", "install", "maturin"])
            maturin_cmd = ["uv", "run", "maturin"]
        else:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "maturin"])

    print("编译 Rust 加速模块 ...")
    manifest = str(RUST_DIR / "Cargo.toml")
    result = subprocess.run(
        [*maturin_cmd, "develop", "--manifest-path", manifest, "--release"],
        capture_output=True,
        text=True,
    )

    if result.returncode == 0:
        print("Rust 加速模块安装成功")
    else:
        print("Rust 加速模块编译失败 (非致命错误, 回退到纯 Python)")
        print(result.stderr[-500:] if len(result.stderr) > 500 else result.stderr)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
