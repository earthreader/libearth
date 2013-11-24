""":mod:`xml.compat.clrxmlreader` --- ``System.Xml.XmlReader`` backed SAX
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Python :mod:`xml.sax` parser implementation using CLR ``System.Xml.XmlReader``.

.. seealso::

   - `XmlReader Class`__
   - `Comparing XmlReader to SAX Reader`__

   __ http://msdn.microsoft.com/en-us/library/system.xml.xmlreader.aspx
   __ http://msdn.microsoft.com/en-us/library/sbw89de7.aspx

"""
import clr
clr.AddReference('System.Xml')
import collections
import System
import System.IO
import System.Xml
import xml.sax.xmlreader

from .xmlpullreader import PullReader

__all__ = 'IteratorStream', 'XmlReader', 'create_parser'


def create_parser():
    """Create a new :class:`XmlReader()` parser instance.

    :returns: a new parser instance
    :rtype: :class:`XmlReader`

    """
    return XmlReader()


class XmlReader(PullReader):
    """SAX :class:`~libearth.compat.xmlpullreader.PullReader` implementation
    using CLR ``System.Xml.XmlReader``.

    """

    def prepareParser(self, iterable):
        stream = IteratorStream(iterable)
        self.reader = System.Xml.XmlReader.Create(stream)

    def feed(self):
        reader = self.reader
        if not reader.Read():
            return False
        handler = self.getContentHandler()
        XmlNodeType = System.Xml.XmlNodeType
        node_type = reader.NodeType
        if node_type == XmlNodeType.Element:
            attrs = {}
            qnames = {}
            if reader.HasAttributes:
                while reader.MoveToNextAttribute():
                    attr = reader.NamespaceURI or None, reader.LocalName
                    attrs[attr] = reader.Value
                    qnames[attr] = reader.Name
                reader.MoveToElement()
            handler.startElementNS(
                (reader.NamespaceURI or None, reader.LocalName),
                reader.Name,
                xml.sax.xmlreader.AttributesNSImpl(attrs, qnames)
            )
        elif node_type == XmlNodeType.Text or node_type == XmlNodeType.CDATA:
            handler.characters(reader.Value)
        elif node_type == XmlNodeType.EndElement:
            handler.endElementNS(
                (reader.NamespaceURI or None, reader.LocalName),
                reader.Name
            )
        return True

    def close(self):
        self.reader.Dispose()

    def setFeature(self, name, state):
        pass

    def reset(self):
        pass


class IteratorStream(System.IO.Stream):

    def __new__(cls, iterable):
        stream = System.IO.Stream.__new__(cls)
        stream.__init__(iterable)
        return stream

    def __init__(self, iterable):
        self.iterable = iterable
        self.iterator = iter(iterable)
        self.buffer = []
        self.buffer_length = 0
        self.position = 0
        self.length = 0
        self.length_cache = None

    def consume(self):
        try:
            chunk = next(self.iterator)
        except StopIteration:
            return False
        assert isinstance(chunk, bytes), repr(chunk) + ' is not bytes'
        chunk_size = len(chunk)
        self.buffer.append(chunk)
        self.buffer_length += chunk_size
        self.length += chunk_size
        return True

    def get_CanRead(self):
        return True

    def get_CanSeek(self):
        return False

    def get_CanWrite(self):
        return False

    def get_Length(self):
        if self.length_cache is not None:
            return self.length_cache
        if isinstance(self.iterable, collections.Sequence):
            self.length_cache = sum(len(bytes_) for bytes_ in self.iterable)
            return self.length_cache
        while self.consume():
            pass
        self.length_cache = self.length
        return self.length

    def get_Position(self):
        return self.position

    def Read(self, buffer, offset, count):
        while self.buffer_length < count:
            if not self.consume():
                break
        total_read = 0
        for i, chunk in enumerate(self.buffer):
            read_bytes = min(count, len(chunk))
            chunk[:read_bytes].CopyTo(buffer, offset + total_read)
            count -= read_bytes
            total_read += read_bytes
            if not count:
                break
        if total_read:
            if len(chunk) <= read_bytes:
                self.buffer[:i + 1] = []
            else:
                self.buffer[i] = chunk[read_bytes:]
                self.buffer[:i] = []
            self.buffer_length -= total_read
            self.position += total_read
        return total_read

    def Seek(self, offset, seek_origin):
        raise System.InvalidOperationException(
            'Seek is unsupported on this stream'
        )

    def SetLength(self, value):
        raise System.InvalidOperationException(
            'SetLength is unsupported on this stream'
        )

    def Write(self, buffer, offset, count):
        raise System.InvalidOperationException(
            'Write is unsupported on this stream'
        )
