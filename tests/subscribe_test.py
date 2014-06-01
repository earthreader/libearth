from datetime import datetime
from pytest import fixture, mark

from libearth.feed import Feed, Link, Person, Text
from libearth.session import Session
from libearth.stage import Stage
from libearth.subscribe import Body, Category, Subscription, SubscriptionList
from libearth.schema import read
from libearth.tz import utc
from .stage_test import MemoryRepository, fx_repo, fx_session


@fixture
def fx_subscription():
    return Subscription(
        label='Title',
        feed_uri='http://example.com/rss.xml',
        alternate_uri='http://example.com/'
    )


def test_count_empty_list():
    subs = SubscriptionList()
    assert len(subs) == 0
    subs = SubscriptionList(body=Body())
    assert len(subs) == 0


def test_count_duplicated_url(fx_subscription):
    subs = SubscriptionList()
    subs.add(fx_subscription)
    assert len(subs) == 1
    assert list(subs) == [fx_subscription]
    subs.add(fx_subscription)
    assert len(subs) == 1
    assert list(subs) == [fx_subscription]


def test_count_after_remove(fx_subscription):
    subs = SubscriptionList()
    subs.add(fx_subscription)
    assert len(subs) == 1
    assert list(subs) == [fx_subscription]
    subs.discard(fx_subscription)
    assert not subs
    assert len(subs) == 0
    assert list(subs) == []


XML = b'''
<opml xmlns:e="http://earthreader.org/subscription-list/" version="2.0">
    <head>
        <title>Earth Reader's Subscriptions</title>
        <dateCreated>Sat, 18 Jun 2005 12:11:52 +0000</dateCreated>
        <ownerName>Earth Reader Team</ownerName>
        <ownerEmail>earthreader@librelist.com</ownerEmail>
        <ownerId>http://earthreader.org/</ownerId>
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
        <outline text="test.com" type="rss" xmlUrl="http://test.com/"
                 e:id="2f0bdb1d4987309e304ad0d7f982a37791fb06d4" />
    </body>
</opml>
'''

XML_CATEGORY = b'''
<opml version="2.0">
    <head>
        <title>Earth Reader's Subscriptions</title>
        <dateCreated>Sat, 18 Jun 2005 12:11:52 +0000</dateCreated>
        <ownerName>Earth Reader Team</ownerName>
        <ownerEmail>earthreader@librelist.com</ownerEmail>
        <ownerId>http://earthreader.org/</ownerId>
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
</opml>
'''

XML_DUPLICATION = b'''
<opml version="2.0">
    <head>
        <title>Earth Reader's Subscriptions</title>
        <dateCreated>Sat, 18 Jun 2005 12:11:52 +0000</dateCreated>
        <ownerName>Earth Reader Team</ownerName>
        <ownerEmail>earthreader@librelist.com</ownerEmail>
        <ownerId>http://earthreader.org/</ownerId>
    </head>
    <body>
        <outline text="Duplicated" title="Duplicated" type="category">
            <outline text="dup" title="dup" xmlUrl="http://example.com/" />
            <outline text="dup" title="dup" xmlUrl="http://example.com/" />
        </outline>
        <outline text="Duplicated" title="Duplicated" type="category">
        </outline>
    </body>
</opml>
'''

XML_RECURSIVE = b'''
<opml version="2.0">
    <head>
        <title>Earth Reader's Subscriptions</title>
        <dateCreated>Sat, 18 Jun 2005 12:11:52 +0000</dateCreated>
        <ownerName>Earth Reader Team</ownerName>
        <ownerEmail>earthreader@librelist.com</ownerEmail>
        <ownerId>http://earthreader.org/</ownerId>
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
            <outline text="Riot" title="Riot" type="category">
                <outline text="LOL" title="LOL"
                xmlUrl="http://leagueoflegend.com" />
            </outline>
        </outline>
        <outline text="Music" title="Music" type="category">
            <outline text="capsule" title="capsule"
            xmlUrl="http://www.capsule-web.com/" />
        </outline>
    </body>
</opml>
'''


