# -*- coding: utf-8 -*-
import datetime
import functools
import hashlib
import uuid

from pytest import fixture, raises

from libearth.compat import IRON_PYTHON, binary, text_type, xrange
from libearth.compat.parallel import parallel_map
from libearth.feed import (Category, Content, Entry, EntryList, Feed, Generator,
                           Link, LinkList, Person, Source, Text, Mark)
from libearth.repository import FileSystemRepository
from libearth.schema import read, write
from libearth.session import Session
from libearth.stage import Stage
from libearth.tz import utc
from .stage_test import MemoryRepository


def u(text):
    if isinstance(text, text_type):
        return text
    return text.decode('utf-8')


def test_text_str():
    assert text_type(Text(type='text', value='Hello world')) == 'Hello world'
    assert (text_type(Text(type='text', value='<p>Hello <em>world</em></p>'))
            == '<p>Hello <em>world</em></p>')
    assert text_type(Text(type='html', value='Hello world')) == 'Hello world'
    assert (text_type(Text(type='html', value='<p>Hello <em>world</em></p>'))
            == 'Hello world')


def test_sanitized_html():
    assert (Text(type='text', value='Hello world').sanitized_html ==
            'Hello world')
    assert (Text(type='text', value='Hello\nworld').sanitized_html ==
            'Hello<br>\nworld')
    assert (
        Text(type='text', value='<p>Hello <em>world</em></p>').sanitized_html
        == '&lt;p&gt;Hello &lt;em&gt;world&lt;/em&gt;&lt;/p&gt;'
    )
    assert (Text(type='html', value='Hello world').sanitized_html ==
            'Hello world')
    assert (
        Text(type='html', value='<p>Hello <em>world</em></p>').sanitized_html
        == '<p>Hello <em>world</em></p>'
    )
    assert (
        Text(type='html',
             value='<p>Hello</p><script>alert(1);</script>').sanitized_html
        == '<p>Hello</p>'
    )
    assert (
        Text(type='html', value='<p>Hello</p><hr noshade>').sanitized_html
        == '<p>Hello</p><hr noshade>'
    )


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


@fixture
def fx_feed_links(fx_feed):
    fx_feed.links.extend([
        Link(relation='alternate', mimetype='text/html',
             uri='http://example.com/index.html'),
        Link(relation='alternate', mimetype='text/html',
             uri='http://example.com/index2.html'),
        Link(relation='alternate', mimetype='text/xml',
             uri='http://example.com/index.xml'),
        Link(relation='alternate', mimetype='application/json',
             uri='http://example.com/index.json'),
        Link(relation='alternate', mimetype='text/javascript',
             uri='http://example.com/index.js'),
        Link(relation='alternate', mimetype='application/xml+atom',
             uri='http://example.com/index.atom'),
        Link(relation='alternate', mimetype='application/xml+rss',
             uri='http://example.com/index.atom')
    ])
    return fx_feed


