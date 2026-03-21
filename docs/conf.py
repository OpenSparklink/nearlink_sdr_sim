"""Sphinx configuration for nearlink-sdr documentation."""

import os

project = "nearlink-sdr"
author = "nearlink-sdr contributors"
release = "0.1.0"

extensions = [
    "myst_parser",
    "autodoc2",
    "sphinx.ext.intersphinx",
    "sphinx.ext.viewcode",
    "sphinx.ext.mathjax",
    "sphinxcontrib.mermaid",
]

# -- MyST 配置 ----------------------------------------------------------------

myst_enable_extensions = [
    "colon_fence",
    "fieldlist",
    "deflist",
    "dollarmath",
    "amsmath",
]

# -- autodoc2 配置 -------------------------------------------------------------

autodoc2_packages = [
    {
        "path": "../src/nearlink_sdr",
        "auto_mode": True,
    },
]
autodoc2_render_plugin = "myst"

# -- 通用配置 ------------------------------------------------------------------

templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]
language = "zh_CN"

# -- HTML 输出配置 -------------------------------------------------------------

html_theme = "furo"
html_static_path = ["_static"]
html_js_files = ["version-selector.js"]
html_css_files = ["version-selector.css"]

html_theme_options = {
    "light_css_variables": {
        "color-brand-primary": "#1a73e8",
        "color-brand-content": "#1a73e8",
    },
    "dark_css_variables": {
        "color-brand-primary": "#8ab4f8",
        "color-brand-content": "#8ab4f8",
    },
    "sidebar_hide_name": False,
    "navigation_with_keys": True,
    "footer_icons": [
        {
            "name": "GitHub",
            "url": "https://github.com/sanchuanhehe/nearlink_sdr_sim",
            "html": (
                '<svg stroke="currentColor" fill="currentColor" stroke-width="0"'
                ' viewBox="0 0 16 16"><path fill-rule="evenodd" d="M8 0C3.58 0 0'
                " 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38"
                " 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48"
                "-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82"
                " .72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64"
                "-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12"
                " 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27"
                " 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82"
                " 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48"
                ' 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.013 8.013 0 0016'
                ' 8c0-4.42-3.58-8-8-8z"></path></svg>'
            ),
            "class": "",
        },
    ],
}

# -- LaTeX / PDF 输出配置 ------------------------------------------------------

latex_engine = "xelatex"

latex_elements = {
    "papersize": "a4paper",
    "pointsize": "11pt",
    "fontpkg": "",
    "preamble": r"""
\usepackage{fontspec}
\usepackage{xeCJK}
\setCJKmainfont{HarmonyOS Sans SC}
\setCJKsansfont{HarmonyOS Sans SC}
\setCJKmonofont{HarmonyOS Sans SC}
\setmainfont{HarmonyOS Sans}
\setsansfont{HarmonyOS Sans}
\usepackage{amsmath,amssymb}
""",
    "figure_align": "htbp",
}

latex_use_xindy = False

latex_documents = [
    (
        "index",
        "nearlink-sdr.tex",
        "nearlink-sdr 技术文档",
        author,
        "manual",
    ),
]

# -- intersphinx 配置 ----------------------------------------------------------

intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
    "numpy": ("https://numpy.org/doc/stable/", None),
}

source_suffix = {
    ".rst": "restructuredtext",
    ".md": "markdown",
}

# -- Mermaid 配置 -------------------------------------------------------------
# HTML 输出使用浏览器端 JS 渲染；LaTeX/PDF 输出需要 mmdc CLI 预渲染为 PNG。
# 本地构建 PDF 前请先执行：npm install -g @mermaid-js/mermaid-cli

_PUPPETEER_CFG = os.path.join(os.path.dirname(__file__), "mermaid-puppeteer-config.json")


def _builder_inited(app):
    """LaTeX/PDF 构建时切换为 mmdc PNG 预渲染，并传递 puppeteer 无沙箱配置。"""
    if app.builder.name in ("latex", "latexpdf"):
        app.config.mermaid_output_format = "png"
        if os.path.exists(_PUPPETEER_CFG):
            app.config.mermaid_params = ["--puppeteerConfigFile", _PUPPETEER_CFG]


def setup(app):
    app.connect("builder-inited", _builder_inited)