@fixture
def fx_subscription_list():
    return read(SubscriptionList, [XML])


def test_subscription_list_datetime(fx_subscription_list):
    expected_datetime = datetime(2005, 6, 18, 12, 11, 52, tzinfo=utc)
    assert fx_subscription_list.head.created_at == expected_datetime
    assert fx_subscription_list.head.updated_at is None


def test_subscription_list_title(fx_subscription_list):
    assert fx_subscription_list.head.title == "Earth Reader's Subscriptions"
    assert fx_subscription_list.title == "Earth Reader's Subscriptions"
    fx_subscription_list.title = "Hong Minhee's Subscriptions"
    assert fx_subscription_list.head.title == "Hong Minhee's Subscriptions"


def test_subscription_list_owner(fx_subscription_list):
    assert fx_subscription_list.head.owner_name == 'Earth Reader Team'
    assert (fx_subscription_list.head.owner_email ==
            'earthreader' '@' 'librelist.com')
    assert fx_subscription_list.head.owner_uri == 'http://earthreader.org/'
    assert fx_subscription_list.owner == Person(
        name='Earth Reader Team',
        email='earthreader' '@' 'librelist.com',
        uri='http://earthreader.org/'
    )
    fx_subscription_list.owner = Person(
        name='Hong Minhee',
        email='minhee' '@' 'dahlia.kr',
        uri='http://dahlia.kr/'
    )
    assert fx_subscription_list.head.owner_name == 'Hong Minhee'
    assert fx_subscription_list.head.owner_email == 'minhee' '@' 'dahlia.kr'
    assert fx_subscription_list.head.owner_uri == 'http://dahlia.kr/'
    fx_subscription_list.owner = None
    assert fx_subscription_list.owner is None
    assert fx_subscription_list.head.owner_name is None
    assert fx_subscription_list.head.owner_email is None
    assert fx_subscription_list.head.owner_uri is None


def test_subscription_list_iter(fx_subscription_list):
    assert frozenset(fx_subscription_list) == frozenset([
        Subscription(label='CNET News.com',
                     feed_uri='http://news.com/2547-1_3-0-5.xml'),
        Subscription(label='test.com', feed_uri='http://test.com/')
    ])


def test_subscription_list_update(fx_subscription_list):
    sub = next(iter(fx_subscription_list))
    assert sub.label == 'CNET News.com'
    sub.label = 'updated'
    assert sub.label == 'updated'
    assert next(iter(fx_subscription_list)).label == 'updated'


def test_subscription_feed_id(fx_subscription_list):
    test_com = next(s for s in fx_subscription_list if s.label == 'test.com')
    assert test_com.feed_id == '2f0bdb1d4987309e304ad0d7f982a37791fb06d4'
    cnet = next(s for s in fx_subscription_list if s.label == 'CNET News.com')
    assert cnet.feed_id == '95e2b8d3378bc34d13685583528d616f9b8dce1b'


@fixture
def fx_categorized_subscription_list():
    return read(SubscriptionList, [XML_CATEGORY])


def test_subscription_list_contains_category(fx_categorized_subscription_list):
    subs = fx_categorized_subscription_list
    expected = {
        Category(label='Game'): frozenset([
            Subscription(label='valve', feed_uri='http://valve.com/'),
            Subscription(label='nintendo', feed_uri='http://nintendo.com/')
        ]),
        Category(label='Music'): frozenset([
            Subscription(label='capsule',
                         feed_uri='http://www.capsule-web.com/')
        ])
    }
    assert frozenset(subs) == frozenset(expected)
    for outline in subs:
        print(outline.label)
        assert outline.type == 'category'
        print(list(outline))
        assert frozenset(outline) == expected[outline]


def test_subscription_list_category_update(fx_categorized_subscription_list):
    subs = fx_categorized_subscription_list
    category = next(iter(subs))
    category.add(Subscription(label='added', feed_uri='http://example.com/'))
    assert len(category) == 3
    assert len(next(iter(subs))) == 3


