# -*- coding: utf-8 -*-
import collections
import xml.etree.ElementTree

from pytest import fixture, mark, raises

from libearth.compat import text, text_type
from libearth.schema import (Attribute, Child, Content, DescriptorConflictError,
                             DocumentElement,
                             Element, Text, read, index_descriptors,
                             inspect_attributes, inspect_child_tags,
                             inspect_content_tag, inspect_xmlns_set, write)


def u(text):
    if isinstance(text, text_type):
        return text
    return text.decode('utf-8')


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
    text_combined_decoder = Text('text-combined-decoder',
                                 decoder=int, encoder=lambda i: i and i / 100)
    ns_element_attr = Child('ns-element', TextElement,
                            xmlns='http://earthreader.github.io/')
    ns_text_attr = Text('ns-text', xmlns='http://earthreader.github.io/')
    content_decoder = Child('content-decoder', TextDecoderElement)

    @attr_decoder_decorator.decoder
    def attr_decoder_decorator(self, value):
        return value[::-1]

    @attr_decoder_decorator.encoder
    def attr_decoder_decorator(self, value):
        return value and value[::-1]

    @text_decoder_decorator.decoder
    def text_decoder_decorator(self, text):
        return int(text[::-1])

    @text_decoder_decorator.encoder
    def text_decoder_decorator(self, value):
        if value is not None:
            return str(value)[::-1]

    @text_combined_decoder.decoder
    def text_combined_decoder(self, value):
        return value * 100

    @text_combined_decoder.decoder
    def text_combined_decoder(self, value):
        return -value

    @text_combined_decoder.encoder
    def text_combined_decoder(self, value):
        if value is not None:
            return -value

    @text_combined_decoder.encoder
    def text_combined_decoder(self, value):
        if value is not None:
            if value % 1 <= 0:
                value = int(value)
            return str(value)


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
        '<test attr="속성 값" attr-decoder="Decoder Test">',
        ['TEST_START'], '\n',
        '\t', '<title>', '제목 ', 'test', '</title>', ['TITLE_CLOSE'], '\n',
        '\t', '<multi>', 'a', '</multi>', ['MULTI_1_CLOSE'], '\n',
        '\t', '<content>', 'Content', ' test',
        '</content>', ['CONTENT_CLOSE'], '\n',
        '\t', '<multi>', 'b', '</multi>', ['MULTI_2_CLOSE'], '\n',
        '\t', '<text-content>', '텍스트 ', '내용',
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
    assert doc.title_attr.value == u('제목 test')
    assert consume_log[-1] == 'TITLE_CLOSE'
    assert doc.content_attr.value == 'Content test'
    assert consume_log[-1] == 'CONTENT_CLOSE'
    assert isinstance(doc.multi_attr, collections.Sequence)


def test_attribute(fx_test_doc):
    doc, consume_log = fx_test_doc
    assert doc.attr_attr == u('속성 값')
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
    assert doc.text_content_attr == u('텍스트 내용')
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


def test_element_list_repr(fx_test_doc):
    doc, consume_log = fx_test_doc
    elist = doc.text_multi_attr
    assert repr(elist) == '<libearth.schema.ElementList [...]>'
    it = iter(elist)
    next(it)
    assert (repr(elist) ==
            "<libearth.schema.ElementList [{0!r}, ...]>".format(text_type('a')))
    next(it)
    assert (
        repr(elist) ==
        "<libearth.schema.ElementList [{0!r}, {1!r}, ...]>".format(
            text_type('a'),
            text_type('b')
        )
    )
    next(it, None)
    assert (
        repr(elist) ==
        "<libearth.schema.ElementList [{0!r}, {1!r}]>".format(
            text_type('a'),
            text_type('b')
        )
    )


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
    assert not hasattr(AdhocTextElement, '__xmlns_set__')
    assert not hasattr(AdhocTextElement, '__child_tags__')
    assert not hasattr(AdhocTextElement, '__attributes__')
    assert not hasattr(AdhocTextElement, '__content_tag__')
    index_descriptors(AdhocTextElement)
    assert AdhocTextElement.__content_tag__
    assert not hasattr(AdhocElement, '__xmlns_set__')
    assert not hasattr(AdhocElement, '__child_tags__')
    assert not hasattr(AdhocElement, '__attributes__')
    assert not hasattr(AdhocElement, '__content_tag__')
    index_descriptors(AdhocElement)
    assert len(AdhocElement.__xmlns_set__) == 1
    assert len(AdhocElement.__child_tags__) == 3
    assert len(AdhocElement.__attributes__) == 1
    assert not AdhocElement.__content_tag__


