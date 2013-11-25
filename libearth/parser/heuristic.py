""":mod:`libearth.parser.heuristic` --- Guessing
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Guess the syndication format of given arbitrary XML documents.

"""
from ..compat.etree import fromstring
from .atom import parse_atom
from .rss2 import parse_rss

__all__ = 'TYPE_ATOM', 'TYPE_RSS2', 'get_format'


#: (:class:`str`) The document type value for Atom format.
TYPE_ATOM = parse_atom

#: (:class:`str`) THe document type value for RSS 2.0 format.
TYPE_RSS2 = parse_rss


def get_format(document):
    """Guess the syndication format of an arbitrary ``document``.

    :param document: document string to guess
    :type document: :class:`str`

    """
    try:
        root = fromstring(document)
    except Exception:
        return None
    if root.tag == '{http://www.w3.org/2005/Atom}feed':
        return parse_atom
    elif root.tag == 'rss':
        return parse_rss
    else:
        return None
