""":mod:`libearth.session` --- Isolate data from other installations
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This module provides merging facilities to avoid conflict between concurrent
updates of the same document/entity from different devices (installations).
There are several concepts here.

:class:`Session` abstracts installations on devices.  For example, if you
have a laptop, a tablet, and a mobile phone, and two apps are installed on
the laptop, then there have to be four sessions: `laptop-1`, `laptop-2`,
`table-1`, and `phone-1`.  You can think of it as branch if you are familiar
with DVCS.

:class:`Revision` abstracts timestamps of updated time.  An important thing
is that it preserves its session as well.

Base revisions (:attr:`MergeableDocumentElement.__base_revisions__`) show
what revisions the current revision is built on top of.  In other words,
what revisions were merged into the current revision.  :class:`RevisionSet`
is a dictionary-like data structure to represent them.

"""
import collections
import datetime
import re
import uuid
import xml.sax

from .codecs import Rfc3339
from .compat import string_type
from .compat.xmlpullreader import PullReader
from .schema import (PARSER_LIST, Attribute, Codec, DecodeError,
                     DocumentElement, Element, EncodeError, inspect_attributes,
                     inspect_child_tags, inspect_content_tag)
from .tz import now

__all__ = ('SESSION_XMLNS', 'MergeableDocumentElement', 'Revision',
           'RevisionCodec', 'RevisionParserHandler', 'RevisionSet',
           'RevisionSetCodec', 'Session',
           'ensure_revision_pair', 'parse_revision')


#: (:class:`str`) The XML namespace name used for session metadata.
SESSION_XMLNS = 'http://earthreader.org/session/'


