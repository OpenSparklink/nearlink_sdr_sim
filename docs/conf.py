"""Sphinx configuration for nearlink-sdr documentation."""

project = "nearlink-sdr"
author = "nearlink-sdr contributors"
release = "0.1.0"

extensions = [
    "myst_parser",
    "autodoc2",
    "sphinx.ext.intersphinx",
    "sphinx.ext.viewcode",
]

# -- MyST 配置 ----------------------------------------------------------------

myst_enable_extensions = [
    "colon_fence",
    "fieldlist",
    "deflist",
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

# -- intersphinx 配置 ----------------------------------------------------------

intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
    "numpy": ("https://numpy.org/doc/stable/", None),
}

source_suffix = {
    ".rst": "restructuredtext",
    ".md": "markdown",
}
