"""Test whether all Python modules and packages have docs for themselves."""
from __future__ import print_function

import os
import os.path
import sys


PACKAGES = ['libearth']
ROOT_DIR = os.path.join(os.path.dirname(__file__), '..')
DOCS_DIR = os.path.join(os.path.dirname(__file__))
failed = False


def traverse(package):
    global failed
    path = os.path.join(*package.split('.'))
    if not os.path.isfile(os.path.join(ROOT_DIR, path, '__init__.py')):
        return
    package_rst_path = os.path.join(DOCS_DIR, path + '.rst')
    if not os.path.isfile(package_rst_path):
        print('You seem to miss docs for', package, 'package:',
              package_rst_path, file=sys.stderr)
        failed = True
    for name in os.listdir(os.path.join(ROOT_DIR, path)):
        fullpath = os.path.join(ROOT_DIR, path, name)
        if os.path.isdir(fullpath):
            traverse('{0}.{1}'.format(package, name))
        elif (name not in ('__init__.py', '__main__.py') and
              name.endswith('.py')):
            module_rst_path = os.path.join(DOCS_DIR, path, name[:-3] + '.rst')
            if not os.path.isfile(module_rst_path):
                module = '{0}.{1}'.format(package, name[:-3])
                print('You seem to miss docs for', module, 'module:',
                      module_rst_path, file=sys.stderr)
                failed = True


for package in PACKAGES:
    traverse(package)

if failed:
    sys.exit(1)
