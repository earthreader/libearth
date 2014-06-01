""":mod:`libearth.subscribe` --- Subscription list
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Maintain the subscription list using OPML_ format, which is de facto standard
for the purpose.

.. _OPML: http://dev.opml.org/spec2.html

"""
import collections
import datetime
import distutils.version
import hashlib

from .codecs import Boolean, Integer, Rfc822
from .compat import string_type, text_type
from .feed import Feed, Person
from .schema import Attribute, Child, Codec, Element, Text
from .session import MergeableDocumentElement
from .tz import now

__all__ = ('Body', 'Category', 'CommaSeparatedList', 'Head', 'Outline',
           'Subscription', 'SubscriptionList', 'SubscriptionSet')


#: (:class:`str`) The XML namespace name used for Earth Reader subscription
#: list metadata.
METADATA_XMLNS = 'http://earthreader.org/subscription-list/'


class CommaSeparatedList(Codec):
    """Encode strings e.g. ``['a', 'b', 'c']`` into a comma-separated list
    e.g. ``'a,b,c'``, and decode it back to a Python list.  Whitespaces
    between commas are ignored.

    >>> codec = CommaSeparatedList()
    >>> codec.encode(['technology', 'business'])
    'technology,business'
    >>> codec.decode('technology, business')
    ['technology', 'business']

    """

    def encode(self, value):
        if value is None:
            res = ""
        elif isinstance(value, text_type):
            res = value
        else:
            res = ",".join(value)
        return res

    def decode(self, text):
        if text is None:
            lst = []
        else:
            lst = [elem.strip() for elem in text.split(',')]
        return lst


