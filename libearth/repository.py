""":mod:`libearth.repository` --- Repositories
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:class:`Repository` abstracts storage backend e.g. filesystem.
There might be platforms that have no chance to directly access
file system e.g. iOS, and in that case the concept of repository
makes you to store data directly to Dropbox_ or `Google Drive`_
instead of filesystem.  However in the most cases we will simply use
:class:`FileSystemRepository` even if data are synchronized using
Dropbox or :program:`rsync`.

In order to make the repository highly configurable it provides the way
to lookup and instantiate the repository from url.  For example,
the following url will load :class:`FileSystemRepository` which sets
:attr:`~FileSystemRepository.path` to :file:`/home/dahlia/.earthreader/`:

.. code-block:: text

   file:///home/dahlia/.earthreader/

For extensibility every repository class has to implement :meth:`from_url()`
and :meth:`to_url()` methods, and register it as an `entry point`__ of
``libearth.repositories`` group e.g.:

.. code-block:: ini

   [libearth.repositories]
   file = libearth.repository:FileSystemRepository

Note that the entry point name (``file`` in the above example) becomes
the url scheme to lookup the corresponding repository class
(:class:`libearth.repository.FileSystemRepository` in the above example).

.. _Dropbox: http://dropbox.com/
.. _Google Drive: https://drive.google.com/
__ https://pythonhosted.org/setuptools/pkg_resources.html#entry-points

"""
import collections
import errno
import io
import os
import os.path
import pipes
import shutil
import sys
import tempfile
import threading
try:
    from urllib import parse as urlparse
except ImportError:
    import urlparse
import weakref

from .compat import IRON_PYTHON, string_type, xrange

__all__ = ('FileIterator', 'FileNotFoundError', 'FileSystemRepository',
           'NotADirectoryError', 'Repository', 'RepositoryKeyError',
           'from_url')