class Session(object):
    """The unit of device (more abstractly, *installation*) that updates
    the same document (e.g. :class:`~libearth.feed.Feed`).  Every session
    must have its own unique :attr:`identifier` to avoid conflict between
    concurrent updates from different sessions.

    :param identifier: the unique identifier.  automatically generated
                       using :mod:`uuid` if not present
    :type identifier: :class:`str`

    """

    #: (:class:`re.RegexObject`) The regular expression pattern that matches
    #: to allowed identifiers.
    IDENTIFIER_PATTERN = re.compile(r'^[-a-z0-9_.]+$', re.IGNORECASE)

    #: (:class:`collections.MutableMapping`) The pool of interned sessions.
    #: It's for maintaining single sessions for the same identifiers.
    interns = {}

    #: (:class:`str`) The session identifier.  It has to be distinguishable
    #: from other devices/apps, but consistent for the same device/app.
    identifier = None

    def __new__(cls, identifier=None):
        if not (identifier is None or isinstance(identifier, string_type)):
            raise TypeError('identifier must be a string, not ' +
                            repr(identifier))
        identifier = str(identifier) if identifier else str(uuid.getnode())
        if not cls.IDENTIFIER_PATTERN.match(identifier):
            raise ValueError('invalid identifier format: ' + repr(identifier))
        try:
            session = cls.interns[identifier]
        except KeyError:
            session = super(Session, cls).__new__(cls)
            session.identifier = identifier
            cls.interns[identifier] = session
        return session

    def __eq__(self, other):
        return self is other

    def __ne__(self, other):
        return self is not other

    def __hash__(self):
        return hash(self.identifier)

    def revise(self, document):
        """Mark the given ``document`` as the latest revision of the current
        session.

        :param document: mergeable document to mark
        :type document: :class:`MergeableDocumentElement`

        """
        if not isinstance(document, MergeableDocumentElement):
            raise TypeError(
                'document must be an instance of {0.__module__}.{0.__name__}, '
                'not {1!r}'.format(MergeableDocumentElement, document)
            )
        if document.__base_revisions__:
            updated_at = max(now(), max(document.__base_revisions__.values()))
        else:
            updated_at = now()
        document.__revision__ = Revision(self, updated_at)

    def pull(self, document):
        """Pull the ``document`` (of possibly other session) to the current
        session.

        :param document: the document to pull from the possibly other session
                         to the current session
        :type document: :class:`MergeableDocumentElement`
        :returns: the clone of the given ``document`` with the replaced
                  :attr:`~MergeableDocumentElement.__revision__`.
                  note that the :attr:`Revision.updated_at` value won't
                  be revised.  it could be the same object to the given
                  ``document`` object if the session is the same
        :rtype: :class:`MergeableDocumentElement`

        """
        if not isinstance(document, MergeableDocumentElement):
            raise TypeError(
                'expected a {0.__module__}.{0.__name__} instance, not '
                '{1!r}'.format(MergeableDocumentElement, document)
            )
        rev = document.__revision__
        if rev is not None and rev.session is self:
            return document
        # TODO: It could be efficiently implemented using SAX parser with
        #       less memory use.
        element_type = type(document)
        copy = element_type()
        for name, desc in inspect_child_tags(element_type).values():
            if desc.multiple:
                value = list(getattr(document, name, []))
            else:
                value = getattr(document, name, None)
            setattr(copy, name, value)
        for name, _ in inspect_attributes(element_type).values():
            setattr(copy, name, getattr(document, name, None))
        content = inspect_content_tag(element_type)
        if content is not None:
            name = content[0]
            setattr(copy, name, getattr(document, name))
        if rev:
            copy.__revision__ = Revision(self, rev.updated_at)
        else:
            self.revise(copy)
        return copy

    def merge(self, a, b, force=False):
        """Merge the given two documents and return new merged document.
        The given documents are not manipulated in place.  Two documents
        must have the same type.

        :param a: the first document to be merged
        :type a: :class:`MergeableDocumentElement`
        :param b: the second document to be merged
        :type b: :class:`MergeableDocumentElement`
        :param force: by default (:const:`False`) it doesn't merge but
                      simply pull a or b if one already contains other.
                      if ``force`` is :const:`True` it always merge
                      two.  it assumes ``b`` is newer than ``a``

        """
        element_type = type(a)
        cls_b = type(b)
        if element_type is not cls_b:
            raise TypeError(
                'two document must have the same type; but {0.__module__}.'
                '{0.__name__} and {1.__module__}.{1.__name__} are not the '
                'same type'.format(element_type, cls_b)
            )
        if not force:
            if a.__base_revisions__.contains(b.__revision__):
                return self.pull(a)
            elif b.__base_revisions__.contains(a.__revision__):
                return self.pull(b)
        entity_id = lambda e: (e.__entity_id__()
                               if isinstance(e, Element)
                               else e)
        # The latest one should be `b`.
        if not force and a.__revision__.updated_at > b.__revision__.updated_at:
            a, b = b, a
        merged = element_type()
        for attr_name, desc in inspect_child_tags(element_type).values():
            if desc.multiple:
                a_list = getattr(a, attr_name, [])
                identifiers = dict((entity_id(entity), entity)
                                   for entity in a_list)
                merged_attr = list(a_list)
                for element in getattr(b, attr_name, []):
                    eid = entity_id(element)
                    try:
                        entity = identifiers[eid]
                    except KeyError:
                        merged_element = element
                    else:
                        merged_attr.remove(entity)
                        if isinstance(element, Element):
                            merged_element = element.__merge_entities__(entity)
                        else:
                            merged_element = element
                    identifiers[eid] = merged_element
                    merged_attr.append(merged_element)
            else:
                older_attr = getattr(a, attr_name, None)
                newer_attr = getattr(b, attr_name, None)
                if older_attr is None:
                    merged_attr = newer_attr
                elif newer_attr is None:
                    merged_attr = older_attr
                elif isinstance(newer_attr, Element):
                    merged_attr = newer_attr.__merge_entities__(older_attr)
                else:
                    merged_attr = newer_attr
            setattr(merged, attr_name, merged_attr)
        for attr_name, _ in inspect_attributes(element_type).values():
            setattr(merged, attr_name,
                    getattr(b, attr_name, getattr(a, attr_name, None)))
        content = inspect_content_tag(element_type)
        if content is not None:
            name = content[0]
            setattr(merged, name,
                    getattr(b, name, getattr(a, name, None)))
        self.revise(merged)
        merged_revisions = a.__base_revisions__.merge(
            b.__base_revisions__,
            RevisionSet([a.__revision__, b.__revision__])
        )
        merged.__base_revisions__ = merged_revisions
        self.revise(merged)
        from .subscribe import Feed
        if isinstance(merged, Feed):
            merged.entries = merged.entries.sort_entries()
        return merged

    def __str__(self):
        return self.identifier

    def __repr__(self):
        return '{0.__module__}.{0.__name__}({1!r})'.format(type(self),
                                                           self.identifier)


