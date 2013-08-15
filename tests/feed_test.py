from pytest import mark, raises, skip

from libearth.compat import binary_type, text_type, xrange
from libearth.feed import (AlreadyExistException, Feed, FeedList, OPMLDoc,
                           SaveOPMLError)
from libearth.schema import (Child, Content, DocumentElement, Element, Text,
                             read)


def test_count_empty_list():
    feeds = FeedList()
    assert len(feeds) == 0


def test_count_duplicated_url():
    feeds = FeedList()
    with raises(AlreadyExistException):
        for i in xrange(30):
            feeds.add_feed('type', 'title', 'url')

    assert len(feeds) == 1


def test_count_after_remove():
    feeds = FeedList()
    feeds.add_feed('type', 'title', 'url')
    del feeds[0]

    assert len(feeds) == 0

XML = """<?xml version="1.0" encoding="ISO-8859-1"?>
<opml version="2.0">
    <head>
        <title>EarthReader.opml</title>
        <dateCreated>Sat, 18 Jun 2005 12:11:52 GMT</dateCreated>
        <ownerName>libearth</ownerName>
        <ownerEmail>earthreader@librelist.com</ownerEmail>
        <expansionState>a,b,c,d</expansionState>
        <vertScrollState>1</vertScrollState>
        <windowTop>12</windowTop>
        <windowLeft>34</windowLeft>
        <windowBottom>56</windowBottom>
        <windowRight>78</windowRight>
    </head>
    <body>
        <outline text="CNET News.com" type="rss" version="RSS2"
            xmlUrl="http://news.com/2547-1_3-0-5.xml"/>
        <outline text="test.com" type="rss" xmlUrl="http://test.com"/>
    </body>
</opml>"""

XML_CATEGORY = """<?xml version="1.0" encoding="ISO-8859-1"?>
<opml version="2.0">
    <head>
        <title>EarthReader.opml</title>
        <dateCreated>Sat, 18 Jun 2005 12:11:52 GMT</dateCreated>
        <ownerName>libearth</ownerName>
        <ownerEmail>earthreader@librelist.com</ownerEmail>
        <expansionState>a,b,c,d</expansionState>
        <vertScrollState>1</vertScrollState>
        <windowTop>12</windowTop>
        <windowLeft>34</windowLeft>
        <windowBottom>56</windowBottom>
        <windowRight>78</windowRight>
    </head>
    <body>
        <outline text="Game" title="Game" type="category">
            <outline text="valve" title="valve" xmlUrl="http://valve.com/" />
            <outline text="nintendo" title="nintendo"
            xmlUrl="http://nintendo.com/" />
        </outline>
        <outline text="Music" title="Music" type="category">
            <outline text="capsule" title="capsule"
            xmlUrl="http://www.capsule-web.com/" />
        </outline>
    </body>
</opml>"""

XML_DUPLICAED = """<?xml version="1.0" encoding="utf-8"?><opml version="1.1">
<head>
    <title>feeds for test</title>
    <dateCreated>Tue, 13 Jul 2013 21:34:05 +0900</dateCreated>
    <ownerName>Kjwon15</ownerName>
</head>
<body>
    <outline type="category" text="sub1">
    <outline type="rss" text="cake" xmlUrl="http://kjwon15.tistory.com/" />
    </outline>
    <outline type="category" text="sub2">
    <outline type="rss" text="cake" xmlUrl="http://kjwon15.tistory.com/" />
    </outline>
</body>
</opml>
"""


def test_OPMLDocment():
    doc = read(OPMLDoc, XML)
    assert doc.head.title == "EarthReader.opml"
    assert doc.head.date_created == "Sat, 18 Jun 2005 12:11:52 GMT"
    assert doc.head.date_modified is None
    assert doc.head.owner_name == "libearth"
    assert doc.head.expansion_state == ['a', 'b', 'c', 'd']
    assert doc.head.window_top == 12

    assert len(doc.body.outline) == 2
    assert doc.body.outline[0].text == "CNET News.com"


def test_file_not_found():
    with raises(IOError):
        feeds = FeedList('this_file_must_be_not_found.ext')


def test_path_as_string():
    feeds = FeedList(XML, is_xml_string=True)
    assert feeds.title == "EarthReader.opml"
    assert len(feeds) == 2


def test_feed_as_iterator():
    feeds = FeedList(XML, is_xml_string=True)
    expected = ['CNET News.com', 'test.com']
    for feed in feeds:
        print(feed.title)
        expected.remove(feed.title)
    assert not expected


def test_feed_contains_category():
    feeds = FeedList(XML_CATEGORY, is_xml_string=True)
    expected = {
        'Game': ['valve', 'nintendo'],
        'Music': ['capsule'],
    }
    for feed in feeds:
        print(feed.title)
        assert feed.type == 'category'
        for child_feed in feed:
            print(child_feed.title)
            expected[feed.title].remove(child_feed.title)
        assert not expected[feed.title]
        expected.pop(feed.title)
    assert not expected.keys()


def test_save_as_file(tmpdir):
    filename = tmpdir.join('feeds.opml').strpath
    print(filename)
    feeds = FeedList(XML, is_xml_string=True)
    feeds.title = "changed_title"
    newfeed = Feed('rss2', 'newfeed', 'http://earthreader.com/rss')
    feeds.append(newfeed)
    feeds.save_file(filename)

    feeds_another = FeedList(filename)
    assert feeds_another.title == "changed_title"
    assert feeds_another.expansion_state == ['a', 'b', 'c', 'd']
    assert feeds_another[2].title == "newfeed"

    assert feeds_another.window_top == 12
    assert feeds_another.window_left == 34
    assert feeds_another.window_bottom == 56
    assert feeds_another.window_right == 78


def test_same_feed_on_multi_category():
    feeds = FeedList(XML_DUPLICAED, is_xml_string=True)
    feeds[0][0].xml_url = "changed"
    assert feeds[1][0].xml_url == "changed"
