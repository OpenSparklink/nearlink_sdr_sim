.PHONY: help install lint test coverage docs-html docs-pdf \
       install-fonts install-mermaid accel examples clean

# [help-start]
help:  ## 显示帮助信息
	@grep -E '^[a-zA-Z_-]+:.*##' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*## "}; {printf "  \033[36m%-16s\033[0m %s\n", $$1, $$2}'
# [help-end]

# -- 安装 --------------------------------------------------------------------

install:  ## 安装项目依赖
# [install-start]
	uv sync
# [install-end]

accel:  ## 编译并安装 Rust 加速模块
# [accel-start]
	uv pip install maturin
	uv run maturin develop --manifest-path rust/Cargo.toml --release
# [accel-end]

install-fonts:  ## 安装 HarmonyOS 字体到系统
# [install-fonts-start]
	sudo mkdir -p /usr/local/share/fonts/harmonyos
	sudo cp fonts/*.ttf /usr/local/share/fonts/harmonyos/
	sudo fc-cache -f
# [install-fonts-end]

install-mermaid:  ## 安装 Mermaid CLI (构建 PDF 文档所需)
# [install-mermaid-start]
	npm install -g @mermaid-js/mermaid-cli
# [install-mermaid-end]

# -- 质量检查 -----------------------------------------------------------------

lint:  ## 运行 ruff 代码检查
# [lint-start]
	uv run ruff check src/ tests/ examples/
# [lint-end]

mdlint:  ## 运行 markdownlint 检查
# [mdlint-start]
	markdownlint-cli2 "docs/**/*.md" "*.md"
# [mdlint-end]

test:  ## 运行全量测试
# [test-start]
	uv run pytest tests/ -v --tb=short
# [test-end]

coverage:  ## 运行测试并收集覆盖率
# [coverage-start]
	uv run pytest tests/ --cov=nearlink_sdr --cov-report=xml --cov-report=term-missing
# [coverage-end]

# -- 文档 --------------------------------------------------------------------

docs-html:  ## 构建 HTML 文档
# [docs-html-start]
	uv run sphinx-build -b html docs docs/_build/html
# [docs-html-end]

docs-strict:  ## 严格模式构建文档 (CI 用)
# [docs-strict-start]
	uv run sphinx-build -E -W docs docs/_build/html
# [docs-strict-end]

docs-pdf:  ## 构建 PDF 文档 (需提前运行 make install-mermaid)
# [docs-pdf-start]
	uv run sphinx-build -b latex docs docs/_build/latex
	cd docs/_build/latex && make
# [docs-pdf-end]

docs-live:  ## 实时预览文档 (自动刷新)
# [docs-live-start]
	uv run pip install sphinx-autobuild
	uv run sphinx-autobuild docs docs/_build/html
# [docs-live-end]

# -- 仿真 --------------------------------------------------------------------

sim-%:  ## 运行仿真阶段, 如 make sim-phase1
# [sim-start]
	uv run python -m nearlink_sdr.sim.link_sim $*
# [sim-end]

# -- 示例 --------------------------------------------------------------------

examples:  ## 运行所有示例脚本
# [examples-start]
	uv run python examples/getting_started.py
	uv run python examples/qos_management.py
	uv run python examples/node_usage.py
	uv run python examples/custom_modulation.py
# [examples-end]

# -- Rust 质量 ---------------------------------------------------------------

rust-check:  ## Rust 格式检查 + Clippy + 测试
# [rust-check-start]
	cd rust && cargo fmt --check
	cd rust && cargo clippy --all-targets -- -D warnings
	cd rust && cargo test
# [rust-check-end]

# -- 清理 --------------------------------------------------------------------

clean:  ## 清理构建产物
# [clean-start]
	rm -rf docs/_build/ dist/ output/ .coverage coverage.xml report.xml
# [clean-end]
