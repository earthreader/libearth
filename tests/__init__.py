import platform
import sys


# Workaround segmentation fault by cElementTree.fromstring() on Python 2.6/2.7
if platform.python_implementation() == 'CPython' and \
   sys.version_info < (3, 0) and \
   platform.system() == 'Linux':
    from xml.etree import ElementTree
    sys.modules['xml.etree.cElementTree'] = ElementTree
