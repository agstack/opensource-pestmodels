"""Sphinx configuration for agstack-pnd documentation."""

project = "agstack-pnd"
copyright = "2026, AgStack Foundation (Linux Foundation)"
author = "AgStack Foundation"
release = "2.0.0a1"

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx_autodoc_typehints",
    "myst_parser",
]

templates_path = ["_templates"]
exclude_patterns = ["_build"]

html_theme = "sphinx_rtd_theme"
html_static_path = ["_static"]

autodoc_member_order = "bysource"
autodoc_typehints = "description"
