from pytest import mark

from libearth.compat import IRON_PYTHON
if IRON_PYTHON:
    import System  # to import bytes.ToByteArray()
    from libearth.compat.clrxmlreader import IteratorStream


iron_python_only = mark.skipif('not IRON_PYTHON',
                               reason='Test only for Iron Python')


@iron_python_only
def test_iterator_stream():
    is_ = IteratorStream([b'abc', b'def', b'ghi', b'jkl', b'mno'])
    assert is_.Position == 0
    assert is_.Length == 15, 'is_.Length = ' + repr(is_.Length)
    read_byte = is_.ReadByte()
    assert read_byte == ord(b'a')
    assert is_.Position == 1
    assert len(is_.buffer) == 1, 'is_.buffer = ' + repr(is_.buffer)
    buffer_ = b'buffer'.ToByteArray()
    read_size = is_.Read(buffer_, 0, 6)
    assert read_size == 6 and bytes(buffer_) == b'bcdefg'
    assert is_.Position == 7
    assert len(is_.buffer) == 1, 'is_.buffer = ' + repr(is_.buffer)
    read_size = is_.Read(buffer_, 1, 5)
    assert read_size == 5 and bytes(buffer_) == b'bhijkl'
    assert is_.Position == 12
    assert len(is_.buffer) == 0, 'is_.buffer = ' + repr(is_.buffer)
    read_size = is_.Read(buffer_, 0, 6)
    assert read_size == 3 and bytes(buffer_) == b'mnojkl'
    assert is_.Position == 15
    assert len(is_.buffer) == 0, 'is_.buffer = ' + repr(is_.buffer)