def test_subscription_set_categories_subscriptions():
    subs = SubscriptionList()
    subs.add(Category(label='Category A'))
    subs.add(Subscription(label='Subscription A', feed_uri='http://feeda.com/'))
    subs.add(Category(label='Category B'))
    subs.add(Subscription(label='Subscription B', feed_uri='http://feedb.com/'))
    subs.add(Category(label='Category C'))
    subs.add(Subscription(label='Subscription C', feed_uri='http://feedc.com/'))
    assert subs.categories == {
        'Category A': Category(label='Category A'),
        'Category B': Category(label='Category B'),
        'Category C': Category(label='Category C')
    }
    assert subs.subscriptions == frozenset([
        Subscription(label='Subscription A', feed_uri='http://feeda.com/'),
        Subscription(label='Subscription B', feed_uri='http://feedb.com/'),
        Subscription(label='Subscription C', feed_uri='http://feedc.com/')
    ])


@fixture
def fx_duplicated_subscription_list():
    return read(SubscriptionList, [XML_DUPLICATION])


def test_subscription_set_iter_uniqueness(fx_duplicated_subscription_list):
    assert len(list(fx_duplicated_subscription_list)) == 1
    category = next(iter(fx_duplicated_subscription_list))
    assert len(list(category)) == 1


@fixture
def fx_recursive_subscription_list():
    return read(SubscriptionList, [XML_RECURSIVE])


def test_recursive_subscription_list(fx_recursive_subscription_list):
    assert len(fx_recursive_subscription_list.recursive_subscriptions) == 4
    game_category = fx_recursive_subscription_list.categories['Game']
    assert len(game_category.recursive_subscriptions) == 3


XML_NO_HEAD = b'''
<opml version="2.0">
    <body>
        <outline text="CNET News.com" type="rss" version="RSS2"
            xmlUrl="http://news.com/2547-1_3-0-5.xml"/>
        <outline text="test.com" type="rss" xmlUrl="http://test.com/"/>
    </body>
</opml>
'''


@fixture
def fx_headless_subscription_list():
    return read(SubscriptionList, [XML_NO_HEAD])


def test_no_head(fx_headless_subscription_list):
    subs = fx_headless_subscription_list
    assert subs.owner is None
    assert subs.title is None
    repr(subs)  # should not raise AttributeError


def test_no_head_set_title(fx_headless_subscription_list):
    fx_headless_subscription_list.title = 'Title'
    assert fx_headless_subscription_list.title == 'Title'
    assert fx_headless_subscription_list.head.title == 'Title'


def test_no_head_set_owner(fx_headless_subscription_list):
    owner = Person(
        name='Earth Reader Team',
        email='earthreader' '@' 'librelist.com',
        uri='http://earthreader.org/'
    )
    fx_headless_subscription_list.owner = owner
    assert fx_headless_subscription_list.owner == owner
    assert fx_headless_subscription_list.head.owner_name == owner.name
    assert fx_headless_subscription_list.head.owner_email == owner.email
    assert fx_headless_subscription_list.head.owner_uri == owner.uri


@mark.parametrize('subs', [
    SubscriptionList(),
    Category()
])
def test_subscription_set_subscribe(subs):
    feed = Feed(
        id='urn:earthreader:test:test_subscription_set_subscribe',
        title=Text(value='Feed title')
    )
    feed.links.extend([
        Link(uri='http://example.com/index.xml',
             relation='self',
             mimetype='application/atom+xml'),
        Link(uri='http://example.com/',
             relation='alternate',
             mimetype='text/html')
    ])
    rv = subs.subscribe(feed, icon_uri='http://example.com/favicon.ico')
    sub = next(iter(subs))
    assert rv is sub
    assert sub.feed_id == '0691e2f0c3ea1d7fa9da48e14a46ac8077815ad3'
    assert sub.icon_uri == 'http://example.com/favicon.ico'
    assert sub.label == 'Feed title'
    assert sub.feed_uri == 'http://example.com/index.xml'
    assert sub.alternate_uri == 'http://example.com/'
    assert not sub.deleted_at
    subs.remove(sub)
    assert sub.deleted_at
    assert not subs
    feed.links.append(
        Link(uri='http://example.com/favicon.ico', relation='shortcut icon')
    )
    rv = subs.subscribe(feed)
    first = next(iter(subs))
    assert rv is first
    assert rv == sub


