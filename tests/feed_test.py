# -*- coding: utf-8 -*-
from libearth.compat import text_type
from libearth.feed import Link, MarkupTagCleaner, Person, Text


def u(text):
    if isinstance(text, text_type):
        return text
    return text.decode('utf-8')


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


def test_person_str():
    assert text_type(Person(name='Hong Minhee')) == 'Hong Minhee'
    assert (text_type(Person(name='Hong Minhee', uri='http://dahlia.kr/')) ==
            'Hong Minhee <http://dahlia.kr/>')
    email = '\x6d\x69\x6e\x68\x65\x65\x40\x64\x61\x68\x6c\x69\x61\x2e\x6b\x72'
    assert (text_type(Person(name='Hong Minhee', email=email)) ==
            'Hong Minhee <' + email + '>')
    assert u('홍민희 <http://dahlia.kr/>') == text_type(
        Person(
            name=u('홍민희'),
            uri='http://dahlia.kr/',
            email=email
        )
    )


def test_person_html():
    assert (Person(name='Hong "Test" Minhee').__html__() ==
            'Hong &quot;Test&quot; Minhee')
    assert (Person(name='Hong Minhee', uri='http://dahlia.kr/').__html__() ==
            '<a href="http://dahlia.kr/">Hong Minhee</a>')
    email = '\x6d\x69\x6e\x68\x65\x65\x40\x64\x61\x68\x6c\x69\x61\x2e\x6b\x72'
    assert (Person(name='Hong Minhee', email=email).__html__() ==
            '<a href="mailto:' + email + '">Hong Minhee</a>')
    assert u('<a href="http://dahlia.kr/">홍민희</a>') == Person(
        name=u('홍민희'),
        uri='http://dahlia.kr/',
        email=email
    ).__html__()


def test_link_str():
    link = Link(
        uri='http://dahlia.kr/',
        relation='alternate',
        mimetype='text/html',
        title="Hong Minhee's website"
    )
    assert text_type(link) == 'http://dahlia.kr/'


def test_link_html():
    link = Link(
        uri='http://dahlia.kr/',
        relation='alternate',
    )
    assert link.__html__() == '<link rel="alternate" href="http://dahlia.kr/">'
    link = Link(
        uri='http://dahlia.kr/',
        relation='alternate',
        mimetype='text/html',
        title="Hong Minhee's website",
        language='en'
    )
    assert (
        link.__html__() ==
        '<link rel="alternate" type="text/html" hreflang="en" '
        'href="http://dahlia.kr/" title="Hong Minhee\'s website">'
    )
