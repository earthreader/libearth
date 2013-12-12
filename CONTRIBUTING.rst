How to contribute
=================

License agreement
-----------------

All contributed codes have to be free software licensed under the terms of
the `GNU General Public License Version 2`__ or any later version.
We treat all pull requests imply agreement of it, but if a significant
amount of code is involved, it is safest to mention in the pull request
comments that you agree to let the patch be used under the GNU General
Public License Version 2 or any later version as part of the libearth code.

__ http://www.gnu.org/licenses/gpl-2.0.html


Coding style
------------

- Follow `PEP 8`_ except you can limit all lines to
  a maximum of 80 characters (not 79).
- Order ``import``\ s in lexicographical order.
- Prefer relative ``import``\ s.
- All functions, classes, methods, attributes, and modules
  should have the docstring.


.. _PEP 8: http://www.python.org/dev/peps/pep-0008/


Tests
-----

- All code patches should contain one or more unit tests of
  the feature to add or regression tests of the bug to fix.
- Run the whole test suite on every Python VM using ``tox``.
- All commits will be tested by `Travis CI`__.

__ https://travis-ci.org/earthreader/libearth
