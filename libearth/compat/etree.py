""":mod:`libearth.compat.etree` --- ElementTree compatibility layer
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This proxy module offers a compatibility layer between several ElementTree
implementations.

- If there's installed :mod:`lxml` module, use :mod:`lxml.etree`.
- If :mod:`xml.etree.cElementTree` is available, use it.
- If IronPython, use :mod:`xml.etree.ElementTree` with
  :class:`libearth.compat.clrxmlreader.TreeBuilder`.
- Otherwise, use :mod:`xml.etree.ElementTree`.

It provides the following two functions:

.. function:: fromstring(string)

   Parse the given XML ``string``.

   :param string: xml string to parse
   :type string: :class:`str`, :class:`bytes`, :class:`basestring`
   :returns: the element tree object

.. function:: fromstringlist(iterable)

   Parse the given chunks of XML string.

   :param iterable: chunks of xml string to parse
   :type iterable: :class:`collections.Iterable`
   :returns: the element tree object

.. function:: tostring(tree)

   Generate an XML string from the given element tree.

   :param tree: an element tree object to serialize
   :returns: an xml string
   :rtype: :class:`str`, :class:`bytes`

"""
try:
    from lxml.etree import fromstring, fromstringlist, tostring
except ImportError:
    try:
        from xml.etree.cElementTree import fromstring, tostring
    except ImportError:
        from xml.etree.ElementTree import fromstring, tostring
        try:
            from xml.etree.ElementTree import fromstringlist
        except ImportError:
            fromstringlist = None
    else:
        try:
            from xml.etree.cElementTree import fromstringlist
        except ImportError:
            fromstringlist = None

__all__ = 'fromstring', 'fromstringlist'


if fromstringlist is None:
    def fromstringlist(iterable):
        it = iter(iterable)
        try:
            first = next(it)
        except StopIteration:
            return fromstring('')
        return fromstring(first + type(first)().join(it))
