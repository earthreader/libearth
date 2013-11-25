Core concepts
=============

To achieve the :doc:`goal <goal>` of Earth Reader, its design need to resolve
the following subproblems:

1. Data should be stored in tangible format and more specifically,
   in plain text with well-structured directory layout.
   It would be much better if data can be easily read and parsed by
   other softwares.

2. Data should be possible to be synchronized through several existing
   utilities including Dropbox_, `Google Drive`_, and even :program:`rsync`,
   without any data corruption.
   In this docs we try to explain core concepts of libearth and what
   these concepts purpose to resolve.

.. _Dropbox: http://dropbox.com/
.. _Google Drive: https://drive.google.com/


Schema
------

All data libearth deals with are based on (de facto) standard formats.
For example, it stores subscription list and its category hierarchy to an
OPML file.  OPML_ have been a de facto standard format to exchange
subscription list by feed readers.  It also stores all feed data to Atom
format (:rfc:`4287`).

Actually the most technologies related to RSS/syndication formats are from
early 00's, and it means they had used XML instead of JSON today we use for
the same purpose.  OPML is an (though poorly structured) XML format,
and Atom also is an XML format.

Since we need to deal with several XML data and not need any other formats,
we decided to make something first-class model objects to XML like ORM to
relational databases.  You can find how it can be used for designing model
objects at :file:`libearth/feed.py` and :file:`libearth/subscribe.py`.
It looks similar to Django ORM and SQLAlchemy, and makes you to deal with XML
documents in the same way you use plain Python objects.

Under the hood it does incremental parsing using SAX_ instead of DOM to
reduce memory usage when the document is larger than a hundred megabytes.

.. seealso::
   
   Module :mod:`libearth.schema`
      Declarative schema for pulling DOM parser of XML

.. _OPML: http://dev.opml.org/
.. _SAX: http://en.wikipedia.org/wiki/Simple_API_for_XML


Read-time merge
---------------

Earth Reader data can be shared by multiple installations e.g. desktop apps,
mobile apps, web apps.  So there must be simultaneous updates between them
that could conflict.  An important constraint we have is synchronization isn't
done by Earth Reader.  We can't lock files nor do atomic operations on them.

Our solution to this is read-time merge.  All data are not shared between
installations at least in filesystem level.  They have isolated files for
the same entities, and libearth merges all of them when it's loaded into memory.
Merged result doesn't affect to all replicas but only a replica that
corresponds to the installation.  You can understand the approach similar to
DVCS (although there are actually many differences): installations are branches,
and updates from others can be pulled to mine.  If there are simultaneous
changes, these are merged and then committed to mine.  If there's no change
for me, simply pull changes from others without merge.  A big difference is
that there's no push.  You can only do pull others, or wait others to pull
yours.  It's because the most of existing synchronization utilities like
Dropbox_ passively works in background. Moreover there could be offline.


Repository
----------

:class:`~libearth.repository.Repository` abstracts storage backend
e.g. filesystem.  There might be platforms that have no chance to
directly access file system e.g. iOS, and in that case the concept of
repository makes you to store data directly to Dropbox_ or `Google Drive`_
instead of filesystem.  However in the most cases we will simply use
:class:`~libearth.repository.FileSystemRepository` even if data are
synchronized using Dropbox or rsync.

.. seealso::

   Module :mod:`libearth.repository`
      Repositories


Session
-------

:class:`~libearth.session.Session` abstracts installations.
Every installation has its own session identifier.
To be more exact it purposes to distinguish processes,
hence every process has its unique identifier even if they are child
processes of the same installation e.g. prefork workers.

Every session makes its own file for a document, for example,
if there are two sessions identified *a* and *b*, two files for a document
e.g. :file:`doc.xml` will be made :file:`doc.a.xml` and :file:`doc.b.xml`
respectively.

For each change a session merges all changes from other sessions
when a document is being loaded (read-time merge).

.. seealso::

   Module :mod:`libearth.session`
      Isolate data from other installations


Stage
-----

:class:`Stage <libearth.stage.BaseStage>` is a unit of changes i.e. an atomic
changes to be merged.  It provides transactions for multi threaded environment.
If there are simultaneous changes from other sessions or other transactions,
these are automatically merged when the currently ongoing transaction is
committed.

Stage also provides :class:`~libearth.stage.Route`, a convenient interface to
access documents.
For example, you can read the subscription list by ``stage.subscriptions``,
and write it by ``stage.subscriptions = new_subscriptions``.
In the similar way you can read a feed by ``stage.feeds[feed_id]``,
and write it by ``stage.feeds[feed_id] = new_feed``.

.. seealso::

   Module :mod:`libearth.stage`
      Staging updates and transactions
