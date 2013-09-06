""":mod:`libearth.parser.heuristic` --- Guessing
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Get any XML and guess the type of XML.

"""


import re

try:
    from lxml import etree
except ImportError:
    try:
        from xml.etree import cElementTree as etree
    except ImportError:
        from xml.etree import ElementTree as etree

from .atom import parse_atom
from .rss2 import parse_rss


def get_document_type(document):
    """Get any document and guess the type of XML

    :param document: document to guess
    :type document: :class:`str`

    """
    try:
        root = etree.fromstring(document)
    except:
        return 'not feed'
    if re.search('feed', root.tag):
        return 'atom'
    elif root.tag == 'rss':
        return 'rss2.0'
    elif re.search('RDF', root.tag):
        return 'rss1.0'
    else:
        return 'not feed'


def get_parser(document_type):
    """return appropriate parser for specific feed.

    :param document_type: type of feed
    :type document_type: :class:`str`
    :returns: appropriate parser funcion
    :rtype: :class:`collections.Callable`

    """
    if document_type == 'atom':
        return parse_atom
    elif document_type == 'rss2.0':
        return parse_rss
