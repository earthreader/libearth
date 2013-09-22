""":mod:`libearth.parser.heuristic` --- Guessing
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Guess the syndication format of given arbitrary XML documents.

"""
try:
    from lxml import etree
except ImportError:
    try:
        from xml.etree import cElementTree as etree
    except ImportError:
        from xml.etree import ElementTree as etree

from .atom import parse_atom
from .rss2 import parse_rss

__all__ = 'TYPE_ATOM', 'TYPE_RSS2', 'get_document_type', 'get_parser'


#: (:class:`str`) The document type value for Atom format.
TYPE_ATOM = 'atom'

#: (:class:`str`) THe document type value for RSS 2.0 format.
TYPE_RSS2 = 'rss2.0'


def get_document_type(document):
    """Guess the syndication format of an arbitrary ``document``.

    :param document: document string to guess
    :type document: :class:`str`

    """
    try:
        root = etree.fromstring(document)
    except:
        return None
    if root.tag == '{http://www.w3.org/2005/Atom}feed':
        return TYPE_ATOM
    elif root.tag == 'rss':
        return TYPE_RSS2
    else:
        return None


def get_parser(document_type):
    """return appropriate parser for specific feed.

    :param document_type: type of feed
    :type document_type: :class:`str`
    :returns: appropriate parser funcion
    :rtype: :class:`collections.Callable`

    """
    if document_type == TYPE_ATOM:
        return parse_atom
    elif document_type == TYPE_RSS2:
        return parse_rss