def from_url(url):
    """Load the repository instance from the given configuration ``url``.

    .. note::

       If :mod:`setuptools` is not installed it will only support
       ``file://`` scheme and :class:`FileSystemRepository`.

    :param url: a repository configuration url
    :type url: :class:`str`, :class:`urllib.parse.ParseResult`
    :returns: the loaded repository instance
    :rtype: :class:`Repository`
    :raises LookupError: when the corresponding repository type to
                         the given ``url`` scheme cannot be found
    :raises ValueError: when the given ``url`` is invalid

    """
    if isinstance(url, string_type):
        url = urlparse.urlparse(url)
    elif not isinstance(url, urlparse.ParseResult):
        raise TypeError(
            'url must be a string, or an instance of {0.__module__}.'
            '{0.__name__}, not {1!r}'.format(urlparse.ParseResult, url)
        )
    lookup_error = LookupError('cannot find the corresponding repository to '
                               '{0}:// scheme'.format(url.scheme))
    try:
        from pkg_resources import iter_entry_points
    except ImportError:
        if url.scheme != 'file':  # FIXME
            raise lookup_error
        repository_type = FileSystemRepository
    else:
        entry_points = iter_entry_points(
            group='libearth.repositories',
            name=url.scheme
        )
        for ep in entry_points:
            repository_type = ep.load()
            if issubclass(repository_type, Repository):
                break
        else:
            raise lookup_error
    return repository_type.from_url(url)


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

    @classmethod
    def from_url(cls, url):
        """Create a new instance of the repository from the given ``url``.
        It's used for configuring the repository in plain text
        e.g. :file:`*.ini`.

        .. note::

           Every subclass of :class:`Repository` has to override
           :meth:`from_url()` static/class method to implement details.

        :param url: the parsed url tuple
        :type url: :class:`urllib.parse.ParseResult`
        :returns: a new repository instance
        :rtype: :class:`Repository`
        :raises ValueError: when the given url is not invalid

        """
        raise NotImplementedError(
            'every subclass of {0.__module__}.{0.__name__} has to '
            'implement from_url() static/class method'.format(Repository)
        )

    def to_url(self, scheme):
        """Generate a url that :meth:`from_url()` can accept.
        It's used for configuring the repository in plain text
        e.g. :file:`*.ini`.  URL ``scheme`` is determined by caller,
        and given through argument.

        .. note::

           Every subclass of :class:`Repository` has to override
           :meth:`to_url()` method to implement details.

        :param scheme: a determined url scheme
        :returns: a url that :meth:`from_url()` can accept
        :rtype: :class:`str`

        """
        if not isinstance(scheme, string_type):
            raise TypeError('scheme must be a string, not ' + repr(scheme))
        if hash(type(self).to_url) == hash(Repository.to_url):
            raise NotImplementedError(
                'every subclass of {0.__module__}.{0.__name__} has to '
                'implement to_url() method'.format(Repository)
            )

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
    :param atomic: make the update invisible until it's complete.
                   :const:`False` by default
    :raises FileNotFoundError: when the ``path`` doesn't exist
    :raises NotADirectoryError: when the ``path`` is not a directory

    """

    #: (:class:`str`) The path of the directory to read and write data files.
    #: It should be readable and writable.
    path = None

    @classmethod
    def from_url(cls, url):
        if not isinstance(url, urlparse.ParseResult):
            raise TypeError(
                'url must be an instance of {0.__module__}.{0.__name__}, '
                'not {1!r}'.format(urlparse.ParseResult, url)
            )
        if url.scheme != 'file':
            raise ValueError('{0.__module__}.{0.__name__} only accepts '
                             'file:// scheme'.format(FileSystemRepository))
        elif url.netloc or url.params or url.query or url.fragment:
            raise ValueError('file:// must not contain any host/port/user/'
                             'password/parameters/query/fragment')
        if sys.platform == 'win32':
            if not url.path.startswith('/'):
                raise ValueError('invalid file path: ' + repr(url.path))
            parts = url.path.lstrip('/').split('/')
            path = os.path.join(parts[0] + os.path.sep, *parts[1:])
        else:
            path = url.path
        return cls(path)

    def __init__(self, path, mkdir=True, atomic=IRON_PYTHON):
        if not os.path.exists(path):
            if mkdir:
                try:
                    os.makedirs(path)
                except OSError as e:
                    if e.errno == errno.EEXIST:
                        pass
                    else:
                        raise
            else:
                raise FileNotFoundError(repr(path) + ' does not exist')
        if not os.path.isdir(path):
            raise NotADirectoryError(repr(path) + ' is not a directory')
        self.path = path
        self.atomic = atomic
        self.lock = threading.RLock()
        self.file_iterators = {}

    def to_url(self, scheme):
        super(FileSystemRepository, self).to_url(scheme)
        if sys.platform == 'win32':
            drive, path = os.path.splitdrive(self.path)
            path = '/'.join(path.lstrip(os.path.sep).split(os.path.sep))
            return '{0}:///{1}/{2}'.format(scheme, drive, path)
        return '{0}://{1}'.format(scheme, self.path)

    def read(self, key):
        super(FileSystemRepository, self).read(key)
        path = os.path.join(self.path, *key)
        if not os.path.isfile(path):
            raise RepositoryKeyError(key)
        with self.lock:
            iterator = FileIterator(path, buffer_size=4096)
            try:
                iterator_set = self.file_iterators[path]
            except KeyError:
                # weakref.WeakSet was introduced since Python 2.7,
                # so workaround it on Python 2.6 by using WeakKeyDictionary
                iterator_set = weakref.WeakKeyDictionary({iterator: 1})
                self.file_iterators[path] = iterator_set
            else:
                iterator_set[iterator] = len(iterator_set) + 1
            return iterator

    def write(self, key, iterable):
        super(FileSystemRepository, self).write(key, iterable)
        dirpath = list(key)[:-1]
        dirpath.insert(0, self.path)
        for i in xrange(len(dirpath)):
            p = os.path.join(*dirpath[:i + 1])
            if not os.path.exists(p):
                try:
                    os.mkdir(p)
                except OSError as e:
                    if e.errno == errno.EEXIST:
                        pass
                    else:
                        raise
            elif not os.path.isdir(p):
                raise RepositoryKeyError(key)
        filename = os.path.join(self.path, *key)
        with self.lock:
            already_opened_iterators = self.file_iterators.get(filename, {})
            for iterator in already_opened_iterators.keys():
                iterator.preload_all()
        if self.atomic:
            f = tempfile.NamedTemporaryFile('wb', delete=False)
        else:
            f = io.open(filename, 'wb')
        with f:
            for chunk in iterable:
                f.write(chunk)
        if self.atomic:
            if IRON_PYTHON:
                # FIXME: no mv in windows
                cmd = '/bin/mv {0} {1}'.format(
                    pipes.quote(f.name),
                    pipes.quote(filename)
                )
                with os.popen(cmd) as pf:
                    pf.read()
            else:
                shutil.move(f.name, filename)

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


class FileIterator(collections.Iterator):
    """Read a file through :class:`~collections.Iterator` protocol,
    with automatic closing of the file when it ends.

    :param path: the path of file
    :type path: :class:`str`
    :param buffer_size: the size of bytes that would be produced each step
    :type buffer_size: :class:`numbers.Integral`

    """

    def __init__(self, path, buffer_size):
        self.path = path
        self.buffer_size = buffer_size
        self.file_ = None

    def __iter__(self):
        self.file_ = io.open(self.path, 'rb', buffering=0)
        return self

    def __next__(self):
        f = self.file_
        if f is None:
            f = self.__iter__().file_
        elif f.closed:
            if hasattr(self, 'preloaded'):
                rest = self.preloaded
                del self.preloaded
                return rest
            raise StopIteration
        try:
            chunk = f.read(self.buffer_size)
        except:
            self.file_.close()
            raise
        if chunk:
            return chunk
        self.file_.close()
        raise StopIteration

    next = __next__

    def tell(self):
        return self.file_ and self.file_.tell()

    def seek(self, *args):
        if self.file_ is not None:
            self.file_.seek(*args)

    def read(self, *args):
        if self.file_ is not None:
            return self.file_.read(*args)

    def preload_all(self):
        f = self.file_
        if f is None:
            f = self.__iter__().file_
        elif not f.closed:
            self.preloaded = f.read()
            f.close()


try:
    FileNotFoundError = FileNotFoundError
    NotADirectoryError = NotADirectoryError
except NameError:
    class FileNotFoundError(IOError, OSError):
        """Raised when a given path does not exist."""

    class NotADirectoryError(IOError, OSError):
        """Raised when a given path is not a directory."""