def test_stage_subscription_list(fx_repo, fx_session):
    stage = Stage(fx_session, fx_repo)
    with stage:
        stage.subscriptions = SubscriptionList()
        subs = stage.subscriptions
        subs.add(Category(label='Test'))
        stage.subscriptions = subs
    with stage:
        assert (frozenset(stage.subscriptions) ==
                frozenset([Category(label='Test')]))


def test_subscription_set_contains(fx_recursive_subscription_list,
                                   fx_subscription):
    tree = fx_recursive_subscription_list
    game_c = next(c for c in tree if c.label == 'Game')
    riot_c = next(c for c in game_c if c.label == 'Riot')
    lol_s = next(s for s in riot_c if s.label == 'LOL')
    none_c = Category(label='None')
    assert none_c not in tree
    assert not tree.contains(none_c)
    assert not tree.contains(none_c, recursively=True)
    assert fx_subscription not in tree
    assert not tree.contains(fx_subscription)
    assert not tree.contains(fx_subscription, recursively=True)
    assert lol_s not in tree
    assert not tree.contains(lol_s)
    assert tree.contains(lol_s, recursively=True)
    assert riot_c not in tree
    assert not tree.contains(riot_c)
    assert tree.contains(riot_c, recursively=True)
    assert game_c in tree
    assert tree.contains(game_c)
    assert tree.contains(game_c, recursively=True)


@fixture
def fx_stages():
    repo = MemoryRepository()
    session = Session('SESSID')
    stage = Stage(session, repo)
    other_session = Session('SESSID2')
    other_stage = Stage(other_session, repo)
    return stage, other_stage


def test_remove_subscription(fx_stages, fx_subscription):
    a, b = fx_stages
    with a:
        s = SubscriptionList()
        s.add(fx_subscription)
        a.subscriptions = s
    with a:
        assert fx_subscription in a.subscriptions
    with b:
        assert fx_subscription in b.subscriptions
    added = Subscription(
        label='Added',
        feed_uri='http://example.com/atom.xml',
        alternate_uri='http://example.com/'
    )
    with a:
        a_s = a.subscriptions
        a_s.remove(fx_subscription)
        a.subscriptions = a_s
        with b:
            b_s = b.subscriptions
            b_s.add(added)
            b.subscriptions = b_s
    with a:
        assert added in a.subscriptions
        assert fx_subscription not in a.subscriptions
    with b:
        assert added in b.subscriptions
        assert fx_subscription not in b.subscriptions


def test_remove_category(fx_stages, fx_subscription):
    a, b = fx_stages
    with a:
        s = SubscriptionList()
        c = Category(label='To be deleted')
        c.add(fx_subscription)
        s.add(c)
        a.subscriptions = s
    with a:
        assert c in a.subscriptions
        assert fx_subscription in a.subscriptions.recursive_subscriptions
    with b:
        assert c in b.subscriptions
        assert fx_subscription in b.subscriptions.recursive_subscriptions
    added = Category(label='Added')
    with a:
        a_s = a.subscriptions
        a_s.remove(c)
        a.subscriptions = a_s
        with b:
            b_s = b.subscriptions
            b_s.add(added)
            b.subscriptions = b_s
    with a:
        assert added in a.subscriptions
        assert c not in a.subscriptions
        assert fx_subscription not in a.subscriptions.recursive_subscriptions
    with b:
        assert added in b.subscriptions
        assert c not in b.subscriptions
        assert fx_subscription not in b.subscriptions.recursive_subscriptions
