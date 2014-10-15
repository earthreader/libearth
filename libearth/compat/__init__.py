""":mod:`libearth.compat` --- Compatibility layer
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This module provides several subtle things to support
multiple Python versions (2.6, 2.7, 3.2, 3.3) and VM implementations
(CPython, PyPy).

"""
import functools
import io
import platform
import sys
import types

__all__ = ('IRON_PYTHON', 'PY3', 'UNICODE_BY_DEFAULT', 'binary', 'binary_type',
           'encode_filename', 'file_types', 'string_type', 'text', 'text_type',
           'xrange')


#: (:class:`bool`) Whether it is Python 3.x or not.
PY3 = sys.version_info >= (3,)

#: (:class:`bool`) Whether it is IronPython or not.
IRON_PYTHON = platform.python_implementation() == 'IronPython'

#: (:class:`bool`) Whether the Python VM uses Unicode strings by default.
#: It must be :const:`True` if :const:`PY3` or IronPython.
UNICODE_BY_DEFAULT = PY3 or IRON_PYTHON

#: (:class:`type`) Type for representing binary data.  :class:`str` in Python 2
#: and :class:`bytes` in Python 3.
binary_type = bytes if PY3 or IRON_PYTHON else str

#: (:class:`type`) Type for text data.  :class:`basestring` in Python 2
#: and :class:`str` in Python 3.
string_type = str if PY3 else basestring

#: (:class:`type`) Type for representing Unicode textual data.
#: :class:`unicode` in Python 2 and :class:`str` in Python 3.
text_type = str if PY3 else unicode

#: The function that takes a Unicode codepoint and returns the corresponding
#: Unicode character.
unichr = chr if PY3 else unichr


def binary(string, var=None):
    """Makes ``string`` to :class:`str` in Python 2.
    Makes ``string`` to :class:`bytes` in Python 3 or IronPython.

    :param string: a string to cast it to :data:`binary_type`
    :type string: :class:`bytes`, :class:`str`, :class:`unicode`
    :param var: an optional variable name to be used for error message
    :type var: :class:`str`

    """
    if isinstance(string, text_type):
        if IRON_PYTHON:
            return bytes(string, sys.getdefaultencoding())
        return string.encode()
    elif isinstance(string, binary_type):
        return string
    if var:
        raise TypeError('{0} must be a string, not {1!r}'.format(var, string))
    raise TypeError('expected a string, not ' + repr(string))


def text(string):
    """Makes ``string`` to :class:`str` in Python 3 or IronPython.
    Does nothing in Python 2.

    :param string: a string to cast it to :data:`text_type`
    :type string: :class:`bytes`, :class:`str`, :class:`unicode`

    """
    return string


if PY3 or IRON_PYTHON:
    def text(string):
        if isinstance(string, bytes):
            return string.decode('utf-8')
        return string


#: The :func:`xrange()` function.  Alias for :func:`range()` in Python 3.
xrange = range if PY3 else xrange


#: The :func:`reduce()` function.  Alias for :func:`functools.reduce()`
#: in Python 3.
reduce = functools.reduce if PY3 else reduce


#: (:class:`type`, :class:`tuple`) Types for file objects that have
#: ``fileno()``.
file_types = io.RawIOBase if PY3 else (io.RawIOBase, types.FileType)


def encode_filename(filename):
    """If ``filename`` is a :data:`text_type`, encode it to
    :data:`binary_type` according to filesystem's default encoding.

    """
    if isinstance(filename, text_type):
        return filename.encode(sys.getfilesystemencoding())
    return filename