#: The named tuple type of (:class:`Session`, :class:`datetime.datetime`) pair.
Revision = collections.namedtuple('Revision', 'session updated_at')


def ensure_revision_pair(pair, force_cast=False):
    """Check the type of the given ``pair`` and error unless it's a valid
    revision pair (:class:`Session`, :class:`datetime.datetime`).

    :param pair: a value to check
    :type pair: :class:`collections.Sequence`
    :param force_cast: whether to return the casted value to :class:`Revision`
                       named tuple type
    :type force_cast: :class:`bool`
    :returns: the revision pair
    :rtype: :class:`Revision`, :class:`collections.Sequence`

    """
    try:
        session, updated_at = pair
    except ValueError:
        raise TypeError('expected a pair, not ' + repr(pair))
    if not isinstance(session, Session):
        raise TypeError('{0!r} is not an instance of {1.__module__}.'
                        '{1.__name__}'.format(session, Session))
    elif not isinstance(updated_at, datetime.datetime):
        raise TypeError('{0!r} is not an instance of {1.__module__}.{1.'
                        '__name__}'.format(updated_at, datetime.datetime))
    if isinstance(pair, Revision) or not force_cast:
        return pair
    return Revision(*pair)


class RevisionSet(collections.Mapping):
    """Set of :class:`Revision` pairs.  It provides dictionary-like
    mapping protocol.

    :param revisions: the iterable of
                      (:class:`Session`, :class:`datetime.datetime`) pairs
    :type revisions: :class:`collections.Iterable`

    """

    def __init__(self, revisions=[]):
        self.revisions = dict(map(ensure_revision_pair, revisions))

    def __len__(self):
        return len(self.revisions)

    def __iter__(self):
        return iter(self.revisions)

    def __getitem__(self, session):
        return self.revisions[session]

    def items(self):
        """The list of (:class:`Session`, :class:`datetime.datetime`) pairs.

        :return: the list of :class:`Revision` instances
        :rtype: :class:`collections.ItemsView`

        """
        return [Revision(*pair) for pair in super(RevisionSet, self).items()]

    def copy(self):
        """Make a copy of the set.

        :returns: a new equivalent set
        :rtype: :class:`RevisionSet`

        """
        return type(self)(self.items())

    def merge(self, *sets):
        """Merge two or more :class:`RevisionSet`\ s.  The latest time
        remains for the same session.

        :param \*sets: one or more :class:`RevisionSet` objects to merge
        :returns: the merged set
        :rtype: :class:`RevisionSet`

        """
        cls = type(self)
        if not sets:
            raise TypeError('expected one or more {0.__module__}.{0.__name__} '
                            'objects'.format(cls))
        sets = sets + (self,)
        sessions = set()
        for revisions in sets:
            if not isinstance(revisions, cls):
                raise TypeError('{0!r} is not an instance of {1.__module__}.'
                                '{1.__name__}'.format(revisions, cls))
            sessions.update(revisions)
        return cls(
            Revision(session, max(s[session] for s in sets if session in s))
            for session in sessions
        )

    def contains(self, revision):
        """Find whether the given ``revision`` is already merged to
        the revision set.  In other words, return :const:`True`
        if the ``revision`` doesn't have to be merged to the revision set
        anymore.

        :param revision: the revision to find whether it has to be merged
                         or not
        :type revision: :class:`Revision`
        :returns: :const:`True` if the ``revision`` is included in
                  the revision set, or :const:`False`
        :rtype: :class:`bool`

        """
        try:
            return self[revision.session] >= revision.updated_at
        except KeyError:
            return False

    def __repr__(self):
        return '{0.__module__}.{0.__name__}({1!r})'.format(type(self),
                                                           self.items())


