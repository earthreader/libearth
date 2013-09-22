""":mod:`libearth.session` --- Merging concurrent updates between devices
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

"""
import collections
import datetime
import re
import uuid

from .codecs import Rfc3339
from .compat import string_type
from .schema import Codec

__all__ = 'SESSION_XMLNS', 'Revision', 'RevisionCodec', 'Session'


#: (:class:`str`) The XML namespace name used for session metadata.
SESSION_XMLNS = 'http://earthreader.github.io/session/'


class Session(object):

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

    def __str__(self):
        return self.identifier

    def __repr__(self):
        return '{0.__module__}.{0.__name__}({1!r})'.format(type(self),
                                                           self.identifier)


#: The named tuple type of (:class:`Session`, :class:`datetime.datetime`) pair.
Revision = collections.namedtuple('Revision', 'session updated_at')


class RevisionCodec(Codec):
    """Codec to encode/decode :class:`Revision` pairs.

    >>> from libearth.tz import utc
    >>> session = Session('test-identifier')
    >>> updated_at = datetime.datetime(2013, 9, 22, 3, 43, 40, tzinfo=utc)
    >>> rev = Revision(session, updated_at)
    >>> RevisionCodec().encode(rev)
    'test-identifier 2013-09-22T03:43:40Z'

    """

    #: (:class:`Rfc3339`) The intenally used codec to encode
    #: :attr:`Revision.updated_at` time to :rfc:`3339` format.
    RFC3339_CODEC = Rfc3339(prefer_utc=True)

    def encode(self, value):
        session, updated_at = value
        if not isinstance(session, Session):
            raise TypeError('{0!r} is not an instance of {1.__module__}.'
                            '{1.__name__}'.format(session, Session))
        elif not isinstance(updated_at, datetime.datetime):
            raise TypeError('{0!r} is not an instance of {1.__module__}.{1.'
                            '__name__}'.format(updated_at, datetime.datetime))
        return '{0} {1}'.format(session, self.RFC3339_CODEC.encode(updated_at))

    def decode(self, text):
        identifier, updated_at = text.split()
        return Revision(
            session=Session(identifier),
            updated_at=self.RFC3339_CODEC.decode(updated_at)
        )
