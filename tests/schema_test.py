# -*- coding: utf-8 -*-
import collections

from pytest import fixture, mark, raises

from libearth.codecs import Integer
from libearth.compat import (IRON_PYTHON, binary_type, text, text_type,
                             string_type)
from libearth.compat.etree import fromstringlist, tostring
from libearth.parser.rss2 import parse_rss
from libearth.schema import (SCHEMA_XMLNS,
                             Attribute, Child, Codec, Content,
                             DescriptorConflictError, DocumentElement,
                             Element, ElementList, EncodeError, IntegrityError,
                             Text,
                             complete, element_list_for, index_descriptors,
                             inspect_attributes, inspect_child_tags,
                             inspect_content_tag, inspect_xmlns_set,
                             is_partially_loaded, read, validate, write)
from libearth.subscribe import SubscriptionList


def u(text):
    if isinstance(text, text_type):
        return text
    return text.decode('utf-8')


class TextElement(Element):

    ns_attr_attr = Attribute('ns-attr', xmlns='http://earthreader.github.io/')
    value = Content()

    @classmethod
    def __coerce_from__(cls, value):
        if isinstance(value, string_type):
            return TextElement(value=value)
        raise TypeError


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
    sorted_children = Child('s-multi', TextElement,
                            multiple=True, sort_key=lambda e: e.value)
    text_content_attr = Text('text-content')
    text_multi_attr = Text('text-multi', multiple=True)
    sorted_texts = Text('s-text-multi',
                        multiple=True, sort_key=lambda t: t, sort_reverse=True)
    text_decoder = Text('text-decoder', decoder=float, encoder=str)
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
        if not isinstance(chunk, binary_type):
            # In IronPython str.encode() returns str instead of bytes,
            # and bytes(str, encoding) returns bytes.
            chunk = binary_type(chunk, 'utf-8')
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
        '\t', '<s-multi>c</s-multi><s-multi>a</s-multi><s-multi>b</s-multi>\n',
        '\t', '<s-text-multi>c</s-text-multi>', '\n',
        '\t', '<s-text-multi>a</s-text-multi>', '\n',
        '\t', '<s-text-multi>b</s-text-multi>', '\n',
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
    assert consume_log[-1] == 'TEST_START' or IRON_PYTHON
    assert is_partially_loaded(doc) or IRON_PYTHON
    assert doc.title_attr.value == u('제목 test')
    assert consume_log[-1] == 'TITLE_CLOSE' or IRON_PYTHON
    assert is_partially_loaded(doc) or IRON_PYTHON
    assert doc.content_attr.value == 'Content test'
    assert consume_log[-1] == 'CONTENT_CLOSE' or IRON_PYTHON
    assert is_partially_loaded(doc) or IRON_PYTHON
    assert isinstance(doc.multi_attr, collections.Sequence)


def test_attribute(fx_test_doc):
    doc, consume_log = fx_test_doc
    assert doc.attr_attr == u('속성 값')
    assert consume_log[-1] == 'TEST_START' or IRON_PYTHON
    assert is_partially_loaded(doc) or IRON_PYTHON


def test_xmlns_attribute(fx_test_doc):
    doc, consume_log = fx_test_doc
    assert doc.ns_element_attr.ns_attr_attr == 'namespace attribute value'
    assert consume_log[-1] == 'NS_ELEMENT_START' or IRON_PYTHON
    assert is_partially_loaded(doc) or IRON_PYTHON


def test_attribute_decoder(fx_test_doc):
    doc, consume_log = fx_test_doc
    assert doc.attr_decoder == 'decoder test'
    assert consume_log[-1] == 'TEST_START' or IRON_PYTHON
    assert is_partially_loaded(doc) or IRON_PYTHON


def test_content_decoder(fx_test_doc):
    doc, consume_log = fx_test_doc
    assert doc.content_decoder.value == 'CONTENT DECODER'
    assert is_partially_loaded(doc) or IRON_PYTHON