def test_link_list_filter_by_mimetype(fx_feed_links):
    assert isinstance(fx_feed_links.links, LinkList)
    result = fx_feed_links.links.filter_by_mimetype('text/html')
    assert isinstance(result, LinkList)
    assert len(result) == 2
    assert [link.mimetype for link in result] == ['text/html', 'text/html']
    result = fx_feed_links.links.filter_by_mimetype('application/*')
    assert isinstance(result, LinkList)
    assert len(result) == 3
    assert [link.mimetype for link in result] == [
        'application/json',
        'application/xml+atom',
        'application/xml+rss'
    ]


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
    entry = read(Entry, [b'''
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
    assert entry.title == Text(value='Atom-Powered Robots Run Amok')
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
    assert text_type(Entry(title=Text(value='Title desu'))) == 'Title desu'
    assert text_type(Entry()) == ''


@fixture
def fx_feed_entries(fx_feed, fx_test_entries):
    fx_feed.entries.extend(fx_test_entries)
    return fx_feed


def test_entry_list_sorted(fx_feed_entries):
    assert isinstance(fx_feed_entries.entries, EntryList)
    result = fx_feed_entries.entries.sort_entries()
    assert isinstance(result, EntryList)
    sorted_entries = sorted(fx_feed_entries.entries, key=lambda entry:
                            entry.updated_at, reverse=True)
    assert sorted_entries == result


def test_source():
    entry = read(Entry, [b'''
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
    assert source.title == Text(value='Source of all knowledge')
    assert source.id == 'urn:uuid:28213c50-f84c-11d9-8cd6-0800200c9a66'
    assert source.updated_at == datetime.datetime(2003, 12, 13, 17, 46, 27,
                                                  tzinfo=utc)
    categories = source.categories
    assert isinstance(categories[0], Category)
    assert categories[0].term == 'technology'
    assert isinstance(categories[1], Category)
    assert categories[1].term == 'business'
    assert len(categories) == 2


@fixture
def fx_feed():
    return read(Feed, [b'''
        <feed xmlns="http://www.w3.org/2005/Atom"
              xmlns:mark="http://earthreader.org/mark/">
            <title>Example Feed</title>
            <link href="http://example.org/"/>
            <updated>2003-12-13T18:30:02Z</updated>
            <author><name>John Doe</name></author>
            <author><name>Jane Doe</name></author>
            <id>urn:uuid:60a76c80-d399-11d9-b93C-0003939e0af6</id>
            <category term="technology"/>
            <category term="business"/>
            <rights>Public Domain</rights>
            <entry>
                <title>Atom-Powered Robots Run Amok</title>
                <link href="http://example.org/2003/12/13/atom03"/>
                <id>urn:uuid:1225c695-cfb8-4ebb-aaaa-80da344efa6a</id>
                <updated>2003-12-13T18:30:02Z</updated>
                <summary>Some text.</summary>
                <author><name>Jane Doe</name></author>
                <mark:read updated="2013-11-06T14:36:00Z">true</mark:read>
            </entry>
            <entry>
                <title>Danger, Will Robinson!</title>
                <link href="http://example.org/2003/12/13/lost"/>
                <id>urn:uuid:b12f2c10-ffc1-11d9-8cd6-0800200c9a66</id>
                <updated>2003-12-13T18:30:02Z</updated>
                <summary>Don't Panic!</summary>
            </entry>
        </feed>
    '''])


def test_feed_read(fx_feed):
    feed = fx_feed
    assert feed.title == Text(value='Example Feed')
    link = feed.links[0]
    assert isinstance(link, Link)
    assert link.relation == 'alternate'
    assert link.uri == 'http://example.org/'
    assert len(feed.links) == 1
    assert feed.updated_at == datetime.datetime(2003, 12, 13, 18, 30, 2,
                                                tzinfo=utc)
    authors = feed.authors
    assert isinstance(authors[0], Person)
    assert authors[0].name == 'John Doe'
    assert isinstance(authors[1], Person)
    assert authors[1].name == 'Jane Doe'
    assert len(feed.authors) == 2
    assert feed.id == 'urn:uuid:60a76c80-d399-11d9-b93C-0003939e0af6'
    categories = feed.categories
    assert isinstance(categories[0], Category)
    assert categories[0].term == 'technology'
    assert isinstance(categories[1], Category)
    assert categories[1].term == 'business'
    assert len(categories) == 2
    assert feed.rights == Text(value='Public Domain')
    entries = feed.entries
    assert isinstance(entries[0], Entry)
    assert entries[0].title == Text(value='Atom-Powered Robots Run Amok')
    assert (list(entries[0].links) ==
            [Link(uri='http://example.org/2003/12/13/atom03')])
    assert entries[0].id == 'urn:uuid:1225c695-cfb8-4ebb-aaaa-80da344efa6a'
    assert entries[0].updated_at == datetime.datetime(2003, 12, 13, 18, 30, 2,
                                                      tzinfo=utc)
    assert entries[0].summary == Text(value='Some text.')
    assert list(entries[0].authors) == [Person(name='Jane Doe')]
    assert isinstance(entries[1], Entry)
    assert entries[1].title == Text(value='Danger, Will Robinson!')
    assert (list(entries[1].links) ==
            [Link(uri='http://example.org/2003/12/13/lost')])
    assert entries[1].id == 'urn:uuid:b12f2c10-ffc1-11d9-8cd6-0800200c9a66'
    assert entries[1].updated_at == datetime.datetime(2003, 12, 13, 18, 30, 2,
                                                      tzinfo=utc)
    assert entries[1].summary == Text(value="Don't Panic!")
    assert len(entries) == 2


def test_generator_eq():
    generator_one = Generator()
    generator_two = Generator()
    generator_one.value = 'generator'
    generator_two.value = 'generator'
    assert generator_one == generator_two


def test_feed_mark_read(fx_feed):
    assert fx_feed.entries[0].read == Mark(
        marked=True,
        updated_at=datetime.datetime(2013, 11, 6, 14, 36, 0, tzinfo=utc)
    )
    assert fx_feed.entries[1].read is None


@fixture
def fx_mark_true():
    return Mark(
        marked=True,
        updated_at=datetime.datetime(2013, 11, 6, 14, 36, 0, tzinfo=utc)
    )


@fixture
def fx_mark_false():
    return Mark(
        marked=False,
        updated_at=datetime.datetime(2013, 11, 6, 14, 36, 0, tzinfo=utc)
    )


def test_mark(fx_mark_true, fx_mark_false):
    assert fx_mark_true
    assert not fx_mark_false
    assert (fx_mark_true.updated_at ==
            datetime.datetime(2013, 11, 6, 14, 36, 0, tzinfo=utc))


@fixture
def fx_stages(tmpdir):
    if IRON_PYTHON:
        repo = MemoryRepository()
    else:
        repo = FileSystemRepository(str(tmpdir))
    session_a = Session(identifier='a')
    session_b = Session(identifier='b')
    stage_a = Stage(session_a, repo)
    stage_b = Stage(session_b, repo)
    return stage_a, stage_b


def timestamp(minute, second=0):
    """Creates an arbitrary timestamp with a short call."""
    return datetime.datetime(2013, 11, 7, 18, minute, second, tzinfo=utc)


def test_merge_marks(fx_stages, fx_feed):
    stage_a, stage_b = fx_stages
    with stage_a:
        stage_a.feeds['test'] = fx_feed
        feed_a = stage_a.feeds['test']
    with stage_b:
        feed_b = stage_b.feeds['test']
    with stage_b:
        feed_b.entries[0].read = Mark(marked=True, updated_at=timestamp(1))
        stage_b.feeds['test'] = feed_b
    with stage_a:
        feed_a.entries[0].read = Mark(marked=True, updated_at=timestamp(2))
        stage_a.feeds['test'] = feed_a
    with stage_b:
        feed_b.entries[0].read = Mark(marked=False, updated_at=timestamp(3))
        stage_b.feeds['test'] = feed_b
    with stage_b:
        feed_b.entries[0].starred = Mark(marked=True, updated_at=timestamp(4))
        stage_b.feeds['test'] = feed_b
    with stage_b:
        feed_b.entries[0].starred = Mark(marked=False, updated_at=timestamp(5))
        stage_b.feeds['test'] = feed_b
    with stage_a:
        feed_a.entries[0].starred = Mark(marked=True, updated_at=timestamp(6))
        stage_a.feeds['test'] = feed_a
    with stage_b:
        stage_b.feeds['test'] = feed_b
    with stage_a:
        print(repr(stage_a.feeds['test']))
    with stage_a:
        entry_a = stage_a.feeds['test'].entries[0]
    with stage_b:
        entry_b = stage_b.feeds['test'].entries[0]
    assert not entry_a.read
    assert not entry_b.read
    assert entry_a.starred
    assert entry_b.starred
    assert (entry_a.read.updated_at == entry_b.read.updated_at ==
            timestamp(3))
    assert (entry_a.starred.updated_at == entry_b.starred.updated_at ==
            timestamp(6))


def test_merge_mark_crawled(fx_stages, fx_feed):
    stage, _ = fx_stages
    with stage:
        stage.feeds['test'] = fx_feed
        feed = stage.feeds['test']
    feed.updated_at = timestamp(1)
    feed.entries[1].read = True
    with stage:
        stage.feeds['test'] = feed
    with stage:
        assert stage.feeds['test'].entries[1].read
    crawled_feed = fx_feed
    assert not crawled_feed.entries[1].read
    crawled_feed.updated_at = timestamp(2)
    with stage:
        stage.feeds['test'] = crawled_feed
    with stage:
        assert stage.feeds['test'].entries[1].read


@fixture
def fx_test_feeds():
    authors = [Person(name='vio')]
    feed = Feed(id='http://feedone.com/', authors=authors,
                title='Feed One',
                updated_at=datetime.datetime(2013, 10, 29, 20, 55, 30,
                                             tzinfo=utc))
    updated_feed = Feed(id='http://feedone.com/', authors=authors,
                        title=Text(value='Feed One'),
                        updated_at=datetime.datetime(2013, 10, 30, 20, 55, 30,
                                                     tzinfo=utc))
    entry = Entry(id='http://feedone.com/1', authors=authors,
                  title=Text(value='Test Entry'),
                  updated_at=datetime.datetime(2013, 10, 30, 20, 55, 30,
                                               tzinfo=utc))
    updated_feed.entries.append(entry)
    return feed, updated_feed


def get_hash(name):
    return hashlib.sha1(binary(name)).hexdigest()


def test_stage(fx_stages, fx_test_feeds):
    stage1, stage2 = fx_stages
    feed, updated_feed = fx_test_feeds
    assert feed.id == updated_feed.id
    feed_id = feed.id
    with stage1:
        stage1.feeds[get_hash(feed.id)] = feed
        feed1 = stage1.feeds[get_hash(feed_id)]
    with stage2:
        feed2 = stage2.feeds[get_hash(feed_id)]
    assert (feed1.updated_at == feed2.updated_at ==
            datetime.datetime(2013, 10, 29, 20, 55, 30, tzinfo=utc))
    assert not feed1.entries and not feed2.entries
    with stage2:
        stage2.feeds[get_hash(feed_id)] = updated_feed
    with stage1:
        feed1 = stage1.feeds[get_hash(feed_id)]
    with stage2:
        feed2 = stage2.feeds[get_hash(feed_id)]
    assert (feed1.updated_at == feed2.updated_at ==
            datetime.datetime(2013, 10, 30, 20, 55, 30, tzinfo=utc))
    assert feed1.entries[0].title == feed2.entries[0].title


@fixture
def fx_test_entries():
    entry1 = Entry(
        id='http://feed.com/entry1', title=Text(value='new1'),
        updated_at=datetime.datetime(2013, 1, 1, 0, 0, 0, tzinfo=utc))
    entry2 = Entry(
        id='http://feed.com/entry2', title=Text(value='new2'),
        updated_at=datetime.datetime(2013, 1, 1, 0, 0, 1, tzinfo=utc))
    return entry1, entry2


def test_merge_entries(fx_stages, fx_test_feeds, fx_test_entries):
    stage1, stage2 = fx_stages
    feed1, feed2 = fx_test_feeds
    entry0 = feed2.entries[0]
    entry1, entry2 = fx_test_entries
    assert feed1.id == feed2.id
    feed1.entries.append(entry1)
    feed2.entries.append(entry2)
    print(feed1.entries)
    print(feed2.entries)
    assert entry1 in feed1.entries and entry2 in feed2.entries
    assert entry2 not in feed1.entries and entry1 not in feed2.entries
    with stage1:
        stage1.feeds[get_hash(feed1.id)] = feed1
    with stage2:
        stage2.feeds[get_hash(feed2.id)] = feed2
    with stage1:
        feed1 = stage1.feeds[get_hash(feed1.id)]
    with stage2:
        feed2 = stage2.feeds[get_hash(feed2.id)]
    print(repr(entry1))
    print(repr(entry2))
    print(feed1.entries)
    print(feed2.entries)
    assert (frozenset(entry.id for entry in feed1.entries) ==
            frozenset(entry.id for entry in feed2.entries) ==
            frozenset([entry0.id, entry2.id, entry1.id]))


def apply_timestamp(stage, feed_id, timestamp):
    with stage:
        feed = stage.feeds[feed_id]
        feed.entries[0].read = Mark(marked=True, updated_at=timestamp)
        assert feed.entries[0].read.updated_at == timestamp
        written = read(Feed, write(feed, as_bytes=True))
        assert written.entries[0].read.updated_at == timestamp, repr(
            (written.entries[0].read.updated_at, timestamp)
        )
        stage.feeds[feed_id] = feed


def test_race_condition(fx_stages, fx_feed):
    stage, _ = fx_stages
    with stage:
        stage.feeds['test'] = fx_feed
    result = parallel_map(
        10,
        functools.partial(apply_timestamp, stage, 'test'),
        map(timestamp, range(10))
    )
    for _ in result:
        pass
    with stage:
        updated_at = stage.feeds['test'].entries[0].read.updated_at
    assert updated_at == timestamp(9)


@fixture
def fx_entries():
    entries = [
        Entry(
            title='entry {0}'.format(i),
            updated_at=timestamp(i),
            id='urn:uuid:{0}'.format(uuid.uuid4())
        ) for i in xrange(10)
    ]
    return entries


def test_merge_sorted(fx_stages, fx_feed, fx_entries):
    stage, _ = fx_stages

    with stage:
        stage.feeds[fx_feed.id] = fx_feed

    with stage:
        for entry in fx_entries:
            feed = stage.feeds[fx_feed.id]
            feed.entries = [entry]
            stage.feeds[fx_feed.id] = feed

    with stage:
        entries = stage.feeds[fx_feed.id].entries
        sorted_entries = sorted(entries, key=lambda entry: entry.updated_at,
                                reverse=True)
        assert len(entries) == len(sorted_entries)
        for i in range(len(entries)):
            assert entries[i] == sorted_entries[i]
