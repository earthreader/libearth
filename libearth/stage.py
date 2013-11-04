""":mod:`libearth.stage` --- Staging updates
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Stage is a similar concept to Git's one.  It's a unit of updates,
so every change to the repository should be done through a stage.

It also does more than Git's stage: :class:`Route`.  Routing system
hide how document should be stored in the repository, and provides
the natural object-mapping interface instead.

"""
import collections
import re

from .feed import Feed
from .repository import Repository, RepositoryKeyError
from .schema import read, write
from .session import MergeableDocumentElement, Session
from .subscribe import SubscriptionList
from .tz import now

__all__ = ('BaseStage', 'Directory', 'Route', 'Stage',
           'compile_format_to_pattern')


class BaseStage(object):
    """Base stage class that routes nothing yet.  It should be inherited
    to route document types.  See also :class:`Route` class.

    :param session: the current session to stage
    :type session: :class:`~libearth.session.Session`
    :param repository: the repository to stage
    :type repository: :class:`~libearth.repository.Repository`

    """

    #: (:class:`collections.Sequence`) The repository key of the directory
    #: where session list are stored.
    SESSION_DIRECTORY_KEY = ['.sessions']

    #: (:class:`~libearth.session.Session`) The current session of the stage.
    session = None

    #: (:class:`~libearth.repository.Repository`) The staged repository.
    repository = None

    def __init__(self, session, repository):
        if not isinstance(session, Session):
            raise TypeError('session must be an instance of {0.__module__}.'
                            '{0.__name__}, not {1!r}'.format(Session, session))
        elif not isinstance(repository, Repository):
            raise TypeError(
                'repository must be an instance of {0.__module__}.'
                '{0.__name__}, not {1!r}'.format(Repository, repository)
            )
        self.session = session
        self.repository = repository
        self.touch()

    @property
    def sessions(self):
        """(:class:`collections.Set`) List all sessions associated to
         the :attr:`repository`.  It includes the session of the current stage.

        """
        identifiers = self.repository.list(self.SESSION_DIRECTORY_KEY)
        return frozenset(Session(identifier=ident) for ident in identifiers)

    def touch(self):
        """Touch the latest staged time of the current :attr:`session`
        into the :attr:`repository`.

        .. note::

           This method is intended to be internal.

        """
        self.repository.write(
            self.SESSION_DIRECTORY_KEY + [self.session.identifier],
            [now().isoformat()]
        )

    def read(self, document_type, key):
        """Read a document of ``document_type`` by the given ``key``
        in the staged :attr:`repository`.

        :param document_type:
            the type of document to read. it has to be a subclass of
            :class:`~libearth.session.MergeableDocumentElement`
        :type document_type: :class:`type`
        :param key: the key to find the ``document`` in the :attr:`repository`
        :type key: :class:`collections.Seqeuence`
        :returns: found document instance
        :rtype: :class:`~libearth.session.MergeableDocumentElement`
        :raises libearth.repository.RepositoryKeyError: when the key cannot
                                                        be found

        .. note::

           This method is intended to be internal.  Use routed properties
           rather than this.  See also :class:`Route`.

        """
        if not isinstance(document_type, type):
            raise TypeError('document_type must be a type object, '
                            'not {1!r}'.format(document_type))
        elif not issubclass(document_type, MergeableDocumentElement):
            raise TypeError(
                'document_type must be a subtype of {0.__module__}.'
                '{0.__name__}, not {1.__module__}.{1.__name__}'.format(
                    MergeableDocumentElement,
                    document_type
                )
            )
        document = read(document_type, self.repository.read(key))
        assert isinstance(document, MergeableDocumentElement)
        self.touch()
        not_stamped = document.__revision__ is None
        if not_stamped:
            return self.write(key, document)
        return document

    def read_merged_document(self, document_type, key_spec, key):
        # FIXME: remove assumption that it always takes Session.identifier
        complete_size = len(key)
        pattern = compile_format_to_pattern(key_spec[complete_size])
        for subkey in key_spec[complete_size + 1:]:
            try:
                subkey.format()
            except IndexError:
                raise  # FIXME: should return Directory instead
        docs = []
        for subkey in self.repository.list(key):
            match = pattern.match(subkey)
            if match:
                k = key + [subkey] + key_spec[complete_size + 1:]
                doc = self.read(document_type, k)
                triple = match.group(1), doc, k
                docs.append(triple)
        session = self.session
        if len(docs) == 1:
            _, doc, key = docs[0]
            if doc.__revision__.session is session:
                return doc
            return self.write(key, doc)
        docs.sort(key=lambda pair: pair[0] == session.identifier,
                  reverse=True)  # the current session comes first
        if docs:
            session_id, doc = reduce(lambda a, b:
                                     (a[0], session.merge(a[1], b[1])), docs)
            return doc

    def write(self, key, document):
        """Save the ``document`` to the ``key`` in the staged
        :attr:`repository`.

        :param key: the key to be stored
        :type key: :class:`collections.Sequence`
        :param document: the document to save
        :type document: :class:`~libearth.schema.MergeableDocumentElement`
        :returns: actually written document
        :rtype: :class:`~libearth.schema.MergeableDocumentElement`

        .. note::

           This method is intended to be internal.  Use routed properties
           rather than this.  See also :class:`Route`.

        """
        document = self.session.pull(document)
        self.repository.write(key, write(document))
        self.touch()
        return document

    def __repr__(self):
        return '{0.__module__}.{0.__name__}({1!r}, {2!r})'.format(
            type(self), self.session, self.repository
        )