class SubscriptionSet(collections.MutableSet):
    """Mixin for :class:`SubscriptionList` and :class:`Category`, both can
    group :class:`Subscription` object and other :class:`Category` objects,
    to implement :class:`collections.MutableSet` protocol.

    """

    @property
    def children(self):
        """(:class:`collections.MutableSequence`) Child :class:`Outline`
         objects.

        .. note::

           Every subclass of :class:`SubscriptionSet` has to override
           :attr:`children` property to implement details.

         """
        raise NotImplementedError(
            'every subclass of {0.__module__}.{0.__name__} has to '
            'implement children property'.format(SubscriptionSet)
        )

    def __len__(self):
        if not self.children:
            return 0
        return sum(not child.deleted for child in self.children)

    def __iter__(self):
        categories = set()
        subscriptions = set()
        for outline in self.children:
            if outline.deleted:
                continue
            elif (outline.type == 'rss' or outline.feed_uri or
                  isinstance(outline, Subscription)):
                if outline.feed_uri in subscriptions:
                    continue
                subscriptions.add(outline.feed_uri)
                if not isinstance(outline, Subscription):
                    if not outline.feed_id:
                        outline.feed_id = hashlib.sha1(
                            outline.feed_uri.encode('utf-8')
                        ).hexdigest()
                    outline.__class__ = Subscription
                    outline._title = outline.label
                yield outline
            elif outline.label in categories:
                continue
            else:
                categories.add(outline.label)
                if not isinstance(outline, Category):
                    outline.__class__ = Category
                    outline._title = outline.label
                yield outline

    def contains(self, outline, recursively=False):
        """Determine whether the set contains the given ``outline``.
        If ``recursively`` is :const:`False` (which is by default)
        it works in the same way to :keyword:`in` operator.

        :param outline: the subscription or category to find
        :type outline: :class:`Outline`
        :param recursively: if it's :const:`True` find the ``outline``
                            in the whole tree, or if :const:`False` find
                            it in only its direct children.
                            :const:`False` by default
        :type recursively: :class:`bool`
        :returns: :const:`True` if the set (or tree) contains the given
                  ``outline``, or :const:`False`
        :rtype: :class:`bool`

        .. versionadded:: 0.2.0

        """
        if not isinstance(outline, Outline):
            raise TypeError('expected an instance of {0.__module__}.'
                            '{0.__name__}, not {1!r}'.format(Outline, outline))
        for child in self.children:
            if outline == child:
                if recursively:
                    return not child.deleted
                elif not child.deleted:
                    return True
        if recursively:
            for subcategory in self:
                if isinstance(subcategory, SubscriptionSet) and \
                   subcategory.contains(outline, recursively=True):
                    return True
        return False

    def __contains__(self, outline):
        try:
            return self.contains(outline, recursively=False)
        except TypeError:
            return False

    def add(self, value):
        if not isinstance(value, Outline):
            raise TypeError('expected {0.__module__}.{0.__name__}, not '
                            '{1!r}'.format(Outline, value))
        if value.type == 'rss' or isinstance(value, Subscription):
            value.type = 'rss'
            for outline in self.children:
                if not (outline.type == 'rss' or
                        isinstance(outline, Subscription)):
                    continue
                if outline.feed_uri == value.feed_uri:
                    outline.created_at = now()
                    return
        else:
            value.type = 'category'
            for outline in self.children:
                if not (outline.type == 'category' or
                        isinstance(outline, Category)):
                    continue
                if outline.label == value.label:
                    outline.created_at = now()
                    return
        value.created_at = now()
        self.children.append(value)

    def discard(self, outline):
        if not isinstance(outline, Outline):
            raise TypeError('expected {0.__module__}.{0.__name__}, not '
                            '{1!r}'.format(Outline, outline))
        deleted_at = now()
        if deleted_at <= outline.created_at:
            deleted_at = (outline.created_at +
                          datetime.timedelta(microseconds=1))  # FIXME
        for child in self.children:
            if child == outline:
                child.deleted_at = deleted_at
                del outline.children[:]
                assert child.deleted

    def subscribe(self, feed, icon_uri=None):
        """Add a subscription from :class:`~libearth.feed.Feed` instance.
        Prefer this method over :meth:`add()` method.

        :param feed: feed to subscribe
        :type feed: :class:`~libearth.feed.Feed`
        :param icon_uri: optional favicon url of the ``feed``
        :type icon_uri: :class:`str`
        :returns: the created subscription object
        :rtype: :class:`Subscription`

        .. versionadded:: 0.3.0
           Optional ``icon_url`` parameter was added.

        """
        if not isinstance(feed, Feed):
            raise TypeError('feed must be an instance of {0.__module__}.'
                            '{0.__name__}, not {1!r}'.format(Feed, feed))
        elif icon_uri is None:
            favicon = feed.links.favicon
            if favicon is not None:
                icon_uri = favicon.uri
        elif not isinstance(icon_uri, string_type):
            raise TypeError('icon_uri must be a string, not ' +
                            repr(icon_uri))
        sub = Subscription(
            feed_id=hashlib.sha1(feed.id.encode('utf-8')).hexdigest(),
            icon_uri=icon_uri,
            label=text_type(feed.title),
            _title=text_type(feed.title),
            feed_uri=next(l.uri for l in feed.links if l.relation == 'self'),
            alternate_uri=next(
                (l.uri for l in feed.links
                 if l.relation == 'alternate' and l.mimetype == 'text/html'),
                None
            ),
            created_at=now()
        )
        for child in self.children:
            if child == sub:
                self.children.remove(child)
        self.children.append(sub)
        return sub

    @property
    def categories(self):
        """(:class:`collections.Mapping`) Label to :class:`Category` instance
        mapping.

        """
        categories = {}
        for child in self:
            if isinstance(child, Category):
                categories[child.label] = child
        return categories

    @property
    def subscriptions(self):
        """(:class:`collections.Set`) The subset which consists of only
        :class:`Subscription` instances.

        """
        return frozenset(e for e in self if isinstance(e, Subscription))

    @property
    def recursive_subscriptions(self):
        subscriptions = set()
        for child in self:
            if isinstance(child, Subscription):
                subscriptions.add(child)
            elif isinstance(child, Category):
                subscriptions.update(child.recursive_subscriptions)
        return subscriptions

    def __merge_entities__(self, other):
        for outline in other.children:
            for child in self.children:
                if child == outline:
                    if type(child) is Outline:
                        child.__class__ = (Subscription
                                           if child.type == 'rss'
                                           else Category)
                        outline._title = outline.label
                    child.created_at = max(child.created_at,
                                           outline.created_at)
                    if not child.deleted_at:
                        child.deleted_at = outline.deleted_at
                    elif outline.deleted_at:
                        child.deleted_at = max(child.deleted_at,
                                               outline.deleted_at)
                    if child.children:
                        if child.deleted:
                            del child.children[:]
                        else:
                            child.__merge_entities__(outline)
                    break
            else:
                self.add(outline)
        return self


