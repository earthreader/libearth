""":mod:`libearth.repository` --- Repositories
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

"""
import os.path

__all__ = 'FileNotFoundError', 'NotADirectoryError', 'Repository'


class Repository(object):

    #: (:class:`str`) The path of the directory to read and write data files.
    #: It should be readable and writable.
    path = None

    def __init__(self, path):
        if not os.path.exists(path):
            raise FileNotFoundError(repr(path) + ' does not exist')
        elif not os.path.isdir(path):
            raise NotADirectoryError(repr(path) + ' is not a directory')
        self.path = path

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
