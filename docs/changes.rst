Libearth Changelog
==================

Version 0.3.0
-------------

To be released.

- Root :class:`~libearth.session.MergeableDocumentElement`\ s'
  :meth:`~libearth.session.MergeableDocumentElement.__merge_entities__()`
  methods are not ignored anymore.  Respnosibilty to merge two documents is
  now moved from :meth:`Session.merge() <libearth.session.Session.merge>`
  method to :meth:`MergeableDocumentElement.__merge_entities__()
  <libearth.session.MergeableDocumentElement.__merge_entities__>` method.
- :func:`~libearth.crawler.crawl()` now return a set of
  :class:`~libearth.crawler.CrawlResult` objects instead of :class:`tuple`\ s.
- ``feeds`` parameter of :func:`~libearth.crawler.crawl()` function was
  renamed to ``feed_urls``.
- Added :attr:`LinkList.favicon <libearth.feed.LinkList.favicon>` property.
  [:issue:`49`]
- :meth:`AutoDiscovery.find_feed_url()
  <libearth.parser.autodiscovery.AutoDiscovery.find_feed_url>` method (that
  returned feed links) was gone.  Instead :meth:`AutoDiscovery.find()
  <libearth.parser.autodiscovery.AutoDiscovery.find>` method (that returns
  a pair of feed links and favicon links) was introduced.
  [:issue:`49`]
- :attr:`Subscription.icon_uri <libearth.subscribe.Subscription.icon_uri>`
  attribute was introduced.  [:issue:`49`]
- Added an optional ``icon_uri`` parameter to :meth:`SubscriptionSet.subscribe()
  <libearth.subscribe.SubscriptionSet.subscribe>` method.  [:issue:`49`]
- Added :func:`~libearth.parser.util.normalize_xml_encoding()`
  function to workaround :mod:`xml.etree.ElementTree` module's
  `encoding detection bug`__.  [:issue:`41`]
- Added :func:`~libearth.tz.guess_tzinfo_by_locale()` function.  [:issue:`41`]
- Added ``microseconds`` option to :class:`~libearth.codecs.Rfc822` codec.
- Fixed incorrect merge of subscription/category deletion.

  - Subscriptions are now archived rather than deleted.
  - :class:`~libearth.subscribe.Outline` (which is a common superclass of
    :class:`~libearth.subscribe.Subscription` and
    :class:`~libearth.subscribe.Category`) now has
    :attr:`~libearth.subscribe.Outline.deleted_at` attribute and
    :attr:`~libearth.subscribe.Outline.deleted` property.

__ http://bugs.python.org/issue13612


Version 0.2.1
-------------

To be released.

- Fixed :mod:`~libearth.parser.rss2` parsing error when any empty element
  occurs.
- Fixed a bug that :func:`~libearth.schema.validate()` function errored
  when any subelement has :class:`~libearth.schema.Text` descriptor.


Version 0.2.0
-------------

Released April 22, 2014.

- Session files in :file:`.sessions/` directory become to be touched
  only once at a transaction.  [:issue:`43`]
- Added :meth:`SubscriptionSet.contains()
  <libearth.subscribe.SubscriptionSet.contains>` method which provides
  ``recursively=True`` option.  It's useful for determining that
  a subcategory or subscription is in the whole tree.
- :attr:`Attribute.default <libearth.schema.Attribute.default>` option
  becomes to accept only callable objects.  Below 0.2.0,
  :attr:`~libearth.schema.Attribute.default` is not a function but a value
  which is simply used as it is.
- ``libearth.parser.heuristic`` module is gone; and ``get_format()``
  function in the module is moved to :mod:`libearth.parser.autodiscovery`
  module: :func:`~libearth.parser.autodiscovery.get_format()`.
- Added :attr:`Link.html <libearth.feed.Link.html>` property.
- Added :attr:`LinkList.permalink <libearth.feed.LinkList.permalink>` property.
- Fixed a :class:`~libearth.repository.FileSystemRepository` bug that conflicts
  reading buffer and emits broken mixed bytes when there are simultaneous
  readings and writings to the same key.
- Fixed broken functions related to repository urls on Windows.
- Fixed :func:`libearth.compat.parallel.cpu_count()` function not to
  raise :exc:`NotImplementedError` in some cases.
- Fixed :class:`~libearth.codecs.Rfc822` to properly work also on
  non-English locales e.g. ``ko_KR``.


Version 0.1.2
-------------

Released on January 19, 2014.

- XML elements in data files are written in canonical order.  For example,
  ``<title>`` element of the feed was at the back before, but now is in front.
- :class:`write() <libearth.schema.write>` becomes to store length hints of
  children that is :attr:`~libearth.schema.Child.multiple`, and
  :func:`~libearth.schema.read()` becomes aware of the hints.
  When hints are read :func:`len()` for the
  :class:`~libearth.schema.ElementList` is O(1).
- Fixed a bug that :mod:`~libearth.parser.autodiscovery` raises
  :exc:`AttributeError` when the given HTML contains ``<link>`` to
  both :mimetype:`application/atom+xml` and :mimetype:`application/rss+xml`.
  [:issue:`40`]
- Fill ``<title>`` to ``<description>`` if there's no ``<title>``
  (:mod:`~libearth.parser.rss2`).
- Fill ``<id>`` to the feed URL if there's no ``<id>``
  (:mod:`~libearth.parser.atom`).


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
