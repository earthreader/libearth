""":mod:`xml.compat.clrxmlreader` --- ``System.Xml.XmlReader`` backed SAX
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

"""
import collections
import System
import System.IO

__all__ = 'IteratorStream',


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