def test_multiple_child_iter(fx_test_doc):
    doc, consume_log = fx_test_doc
    it = iter(doc.multi_attr)
    assert consume_log[-1] == 'TEST_START' or IRON_PYTHON
    assert is_partially_loaded(doc) or IRON_PYTHON
    el = next(it)
    assert el.value == 'a'
    assert consume_log[-1] == 'MULTI_1_CLOSE' or IRON_PYTHON
    assert is_partially_loaded(doc) or IRON_PYTHON
    assert not is_partially_loaded(el)
    el = next(it)
    assert el.value == 'b'
    assert consume_log[-1] == 'MULTI_2_CLOSE' or IRON_PYTHON
    assert is_partially_loaded(doc) or IRON_PYTHON
    assert not is_partially_loaded(el)
    el = next(it)
    assert el.value == 'c'
    assert consume_log[-1] == 'MULTI_3_CLOSE' or IRON_PYTHON
    assert is_partially_loaded(doc) or IRON_PYTHON
    assert not is_partially_loaded(el)
    with raises(StopIteration):
        next(it)
    assert consume_log[-1] == 'TEST_CLOSE'
    assert not is_partially_loaded(doc)


def test_multiple_child_len(fx_test_doc):
    doc, consume_log = fx_test_doc
    assert consume_log[-1] == 'TEST_START' or IRON_PYTHON
    assert is_partially_loaded(doc) or IRON_PYTHON
    assert len(doc.multi_attr) == 3
    assert consume_log[-1] == 'TEST_CLOSE'
    assert not is_partially_loaded(doc)


def test_multiple_child_getitem(fx_test_doc):
    doc, consume_log = fx_test_doc
    assert consume_log[-1] == 'TEST_START' or IRON_PYTHON
    assert is_partially_loaded(doc) or IRON_PYTHON
    assert doc.multi_attr[0].value == 'a'
    assert consume_log[-1] == 'MULTI_1_CLOSE' or IRON_PYTHON
    assert is_partially_loaded(doc) or IRON_PYTHON
    assert doc.multi_attr[1].value == 'b'
    assert consume_log[-1] == 'MULTI_2_CLOSE' or IRON_PYTHON
    assert is_partially_loaded(doc) or IRON_PYTHON
    assert doc.multi_attr[2].value == 'c'
    assert consume_log[-1] == 'MULTI_3_CLOSE' or IRON_PYTHON
    assert is_partially_loaded(doc) or IRON_PYTHON


def test_multiple_child_getitem_from_last(fx_test_doc):
    doc, consume_log = fx_test_doc
    assert consume_log[-1] == 'TEST_START' or IRON_PYTHON
    assert is_partially_loaded(doc) or IRON_PYTHON
    assert doc.multi_attr[2].value == 'c'
    assert consume_log[-1] == 'MULTI_3_CLOSE' or IRON_PYTHON
    assert is_partially_loaded(doc) or IRON_PYTHON
    assert doc.multi_attr[1].value == 'b'
    assert consume_log[-1] == 'MULTI_3_CLOSE' or IRON_PYTHON
    assert is_partially_loaded(doc) or IRON_PYTHON
    assert doc.multi_attr[0].value == 'a'
    assert consume_log[-1] == 'MULTI_3_CLOSE' or IRON_PYTHON
    assert is_partially_loaded(doc) or IRON_PYTHON


def test_text_attribute(fx_test_doc):
    doc, consume_log = fx_test_doc
    assert consume_log[-1] == 'TEST_START' or IRON_PYTHON
    assert is_partially_loaded(doc) or IRON_PYTHON
    assert doc.text_content_attr == u('텍스트 내용')
    assert consume_log[-1] == 'TEXT_CONTENT_CLOSE' or IRON_PYTHON
    assert is_partially_loaded(doc) or IRON_PYTHON


def test_text_multiple_text_len(fx_test_doc):
    doc, consume_log = fx_test_doc
    assert consume_log[-1] == 'TEST_START' or IRON_PYTHON
    assert is_partially_loaded(doc) or IRON_PYTHON
    assert len(doc.text_multi_attr) == 2
    assert consume_log[-1] == 'TEST_CLOSE'
    assert not is_partially_loaded(doc)


def test_multiple_text_getitem(fx_test_doc):
    doc, consume_log = fx_test_doc
    assert consume_log[-1] == 'TEST_START' or IRON_PYTHON
    assert is_partially_loaded(doc) or IRON_PYTHON
    assert doc.text_multi_attr[0] == 'a'
    assert consume_log[-1] == 'TEXT_MULTI_1_CLOSE' or IRON_PYTHON
    assert is_partially_loaded(doc) or IRON_PYTHON
    assert doc.text_multi_attr[1] == 'b'
    assert consume_log[-1] == 'TEXT_MULTI_2_CLOSE' or IRON_PYTHON
    assert is_partially_loaded(doc) or IRON_PYTHON