class Route(object):
    """Descriptor that routes a ``document_type`` to a particular key
    path pattern in the repository.

    ``key_spec`` could contain some format strings.  Format strings can
    take a keyword (``session``) and zero or more positional arguments.

    For example, if you route a document type without any positional
    arguments in ``key_spec`` format::

        class Stage(BaseStage):
            '''Stage example.'''

            metadata = Route(
                Metadata,
                ['metadata', '{session.identifier}.xml']
            )

    Stage instance will has a ``metadata`` attribute that simply holds
    ``Metadata`` document instance (in the example):

    >>> stage.metadata  # ['metadata', 'session-id.xml']
    <Metadata ...>

    If you route something with one or more positional arguments in
    ``key_spec`` format, then it works in some different way::

        class Stage(BaseStage):
            '''Stage example.'''

            seating_chart = Route(
                Student,
                ['students', 'col-{0}', 'row-{1}', '{session.identifier}.xml']
            )

    In the above routing, two positional arguments were used.  It means that
    the ``seating_chart`` property will return two-dimensional mapping object
    (:class:`Directory`):

    >>> stage.seating_chart  # ['students', ...]
    <libearth.directory.Directory ['students']>
    >>> list(stage.seating_chart)
    ['A', 'B', 'C', 'D']
    >>> b = stage.seating_chart['B']  # ['students', 'col-B', ...]
    <libearth.directory.Directory ['students', 'col-B']>
    >>> list(stage.seating_chart['B'])
    ['1', '2', '3', '4', '5', '6']
    >>> stage.seating_chart['B']['6']  \\
    ... # ['students', 'col-B', 'row-6', 'session-id.xml']
    <Student B6>

    :param document_type: the type of document to route.
                          it has to be a subclass of
                          :class:`~libearth.session.MergeableDocumentElement`
    :type document_type: :class:`type`
    :param key_spec: the repository key pattern that might contain some
                     format strings
                     e.g. ``['docs', '{0}', '{session.identifier}.xml']`.
                     positional values are used for directory indices
                     (if present), and ``session`` keyword value is used
                     for identifying sessions
    :type key_spec: :class:`collections.Sequence`

    """

    #: (:class:`type`) The type of the routed document.  It is a subtype of
    #: :class:`~libearth.session.MergeableDocumentElement`.
    document_type = None

    #: (:class:`collections.Sequence`) The repository key pattern that
    #: might contain some format strings.
    key_spec = None

    def __init__(self, document_type, key_spec):
        if not isinstance(document_type, type):
            raise TypeError('document_type must be a type object, '
                            'not {1!r}'.format(document_type))
        elif not issubclass(document_type, MergeableDocumentElement):
            raise TypeError(
                'document_type must be a subtype of {0.__module__}.'
                '{0.__name__}, not {1.__module__}.{1.__name__}'.format(
                    MergeableDocumentElement,
                    document_type
                )
            )
        elif not isinstance(key_spec, collections.Sequence):
            raise TypeError('key_spec must be a sequence, not ' +
                            repr(key_spec))
        self.document_type = document_type
        self.key_spec = key_spec

    def __get__(self, obj, cls=None):
        if isinstance(obj, type):
            return self
        # Should be merged!
        assert isinstance(obj, BaseStage)
        key = []
        for fmt in self.key_spec:
            try:
                chunk = fmt.format(session=obj.session)
            except IndexError:
                return Directory(obj, self.document_type,
                                 self.key_spec, (), key)
            try:
                fmt.format()
            except KeyError:
                break
            else:
                key.append(chunk)
        return obj.read_merged_document(self.document_type, self.key_spec, key)

    def __set__(self, obj, value):
        session = obj.session
        try:
            key = [fmt.format(session=session) for fmt in self.key_spec]
        except IndexError:
            raise AttributeError('cannot set the directory')
        obj.write(key, value)


