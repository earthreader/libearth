""":mod:`libearth.parser.util` --- Utilities for feed parsing
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. versionadded:: 0.3.0

"""
import logging
import re

from ..compat import IRON_PYTHON, binary_type, text_type

__all__ = 'XML_ENCODING_PATTERN ', 'normalize_xml_encoding'


XML_ENCODING_PATTERN = re.compile(br'''
    ^ \s*
    <\?xml
    (?: \s+ version=(?: "[^"]*" | '[^']*')
    |   \s+ encoding=(?: "( [^"]* ) " | '( [^']* )')
    )+
    \s* \?>
''', re.VERBOSE)


def normalize_xml_encoding(document):
    """Normalize the given XML document's encoding to UTF-8 to workaround
    :mod:`xml.etree.ElementTree` module's `encoding detection bug`__.

    __ http://bugs.python.org/issue13612

    .. versionadded:: 0.3.0

    """
    if isinstance(document, text_type):
        return document
    elif not isinstance(document, binary_type):
        raise TypeError('document must be a bytestring or a (unicode) string')
    match = XML_ENCODING_PATTERN.match(document)
    if match:
        encoding = match.group(1) or match.group(2)
        if encoding:
            if not isinstance(encoding, str):
                encoding = encoding.decode('ascii')
            document = document[match.end():]
            try:
                document = document.decode(encoding).encode('utf-8')
            except (LookupError, UnicodeError) as e:
                logger = logging.getLogger(__name__ +
                                           '.normalize_xml_encoding')
                logger.warning(e, exc_info=True)
            if IRON_PYTHON:
                document = bytes(document)
    return document