def test_multiple_text_getitem_from_last(fx_test_doc):
    doc, consume_log = fx_test_doc
    assert consume_log[-1] == 'TEST_START' or IRON_PYTHON
    assert is_partially_loaded(doc) or IRON_PYTHON
    assert doc.text_multi_attr[1] == 'b'
    assert consume_log[-1] == 'TEXT_MULTI_2_CLOSE' or IRON_PYTHON
    assert is_partially_loaded(doc) or IRON_PYTHON
    assert doc.text_multi_attr[0] == 'a'
    assert consume_log[-1] == 'TEXT_MULTI_2_CLOSE' or IRON_PYTHON
    assert is_partially_loaded(doc) or IRON_PYTHON


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


class SpecializedElementList(collections.Sequence):

    def test_extended_method(self):
        return len(self)


class AnotherElementList(collections.Sequence):

    pass


@fixture
def fx_sandboxed_specialized_types(request):
    initial_state = ElementList.specialized_types
    ElementList.specialized_types = {}

    @request.addfinalizer
    def rollback_to_initial_state():
        ElementList.specialized_types = initial_state


def test_element_list_register_specialized_type(fx_sandboxed_specialized_types,
                                                fx_test_doc):
    ElementList.register_specialized_type(TextElement, SpecializedElementList)
    doc, _ = fx_test_doc
    assert isinstance(doc.multi_attr, SpecializedElementList)
    assert doc.multi_attr.test_extended_method() == len(doc.multi_attr)
    # TypeError if try to register another specialized element list type for
    # the already registered element type
    with raises(TypeError):
        ElementList.register_specialized_type(TextElement, AnotherElementList)
    # Does nothing if the given specialized element list type is the same to
    # the previously registered element list type
    ElementList.register_specialized_type(TextElement, SpecializedElementList)


def test_element_list_for(fx_sandboxed_specialized_types, fx_test_doc):
    @element_list_for(TextElement)
    class Decorated(SpecializedElementList):
        pass
    doc, _ = fx_test_doc
    assert isinstance(doc.multi_attr, Decorated)
    assert doc.multi_attr.test_extended_method() == len(doc.multi_attr)


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
    return read(XmlnsDoc, [b'''
        <nstest xmlns="http://earthreader.github.io/"
                xmlns:nst="https://github.com/earthreader/libearth">
            <samens>Same namespace</samens>
            <nst:otherns>Other namespace</nst:otherns>
        </nstest>
    '''])


def test_xmlns_doc(fx_xmlns_doc):
    assert fx_xmlns_doc.samens_attr is not None
    assert fx_xmlns_doc.otherns_attr is not None


def test_xmlns_same_xmlns_child(fx_xmlns_doc):
    assert fx_xmlns_doc.samens_attr == 'Same namespace'


def test_xmlns_other_xmlns_child(fx_xmlns_doc):
    assert fx_xmlns_doc.otherns_attr == 'Other namespace'


def test_complete(fx_test_doc):
    doc, _ = fx_test_doc
    assert is_partially_loaded(doc)
    complete(doc)
    assert not is_partially_loaded(doc)


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
    gf = lambda: write(doc, indent='    ', canonical_order=True, hints=False)
    print(''.join(gf()))
    assert ''.join(gf()) == '''\
<?xml version="1.0" encoding="utf-8"?>
<test xmlns:ns0="http://earthreader.github.io/"\
 attr="속성 값" attr-decoder="decoder test">
    <title>제목 test</title>
    <content>Content test</content>
    <multi>a</multi>
    <multi>b</multi>
    <multi>c</multi>
    <s-multi>a</s-multi>
    <s-multi>b</s-multi>
    <s-multi>c</s-multi>
    <text-content>텍스트 내용</text-content>
    <text-multi>a</text-multi>
    <text-multi>b</text-multi>
    <s-text-multi>c</s-text-multi>
    <s-text-multi>b</s-text-multi>
    <s-text-multi>a</s-text-multi>
    <text-decoder>123.456</text-decoder>
    <text-decoder-decorator>123</text-decoder-decorator>
    <text-combined-decoder>1234</text-combined-decoder>
    <ns0:ns-element ns0:ns-attr="namespace attribute value">\
Namespace test</ns0:ns-element>
    <ns0:ns-text>Namespace test</ns0:ns-text>
    <content-decoder>CONTENT DECODER</content-decoder>
</test>'''


