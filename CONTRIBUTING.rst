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
- Run the whole test suite on every Python VM using ``tox``
  (except for IronPython).
- For IronPython use ``ipy-test.sh`` script.
- All commits will be tested by `Travis CI`__.

__ https://travis-ci.org/earthreader/libearth


Parser test suite
`````````````````

To make feed parser robust we have the parser test suite.  The suite is in
``tests/parsing/``, and consists of various real world feed XML files,
and the expected parsing results of them.  Each test case consists of
two or three files:

``$TEST_NAME.xml`` (parser input)
   An actual feed XML which get from the original url.  Its format could be
   one of formats supported by parser.

``$TEST_NAME.out.xml``
   A serialized XML of the parsed result ``Feed`` object.  Its format is
   Atom extended for libearth.

``$TEST_NAME.uri.txt`` (optional original url)
   The original url of the parser input.

The whole parser test suite is run together when the unit tests runs.
In order to run *only* parser test suite without any other unit tests
filter tests by ``parser_test``:

.. code-block:: console

   $ py.test -k parser_test
   $ # or
   $ tox -- -k parser_test


Adding a new parser test
````````````````````````

If you find a real world feed that libearth parser doesn't work,
and you want to fix it, what you should do first is to add a new test case
to the parser test suite.

Suppose the feed is ``http://example.com/feed.xml``.  You can download it
using ``curl`` or ``wget``.  Name it an unique test suite name.
We recommend to use the website name.  Use ``example`` here.

.. code-block:: console

   $ curl -o tests/parsing/example.xml http://example.com/feed.xml

You also need to provide its original url.

.. code-block:: console

   $ echo http://example.com/feed.xml > tests/parsing/example.uri.txt

Lastly you also need to provide the expected parsing result.  Building the
expected XML tree is less likley to get by hand.  You can create an initial
skeleton using ``tests/parsing_test.py`` script.

.. code-block:: console

   $ python tests/parsing_test.py
   There are 1 XML files that have no paired .out.xml files:
   	example.xml
   Do you want to create scaffold .out.xml files? y
