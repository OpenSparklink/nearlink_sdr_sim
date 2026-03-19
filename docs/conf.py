"""Sphinx configuration for nearlink-sdr documentation."""

project = "nearlink-sdr"
author = "nearlink-sdr contributors"
release = "0.1.0"

extensions = [
    "myst_parser",
    "autodoc2",
    "sphinx.ext.intersphinx",
    "sphinx.ext.viewcode",
    "sphinx.ext.mathjax",
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

html_theme = "sphinx_rtd_theme"
html_static_path = ["_static"]

# -- LaTeX / PDF 输出配置 ------------------------------------------------------

latex_engine = "xelatex"

latex_elements = {
    "papersize": "a4paper",
    "pointsize": "11pt",
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
