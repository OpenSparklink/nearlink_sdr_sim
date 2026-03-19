# 构建文档

## 安装依赖

文档构建工具已包含在开发依赖中:

```bash
uv sync
```

## 构建 HTML

```bash
uv run sphinx-build -b html docs docs/_build/html
```

构建产物在 `docs/_build/html/` 目录下, 用浏览器打开 `index.html` 即可阅读。

## 实时预览

开发文档时, 使用 `sphinx-autobuild` 自动重建并刷新浏览器:

```bash
uv run pip install sphinx-autobuild
uv run sphinx-autobuild docs docs/_build/html
```

浏览器访问 `http://127.0.0.1:8000`。

## 文档结构

```
docs/
├── conf.py               # Sphinx 配置
├── index.md              # 首页
├── tutorials/            # 教程 (学习导向)
├── how-to/               # 操作指南 (任务导向)
├── reference/            # 技术参考 (信息导向)
└── explanation/          # 设计说明 (理解导向)
```

文档使用 MyST Markdown 语法, 详见 [MyST 文档](https://myst-parser.readthedocs.io/)。