class RevisionCodec(Codec):
    """Codec to encode/decode :class:`Revision` pairs.

    >>> from libearth.tz import utc
    >>> session = Session('test-identifier')
    >>> updated_at = datetime.datetime(2013, 9, 22, 3, 43, 40, tzinfo=utc)
    >>> rev = Revision(session, updated_at)
    >>> RevisionCodec().encode(rev)
    'test-identifier 2013-09-22T03:43:40Z'

    """

    #: (:class:`Rfc3339`) The internally used codec to encode
    #: :attr:`Revision.updated_at` time to :rfc:`3339` format.
    RFC3339_CODEC = Rfc3339(prefer_utc=True)

    def encode(self, value):
        try:
            session, updated_at = ensure_revision_pair(value)
        except TypeError as e:
            raise EncodeError(str(e))
        return '{0} {1}'.format(session, self.RFC3339_CODEC.encode(updated_at))

    def decode(self, text):
        try:
            identifier, updated_at = text.split()
        except ValueError:
            raise DecodeError(repr(text) + ' is an invalid revision format')
        try:
            session = Session(identifier)
        except ValueError:
            raise DecodeError(repr(identifier) +
                              ' is and invalid session identifier')
        return Revision(
            session=session,
            updated_at=self.RFC3339_CODEC.decode(updated_at)
        )


class RevisionSetCodec(RevisionCodec):
    r"""Codec to encode/decode multiple :class:`Revision` pairs.

    >>> from datetime import datetime
    >>> from libearth.tz import utc
    >>> revs = RevisionSet([
    ...     (Session('a'), datetime(2013, 9, 22, 16, 58, 57, tzinfo=utc)),
    ...     (Session('b'), datetime(2013, 9, 22, 16, 59, 30, tzinfo=utc)),
    ...     (Session('c'), datetime(2013, 9, 22, 17, 0, 30, tzinfo=utc))
    ... ])
    >>> encoded = RevisionSetCodec().encode(revs)
    >>> encoded
    'c 2013-09-22T17:00:30Z,\nb 2013-09-22T16:59:30Z,\na 2013-09-22T16:58:57Z'
    >>> RevisionSetCodec().decode(encoded)
    libearth.session.RevisionSet([
        Revision(session=libearth.session.Session('b'),
                 updated_at=datetime.datetime(2013, 9, 22, 16, 59, 30,
                                              tzinfo=libearth.tz.Utc())),
        Revision(session=libearth.session.Session('c'),
                 updated_at=datetime.datetime(2013, 9, 22, 17, 0, 30,
                                              tzinfo=libearth.tz.Utc())),
        Revision(session=libearth.session.Session('a'),
                 updated_at=datetime.datetime(2013, 9, 22, 16, 58, 57,
                                              tzinfo=libearth.tz.Utc()))
    ])

    """

    #: (:class:`re.RegexObject`) The regular expression pattern that matches
    #: to separator substrings between revision pairs.
    SEPARATOR_PATTERN = re.compile(r'\s*,\s*')

    def encode(self, value):
        if not isinstance(value, RevisionSet):
            raise EncodeError('{0!r} is not an instance of {1.__module__}.'
                              '{1.__name__}'.format(value, RevisionSet))
        encode_pair = super(RevisionSetCodec, self).encode
        pairs = value.items()
        if not isinstance(pairs, list):
            pairs = list(pairs)
        pairs.sort(key=lambda pair: pair[1], reverse=True)
        return ',\n'.join(map(encode_pair, pairs))

    def decode(self, text):
        decode_pair = super(RevisionSetCodec, self).decode
        pairs = self.SEPARATOR_PATTERN.split(text) if text.strip() else []
        return RevisionSet(map(decode_pair, pairs))