def test_write_test_doc_tree(fx_test_doc):
    doc, _ = fx_test_doc
    g = write(doc, canonical_order=True)
    tree = fromstringlist(g)
    assert tree.tag == 'test'
    assert tree.attrib == {
        'attr': u('속성 값'),
        'attr-decoder': 'decoder test'
    }
    assert tree[0].tag == 'title'
    assert not tree[0].attrib
    assert tree[0].text == u('제목 test')
    assert tree[1].tag == 'content'
    assert tree[1].text == 'Content test'
    assert not tree[1].attrib
    assert tree[2].tag == tree[3].tag == tree[4].tag == 'multi'
    assert tree[2].attrib == tree[3].attrib == tree[4].attrib == {}
    assert tree[2].text == 'a'
    assert tree[3].text == 'b'
    assert tree[4].text == 'c'
    assert tree[5].tag == tree[6].tag == tree[7].tag == 's-multi'
    assert tree[5].attrib == tree[6].attrib == tree[7].attrib == {}
    assert tree[5].text == 'a'
    assert tree[6].text == 'b'
    assert tree[7].text == 'c'
    assert tree[8].tag == 'text-content'
    assert not tree[8].attrib
    assert tree[8].text == u('텍스트 내용')
    assert tree[9].tag == tree[10].tag == 'text-multi'
    assert tree[9].attrib == tree[10].attrib == {}
    assert tree[9].text == 'a'
    assert tree[10].text == 'b'
    assert tree[11].tag == tree[12].tag == tree[13].tag == 's-text-multi'
    assert tree[11].attrib == tree[12].attrib == tree[13].attrib == {}
    assert tree[11].text == 'c'
    assert tree[12].text == 'b'
    assert tree[13].text == 'a'
    assert tree[14].tag == 'text-decoder'
    assert not tree[14].attrib
    assert tree[14].text == '123.456'
    assert tree[15].tag == 'text-decoder-decorator'
    assert not tree[15].attrib
    assert tree[15].text == '123'
    assert tree[16].tag == 'text-combined-decoder'
    assert not tree[16].attrib
    assert tree[16].text == '1234'
    assert tree[17].tag == '{http://earthreader.github.io/}ns-element'
    assert tree[17].attrib == {
        '{http://earthreader.github.io/}ns-attr': 'namespace attribute value'
    }
    assert tree[17].text == 'Namespace test'
    assert tree[18].tag == '{http://earthreader.github.io/}ns-text'
    assert not tree[18].attrib
    assert tree[18].text == 'Namespace test'
    assert tree[19].tag == 'content-decoder'
    assert tree[19].text == 'CONTENT DECODER'
    assert not tree[19].attrib
    assert len(tree) == 20


def test_write_xmlns_doc(fx_xmlns_doc):
    doc = fx_xmlns_doc
    g = write(doc, indent='    ', canonical_order=True)
    assert ''.join(g) == text_type('''\
<?xml version="1.0" encoding="utf-8"?>
<ns0:nstest xmlns:ns0="http://earthreader.github.io/"\
 xmlns:libearth="http://earthreader.org/schema/"\
 xmlns:ns1="https://github.com/earthreader/libearth">
    <ns0:samens>Same namespace</ns0:samens>
    <ns1:otherns>Other namespace</ns1:otherns>
</ns0:nstest>''')


def test_mutate_element_before_read(fx_test_doc):
    doc, consume_log = fx_test_doc
    assert consume_log[-1] == 'TEST_START' or IRON_PYTHON
    doc.text_content_attr = u('바뀐 텍스트 내용')
    assert consume_log[-1] == 'TEST_START' or IRON_PYTHON
    assert doc.text_content_attr == u('바뀐 텍스트 내용')
    assert consume_log[-1] == 'TEST_START' or IRON_PYTHON
    assert doc.text_multi_attr[0] == 'a'
    assert consume_log[-1] == 'TEXT_MULTI_1_CLOSE' or IRON_PYTHON
    assert doc.text_content_attr == u('바뀐 텍스트 내용')
    assert consume_log[-1] == 'TEXT_MULTI_1_CLOSE' or IRON_PYTHON


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
    tree = fromstringlist(write(doc))
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
    tree = fromstringlist(write(doc, validate=False))
    elements = tree.findall('multi')
    assert len(elements) == 2
    assert elements[0].text == 'First element'
    assert elements[1].text == 'Second element'
    doc.multi_attr[0] = TextElement(value='Replacing element')
    assert doc.multi_attr[0].value == 'Replacing element'
    assert len(doc.multi_attr) == 2
    tree = fromstringlist(write(doc, validate=False))
    elements = tree.findall('multi')
    assert len(elements) == 2
    assert elements[0].text == 'Replacing element'
    assert elements[1].text == 'Second element'
    del doc.multi_attr[0]
    assert doc.multi_attr[0].value == 'Second element'
    assert len(doc.multi_attr) == 1
    tree = fromstringlist(write(doc, validate=False))
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
    tree = fromstringlist(write(doc))
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


