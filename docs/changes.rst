Libearth Changelog
==================

Version 0.1.1
-------------

To be released.

- Added a workaround for thread unsafety :func:`time.strftime()` on CPython.
  See http://bugs.python.org/issue7980 as well.  [:issue:`32`]
- Fixed :exc:`UnicodeDecodeError` which is raised when a feed title contains
  any non-ASCII characters.  [:issue:`34` by Jae-Myoung Yu]
- Now :mod:`libearth.parser.rss2` fills :attr:`Entry.updated_at
  <libearth.feed.Entry.updated_at>` if it's not given.  [:issue:`35`]
- Fixed :exc:`TypeError` which is raised when any
  :class:`~libearth.schema.DocumentElement` with ``multiple``
  :class:`~libearth.schema.Child` elements is passed to
  :func:`~libearth.schema.validate()` function.
- Fixed the race condition of two :class:`FileSystemRepository
  <libearth.repository.FileSystemRepository>` objects creating
  the same directory.  [:issue:`36` by klutzy]


Version 0.1.0
-------------

Released on December 13, 2013.  Initial alpha version.
