""":mod:`libearth.repository` --- Repositories
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

"""
import collections
import io
import os
import os.path

from .compat import xrange

__all__ = ('FileNotFoundError', 'FileSystemRepository', 'NotADirectoryError',
           'Repository', 'RepositoryKeyError')


class Repository(object):
    """Repository interface agnostic to its underlying storage implementation.
    :class:`~libearth.stage.Stage` objects can deal with documents to be stored
    using the interface.

    Every content in repositories is accessible using *keys*.  It actually
    abstracts out "filenames" in "file systems", hence keys share the common
    concepts with filenames.  Keys are hierarchical, like file paths, so
    consists of multiple sequential strings e.g. ``['dir', 'subdir', 'key']``.
    You can :meth:`list()` all subkeys in the upper key as well e.g.::

        repository.list(['dir', 'subdir'])

    """

    def read(self, key):
        """Read the content from the ``key``.

        :param key: the key which stores the content to read
        :type key: :class:`collections.Sequence`
        :returns: byte string chunks
        :rtype: :class:`collections.Iterable`
        :raises RepositoryKeyError: the ``key`` cannot be found in
                                    the repository, or it's not a file

        .. note::

           Every subclass of :class:`Repository` has to override
           :meth:`read()` method to implement details.

        """
        if not isinstance(key, collections.Sequence):
            raise TypeError('key must be a sequence, not ' + repr(key))
        elif not key:
            raise RepositoryKeyError(key, 'key cannot be empty')
        if hash(type(self).read) == hash(Repository.read):
            raise NotImplementedError(
                'every subclass of {0.__module__}.{0.__name__} has to '
                'implement read() method'.format(Repository)
            )

    def write(self, key, iterable):
        """Write the ``iterable`` into the ``key``.

        :param key: the key to stores the ``iterable``
        :type key: :class:`collections.Sequence`
        :param iterable: the iterable object yiels chunks of the whole
                         content.  every chunk has to be a byte string
        :type iterable: :class:`collections.Iterable`

        .. note::

           Every subclass of :class:`Repository` has to override
           :meth:`write()` method to implement details.

        """
        if not isinstance(key, collections.Sequence):
            raise TypeError('key must be a sequence, not ' + repr(key))
        elif not isinstance(iterable, collections.Iterable):
            raise TypeError('expected an iterable object, not ' +
                            repr(iterable))
        elif not key:
            raise RepositoryKeyError(key, 'key cannot be empty')
        if hash(type(self).write) == hash(Repository.write):
            raise NotImplementedError(
                'every subclass of {0.__module__}.{0.__name__} has to '
                'implement write() method'.format(Repository)
            )

    def exists(self, key):
        """Return whether the ``key`` exists or not.  It returns :const:`False`
        if it doesn't exist instead of raising :exc:`RepositoryKeyError`.

        :param key: the key to find whether it exists
        :type key: :class:`collections.Sequence`
        :returns: :const:`True` only if the given ``key`` exists,
                  or :const:`False` if not exists
        :rtype: :class:`bool`

        .. note::

           Every subclass of :class:`Repository` has to override
           :meth:`exists()` method to implement details.

        """
        if not isinstance(key, collections.Sequence):
            raise TypeError('key must be a sequence, not ' + repr(key))
        if hash(type(self).exists) == hash(Repository.exists):
            raise NotImplementedError(
                'every subclass of {0.__module__}.{0.__name__} has to '
                'implement exists() method'.format(Repository)
            )

    def list(self, key):
        """List all subkeys in the ``key``.

        :param key: the incomplete key that might have subkeys
        :type key: :class:`collections.Sequence`
        :returns: the set of subkeys (set of strings, not set of string lists)
        :rtype: :class:`collections.Set`
        :raises RepositoryKeyError: the ``key`` cannot be found in
                                    the repository, or it's not a directory

        .. note::

           Every subclass of :class:`Repository` has to override
           :meth:`list()` method to implement details.

        """
        if not isinstance(key, collections.Sequence):
            raise TypeError('key must be a sequence, not ' + repr(key))
        if hash(type(self).list) == hash(Repository.list):
            raise NotImplementedError(
                'every subclass of {0.__module__}.{0.__name__} has to '
                'implement list() method'.format(Repository)
            )

    def __repr__(self):
        return '{0.__module__}.{0.__name__}()'.format(type(self))


class RepositoryKeyError(LookupError, IOError):
    """Exception which rises when the requested key cannot be found
    in the repository.

    """

    #: (:class:`collections.Sequence`) The requested key.
    key = None

    def __init__(self, key, *args, **kwargs):
        super(RepositoryKeyError, self).__init__(*args, **kwargs)
        self.key = key


class FileSystemRepository(Repository):
    """Builtin implementation of :class:`Repository` interface which uses
    the ordinary file system.

    :param path: the directory path to store keys
    :type path: :class:`str`
    :param mkdir: create the directory if it doesn't exist yet.
                  :const:`True` by default
    :type mkdir: :class:`bool`
    :raises FileNotFoundError: when the ``path`` doesn't exist
    :raises NotADirectoryError: when the ``path`` is not a directory

    """

    #: (:class:`str`) The path of the directory to read and write data files.
    #: It should be readable and writable.
    path = None

    def __init__(self, path, mkdir=True):
        if not os.path.exists(path):
            if mkdir:
                os.makedirs(path)
            else:
                raise FileNotFoundError(repr(path) + ' does not exist')
        if not os.path.isdir(path):
            raise NotADirectoryError(repr(path) + ' is not a directory')
        self.path = path

    def read(self, key):
        super(FileSystemRepository, self).read(key)
        try:
            f = io.open(os.path.join(self.path, *key), 'rb')
        except IOError as e:
            raise RepositoryKeyError(key, str(e))
        return self._read(f)

    def _read(self, f):
        with f:
            while 1:
                chunk = f.read(4096)
                if not chunk:
                    break
                yield chunk

    def write(self, key, iterable):
        super(FileSystemRepository, self).write(key, iterable)
        dirpath = list(key)[:-1]
        dirpath.insert(0, self.path)
        for i in xrange(len(dirpath)):
            p = os.path.join(*dirpath[:i + 1])
            if not os.path.isdir(p):
                os.mkdir(p)
        with io.open(os.path.join(self.path, *key), 'wb') as f:
            for chunk in iterable:
                f.write(chunk)

    def exists(self, key):
        super(FileSystemRepository, self).exists(key)
        return os.path.exists(os.path.join(self.path, *key))

    def list(self, key):
        super(FileSystemRepository, self).list(key)
        try:
            names = os.listdir(os.path.join(self.path, *key))
        except (IOError, OSError) as e:
            raise RepositoryKeyError(key, str(e))
        return frozenset(name for name in names if name != '..' or name != '.')

    def __repr__(self):
        return '{0.__module__}.{0.__name__}({1!r})'.format(type(self),
                                                           self.path)


try:
    FileNotFoundError = FileNotFoundError
    NotADirectoryError = NotADirectoryError
except NameError:
    class FileNotFoundError(IOError, OSError):
        """Raised when a given path does not exist."""

    class NotADirectoryError(IOError, OSError):
        """Raised when a given path is not a directory."""