class VTElement(Element):

    req_attr = Attribute('a', required=True)
    attr = Attribute('b')
    req_child = Child('c', TextElement, required=True)
    child = Child('d', TextElement)
    req_text = Text('e', required=True)
    text = Text('f')

    def __repr__(self):
        fmt = 'VTElement(req_attr={0!r}, req_child={1!r}, req_text={2!r})'
        return fmt.format(self.req_attr, self.req_child, self.req_text)


class VTDoc(DocumentElement):

    __tag__ = 'vtest'
    req_attr = Attribute('a', required=True)
    attr = Attribute('b')
    req_child = Child('c', VTElement, required=True)
    child = Child('d', VTElement)
    multi = Child('e', VTElement, multiple=True)
    req_text = Text('f', required=True)
    text = Text('g')

    def __repr__(self):
        fmt = 'VTDoc(req_attr={0!r}, req_child={1!r}, req_text={2!r})'
        return fmt.format(self.req_attr, self.req_child, self.req_text)


@mark.parametrize(('element', 'recur_valid', 'valid'), [
    (VTDoc(), False, False),
    (VTDoc(req_attr='a'), False, False),
    (VTDoc(req_child=VTElement()), False, False),
    (VTDoc(req_text='f'), False, False),
    (VTDoc(req_child=VTElement(req_attr='a')), False, False),
    (VTDoc(req_child=VTElement(req_child=TextElement(value='a'))),
     False, False),
    (VTDoc(req_child=VTElement(req_attr='a',
                               req_child=TextElement(value='a'))),
     False, False),
    (VTDoc(req_child=VTElement(req_attr='a',
                               req_child=TextElement(value='a'),
                               req_text='e')),
     False, False),
    (VTDoc(req_attr='a', req_child=VTElement(), req_text='f'), False, True),
    (VTDoc(req_attr='a', req_child=VTElement(), multi=[], req_text='f'),
     False, True),
    (VTDoc(req_attr='a', req_child=VTElement(), multi=[
        VTElement()
    ], req_text='f'), False, True),
    (VTDoc(req_attr='a', req_child=VTElement(), multi=[
        VTElement(req_attr='a', req_child=TextElement(value='a'))
    ], req_text='f'), False, True),
    (VTDoc(req_attr='a', req_child=VTElement(req_attr='a'), req_text='f'),
     False, True),
    (VTDoc(req_attr='a', req_child=VTElement(req_attr='a'),
           multi=[], req_text='f'), False, True),
    (VTDoc(req_attr='a',
           req_child=VTElement(req_child=TextElement(value='a')),
           multi=[], req_text='f'), False, True),
    (VTDoc(req_attr='a',
           req_child=VTElement(req_attr='a',
                               req_child=TextElement(value='a'),
                               req_text='e'),
           multi=[], req_text='f'), True, True),
    (VTDoc(req_attr='a',
           req_child=VTElement(req_attr='a',
                               req_child=TextElement(value='a'),
                               req_text='e'),
           multi=[VTElement()], req_text='f'), False, True),
    (VTDoc(req_attr='a',
           req_child=VTElement(req_attr='a',
                               req_child=TextElement(value='a'),
                               req_text='e'),
           multi=[VTElement(req_attr='a',
                            req_child=TextElement(value='a'),
                            req_text='e')],
           req_text='f'), True, True)
])
def test_validate_recurse(element, recur_valid, valid):
    assert validate(element, recurse=True, raise_error=False) is recur_valid
    try:
        validate(element, recurse=True, raise_error=True)
    except IntegrityError:
        assert not recur_valid
    else:
        assert recur_valid
    assert validate(element, recurse=False, raise_error=False) is valid
    try:
        validate(element, recurse=False, raise_error=True)
    except IntegrityError:
        assert not valid
    else:
        assert valid
    try:
        for _ in write(element):
            pass
    except IntegrityError:
        assert not recur_valid
    else:
        assert recur_valid


