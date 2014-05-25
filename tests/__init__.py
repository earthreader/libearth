import platform
import sys


# Workaround segmentation fault by cElementTree.fromstring() on CPython
if platform.python_implementation() == 'CPython' and \
   platform.system() == 'Linux':
    from xml.etree import ElementTree
    sys.modules['xml.etree.cElementTree'] = ElementTree