class MergeableDocumentElement(DocumentElement):
    """Document element which is mergeable using :class:`Session`."""

    #: (:class:`Revision`) The revision of the document.
    __revision__ = Attribute('revision', RevisionCodec, xmlns=SESSION_XMLNS)

    #: (:class:`RevisionSet`) The set of revisions that its current
    #: :attr:`revision` is built on top of.  That means these revisions
    #: no longer need to be merged.
    __base_revisions__ = Attribute('bases', RevisionSetCodec,
                                   xmlns=SESSION_XMLNS,
                                   default=RevisionSet())


class RevisionParserHandler(xml.sax.handler.ContentHandler):
    """SAX content handler that picks session metadata
    (:attr:`~MergeableDocumentElement.__revision__` and
    :attr:`~MergeableDocumentElement.__base_revisions__`) from the given
    document element.

    Parsed result goes :attr:`revision` and :attr:`base_revisions`.

    Used by :func:`parse_revision()`.

    """

    #: (:class:`bool`) Represents whether the parsing is complete.
    done = None

    #: (:class:`Revision`) The parsed
    #: :attr:`~MergeableDocumentElement.__revision__`.  It might be
    #: :const:`None`.
    revision = None

    #: (:class:`RevisionSet`). The parsed
    #: :attr:`~MergeableDocumentElement.__base_revisions__`.  It might be
    #: :const:`None`.

    def __init__(self):
        self.done = False
        self.revision = None
        self.base_revisions = None

    def startElementNS(self, tag, qname, attrs):
        if self.done:
            return
        revision_desc = MergeableDocumentElement.__revision__
        bases_desc = MergeableDocumentElement.__base_revisions__
        self.revision = attrs.get((revision_desc.xmlns, revision_desc.name))
        self.base_revisions = attrs.get((bases_desc.xmlns, bases_desc.name))
        self.done = True


def parse_revision(iterable):
    """Efficiently parse only :attr:`~MergeableDocumentElement.__revision__`
    and :attr:`~MergeableDocumentElement.__base_revisions__` from the given
    ``iterable`` which contains chunks of XML.  It reads only head of
    the given document, and ``iterable`` will be not completely consumed
    in most cases.

    Note that it doesn't validate the document.

    :param iterable: chunks of bytes which contains
                     a :class:`MergeableDocumentElement` element
    :type iterable: :class:`collections.Iterable`
    :returns: a pair of (:attr:`~MergeableDocumentElement.__revision__`,
              :attr:`~MergeableDocumentElement.__base_revisions__`).
              it might be :const:`None` if the document is not stamped
    :rtype: :class:`collections.Sequence`

    """
    parser = xml.sax.make_parser(PARSER_LIST)
    handler = RevisionParserHandler()
    parser.setContentHandler(handler)
    parser.setFeature(xml.sax.handler.feature_namespaces, True)
    if isinstance(parser, PullReader):
        parser.prepareParser(iterable)
        while not handler.done and parser.feed():
            pass
    else:
        iterator = iter(iterable)
        while not handler.done:
            try:
                chunk = next(iterator)
            except StopIteration:
                break
            parser.feed(chunk)
    if handler.revision is None:
        return
    rev_codec = RevisionCodec()
    revset_codec = RevisionSetCodec()
    return (rev_codec.decode(handler.revision),
            revset_codec.decode(handler.base_revisions))
