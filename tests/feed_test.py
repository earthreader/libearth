# -*- coding: utf-8 -*-
import datetime

from pytest import raises

from libearth.compat import text_type
from libearth.feed import (Category, Content, Entry, Generator, Link,
                           MarkupTagCleaner, Person, Source, Text)
from libearth.schema import read
from libearth.tz import utc


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


def test_category_str():
    assert text_type(Category(term='python')) == 'python'
    assert text_type(Category(term='python', label='Python')) == 'Python'


def test_content_mimetype():
    assert Content(type='text', value='Hello').mimetype == 'text/plain'
    assert Content(type='html', value='Hello').mimetype == 'text/html'
    assert Content(type='text/xml', value='<a>Hello</a>').mimetype == 'text/xml'
    assert Content(mimetype='text/plain', value='Hello').type == 'text'
    assert Content(mimetype='text/html', value='Hello').type == 'html'
    assert Content(mimetype='text/xml', value='<a>Hello</a>').type == 'text/xml'


def test_content_invalid_mimetype():
    with raises(ValueError):
        Content(mimetype='invalid/mime/type')
    with raises(ValueError):
        Content(mimetype='invalidmimetype')
    with raises(ValueError):
        Content(mimetype='invalid/(mimetype)')


def test_generator_str():
    assert text_type(Generator(value='Earth Reader')) == 'Earth Reader'
    assert text_type(Generator(value='Earth Reader',
                     uri='http://earthreader.github.io/')) == 'Earth Reader'
    assert (text_type(Generator(value='Earth Reader', version='1.0')) ==
            'Earth Reader 1.0')
    assert text_type(Generator(value='Earth Reader',
                     version='1.0',
                     uri='http://earthreader.github.io/')) == 'Earth Reader 1.0'


def test_generator_html():
    assert Generator(value='Earth Reader').__html__() == 'Earth Reader'
    assert Generator(value='<escape test>').__html__() == '&lt;escape test&gt;'
    html = Generator(
        value='Earth Reader',
        uri='http://earthreader.github.io/'
    ).__html__()
    assert html == '<a href="http://earthreader.github.io/">Earth Reader</a>'
    assert (Generator(value='Earth Reader', version='1.0').__html__() ==
            'Earth Reader 1.0')
    html = Generator(
        value='Earth Reader',
        version='1.0',
        uri='http://earthreader.github.io/'
    ).__html__()
    assert (html ==
            '<a href="http://earthreader.github.io/">Earth Reader 1.0</a>')


def test_entry_read():
    # http://www.intertwingly.net/wiki/pie/FormatTests
    entry = read(Entry, ['''
        <entry xmlns="http://www.w3.org/2005/Atom">
            <title>Atom-Powered Robots Run Amok</title>
            <link href="http://example.org/2003/12/13/atom03"/>
            <id>urn:uuid:1225c695-cfb8-4ebb-aaaa-80da344efa6a</id>
            <updated>2003-12-13T18:30:02Z</updated>
            <summary>Some text.</summary>
            <category term="technology"/>
            <category term="business"/>
            <contributor>
                <name>John Smith</name>
            </contributor>
            <contributor>
                <name>Jane Doe</name>
            </contributor>
        </entry>
    '''])
    assert entry.id == 'urn:uuid:1225c695-cfb8-4ebb-aaaa-80da344efa6a'
    assert entry.title == 'Atom-Powered Robots Run Amok'
    assert entry.updated_at == datetime.datetime(2003, 12, 13, 18, 30, 2,
                                                 tzinfo=utc)
    assert isinstance(entry.links[0], Link)
    assert entry.links[0].uri == 'http://example.org/2003/12/13/atom03'
    assert entry.links[0].relation == 'alternate'
    assert len(entry.links) == 1
    assert isinstance(entry.summary, Text)
    assert entry.summary.type == 'text'
    assert entry.summary.value == 'Some text.'
    assert isinstance(entry.categories[0], Category)
    assert entry.categories[0].term == 'technology'
    assert entry.categories[1].term == 'business'
    assert len(entry.categories) == 2
    assert isinstance(entry.contributors[0], Person)
    assert entry.contributors[0].name == 'John Smith'
    assert entry.contributors[1].name == 'Jane Doe'
    assert len(entry.contributors) == 2


def test_entry_str():
    assert text_type(Entry(title='Title desu')) == 'Title desu'


def test_source():
    entry = read(Entry, ['''
        <entry xmlns="http://www.w3.org/2005/Atom">
            <source>
                <title>Source of all knowledge</title>
                <id>urn:uuid:28213c50-f84c-11d9-8cd6-0800200c9a66</id>
                <updated>2003-12-13T17:46:27Z</updated>
                <category term="technology"/>
                <category term="business"/>
            </source>
            <title>Atom-Powered Robots Run Amok</title>
            <link href="http://example.org/2003/12/13/atom03"/>
            <id>urn:uuid:1225c695-cfb8-4ebb-aaaa-80da344efa6a</id>
            <updated>2003-12-13T18:30:02Z</updated>
            <summary>Some text.</summary>
        </entry>
    '''])
    source = entry.source
    assert isinstance(source, Source)
    assert source.title == 'Source of all knowledge'
    assert source.id == 'urn:uuid:28213c50-f84c-11d9-8cd6-0800200c9a66'
    assert source.updated_at == datetime.datetime(2003, 12, 13, 17, 46, 27,
                                                  tzinfo=utc)
    categories = source.categories
    assert isinstance(categories[0], Category)
    assert categories[0].term == 'technology'
    assert isinstance(categories[1], Category)
    assert categories[1].term == 'business'
    assert len(categories) == 2
