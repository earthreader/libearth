from libearth.compat import text
from libearth.schema import Child, Content, DocumentElement, Element


class Text(Element):

    value = Content()


class TestDoc(DocumentElement):

    __tag__ = 'test'
    title = Child('title', Text, required=True)
    content = Child('content', Text, required=True)


def test_document_parse():
    xml = text('''
        <test>
            <title>Title test</title>
            <content>Content test</content>
        </test>
    ''')
    doc = TestDoc(xml)
    assert doc.title.value == 'Title test'
    assert doc.content.value == 'Content test'