def compile_format_to_pattern(format_string):
    """Compile a ``format_string`` to regular expression pattern.
    For example, ``'string{0}like{1}this{{2}}'`` will be compiled to
    ``/^string(.*?)like(.*?)this\{2\}$/``.

    :param format_string: format string to compile
    :type format_string: :class:`str`
    :returns: compiled pattern object
    :rtype: :class:`re.RegexObject`

    """
    pattern = ['^']
    i = 0
    for match in re.finditer(r'(^|[^{])\{[^}]+\}|(\{\{)|(\}\})', format_string):
        if match.group(2):
            j = match.start()
            chunk = r'\{'
        elif match.group(3):
            j = match.start()
            chunk = r'\}'
        else:
            j = match.end(1)
            chunk = '(.*?)'
        pattern.append(re.escape(format_string[i:j]))
        pattern.append(chunk)
        i = match.end(0)
    if len(format_string) > i:
        pattern.append(re.escape(format_string[i:]))
    pattern.append('$')
    return re.compile(''.join(pattern))


class Directory(collections.Mapping):
    """Mapping object which represents hierarchy of routed key path.

    :param stage: the current stage
    :type stage: :class:`BaseStage`
    :param document_type: the same to :attr:`Route.document_type`
    :type document_type: :class:`type`
    :param key_spec: the same to :attr:`Route.key_spec` value
    :type key_spec: :class:`collections.Sequence`
    :param indices: the upper indices that are already completed
    :type indices: :class:`collections.Sequence`
    :param key: the upper key that are already completed
    :type key: :class:`collections.Sequence`

    .. note::

       The constructor is intended to be internal, so don't instantiate
       it directory.  Use :class:`Route` instead.

    """

    def __init__(self, stage, document_type, key_spec, indices, key):
        if not isinstance(stage, BaseStage):
            raise TypeError('stage must be an instance of {0.__module__}.'
                            '{0.__name__}, not {1!r}'.format(BaseStage, stage))
        elif not isinstance(document_type, type):
            raise TypeError('document_type must be a type object, '
                            'not {1!r}'.format(document_type))
        elif not issubclass(document_type, MergeableDocumentElement):
            raise TypeError(
                'document_type must be a subtype of {0.__module__}.'
                '{0.__name__}, not {1.__module__}.{1.__name__}'.format(
                    MergeableDocumentElement,
                    document_type
                )
            )
        elif not isinstance(key_spec, collections.Sequence):
            raise TypeError('key_spec must be a sequence, not ' +
                            repr(key_spec))
        elif not isinstance(indices, collections.Sequence):
            raise TypeError('indices must be a sequence, not ' + repr(indices))
        elif not isinstance(key, collections.Sequence):
            raise TypeError('key must be a sequence, not ' + repr(key))
        elif len(key) >= len(key_spec):
            raise ValueError('key seems already complete')
        self.stage = stage
        self.document_type = document_type
        self.key_spec = key_spec
        self.indices = tuple(indices)
        self.key = key

    def __len__(self):
        return sum(1 for _ in self)

    def __getitem__(self, index):
        key = list(self.key)
        indices = self.indices + (index,)
        stage = self.stage
        session = stage.session
        for fmt in self.key_spec[len(key):]:
            try:
                chunk = fmt.format(*indices, session=session)
            except IndexError:
                if stage.repository.exists(key):
                    return Directory(stage, self.document_type,
                                     self.key_spec, indices, key)
                raise KeyError(index)
            try:
                fmt.format(*indices)
            except KeyError:
                break
            else:
                key.append(chunk)
        try:
            doc = stage.read_merged_document(self.document_type,
                                             self.key_spec,
                                             key)
        except RepositoryKeyError:
            raise KeyError(index)
        if doc:
            return doc
        raise KeyError(index)

    def __setitem__(self, index, doc):
        indices = self.indices + (index,)
        session = self.stage.session
        try:
            key = [fmt.format(*indices, session=session)
                   for fmt in self.key_spec]
        except IndexError:
            raise TypeError('cannot set the directory')
        self.stage.write(key, doc)

    def __iter__(self):
        it = self.stage.repository.list(self.key)
        pattern = compile_format_to_pattern(self.key_spec[len(self.key)])
        indices = set()
        for key in it:
            match = pattern.match(key)
            if match:
                index = match.group(1)
                if index not in indices:
                    yield index
                    indices.add(index)

    def __repr__(self):
        return '<{0.__module__}.{0.__name__} {1!r}>'.format(
            type(self), self.key
        )


class Stage(BaseStage):
    """Staged documents of Earth Reader."""

    #: (:class:`collections.MutableMapping`) The map of feed ids to
    #: :class:`~libearth.feed.Feed` objects.
    feeds = Route(Feed, ['feeds', '{0}', '{session.identifier}.xml'])

    #: (:class:`~libearth.subscribe.SubscriptionList`) The set of subscriptions.
    subscriptions = Route(SubscriptionList,
                          ['subscriptions.{session.identifier}.xml'])
