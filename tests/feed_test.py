from libearth.compat import text_type
from libearth.feed import MarkupTagCleaner, Text


def test_markup_tag_cleaner():
    assert MarkupTagCleaner.clean('<b>Hello</b>') == 'Hello'
    assert MarkupTagCleaner.clean('<p><b>Hello</b></p>') == 'Hello'
    assert MarkupTagCleaner.clean('<p>Hello <b>world</b></p>') == 'Hello world'


def test_text_str():
    assert text_type(Text(type='text', value='Hello world')) == 'Hello world'
    assert (text_type(Text(type='text', value='<p>Hello <em>world</em></p>'))
            == '<p>Hello <em>world</em></p>')
    assert text_type(Text(type='html', value='Hello world')) == 'Hello world'
    assert (text_type(Text(type='html', value='<p>Hello <em>world</em></p>'))
            == 'Hello world')


def test_text_html():
    assert Text(type='text', value='Hello world').__html__() == 'Hello world'
    assert (Text(type='text', value='Hello\nworld').__html__() ==
            'Hello<br>\nworld')
    assert (Text(type='text', value='<p>Hello <em>world</em></p>').__html__()
            == '&lt;p&gt;Hello &lt;em&gt;world&lt;/em&gt;&lt;/p&gt;')
    assert Text(type='html', value='Hello world').__html__() == 'Hello world'
    assert (Text(type='html', value='<p>Hello <em>world</em></p>').__html__()
            == '<p>Hello <em>world</em></p>')