class InspectXmlnsSetElement(Element):

    a = Child('child', XmlnsDoc, xmlns='http://dahlia.kr/')


def test_inspect_xmlns_set(fx_adhoc_element_type):
    element_type, text_element_type = fx_adhoc_element_type
    assert inspect_xmlns_set(element_type) == set(['http://example.com/'])
    assert not inspect_xmlns_set(text_element_type)
    assert inspect_xmlns_set(TestDoc) == frozenset([
        'http://earthreader.github.io/'
    ])
    assert inspect_xmlns_set(TextElement) == frozenset([
        'http://earthreader.github.io/'
    ])
    assert inspect_xmlns_set(XmlnsDoc) == frozenset([
        'https://github.com/earthreader/libearth',
        'http://earthreader.github.io/'
    ])
    assert inspect_xmlns_set(InspectXmlnsSetElement) == frozenset([
        'https://github.com/earthreader/libearth',
        'http://earthreader.github.io/',
        'http://dahlia.kr/'
    ])


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


class ContentDescriptorConflictElement(Element):

    value = Content()
    value2 = Content()


def test_content_descriptor_conflict():
    with raises(DescriptorConflictError):
        index_descriptors(ContentDescriptorConflictElement)


class ChildDescriptorConflictElement(Element):

    child = Child('same-tag', TextElement)
    text = Text('same-tag')


def test_child_descriptor_conflict():
    with raises(DescriptorConflictError):
        index_descriptors(ChildDescriptorConflictElement)


class AttrDescriptorConflictElement(Element):

    attr = Attribute('same-attr')
    attr2 = Attribute('same-attr')


def test_attribute_descriptor_conflict():
    with raises(DescriptorConflictError):
        index_descriptors(AttrDescriptorConflictElement)


def test_write_test_doc(fx_test_doc):
    doc, _ = fx_test_doc
    g = write(doc, indent='    ', canonical_order=True)
    assert ''.join(g) == '''\
<?xml version="1.0" encoding="utf-8"?>
<test xmlns:ns0="http://earthreader.github.io/"\
 attr="속성 값" attr-decoder="decoder test">
    <content>Content test</content>
    <content-decoder>CONTENT DECODER</content-decoder>
    <multi>a</multi>
    <multi>b</multi>
    <multi>c</multi>
    <ns0:ns-element ns0:ns-attr="namespace attribute value">\
Namespace test</ns0:ns-element>
    <ns0:ns-text>Namespace test</ns0:ns-text>
    <text-combined-decoder>1234</text-combined-decoder>
    <text-content>텍스트 내용</text-content>
    <text-decoder>123.456</text-decoder>
    <text-decoder-decorator>123</text-decoder-decorator>
    <text-multi>a</text-multi>
    <text-multi>b</text-multi>
    <title>제목 test</title>
</test>'''


def etree_fromstringlist(iterable):
    if hasattr(xml.etree.ElementTree, 'fromstringlist'):
        return xml.etree.ElementTree.fromstringlist(iterable)
    return xml.etree.ElementTree.fromstring(''.join(iterable))


