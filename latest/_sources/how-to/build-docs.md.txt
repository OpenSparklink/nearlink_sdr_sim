# 构建文档

## 安装依赖

文档构建工具已包含在开发依赖中:

:::{literalinclude} ../../Makefile
:language: makefile
:start-after: "# [install-start]"
:end-before: "# [install-end]"
:::

## 构建 HTML

:::{literalinclude} ../../Makefile
:language: makefile
:start-after: "# [docs-html-start]"
:end-before: "# [docs-html-end]"
:::

构建产物在 `docs/_build/html/` 目录下, 用浏览器打开 `index.html` 即可阅读。

## 构建 PDF

使用 XeLaTeX 编译, 字体为 HarmonyOS Sans SC。

### 安装 TeX 环境

Ubuntu/Debian:

```bash
sudo apt install texlive-xetex texlive-fonts-recommended texlive-latex-extra \
  texlive-lang-chinese latexmk
```

### 安装字体

项目仓库已包含 HarmonyOS Sans SC 字体文件 (位于 `fonts/` 目录):

:::{literalinclude} ../../Makefile
:language: makefile
:start-after: "# [install-fonts-start]"
:end-before: "# [install-fonts-end]"
:::

验证字体可用:

```bash
fc-list | grep HarmonyOS
```

### 编译 PDF

:::{literalinclude} ../../Makefile
:language: makefile
:start-after: "# [docs-pdf-start]"
:end-before: "# [docs-pdf-end]"
:::

生成的 PDF 位于 `docs/_build/latex/nearlink-sdr.pdf`。

## 实时预览

开发文档时, 使用 `sphinx-autobuild` 自动重建并刷新浏览器:

:::{literalinclude} ../../Makefile
:language: makefile
:start-after: "# [docs-live-start]"
:end-before: "# [docs-live-end]"
:::

浏览器访问 `http://127.0.0.1:8000`。

## 文档结构

```text
docs/
├── conf.py               # Sphinx 配置
├── index.md              # 首页
├── tutorials/            # 教程 (学习导向)
├── how-to/               # 操作指南 (任务导向)
├── reference/            # 技术参考 (信息导向)
└── explanation/          # 设计说明 (理解导向)
```

文档使用 MyST Markdown 语法, 详见 [MyST 文档](https://myst-parser.readthedocs.io/)。
