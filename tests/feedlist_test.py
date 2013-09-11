from datetime import datetime
from pytest import raises

from libearth.feedlist import (AlreadyExistException, Feed, FeedCategory,
                               FeedList, OpmlDoc)
from libearth.schema import read
from libearth.tz import utc


def test_count_empty_list():
    feeds = FeedList()
    assert len(feeds) == 0


def test_count_duplicated_url():
    feeds = FeedList()
    feeds.add_feed('type', 'title', 'url')
    with raises(AlreadyExistException):
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
        <dateCreated>Sat, 18 Jun 2005 12:11:52 +0000</dateCreated>
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
        <dateCreated>Sat, 18 Jun 2005 12:11:52 +0000</dateCreated>
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


def test_OpmlDocment():
    doc = read(OpmlDoc, XML)
    expected_datetime = datetime(2005, 6, 18, 12, 11, 52, tzinfo=utc)

    assert doc.head.title == "EarthReader.opml"
    assert doc.head.date_created == expected_datetime
    assert doc.head.date_modified is None
    assert doc.head.owner_name == "libearth"
    assert doc.head.expansion_state == ['a', 'b', 'c', 'd']
    assert doc.head.window_top == 12

    assert len(doc.body.outline) == 2
    assert doc.body.outline[0].text == "CNET News.com"


def test_file_not_found():
    with raises(IOError):
        FeedList('this_file_must_be_not_found.ext')


def test_path_as_string():
    feeds = FeedList(XML, is_xml_string=True)
    assert feeds.title == "EarthReader.opml"
    assert len(feeds) == 2


def test_feed_as_iterator():
    feeds = FeedList(XML, is_xml_string=True)
    expected = set(['CNET News.com', 'test.com'])
    assert set(f.title for f in feeds) == expected


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


def test_feedTree_in_category():
    feed1 = Feed('rss2', 'newfeed', 'http://some.url/rss2')
    feed2 = Feed('rss2', 'otherfeed', 'http://different.url/rss2')
    feed3 = Feed('rss2', 'anotherfeed', 'http://another.url/rss2')

    root = FeedCategory('root')
    sub = FeedCategory('sub')
    cate3 = FeedCategory('outer')

    sub.append(feed2)

    root.append(feed1)
    root.append(sub)

    assert feed1 in root
    assert feed1 not in sub
    assert feed2 in sub
    assert feed2 in root
    assert feed3 not in sub
    assert feed3 not in sub

    assert sub in root
    assert cate3 not in root


def test_circular_reference(tmpdir):
    cate = FeedCategory('Root category')
    subcate = FeedCategory('Sub category')
    lastcate = FeedCategory('last category')

    cate.append(subcate)
    subcate.append(lastcate)
    with raises(AlreadyExistException):
        subcate.append(cate)
    with raises(AlreadyExistException):
        lastcate.append(cate)
    with raises(AlreadyExistException):
        subcate.append(subcate)
    feeds = FeedList(XML, is_xml_string=True)
    feeds.append(cate)

    filename = tmpdir.join('feeds.opml').strpath
    print(filename)
    feeds.save_file(filename)
