""":mod:`libearth.stage` --- Staging updates and transactions
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Stage is a similar concept to Git's one.  It's a unit of updates,
so every change to the repository should be done through a stage.

It also does more than Git's stage: :class:`Route`.  Routing system
hides how document should be stored in the repository, and provides
the natural object-mapping interface instead.

Stage also provides transactions.  All operations on staged documents should
be done within a transaction.  You can open and close a transaction using
:keyword:`with` statement e.g.::

    with stage:
        subs = stage.subscriptions
        stage.subscriptions = some_operation(subs)

Transaction will merge all simultaneous updates if there are multiple updates
when it's committed.  You can easily achieve thread safety using transactions.

Note that it however doesn't guarantee data integrity between multiple
processes, so *you have to use different session ids when there are multiple
processes.*

"""
import collections
import contextlib
import io
import re
import sys
import threading
import traceback

if sys.version_info >= (3,):
    try:
        import _thread
    except ImportError:
        import _dummy_thread as _thread
else:
    try:
        import thread as _thread
    except ImportError:
        import dummy_thread as _thread

try:
    import greenlet
except ImportError:
    greenlet = None
try:
    import stackless
except ImportError:
    stackless = None

from .compat import IRON_PYTHON, binary_type, reduce
from .feed import Feed
from .repository import Repository, RepositoryKeyError
from .schema import read, write
from .session import (MergeableDocumentElement, RevisionSet, Session,
                      parse_revision)
from .subscribe import SubscriptionList
from .tz import now

__all__ = ('BaseStage', 'Directory', 'DirtyBuffer', 'Route', 'Stage',
           'TransactionError',
           'compile_format_to_pattern', 'get_current_context_id')


def get_current_context_id():
    """Identifies which context it is (greenlet, stackless, or thread).

    :returns: the identifier of the current context

    """
    global get_current_context_id
    if greenlet is not None:
        if stackless is None:
            get_current_context_id = greenlet.getcurrent
            return greenlet.getcurrent()
        return greenlet.getcurrent(), stackless.getcurrent()
    elif stackless is not None:
        get_current_context_id = stackless.getcurrent
        return stackless.getcurrent()
    get_current_context_id = _thread.get_ident
    return _thread.get_ident()


