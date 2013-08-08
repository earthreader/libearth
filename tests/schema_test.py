import collections

from pytest import fixture, mark, raises

from libearth.compat import text
from libearth.schema import (Attribute, Child, Content, DocumentElement,
                             Element, Text, read, index_descriptors,
                             inspect_attributes, inspect_child_tags,
                             inspect_content_tag)


class TextElement(Element):

    ns_attr_attr = Attribute('ns-attr', xmlns='http://earthreader.github.io/')
    value = Content()


class TextDecoderElement(Element):

    value = Content(decoder=lambda s: s.upper())


class TestDoc(DocumentElement):

    __tag__ = 'test'
    attr_attr = Attribute('attr')
    attr_decoder = Attribute('attr-decoder', decoder=lambda s: s.lower())
    attr_decoder_decorator = Attribute('attr-decoder-decorator')
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
    content_decoder = Child('content-decoder', TextDecoderElement)

    @attr_decoder_decorator.decoder
    def attr_decoder_decorator(self, value):
        return value[::-1]

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
        '<test attr="attribute value" attr-decoder="Decoder Test">',
        ['TEST_START'], '\n',
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
        '\t', '<content-decoder>', 'content decoder', '</content-decoder>', '\n'
        '</test>', ['TEST_CLOSE'], '\n'
    )
    return read(TestDoc, xml), consume_log


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


def test_attribute_decoder(fx_test_doc):
    doc, consume_log = fx_test_doc
    assert doc.attr_decoder == 'decoder test'
    assert consume_log[-1] == 'TEST_START'


def test_content_decoder(fx_test_doc):
    doc, consume_log = fx_test_doc
    assert doc.content_decoder.value == 'CONTENT DECODER'


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
    assert doc.multi_attr[0].value == 'a'
    assert consume_log[-1] == 'MULTI_1_CLOSE'
    assert doc.multi_attr[1].value == 'b'
    assert consume_log[-1] == 'MULTI_2_CLOSE'
    assert doc.multi_attr[2].value == 'c'
    assert consume_log[-1] == 'MULTI_3_CLOSE'


def test_multiple_child_getitem_from_last(fx_test_doc):
    doc, consume_log = fx_test_doc
    assert consume_log[-1] == 'TEST_START'
    assert doc.multi_attr[2].value == 'c'
    assert consume_log[-1] == 'MULTI_3_CLOSE'
    assert doc.multi_attr[1].value == 'b'
    assert consume_log[-1] == 'MULTI_3_CLOSE'
    assert doc.multi_attr[0].value == 'a'
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
    assert doc.text_multi_attr[0] == 'a'
    assert consume_log[-1] == 'TEXT_MULTI_1_CLOSE'
    assert doc.text_multi_attr[1] == 'b'
    assert consume_log[-1] == 'TEXT_MULTI_2_CLOSE'


def test_multiple_text_getitem_from_last(fx_test_doc):
    doc, consume_log = fx_test_doc
    assert consume_log[-1] == 'TEST_START'
    assert doc.text_multi_attr[1] == 'b'
    assert consume_log[-1] == 'TEXT_MULTI_2_CLOSE'
    assert doc.text_multi_attr[0] == 'a'
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
    return read(XmlnsDoc, '''
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


@fixture
def fx_adhoc_element_type():

    class AdhocTextElement(Element):
        value = Content()

    class AdhocElement(Element):
        format_version = Attribute('version')
        name = Text('name-e')
        url = Child('url-e', AdhocTextElement, multiple=True)
        dob = Child('dob-e', AdhocTextElement, xmlns='http://example.com/')
    return AdhocElement, AdhocTextElement


def test_index_descriptors(fx_adhoc_element_type):
    AdhocElement, AdhocTextElement = fx_adhoc_element_type
    assert not hasattr(AdhocElement, '__child_tags__')
    assert not hasattr(AdhocElement, '__attributes__')
    assert not hasattr(AdhocElement, '__content_tag__')
    index_descriptors(AdhocElement)
    assert len(AdhocElement.__child_tags__) == 3
    assert len(AdhocElement.__attributes__) == 1
    assert not AdhocElement.__content_tag__
    assert not hasattr(AdhocTextElement, '__child_tags__')
    assert not hasattr(AdhocTextElement, '__attributes__')
    assert not hasattr(AdhocTextElement, '__content_tag__')
    index_descriptors(AdhocTextElement)
    assert AdhocTextElement.__content_tag__


def test_inspect_attributes(fx_adhoc_element_type):
    element_type, _ = fx_adhoc_element_type
    attrs = inspect_attributes(element_type)
    assert len(attrs) == 1
    assert attrs[None, 'version'] == ('format_version',
                                      element_type.format_version)


def test_inspect_child_tags(fx_adhoc_element_type):
    element_type, _ = fx_adhoc_element_type
    child_tags = inspect_child_tags(element_type)
    assert len(child_tags) == 3
    assert child_tags[None, 'name-e'] == ('name', element_type.name)
    assert child_tags[None, 'url-e'] == ('url', element_type.url)
    assert child_tags['http://example.com/', 'dob-e'] == ('dob',
                                                          element_type.dob)


def test_inspect_content_tag(fx_adhoc_element_type):
    _, element_type = fx_adhoc_element_type
    content_tag = inspect_content_tag(element_type)
    assert content_tag == ('value', element_type.value)