class Outline(Element):
    """Represent ``outline`` element of OPML document."""

    #: (:class:`str`) The human-readable text of the outline.
    label = Attribute('text', required=True)

    #: (:class:`str`) Internally-used type identifier.
    type = Attribute('type')

    #: (:class:`datetime.datetime`) The created time.
    created_at = Attribute('created', Rfc822(microseconds=True))

    #: (:class:`datetime.datetime`) The archived time, if deleted ever.
    #: It could be :const:`None` as well if it's never deleted.
    #: Note that it doesn't have enough information about whether
    #: it's actually deleted or not.  For that you have to use
    #: :attr:`deleted` property instead.
    #:
    #: .. versionadded:: 0.3.0
    deleted_at = Attribute(
        'deleted',
        Rfc822(microseconds=True),
        xmlns=METADATA_XMLNS
    )

    feed_uri = Attribute('xmlUrl')
    alternate_uri = Attribute('htmlUrl')
    children = Child('outline', 'Outline', multiple=True)
    feed_id = Attribute('id', xmlns=METADATA_XMLNS)

    _title = Attribute('title')
    _category = Attribute('category', CommaSeparatedList)
    _breakpoint = Attribute('isBreakpoint', Boolean)

    @property
    def deleted(self):
        """(:class:`bool`) Whether it is deleted (archived) or not.

        .. versionadded:: 0.3.0

        """
        return bool(self.deleted_at and self.deleted_at > self.created_at)

    def __eq__(self, other):
        if isinstance(other, Outline):
            if self.type == 'rss':
                return self.feed_uri == other.feed_uri
            return self.label == other.label
        return False

    def __ne__(self, other):
        return not (self == other)

    def __hash__(self):
        if self.type == 'rss':
            return hash(self.feed_uri)
        return hash(self.label)

    def __repr__(self):
        return '<{0.__module__}.{0.__name__} type={1} label={2}{3}>'.format(
            type(self), repr(self.type), repr(self.label),
            ' [deleted]' if self.deleted else ''
        )


class Category(Outline, SubscriptionSet):
    """Category which groups :class:`Subscription` objects or other
    :class:`Category` objects.  It implements :class:`collections.MutableSet`
    protocol.

    .. attribute:: children

       (:class:`collections.MutableSequence`) The list of child :class:`Outline`
       elements.  It's for internal use.

    """

    type = Attribute('type', default=lambda _: 'category')

    def __repr__(self):
        return '<{0.__module__}.{0.__name__} {1!r}{2}>'.format(
            type(self), self.label, ' [deleted]' if self.deleted else ''
        )


