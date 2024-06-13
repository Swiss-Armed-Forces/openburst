# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html


import os
import sys
sys.path.insert(0, os.path.abspath('../../openburst/'))
sys.path.insert(0, os.path.abspath('../../openburst/types/'))
sys.path.insert(0, os.path.abspath('../../openburst/functions/'))
sys.path.insert(0, os.path.abspath('../../openburst/pcl/'))
sys.path.insert(0, os.path.abspath('../../openburst/radterrain/'))
sys.path.insert(0, os.path.abspath('../../openburst/geoplot/'))
sys.path.insert(0, os.path.abspath('../../openburst/pet/'))
sys.path.insert(0, os.path.abspath('../../openburst/replay/'))
sys.path.insert(0, os.path.abspath('../../openburst/detection/'))
sys.path.insert(0, os.path.abspath('../../openburst/webserver/'))
sys.path.insert(0, os.path.abspath('../../openburst/sensorcontrol/'))
sys.path.insert(0, os.path.abspath('../../openburst/analytics/'))

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = 'openBURST'
copyright = '2024, Swiss Armed Forces Staff'
author = 'Swiss Armed Forces Staff'
release = '1.0'

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
        'sphinx.ext.autodoc',
        'myst_parser', # for adding .md files
        'sphinx.ext.napoleon' # For auto-doc configuration
    ]

templates_path = ['_templates']
exclude_patterns = []

autodoc_mock_imports = ["libsplathd", 'octave', 'stonesoup'] # mock some imports 

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = 'sphinx_rtd_theme'
html_static_path = ['_static']


suppress_warnings = ["myst.header"]