class BaseStage(object):
    """Base stage class that routes nothing yet.  It should be inherited
    to route document types.  See also :class:`Route` class.

    It's a context manager, which is possible to be passed to :keyword:`with`
    statement.  The context maintains a transaction, that is required for
    all operations related to the stage::

        with stage:
            v = stage.some_value
            stage.some_value =  operate(v)

    If any ongoing transaction is not present while the operation requires it,
    it will raise :exc:`TransactionError`.

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

    #: (:class:`collections.MutableMapping`) Ongoing transactions.  Keys are
    #: the context identifier (that :func:`get_current_context_id()` returns),
    #: and values are pairs of the :class:`DirtyBuffer` that should be written
    #: when the transaction is committed, and stack information.
    transactions = None

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
        self.transactions = {}
        self.lock = threading.RLock()

    def __enter__(self):
        context_id = get_current_context_id()
        transactions = self.transactions
        try:
            pair = transactions[context_id]
        except KeyError:
            pass
        else:
            _, stack = pair
            raise TransactionError(
                'cannot doubly begin transactions for the same context; '
                'please commit the previously begun transaction first.\n'
                'note that previous transaction is begun at:\n' +
                ''.join('  ' + line.replace('\n', '\n  ', 1) for line in stack)
            )
        transactions[context_id] = (DirtyBuffer(self.repository, self.lock),
                                    traceback.format_stack())
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        dirty_buffer = self.get_current_transaction(pop=True)
        if exc_type is None:
            dirty_buffer.flush()
        self.touch()

    def get_current_transaction(self, pop=False):
        """Get the current ongoing transaction.  If any transaction is not
        begun yet, it raises :exc:`TransactionError`.

        :returns: the dirty buffer that should be written when the transaction
                  is committed
        :rtype: :class:`DirtyBuffer`
        :raises TransactionError: if not any transaction is not begun yet

        """
        context_id = get_current_context_id()
        trans_dict = self.transactions
        try:
            pair = trans_dict.pop(context_id) if pop else trans_dict[context_id]
        except KeyError:
            raise TransactionError(
                'there is no ongoing transaction for the current context; '
                'please begin the transaction using with keyword e.g.:\n'
                '    stage = {0!r}\n'
                '    with stage:\n'
                '        do_something(stage)\n'.format(self)
            )
        dirty_buffer, _ = pair
        return dirty_buffer

    @property
    def sessions(self):
        """(:class:`collections.Set`) List all sessions associated to
         the :attr:`repository`.  It includes the session of the current stage.

        """
        try:
            identifiers = self.repository.list(self.SESSION_DIRECTORY_KEY)
        except RepositoryKeyError:
            return frozenset()
        return frozenset(Session(identifier=ident) for ident in identifiers)

    def touch(self):
        """Touch the latest staged time of the current :attr:`session`
        into the :attr:`repository`.

        .. note::

           This method is intended to be internal.

        """
        timestamp = now().isoformat()
        if not isinstance(timestamp, binary_type):
            timestamp = binary_type(timestamp, 'ascii')
        self.repository.write(
            self.SESSION_DIRECTORY_KEY + [self.session.identifier],
            [timestamp]
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
        repository = self.get_current_transaction()
        chunks = repository.read(key)
        document = read(document_type, chunks)
        assert isinstance(document, MergeableDocumentElement)
        not_stamped = document.__revision__ is None
        if not_stamped:
            return self.write(key, document, merge=False)
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
        repository = self.get_current_transaction()
        docs = []
        for subkey in repository.list(key):
            match = pattern.match(subkey)
            if match:
                k = key + [subkey] + key_spec[complete_size + 1:]
                doc = self.read(document_type, k)
                triple = match.group(1), doc, k
                docs.append(triple)
        session = self.session
        if len(docs) == 1:
            _, doc, __ = docs[0]
            if doc.__revision__.session is session:
                return doc
            doc.__base_revisions__ = doc.__base_revisions__.merge(
                RevisionSet([doc.__revision__])
            )
            doc.__reivison__ = now()
            key = key + [key_spec[complete_size].format(session=session)] \
                      + key_spec[complete_size + 1:]
            return self.write(key, doc, merge=False)
        docs.sort(key=lambda pair: pair[0] == session.identifier,
                  reverse=True)  # the current session comes first
        if docs:
            session_id, doc = reduce(lambda a, b:
                                     (a[0], session.merge(a[1], b[1])), docs)
            return doc

    def write(self, key, document, merge=True):
        """Save the ``document`` to the ``key`` in the staged
        :attr:`repository`.

        :param key: the key to be stored
        :type key: :class:`collections.Sequence`
        :param document: the document to save
        :type document: :class:`~libearth.schema.MergeableDocumentElement`
        :param merge: merge with the previous revision of the same session
                      (if exists).  :const:`True` by default
        :type merge: :class:`bool`
        :returns: actually written document
        :rtype: :class:`~libearth.schema.MergeableDocumentElement`

        .. note::

           This method is intended to be internal.  Use routed properties
           rather than this.  See also :class:`Route`.

        """
        repository = self.get_current_transaction()
        try:
            if not merge:
                raise RepositoryKeyError([])
            prev = repository.read(key)
        except RepositoryKeyError:
            document = self.session.pull(document)
            pull = True
        else:
            prev_doc = read(type(document), prev)
            prev_rev = prev_doc.__revision__
            doc_rev = document.__revision__
            pull = (
                doc_rev is not None and prev_rev is not None and
                (doc_rev.updated_at > prev_rev.updated_at
                 if doc_rev.session is prev_rev.session
                 else document.__base_revisions__.contains(prev_rev))
            )
            if pull:
                # If the document already contains prev_doc, don't merge
                assert prev_rev.session is doc_rev.session
                document = self.session.pull(document)
            else:
                if prev_rev is None:
                    prev_doc = self.session.pull(prev_doc)
                if doc_rev is None:
                    document = self.session.pull(document)
                document = self.session.merge(prev_doc, document, force=True)
        with self.lock:  # FIXME
            bytearray = write(document, canonical_order=True, as_bytes=True)
        repository.write(key, bytearray, _type_hint=type(document))
        return document

    def __repr__(self):
        return '{0.__module__}.{0.__name__}({1!r}, {2!r})'.format(
            type(self), self.session, self.repository
        )


class DirtyBuffer(Repository):
    """Memory-buffered proxy for the repository.  It's used for transaction
    buffer which maintains updates to be written until the ongoing transaction
    is committed.

    :param repository: the bare repository where the buffer will
                       :meth:`flush` to
    :type repository: :class:`~libearth.repository.Repository`
    :param lock: the common lock shared between dirty buffers of the same stage
    :type lock: :class:`threading.RLock`

    .. note::

       This class is intended to be internal.

    """

    #: (:class:`~libearth.repository.Repository`) The bare repository where
    #: the buffer will :meth:`flush` to.
    repository = None

    def __init__(self, repository, lock):
        self.repository = repository
        self.dictionary = {}
        self.lock = lock

    def read(self, key):
        super(DirtyBuffer, self).read(key)
        d = self.dictionary
        for k in key:
            if not isinstance(d, dict):
                raise RepositoryKeyError(key)
            try:
                d = d[k]
            except KeyError:
                with self.lock:
                    return self.repository.read(key)
        return d[1],

    def write(self, key, iterable, _type_hint=None):
        super(DirtyBuffer, self).write(key, iterable)
        d = self.dictionary
        for k in key[:-1]:
            if not isinstance(d, dict):
                raise RepositoryKeyError(key)
            d = d.setdefault(k, {})
        if not isinstance(d, dict):
            raise RepositoryKeyError(key)
        if IRON_PYTHON:
            chunks = io.BytesIO()
            for chunk in iterable:
                chunks.write(chunk)
            bytearray = chunks.getvalue()
        else:
            bytearray = b''.join(iterable)
        d[key[-1]] = _type_hint, bytearray

    def exists(self, key):
        super(DirtyBuffer, self).exists(key)
        d = self.dictionary
        for k in key:
            if not isinstance(d, dict):
                raise RepositoryKeyError(key)
            try:
                d = d[k]
            except KeyError:
                with self.lock:
                    return self.repository.exists(key)
        return True

    def list(self, key):
        super(DirtyBuffer, self).list(key)
        d = self.dictionary
        for k in key:
            if not isinstance(d, dict):
                raise RepositoryKeyError(key)
            try:
                d = d[k]
            except KeyError:
                with self.lock:
                    return self.repository.list(key)
        if not isinstance(d, dict):
            raise RepositoryKeyError(key)
        try:
            with self.lock:
                src = self.repository.list(key)
        except RepositoryKeyError:
            return d
        return frozenset(d).union(src)

    def flush(self, _dictionary=None, _key=None):
        """Flush all buffered updates to the :attr:`repository`."""
        with self.lock if _dictionary is None else self.dump_context():
            if _dictionary is None:
                _dictionary = self.dictionary
                _key = ()
            items = getattr(_dictionary, 'iteritems', _dictionary.items)()
            read_from_repository = self.repository.read
            write_to_repository = self.repository.write
            for key, value in items:
                key = _key + (key,)
                if isinstance(value, dict):
                    self.flush(_dictionary=value, _key=key)
                else:
                    type_hint, bytearray = value
                    bytearray = bytearray,
                    if type_hint is not None:
                        try:
                            prev_iterable = read_from_repository(key)
                        except RepositoryKeyError:
                            pass
                        else:
                            prev_iterable = list(prev_iterable)
                            prev = parse_revision(prev_iterable)
                            crev = parse_revision(bytearray)
                            if prev is not None and \
                                (crev is None or crev[0] is None or
                                 not crev[1].contains(prev[0])):
                                prev_doc = read(type_hint, prev_iterable)
                                doc = read(type_hint, bytearray)
                                merged_doc = prev[0].session.merge(
                                    doc,
                                    prev_doc,
                                    force=True
                                )
                                bytearray = write(
                                    merged_doc,
                                    canonical_order=True,
                                    as_bytes=True
                                )
                    write_to_repository(key, bytearray)
            _dictionary.clear()

    @contextlib.contextmanager
    def dump_context(self):
        yield

    def __repr__(self):
        return '{0.__module__}.{0.__name__}({1!r})'.format(type(self),
                                                           self.repository)


class TransactionError(RuntimeError):
    """The error that rises if there's no ongoing transaction while it's
    needed to update the stage, or if there's already begun ongoing transaction
    when the new transaction get tried to begin.

    """


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
        if obj is None or isinstance(obj, type):
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
