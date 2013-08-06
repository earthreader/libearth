import collections

from pytest import fixture, mark, raises

from libearth.compat import text
from libearth.schema import (Attribute, Child, Content, DocumentElement,
                             Element, Text)


class TextElement(Element):

    ns_attr_attr = Attribute('ns-attr', xmlns='http://earthreader.github.io/')
    value = Content()


class TestDoc(DocumentElement):

    __tag__ = 'test'
    attr_attr = Attribute('attr')
    title_attr = Child('title', TextElement, required=True)
    content_attr = Child('content', TextElement, required=True)
    multi_attr = Child('multi', TextElement, multiple=True)
    text_content_attr = Text('text-content')
    text_multi_attr = Text('text-multi', multiple=True)
    text_decoder = Text('text-decoder', decoder=float)
    text_decoder_decorator = Text('text-decoder-decorator')
    text_combined_decoder = Text('text-combined-decoder', decoder=int)
    ns_element_attr = Child('ns-element', TextElement,
                            xmlns='http://earthreader.github.io/')
    ns_text_attr = Text('ns-text', xmlns='http://earthreader.github.io/')

    @text_decoder_decorator.decoder
    def text_decoder_decorator(self, text):
        return int(text[::-1])

    @text_combined_decoder.decoder
    def text_combined_decoder(self, value):
        return value * 100

    @text_combined_decoder.decoder
    def text_combined_decoder(self, value):
        return -value


def string_chunks(consume_log, *chunks):
    """Iterate the given chunks of a text with logging consumed offsets
    to test laziness of the parser.  If an argument is a list (that consists
    of a string) it's treated as offset tagging.

    """
    size = len(chunks)
    for i, chunk in enumerate(chunks):
        if type(chunk) is list:
            continue
        chunk = text(chunk)
        if size > i + 1 and type(chunks[i + 1]) is list:
            consume_log.append(chunks[i + 1][0])
        yield chunk


@fixture
def fx_test_doc():
    consume_log = []
    xml = string_chunks(
        consume_log,
        '<test attr="attribute value">', ['TEST_START'], '\n',
        '\t', '<title>', 'Title ', 'test', '</title>', ['TITLE_CLOSE'], '\n',
        '\t', '<multi>', 'a', '</multi>', ['MULTI_1_CLOSE'], '\n',
        '\t', '<content>', 'Content', ' test',
        '</content>', ['CONTENT_CLOSE'], '\n',
        '\t', '<multi>', 'b', '</multi>', ['MULTI_2_CLOSE'], '\n',
        '\t', '<text-content>', 'Text ', 'content',
        '</text-content>', ['TEXT_CONTENT_CLOSE'], '\n',
        '\t', '<text-multi>', 'a', '</text-multi>',
        ['TEXT_MULTI_1_CLOSE'], '\n',
        '\t', '<multi>', 'c', '</multi>', ['MULTI_3_CLOSE'], '\n',
        '\t', '<text-multi>', 'b', '</text-multi>',
        ['TEXT_MULTI_2_CLOSE'], '\n',
        '\t', '<text-decoder>', '123.456', '</text-decoder>', '\n',
        '\t', '<text-decoder-decorator>', '123',
        '</text-decoder-decorator>', '\n',
        '\t', '<text-combined-decoder>', '1234',
        '</text-combined-decoder>', '\n',
        '\t', '<nst:ns-element xmlns:nst="http://earthreader.github.io/" ',
        'nst:ns-attr="namespace attribute value">', ['NS_ELEMENT_START'],
        'Namespace test', '</nst:ns-element>', '\n',
        '\t', '<nst2:ns-text xmlns:nst2="http://earthreader.github.io/">',
        'Namespace test', '</nst2:ns-text>', '\n',
        '</test>', ['TEST_CLOSE'], '\n'
    )
    return TestDoc(xml), consume_log


def test_document_parse(fx_test_doc):
    doc, consume_log = fx_test_doc
    assert consume_log[-1] == 'TEST_START'
    assert doc.title_attr.value == 'Title test'
    assert consume_log[-1] == 'TITLE_CLOSE'
    assert doc.content_attr.value == 'Content test'
    assert consume_log[-1] == 'CONTENT_CLOSE'
    assert isinstance(doc.multi_attr, collections.Sequence)


def test_attribute(fx_test_doc):
    doc, consume_log = fx_test_doc
    assert doc.attr_attr == 'attribute value'
    assert consume_log[-1] == 'TEST_START'


def test_xmlns_attribute(fx_test_doc):
    doc, consume_log = fx_test_doc
    assert doc.ns_element_attr.ns_attr_attr == 'namespace attribute value'
    assert consume_log[-1] == 'NS_ELEMENT_START'


def test_multiple_child_iter(fx_test_doc):
    doc, consume_log = fx_test_doc
    it = iter(doc.multi_attr)
    assert consume_log[-1] == 'TEST_START'
    assert next(it).value == 'a'
    assert consume_log[-1] == 'MULTI_1_CLOSE'
    assert next(it).value == 'b'
    assert consume_log[-1] == 'MULTI_2_CLOSE'
    assert next(it).value == 'c'
    assert consume_log[-1] == 'MULTI_3_CLOSE'
    with raises(StopIteration):
        next(it)
    assert consume_log[-1] == 'TEST_CLOSE'


