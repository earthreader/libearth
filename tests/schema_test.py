import collections

from pytest import fixture, raises

from libearth.compat import text
from libearth.schema import Child, Content, DocumentElement, Element


class Text(Element):

    value = Content()


class TestDoc(DocumentElement):

    __tag__ = 'test'
    title = Child('title', Text, required=True)
    content = Child('content', Text, required=True)
    multi = Child('multi', Text, multiple=True)


def string_chunks(consume_log, *chunks):
    """Iterate the given chunks of a text with logging consumed offsets
    to test laziness of the parser.

    """
    for i, chunk in enumerate(chunks):
        chunk = text(chunk)
        consume_log.append((i + 1, chunk))
        yield chunk


@fixture
def fx_test_doc():
    consume_log = []
    xml = string_chunks(
        consume_log,
        '<test>', '\n',
        '\t', '<title>', 'Title ', 'test', '</title>', '\n',
        '\t', '<multi>', 'a', '</multi>', '\n',
        '\t', '<content>', 'Content', ' test', '</content>', '\n',
        '\t', '<multi>', 'b', '</multi>', '\n',
        '\t', '<multi>', 'c', '</multi>', '\n',
        '</test>', '\n'
    )
    return TestDoc(xml), consume_log


def test_document_parse(fx_test_doc):
    doc, consume_log = fx_test_doc
    assert consume_log[-1][0] == 1
    assert doc.title.value == 'Title test'
    assert consume_log[-1][0] == 7
    assert doc.content.value == 'Content test'
    assert consume_log[-1][0] == 18
    assert isinstance(doc.multi, collections.Sequence)


def test_multiple_child_iter(fx_test_doc):
    doc, consume_log = fx_test_doc
    it = iter(doc.multi)
    assert consume_log[-1][0] == 1
    assert next(it).value == 'a'
    assert consume_log[-1][0] == 12
    assert next(it).value == 'b'
    assert consume_log[-1][0] == 23
    assert next(it).value == 'c'
    assert consume_log[-1][0] == 28
    with raises(StopIteration):
        next(it)
    assert consume_log[-1][0] == 30


def test_multiple_child_len(fx_test_doc):
    doc, consume_log = fx_test_doc
    assert consume_log[-1][0] == 1
    assert len(doc.multi) == 3
    assert consume_log[-1][0] == 30


def test_multiple_child_getitem(fx_test_doc):
    doc, consume_log = fx_test_doc
    assert consume_log[-1][0] == 1
    doc.multi[0].value == 'a'
    assert consume_log[-1][0] == 12
    doc.multi[1].value == 'b'
    assert consume_log[-1][0] == 23
    doc.multi[2].value == 'c'
    assert consume_log[-1][0] == 28


def test_multiple_child_getitem_from_last(fx_test_doc):
    doc, consume_log = fx_test_doc
    assert consume_log[-1][0] == 1
    doc.multi[2].value == 'c'
    assert consume_log[-1][0] == 28
    doc.multi[1].value == 'b'
    assert consume_log[-1][0] == 28
    doc.multi[0].value == 'a'
    assert consume_log[-1][0] == 28
