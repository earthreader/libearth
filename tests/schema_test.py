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


@fixture
def fx_doc():
    xml = text('''
        <test>
            <title>Title test</title>
            <multi>a</multi>
            <content>Content test</content>
            <multi>b</multi>
            <multi>c</multi>
        </test>
    ''')
    return TestDoc(xml)


def test_document_parse(fx_doc):
    assert fx_doc.title.value == 'Title test'
    assert fx_doc.content.value == 'Content test'
    assert isinstance(fx_doc.multi, collections.Sequence)


def test_multiple_child_iter(fx_doc):
    it = iter(fx_doc.multi)
    assert next(it).value == 'a'
    assert next(it).value == 'b'
    assert next(it).value == 'c'
    with raises(StopIteration):
        next(it)


def test_multiple_child_len(fx_doc):
    assert len(fx_doc.multi) == 3


def test_multiple_child_getitem(fx_doc):
    fx_doc.multi[0].value == 'a'
    fx_doc.multi[1].value == 'b'
    fx_doc.multi[2].value == 'c'


def test_multiple_child_getitem_from_last(fx_doc):
    fx_doc.multi[2].value == 'c'
    fx_doc.multi[1].value == 'b'
    fx_doc.multi[0].value == 'a'
