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
    if document_type == 'atom':
        return parse_atom
    elif document_type == 'rss2.0':
        return parse_rss