class SelfReferentialChild(Element):

    self_ref = Child('self-ref', 'SelfReferentialChild')


def test_self_referential_child():
    SelfReferentialChild()
    SelfReferentialChild.self_ref.element_type is SelfReferentialChild


class EncodeErrorDoc(DocumentElement):

    __tag__ = 'encode-error-test'
    attr = Attribute('attr', encoder=lambda s: s and 123)
    text = Text('text', encoder=lambda s: s and object())


def test_attribute_encode_error():
    doc = EncodeErrorDoc(attr=True)
    with raises(EncodeError):
        for _ in write(doc):
            pass


def test_text_encode_error():
    doc = EncodeErrorDoc(text=True)
    with raises(EncodeError):
        for _ in write(doc):
            pass


class ContentEncodeErrorDoc(DocumentElement):

    __tag__ = 'content-encode-error-test'
    value = Content(encoder=lambda s: object)


def test_content_encode_error():
    doc = ContentEncodeErrorDoc()
    with raises(EncodeError):
        for _ in write(doc):
            pass


class IntPair(Codec):

    def encode(self, value):
        a, b = value
        return '{0},{1}'.format(a, b)

    def decode(self, text):
        a, b = text.split(',')
        return int(a), int(b)


class CodecTestDoc(DocumentElement):

    __tag__ = 'codec-test'
    attr = Attribute('attr', IntPair)
    text = Text('text', IntPair)


def etree_tobyteslist(tree):
    string = tostring(tree)
    if IRON_PYTHON:
        return [binary_type(string, 'utf-8')]
    return [string]


def test_attribute_codec():
    doc = CodecTestDoc(attr=(1, 2))
    tree = fromstringlist(write(doc))
    assert tree.attrib['attr'] == '1,2'
    doc2 = read(CodecTestDoc, etree_tobyteslist(tree))
    assert doc2.attr == (1, 2)


def test_text_codec():
    doc = CodecTestDoc(text=(3, 4))
    tree = fromstringlist(write(doc))
    assert tree.find('text').text == '3,4'
    doc2 = read(CodecTestDoc, etree_tobyteslist(tree))
    assert doc2.text == (3, 4)


class ContentCodecTestDoc(DocumentElement):

    __tag__ = 'content-codec-test'
    c = Content(IntPair)


def test_content_codec():
    doc = ContentCodecTestDoc(c=(5, 6))
    tree = fromstringlist(write(doc, as_bytes=True))
    assert tree.text == '5,6'
    doc2 = read(ContentCodecTestDoc, etree_tobyteslist(tree))
    assert doc2.c == (5, 6)


def test_read_none_attribute():
    doc = read(CodecTestDoc, [b'<codec-test><text>1,2</text></codec-test>'])
    assert doc.attr is None
    assert doc.text == (1, 2)


def test_read_none_text():
    doc = read(CodecTestDoc, [b'<codec-test attr="1,2"></codec-test>'])
    assert doc.attr == (1, 2)
    assert doc.text is None


def test_write_none_attribute():
    doc = CodecTestDoc(attr=None, text=(1, 2))
    tree = fromstringlist(write(doc))
    assert tree.find('text').text == '1,2'
    assert 'attr' not in tree.attrib


def test_write_none_text():
    doc = CodecTestDoc(attr=(1, 2), text=None)
    tree = fromstringlist(write(doc))
    assert tree.find('text') is None
    assert tree.attrib['attr'] == '1,2'


class DefaultAttrTestDoc(DocumentElement):

    __tag__ = 'default-attr-test'
    attr = Attribute('attr', Integer)
    default_attr = Attribute(
        'default-attr', IntPair,
        default=lambda e: (e.attr, e.attr * 2) if e.attr else (0, 0)
    )


def test_attribute_default():
    present = DefaultAttrTestDoc(default_attr=(1, 2))
    assert present.default_attr == (1, 2)
    lack = DefaultAttrTestDoc()
    assert lack.default_attr == (0, 0)
    present = read(
        DefaultAttrTestDoc,
        [b'<default-attr-test default-attr="1,2" />']
    )
    assert present.default_attr == (1, 2)
    lack = read(DefaultAttrTestDoc, [b'<default-attr-test />'])
    assert lack.default_attr == (0, 0)


