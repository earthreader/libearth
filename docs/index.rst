libearth
========

Libearth is the share dcommon library for various `Earth Reader`_ apps.
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

- Python 2.6, 2.7, 3.2, 3.3
- CPython, PyPy, IronPython

For environments :mod:`setuptools` not available, it has no required
dependencies.

See also :file:`tox.ini` file and CI_ builds.

.. _CI: https://travis-ci.org/earthreader/libearth.png?branch=master


Design docs
-----------

.. toctree::
   :maxdepth: 2

   design/goal
   design/concepts


References
----------

.. toctree::
   :maxdepth: 3

   libearth


Open source
-----------

Libearth is an open source software written by `Hong Minhee`_ and
the `Earth Reader team`_.  See also the complete list of contributors_
as well.  The source code is distributed under `MIT license`_, and you can
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
.. _MIT License: http://minhee.mit-license.org/
.. _GitHub repository: https://github.com/earthreader/libearth
.. _issue tracker: https://github.com/earthreader/libearth/issues
.. _Ozinger: http://ozinger.org/
