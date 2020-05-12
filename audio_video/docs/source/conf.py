import os
import sys

sys.path.insert(0, os.path.abspath('.'))
sys.path.insert(0, os.path.abspath('../../'))

# -- Project information -----------------------------------------------------

project = u'slurk audio pilot'
copyright = u'2019, Tim Diekmann'
author = u'Tim Diekmann'


# -- General configuration ---------------------------------------------------

extensions = ['sphinx.ext.autodoc']
source_suffix = '.rst'
master_doc = 'index'
pygments_style = 'sphinx'


# -- Options for HTML output -------------------------------------------------

html_theme = 'sphinx_rtd_theme'
html_static_path = ['_static']
autoclass_content = "both"