def test_attribute_default_depending_element():
    present = DefaultAttrTestDoc(attr=5, default_attr=(1, 2))
    assert present.default_attr == (1, 2)
    lack = DefaultAttrTestDoc(attr=5)
    assert lack.default_attr == (5, 10)
    present = read(
        DefaultAttrTestDoc,
        [b'<default-attr-test attr="5" default-attr="1,2" />']
    )
    assert present.default_attr == (1, 2)
    lack = read(DefaultAttrTestDoc, [b'<default-attr-test attr="5" />'])
    assert lack.default_attr == (5, 10)


class PartialLoadTestEntry(DocumentElement):

    __tag__ = 'entry'
    __xmlns__ = 'http://example.com/'
    value = Text('value', xmlns=__xmlns__)


class PartialLoadTestDoc(DocumentElement):

    __tag__ = 'partial-load-test'
    __xmlns__ = 'http://example.com/'
    entry = Child('entry', PartialLoadTestEntry, xmlns=__xmlns__)


def test_partial_load_test():
    doc = read(PartialLoadTestDoc, b'''
        <x:partial-load-test xmlns:x="http://example.com/">
            <x:entry>
                <x:value>as<!--
                -->df</x:value>
            </x:entry>
            <x:entry>
                <x:value>as<!--
                -->df</x:value>
            </x:entry>
        </x:partial-load-test>
    '''.splitlines())
    assert doc.entry.value == 'asdf'


class ELConsumeBufferRegressionTestD(Element):

    content = Content()


class ELConsumeBufferRegressionTestC(Element):

    d = Child('d', ELConsumeBufferRegressionTestD)


class ELConsumeBufferRegressionTestB(Element):

    c = Child('c', ELConsumeBufferRegressionTestC, multiple=True)


class ELConsumeBufferRegressionTestDoc(DocumentElement):

    __tag__ = 'a'
    b = Child('b', ELConsumeBufferRegressionTestB, multiple=True)


def test_element_list_consume_buffer_regression():
    xml = [b'<a><b><c></c><c><d>content', b'</d></c><c></c></b><b></b></a>']
    doc = read(ELConsumeBufferRegressionTestDoc, xml)
    assert len(doc.b) == 2
    b = doc.b[0]
    assert len(b.c) == 3


def test_element_list_consume_buffer_regression_root_stack_top_should_be_1():
    xml = [b'<a><b><!-- 1 --><c></c><c><d>', b'content</d></c><c></c></b><b>',
           b'<!-- 2 --><c><d>abc</d></c></b><b><!-- 3 --></b></a>']
    doc = read(ELConsumeBufferRegressionTestDoc, xml)
    assert len(doc.b) == 3
    b = doc.b[0]
    assert len(b.c) == 3


def test_child_set_none(fx_test_doc):
    doc, _ = fx_test_doc
    assert doc.title_attr is not None
    doc.title_attr = None
    assert doc.title_attr is None


def test_element_coerce_from(fx_test_doc):
    doc, _ = fx_test_doc
    doc.title_attr = 'coerce test'
    assert isinstance(doc.title_attr, TextElement)
    assert doc.title_attr.value == 'coerce test'
    with raises(TypeError):
        doc.title_attr = 123
    doc.multi_attr = [TextElement(value='a'), 'b']
    for e in doc.multi_attr:
        assert isinstance(e, TextElement)
    assert doc.multi_attr[0].value == 'a'
    assert doc.multi_attr[1].value == 'b'
    with raises(TypeError):
        doc.multi_attr = [TextElement(value='a'), 'b', 3]
    number = len(doc.multi_attr)
    doc.multi_attr.append('coerce test')
    assert len(doc.multi_attr) == number + 1
    for e in doc.multi_attr:
        assert isinstance(e, TextElement)
    assert doc.multi_attr[-1].value == 'coerce test'
    with raises(TypeError):
        doc.multi_attr.append(123)
    doc.multi_attr[0] = 'coerce test'
    assert isinstance(doc.multi_attr[0], TextElement)
    assert doc.multi_attr[0].value == 'coerce test'
    with raises(TypeError):
        doc.multi_attr[1] = 123
    doc.multi_attr[1:] = ['slice', 'test']
    for e in doc.multi_attr:
        assert isinstance(e, TextElement)
    assert doc.multi_attr[1].value == 'slice'
    assert doc.multi_attr[2].value == 'test'
    with raises(TypeError):
        doc.multi_attr[1:] = ['slice test', 123]