def test_write_test_doc_tree(fx_test_doc):
    doc, _ = fx_test_doc
    g = write(doc, canonical_order=True)
    tree = etree_fromstringlist(g)
    assert tree.tag == 'test'
    assert tree.attrib == {
        'attr': u('속성 값'),
        'attr-decoder': 'decoder test'
    }
    assert tree[0].tag == 'content'
    assert tree[0].text == 'Content test'
    assert not tree[0].attrib
    assert tree[1].tag == 'content-decoder'
    assert tree[1].text == 'CONTENT DECODER'
    assert not tree[1].attrib
    assert tree[2].tag == tree[3].tag == tree[4].tag == 'multi'
    assert tree[2].attrib == tree[3].attrib == tree[4].attrib == {}
    assert tree[2].text == 'a'
    assert tree[3].text == 'b'
    assert tree[4].text == 'c'
    assert tree[5].tag == '{http://earthreader.github.io/}ns-element'
    assert tree[5].attrib == {
        '{http://earthreader.github.io/}ns-attr': 'namespace attribute value'
    }
    assert tree[5].text == 'Namespace test'
    assert tree[6].tag == '{http://earthreader.github.io/}ns-text'
    assert not tree[6].attrib
    assert tree[6].text == 'Namespace test'
    assert tree[7].tag == 'text-combined-decoder'
    assert not tree[7].attrib
    assert tree[7].text == '1234'
    assert tree[8].tag == 'text-content'
    assert not tree[8].attrib
    assert tree[8].text == u('텍스트 내용')
    assert tree[9].tag == 'text-decoder'
    assert not tree[9].attrib
    assert tree[9].text == '123.456'
    assert tree[10].tag == 'text-decoder-decorator'
    assert not tree[10].attrib
    assert tree[10].text == '123'
    assert tree[11].tag == tree[12].tag == 'text-multi'
    assert tree[11].attrib == tree[12].attrib == {}
    assert tree[11].text == 'a'
    assert tree[12].text == 'b'
    assert tree[13].tag == 'title'
    assert not tree[13].attrib
    assert tree[13].text == u('제목 test')
    assert len(tree) == 14


def test_write_xmlns_doc(fx_xmlns_doc):
    doc = fx_xmlns_doc
    g = write(doc, indent='    ', canonical_order=True)
    assert ''.join(g) == text_type('''\
<?xml version="1.0" encoding="utf-8"?>
<ns0:nstest xmlns:ns0="http://earthreader.github.io/"\
 xmlns:ns1="https://github.com/earthreader/libearth">
    <ns1:otherns>Other namespace</ns1:otherns>
    <ns0:samens>Same namespace</ns0:samens>
</ns0:nstest>''')


def test_mutate_element_before_read(fx_test_doc):
    doc, consume_log = fx_test_doc
    assert consume_log[-1] == 'TEST_START'
    doc.text_content_attr = u('바뀐 텍스트 내용')
    assert consume_log[-1] == 'TEST_START'
    assert doc.text_content_attr == u('바뀐 텍스트 내용')
    assert consume_log[-1] == 'TEST_START'
    assert doc.text_multi_attr[0] == 'a'
    assert consume_log[-1] == 'TEXT_MULTI_1_CLOSE'
    assert doc.text_content_attr == u('바뀐 텍스트 내용')
    assert consume_log[-1] == 'TEXT_MULTI_1_CLOSE'


def test_element_initialize():
    doc = TestDoc(title_attr=TextElement(value='Title test'),
                  content_attr=TextElement(value=u('내용 테스트')),
                  attr_attr='Attribute value',
                  text_content_attr='Text content',
                  multi_attr=(TextElement(value='a'), TextElement(value='b')))
    assert doc.title_attr.value == 'Title test'
    assert doc.content_attr.value == u('내용 테스트')
    assert doc.attr_attr == 'Attribute value'
    assert doc.text_content_attr == 'Text content'
    assert len(doc.multi_attr) == 2
    assert doc.multi_attr[0].value == 'a'
    assert doc.multi_attr[1].value == 'b'
    doc.multi_attr.append(TextElement(value='c'))
    assert doc.multi_attr[2].value == 'c'
    assert len(doc.multi_attr) == 3
    tree = etree_fromstringlist(write(doc))
    assert tree.find('title').text == 'Title test'
    assert tree.find('content').text == u('내용 테스트')
    assert tree.attrib['attr'] == 'Attribute value'
    elements = tree.findall('multi')
    assert len(elements) == 3
    assert elements[0].text == 'a'
    assert elements[1].text == 'b'
    assert elements[2].text == 'c'


