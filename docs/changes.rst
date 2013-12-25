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

To be released.

- Added a workaround for thread unsafety :func:`time.strftime()` on CPython.
  See http://bugs.python.org/issue7980 as well.  [:issue:`32`]


Version 0.1.0
-------------

Released on December 13, 2013.  Initial alpha version.