def test_multiple_child_len(fx_test_doc):
    doc, consume_log = fx_test_doc
    assert consume_log[-1] == 'TEST_START'
    assert len(doc.multi_attr) == 3
    assert consume_log[-1] == 'TEST_CLOSE'


def test_multiple_child_getitem(fx_test_doc):
    doc, consume_log = fx_test_doc
    assert consume_log[-1] == 'TEST_START'
    doc.multi_attr[0].value == 'a'
    assert consume_log[-1] == 'MULTI_1_CLOSE'
    doc.multi_attr[1].value == 'b'
    assert consume_log[-1] == 'MULTI_2_CLOSE'
    doc.multi_attr[2].value == 'c'
    assert consume_log[-1] == 'MULTI_3_CLOSE'


def test_multiple_child_getitem_from_last(fx_test_doc):
    doc, consume_log = fx_test_doc
    assert consume_log[-1] == 'TEST_START'
    doc.multi_attr[2].value == 'c'
    assert consume_log[-1] == 'MULTI_3_CLOSE'
    doc.multi_attr[1].value == 'b'
    assert consume_log[-1] == 'MULTI_3_CLOSE'
    doc.multi_attr[0].value == 'a'
    assert consume_log[-1] == 'MULTI_3_CLOSE'


def test_text_attribute(fx_test_doc):
    doc, consume_log = fx_test_doc
    assert consume_log[-1] == 'TEST_START'
    assert doc.text_content_attr == 'Text content'
    assert consume_log[-1] == 'TEXT_CONTENT_CLOSE'


def test_text_multiple_text_len(fx_test_doc):
    doc, consume_log = fx_test_doc
    assert consume_log[-1] == 'TEST_START'
    assert len(doc.text_multi_attr) == 2
    assert consume_log[-1] == 'TEST_CLOSE'


def test_multiple_text_getitem(fx_test_doc):
    doc, consume_log = fx_test_doc
    assert consume_log[-1] == 'TEST_START'
    doc.text_multi_attr[0] == 'a'
    assert consume_log[-1] == 'TEXT_MULTI_1_CLOSE'
    doc.text_multi_attr[1] == 'b'
    assert consume_log[-1] == 'TEXT_MULTI_2_CLOSE'


def test_multiple_text_getitem_from_last(fx_test_doc):
    doc, consume_log = fx_test_doc
    assert consume_log[-1] == 'TEST_START'
    doc.text_multi_attr[1] == 'b'
    assert consume_log[-1] == 'TEXT_MULTI_2_CLOSE'
    doc.text_multi_attr[0] == 'a'
    assert consume_log[-1] == 'TEXT_MULTI_2_CLOSE'


def test_document_element_tag():
    """If a subtype of DocumentElement doesn't define __tag__ attribute,
    it should raise error.

    """
    class DocumentElementWithoutTag(DocumentElement):
        pass
    with raises(NotImplementedError):
        DocumentElementWithoutTag([])


@mark.parametrize('tag', [123, ('t', 'a', 'g'), ['t', 'a', 'g'], {'ta': 'g'}])
def test_document_element_tag_type(tag):
    """__tag__ has to be a string."""
    class DocumentElementWithNonstringTag(DocumentElement):
        __tag__ = tag
    with raises(TypeError):
        DocumentElementWithNonstringTag([])


def test_text_decoder(fx_test_doc):
    doc, _ = fx_test_doc
    assert doc.text_decoder == 123.456


def test_text_decoder_decorator(fx_test_doc):
    doc, _ = fx_test_doc
    assert doc.text_decoder_decorator == 321


def test_text_combined_decoder(fx_test_doc):
    doc, _ = fx_test_doc
    assert doc.text_combined_decoder == -123400


def test_xmlns_element(fx_test_doc):
    doc, _ = fx_test_doc
    assert doc.ns_element_attr.value == 'Namespace test'


def test_xmlns_text(fx_test_doc):
    doc, _ = fx_test_doc
    assert doc.ns_text_attr == 'Namespace test'


class XmlnsDoc(DocumentElement):

    __tag__ = 'nstest'
    __xmlns__ = 'http://earthreader.github.io/'
    samens_attr = Text('samens', xmlns=__xmlns__)
    otherns_attr = Text('otherns',
                        xmlns='https://github.com/earthreader/libearth')


@fixture
def fx_xmlns_doc():
    return XmlnsDoc('''
        <nstest xmlns="http://earthreader.github.io/"
                xmlns:nst="https://github.com/earthreader/libearth">
            <samens>Same namespace</samens>
            <nst:otherns>Other namespace</nst:otherns>
        </nstest>
    ''')


def test_xmlns_doc(fx_xmlns_doc):
    assert fx_xmlns_doc.samens_attr is not None
    assert fx_xmlns_doc.otherns_attr is not None


def test_xmlns_same_xmlns_child(fx_xmlns_doc):
    assert fx_xmlns_doc.samens_attr == 'Same namespace'


def test_xmlns_other_xmlns_child(fx_xmlns_doc):
    assert fx_xmlns_doc.otherns_attr == 'Other namespace'
