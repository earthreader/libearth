libearth
========

Libearth is the shared common library for various `Earth Reader`_ apps.
Earth Reader try to support many platforms as possible (e.g. web_,
mobile apps, desktop apps), so there must be a large part of common concepts
and implementations they share like subscription lists, synchronization
through cloud storages between several devices, and crawler, that libearth
actually implements.

.. _Earth Reader: http://earthreader.org/
.. _web: https://github.com/earthreader/web


Compatibility & portability
---------------------------

Libearth officially supports the following Python implementations:

- Python 2.6, 2.7, 3.2, 3.3, 3.4
- CPython, PyPy, IronPython

For environments :mod:`setuptools` not available, it has no required
dependencies.

See also :file:`tox.ini` file and CI_ builds.

.. _CI: https://travis-ci.org/earthreader/libearth.png?branch=master


Installation
------------

You can install it using :program:`pip`:

.. code-block:: console

   $ pip install libearth

See PyPI_ as well.

.. _PyPI: https://pypi.python.org/pypi/libearth


References
----------

.. toctree::
   :maxdepth: 3

   libearth


Additional notes
----------------

.. toctree::
   :maxdepth: 2

   design/goal
   design/concepts
   changes


Open source
-----------

Libearth is an open source software written by `Hong Minhee`_ and
the `Earth Reader team`_.  See also the complete list of contributors_
as well.  Libearth is free software licensed under the terms of the
`GNU General Public License Version 2`__ or any later version, and you can
find the code at `GitHub repository`_:

.. code-block:: console

   $ git clone git://github.com/earthreader/libearth.git

If you find any bugs, please report them to our `issue tracker`_.
Pull requests are always welcome!

We discuss about libearth's development on IRC.  Come ``#earthreader`` channel
on Ozinger_ network.  (We will make one on freenode as well soon!)

.. image:: https://travis-ci.org/earthreader/libearth.png?branch=master
   :alt: Build Status
   :target: https://travis-ci.org/earthreader/libearth

.. image:: https://coveralls.io/repos/earthreader/libearth/badge.png?branch=master
   :alt: Coverage Status
   :target: https://coveralls.io/r/earthreader/libearth?branch=master

.. _Hong Minhee: http://dahlia.kr/
.. _Earth Reader team: https://github.com/earthreader
.. _contributors: https://github.com/earthreader/libearth/graphs/contributors
__ http://www.gnu.org/licenses/gpl-2.0.html
.. _GitHub repository: https://github.com/earthreader/libearth
.. _issue tracker: https://github.com/earthreader/libearth/issues
.. _Ozinger: http://ozinger.org/