rss_template_with_title = '''
<rss version="2.0" xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"
     xmlns:dc="http://purl.org/dc/elements/1.1/"
     xmlns:taxo="http://purl.org/rss/1.0/modules/taxonomy/"
     xmlns:activity="http://activitystrea.ms/spec/1.0/" >
    <channel>
        <title>{0}</title>
    </channel>
</rss>
'''


def test_write_subscription_with_ascii_title():
    rss = rss_template_with_title.format('english')
    feed, _ = parse_rss(rss)
    feed.id = 'id'

    sublist = SubscriptionList()
    sublist.subscribe(feed)

    g = write(sublist)
    assert ''.join(g)


def test_write_subscription_with_nonascii_title():
    '''SubscriptionList convert the feed title to :class:`str`, and
    :class:`write` try to encode the title in utf8.
    When non-ascii characters are in the title, UnicodeDecodeError is raised.
    '''
    rss = rss_template_with_title.format('한글')
    feed, _ = parse_rss(rss)
    feed.id = 'id'

    sublist = SubscriptionList()
    sublist.subscribe(feed)

    g = write(sublist)
    assert ''.join(g)


def test_write_hints(fx_test_doc):
    doc, _ = fx_test_doc
    doc._hints.update({
        TestDoc.ns_element_attr: {'abc': '123', 'def': '456'},
        TestDoc.title_attr: {'ghi': '789', 'jkl': '012'}
    })
    g = write(doc, canonical_order=True)
    tree = fromstringlist(g)
    hint_tag = '{' + SCHEMA_XMLNS + '}hint'
    assert tree[0].tag == hint_tag
    assert tree[0].attrib['tag'] == 'ns-element'
    assert tree[0].attrib['tag-xmlns'] == 'http://earthreader.github.io/'
    assert tree[0].attrib['id'] == 'abc'
    assert tree[0].attrib['value'] == '123'
    assert tree[1].tag == hint_tag
    assert tree[1].attrib['tag'] == 'ns-element'
    assert tree[1].attrib['tag-xmlns'] == 'http://earthreader.github.io/'
    assert tree[1].attrib['id'] == 'def'
    assert tree[1].attrib['value'] == '456'
    assert tree[2].tag == hint_tag
    assert tree[2].attrib['tag'] == 'title'
    assert 'tag-xmlns' not in tree[2].attrib
    assert tree[2].attrib['id'] == 'ghi'
    assert tree[2].attrib['value'] == '789'
    assert tree[3].tag == hint_tag
    assert tree[3].attrib['tag'] == 'title'
    assert 'tag-xmlns' not in tree[3].attrib
    assert tree[3].attrib['id'] == 'jkl'
    assert tree[3].attrib['value'] == '012'


@fixture
def fx_hinted_doc():
    consume_log = []
    xml = string_chunks(
        consume_log,
        '<test xmlns:l="http://earthreader.org/schema/">', '\n',
        '\t', '<l:hint tag="multi" id="length" value="3" />', '\n',
        '\t', '<l:hint tag="s-multi" id="length" value="0" />', ['HINT'], '\n',
        '\t', '<title>Title</title>', '\n',
        '\t', '<multi>a</multi>', ['MULTI_STARTED'], '\n',
        '\t', '<content>Content</content>', '\n',
        '\t', '<multi>b</multi>', '\n',
        '\t', '<multi>c</multi>', '\n',
        '</test>'
    )
    doc = read(TestDoc, xml)
    return doc, consume_log


def test_read_hints(fx_hinted_doc):
    doc, consume_log = fx_hinted_doc
    assert not doc._hints
    assert is_partially_loaded(doc)
    assert doc._partial == 1
    assert not consume_log or IRON_PYTHON
    doc.title_attr
    assert is_partially_loaded(doc)
    assert doc._partial == 2
    assert consume_log[-1] == 'HINT' or IRON_PYTHON
    assert doc._hints == {
        TestDoc.multi_attr: {'length': '3'},
        TestDoc.sorted_children: {'length': '0'}
    }


def test_element_list_length_hint(fx_hinted_doc):
    doc, consume_log = fx_hinted_doc
    assert len(doc.multi_attr) == 3
    assert len(doc.sorted_children) == 0
    assert consume_log == ['HINT'] or IRON_PYTHON
