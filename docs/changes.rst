Libearth Changelog
==================

Version 0.2.0
-------------

To be released.

- Added :meth:`SubscriptionSet.contains()
  <libearth.subscribe.SubscriptionSet.contains>` method which provides
  ``recursively=True`` option.  It's useful for determining that
  a subcategory or subscription is in the whole tree.
- :attr:`Attribute.default <libearth.schema.Attribute.default>` option
  becomes to accept only callable objects.  Below 0.2.0,
  :attr:`~libearth.schema.Attribute.default` is not a function but a value
  which is simply used as it is.


Version 0.1.1
-------------

Released on January 2, 2014.

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
- :func:`~libearth.compat.parallel.parallel_map()` becomes to raise exceptions
  at the last, if any errored.  [:issue:`38`]


Version 0.1.0
-------------

Released on December 13, 2013.  Initial alpha version.
