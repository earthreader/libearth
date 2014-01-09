Libearth Changelog
==================

Version 0.1.2
-------------

To be released.

- XML elements in data files are written in canonical order.  For example,
  ``<title>`` element of the feed was at the back before, but now is in front.
- Fixed a bug that :mod:`~libearth.parser.autodiscovery` raises
  :exc:`AttributeError` when the given HTML contains ``<link>`` to
  both :mimetype:`application/atom+xml` and :mimetype:`application/rss+xml`.
  [:issue:`40`]


Version 0.1.1
-------------

Released on January 2, 2014.

- Added a workaround for thread unsafety :func:`time.strftime()` on CPython.
  See http://bugs.python.org/issue7980 as well.  [:issue:`32`]
- Fixed :exc:`UnicodeDecodeError` which is raised when a feed title contains
  any non-ASCII characters.  [:issue:`34` by Jae-Myoung Yu]
- Now :mod:`libearth.parser.rss2` fills :attr:`Entry.updated_at
  <libearth.feed.Metadata.updated_at>` if it's not given.  [:issue:`35`]
- Fixed :exc:`TypeError` which is raised when any
  :class:`~libearth.schema.DocumentElement` with ``multiple``
  :class:`~libearth.schema.Child` elements is passed to
  :func:`~libearth.schema.validate()` function.
- Fixed the race condition of two :class:`FileSystemRepository
  <libearth.repository.FileSystemRepository>` objects creating
  the same directory.  [:issue:`36` by klutzy]
- :func:`~libearth.compat.parallel.parallel_map()` becomes to raise exceptions
  at the last, if any errored.  [:issue:`38`]


Version 0.1.0
-------------

Released on December 13, 2013.  Initial alpha version.