class Subscription(Outline):
    """Subscription which holds referring :attr:`feed_uri`.

    .. attribute:: feed_id

       (:class:`str`) The feed identifier to be used for lookup.
       It's intended to be SHA1 digest of :class:`Feed.id
       <libearth.feed.Feed.id>` value (which is UTF-8 encoded).

    .. attribute:: feed_uri

       (:class:`str`) The feed url.

    .. attribute:: alternate_uri

       (:class:`str`) The web page url.

    """

    type = Attribute('type', default=lambda _: 'rss')

    #: (:class:`str`) Optional favicon url.
    #:
    #: .. versionadded:: 0.3.0
    icon_uri = Attribute('icon', xmlns=METADATA_XMLNS, default=lambda _: None)

    def __repr__(self):
        return '<{0.__module__}.{0.__name__} {1} {2!r} ({3!r}){4}>'.format(
            type(self), self.feed_id, self.label, self.feed_uri,
            ' [deleted]' if self.deleted else ''
        )


class Head(Element):
    """Represent ``head`` element of OPML document."""

    #: (:class:`str`) The title of the subscription list.
    title = Text('title')

    #: (:class:`str`) The owner's name.
    owner_name = Text('ownerName')

    #: (:class:`str`) The owner's email.
    owner_email = Text('ownerEmail')

    #: (:class:`str`) The owner's website url.
    owner_uri = Text('ownerId')

    created_at = Text('dateCreated', Rfc822)
    updated_at = Text('dateModified', Rfc822)

    _docs = Text('docs')
    _expansion_state = Text('expansionState', CommaSeparatedList)
    _vert_scroll_state = Text('vertScrollState', Integer)
    _window_top = Text('windowTop', Integer)
    _window_bottom = Text('windowBottom', Integer)
    _window_left = Text('windowLeft', Integer)
    _window_right = Text('windowRight', Integer)


class Body(Element):
    """Represent ``body`` element of OPML document."""

    #: (:class:`collections.MutableSequence`) Child :class:`Outline` objects.
    children = Child('outline', Outline, multiple=True)


class SubscriptionList(MergeableDocumentElement, SubscriptionSet):
    """The set (exactly, tree) of subscriptions.  It consists of
    :class:`Subscription`\ s and :class:`Category` objects for grouping.
    It implements :class:`collections.MutableSet` protocol.

    """

    __tag__ = 'opml'
    head = Child('head', Head)
    body = Child('body', Body)

    #: (:class:`distutils.version.StrictVersion`) The OPML version number.
    version = Attribute(
        'version',
        encoder=str,
        decoder=distutils.version.StrictVersion,
        default=lambda _: distutils.version.StrictVersion('2.0')
    )

    @property
    def children(self):
        if self.body is None:
            self.body = Body()
        return self.body.children

    @property
    def title(self):
        """(:class:`str`) The title of the subscription list."""
        head = self.head
        return head and head.title

    @title.setter
    def title(self, title):
        head = self.head
        if head is None:
            head = Head()
            self.head = head
        head.title = title

    @property
    def owner(self):
        """(:class:`~libearth.feed.Person`) The owner of the subscription
        list.

        """
        head = self.head
        if head is None:
            return
        if head.owner_name is None and head.owner_email is None and \
           head.owner_uri is None:
            return
        return Person(
            name=head.owner_name,
            email=head.owner_email,
            uri=head.owner_uri
        )

    @owner.setter
    def owner(self, owner):
        head = self.head
        if head is None:
            if owner is None:
                return
            head = self.head = Head()
        elif owner is None:
            head.owner_name = head.owner_email = head.owner_uri = None
            return
        head.owner_name = owner.name
        head.owner_email = owner.email
        head.owner_uri = owner.uri

    def __merge_entities__(self, other):
        subs = SubscriptionSet.__merge_entities__(self, other)
        doc = MergeableDocumentElement.__merge_entities__(self, other)
        doc.body = subs.body
        return doc

    def __repr__(self):
        head = self.head
        if head is None:
            return super(SubscriptionList, self).__repr__()
        return '<{0.__module__}.{0.__name__} {1!r} of {2} <{3}>>'.format(
            type(self), head.title, head.owner_name,
            head.owner_email or head.owner_uri
        )