def test_mutate_element_list():
    doc = TestDoc()
    assert not doc.multi_attr
    assert len(doc.multi_attr) == 0
    with raises(IndexError):
        doc.multi_attr[0]
    doc.multi_attr.append(TextElement(value='First element'))
    assert doc.multi_attr
    assert doc.multi_attr[0].value == 'First element'
    assert len(doc.multi_attr) == 1
    doc.multi_attr.insert(1, TextElement(value='Second element'))
    assert doc.multi_attr[1].value == 'Second element'
    assert len(doc.multi_attr) == 2
    tree = etree_fromstringlist(write(doc))
    elements = tree.findall('multi')
    assert len(elements) == 2
    assert elements[0].text == 'First element'
    assert elements[1].text == 'Second element'
    doc.multi_attr[0] = TextElement(value='Replacing element')
    assert doc.multi_attr[0].value == 'Replacing element'
    assert len(doc.multi_attr) == 2
    tree = etree_fromstringlist(write(doc))
    elements = tree.findall('multi')
    assert len(elements) == 2
    assert elements[0].text == 'Replacing element'
    assert elements[1].text == 'Second element'
    del doc.multi_attr[0]
    assert doc.multi_attr[0].value == 'Second element'
    assert len(doc.multi_attr) == 1
    tree = etree_fromstringlist(write(doc))
    elements = tree.findall('multi')
    assert len(elements) == 1
    assert elements[0].text == 'Second element'


def test_mutate_read_element_list(fx_test_doc):
    doc, _ = fx_test_doc
    doc.multi_attr.insert(2, TextElement(value='inserted'))
    assert doc.multi_attr[0].value == 'a'
    assert doc.multi_attr[1].value == 'b'
    assert doc.multi_attr[2].value == 'inserted'
    assert doc.multi_attr[3].value == 'c'
    assert len(doc.multi_attr) == 4
    tree = etree_fromstringlist(write(doc))
    elements = tree.findall('multi')
    assert len(elements) == 4
    assert elements[0].text == 'a'
    assert elements[1].text == 'b'
    assert elements[2].text == 'inserted'
    assert elements[3].text == 'c'


@mark.parametrize('index', [1, -2])
def test_element_list_getslice(index, fx_test_doc):
    doc, _ = fx_test_doc
    sliced = doc.multi_attr[index:]
    assert len(sliced) == 2
    assert sliced[0].value == 'b'
    assert sliced[1].value == 'c'


@mark.parametrize('index', [2, -1])
def test_element_list_setslice(index, fx_test_doc):
    doc, _ = fx_test_doc
    doc.multi_attr[index:2] = [
        TextElement(value='inserted a'),
        TextElement(value='inserted b')
    ]
    assert doc.multi_attr[0].value == 'a'
    assert doc.multi_attr[1].value == 'b'
    assert doc.multi_attr[2].value == 'inserted a'
    assert doc.multi_attr[3].value == 'inserted b'
    assert doc.multi_attr[4].value == 'c'
    assert len(doc.multi_attr) == 5


@mark.parametrize('index', [2, -1])
def test_element_list_delslice(index, fx_test_doc):
    doc, _ = fx_test_doc
    doc.multi_attr[index:] = []
    assert doc.multi_attr[0].value == 'a'
    assert doc.multi_attr[1].value == 'b'
    assert len(doc.multi_attr) == 2
